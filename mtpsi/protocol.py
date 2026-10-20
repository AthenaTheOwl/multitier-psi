from __future__ import annotations

import argparse
import hashlib
import json
import random
import secrets
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .party import SUPPLIER_TYPES, validate_supplier_graph

PROTOCOL_VERSION = "0.1"
DEFAULT_PADDED_TRANSCRIPT_SIZE = 8

# Dictionary attack bound. PSI reveals which of a party's own ids the other
# side also holds, so a party that submits the whole public dictionary learns
# the other side's whole set: the intersection becomes a lookup. A party sees
# the size of the other side's blinded set but not its contents, so the bound
# is on size: a query set may hold at most this fraction of the agreed
# dictionary, and must leave at least one entry out. With the 5-entry fixture
# dictionary that is 4 ids. This stops the full sweep only; it does not stop
# a party splitting the sweep across sessions. See docs/security-disclosure.md.
MAX_QUERY_FRACTION = 0.8

# RFC 3526 group 14: the 2048-bit MODP safe prime p = 2q + 1, q prime. The
# quadratic residues mod p are the subgroup of prime order q. Identifiers are
# hashed into that subgroup and secrets are drawn from [1, q - 1], so every
# blinded value is a residue: it carries no Legendre-symbol bit (or any other
# small-subgroup bit) about the identifier or the secret. The previous group,
# Z_p* with p = 2^255 - 19, has p - 1 divisible by 4, 3 and 65147, so its
# blinded values leaked the quadratic-residue bit of each hashed id.
GROUP_NAME = "rfc3526-modp-2048/prime-order-subgroup"
GROUP_P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A0879"
    "8E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B"
    "0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA4836"
    "1C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804"
    "F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6"
    "955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16,
)
GROUP_Q = (GROUP_P - 1) // 2


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def hash_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _supplier_tier(node_type: str) -> int | None:
    if node_type == "tier1_supplier":
        return 1
    if node_type == "tier2_supplier":
        return 2
    if node_type == "tier3_supplier":
        return 3
    return None


def enumerate_tier_spofs(
    graph: dict[str, Any],
    tiers: tuple[int, ...] = (2, 3),
) -> set[str]:
    """return canonical supplier ids that have no peer at the same tier for a component."""

    validate_supplier_graph(graph)
    node_by_id = {node["node_id"]: node for node in graph["nodes"]}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in graph["edges"]:
        outgoing[edge["from"]].append(edge["to"])

    component_ids = [
        node["node_id"] for node in graph["nodes"] if node["type"] == "component"
    ]
    spofs: set[str] = set()

    for component_id in component_ids:
        seen_paths: set[tuple[str, int]] = set()
        tier_to_ids: dict[int, set[str]] = defaultdict(set)
        stack: list[tuple[str, int]] = [(component_id, 0)]

        while stack:
            node_id, depth = stack.pop()
            if (node_id, depth) in seen_paths:
                continue
            seen_paths.add((node_id, depth))

            node = node_by_id[node_id]
            tier = _supplier_tier(node["type"])
            if tier in tiers and node.get("canonical_id"):
                tier_to_ids[tier].add(node["canonical_id"])
            if depth >= max(tiers) + 1:
                continue
            for target_id in outgoing.get(node_id, []):
                target = node_by_id[target_id]
                if target["type"] in SUPPLIER_TYPES:
                    stack.append((target_id, depth + 1))

        for tier in tiers:
            canonical_ids = tier_to_ids.get(tier, set())
            if len(canonical_ids) == 1:
                spofs.update(canonical_ids)

    return spofs


@dataclass(frozen=True)
class ProtocolResult:
    mode: str
    session: dict[str, Any]
    transcript: list[dict[str, Any]]
    intersection_canonical_ids: tuple[str, ...]
    # each party's query-set size, which the other party sees in a real run
    input_sizes: tuple[int, int] = (0, 0)

    @property
    def intersection_size(self) -> int:
        return int(self.session["intersection_size"])


def _session_record(
    *,
    session_id: str,
    parties: tuple[str, str],
    started_at: str,
    finished_at: str,
    intersection_size: int,
    transcript: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "protocol_version": PROTOCOL_VERSION,
        "parties": [{"party_id": parties[0]}, {"party_id": parties[1]}],
        "started_at": started_at,
        "finished_at": finished_at,
        "intersection_size": intersection_size,
        "transcript_hash": hash_json(transcript),
    }


def run_baseline(
    a_ids: Iterable[str],
    b_ids: Iterable[str],
    *,
    party_a: str = "oem_a",
    party_b: str = "oem_b",
    seed: str | None = None,
) -> ProtocolResult:
    a_sorted = sorted(set(a_ids))
    b_sorted = sorted(set(b_ids))
    intersection = tuple(sorted(set(a_sorted) & set(b_sorted)))

    if seed is None:
        session_id = secrets.token_hex(16)
        started_at = _now()
        finished_at = started_at
    else:
        seed_material = {"seed": seed, "a": a_sorted, "b": b_sorted, "mode": "baseline"}
        session_id = hashlib.sha256(canonical_json(seed_material).encode("utf-8")).hexdigest()[:32]
        started_at = "1970-01-01T00:00:00Z"
        finished_at = "1970-01-01T00:00:00Z"

    transcript = [
        {
            "phase": "baseline_plaintext_exchange",
            "party_a_ids": a_sorted,
            "party_b_ids": b_sorted,
        },
        {
            "phase": "result",
            "intersection_size": len(intersection),
        },
    ]
    session = _session_record(
        session_id=session_id,
        parties=(party_a, party_b),
        started_at=started_at,
        finished_at=finished_at,
        intersection_size=len(intersection),
        transcript=transcript,
    )
    return ProtocolResult("baseline", session, transcript, intersection, (len(a_sorted), len(b_sorted)))


def _jacobi(a: int, n: int) -> int:
    """Jacobi symbol (a/n) for odd n > 0; the Legendre symbol when n is prime."""

    a %= n
    result = 1
    while a:
        while a % 2 == 0:
            a //= 2
            if n % 8 in (3, 5):
                result = -result
        a, n = n, a
        if a % 4 == 3 and n % 4 == 3:
            result = -result
        a %= n
    return result if n == 1 else 0


def in_prime_order_subgroup(value: int) -> bool:
    """True when value is a non-identity element of the order-q subgroup.

    For a safe prime that subgroup is exactly the quadratic residues, so the
    Legendre symbol decides membership without a full-size exponentiation.
    """

    return 1 < value < GROUP_P and _jacobi(value, GROUP_P) == 1


def hash_to_group(identifier: str) -> int:
    """Hash an identifier to a non-identity element of the order-q subgroup.

    SHA-512 is expanded to 2176 bits so the reduction mod p is close to
    uniform, then squared, which lands in the quadratic residues.
    """

    counter = 0
    while True:
        blocks = (
            hashlib.sha512(f"mtpsi-h2g|{counter}|{block}|{identifier}".encode("utf-8")).digest()
            for block in range(5)
        )
        element = pow(int.from_bytes(b"".join(blocks)[:272], "big") % GROUP_P, 2, GROUP_P)
        if element > 1:
            return element
        counter += 1


def _blind(identifier: str, scalar: int) -> int:
    return pow(hash_to_group(identifier), scalar, GROUP_P)


def _blind_value(value: int, scalar: int) -> int:
    # a received element outside the subgroup could carry a small-order
    # component that the reply would echo back; refuse it
    if not in_prime_order_subgroup(value):
        raise ValueError("received element is not in the prime-order subgroup")
    return pow(value, scalar, GROUP_P)


def _token(value: int) -> str:
    return hashlib.sha256(str(value).encode("ascii")).hexdigest()


def _fixture_rng(seed: str, stream: str) -> random.Random:
    """One seeded stream per role, for the deterministic fixture mode only.

    The seed is public (it is in the README run command), so anything drawn
    here is public too. Each party and the transcript padding get their own
    stream, so no party's secret is a later draw of another party's stream.
    """

    material = hashlib.sha256(f"mtpsi-fixture|{stream}|{seed}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(material, "big"))


def _party_secret(seed: str | None, role: str) -> int:
    """Draw one party's blinding secret.

    Real mode (no seed) asks the OS CSPRNG through ``secrets`` once per party,
    so the two secrets are independent. A seed selects the fixture mode, where
    each role reads its own derived stream.
    """

    if seed is None:
        return 1 + secrets.randbelow(GROUP_Q - 1)
    return _fixture_rng(seed, f"party-{role}").randrange(1, GROUP_Q)


def _pad_tokens(tokens: list[str], *, pad_to: int, rng: random.Random) -> list[str]:
    padded = list(tokens)
    while len(padded) < pad_to:
        padded.append(hashlib.sha256(f"pad:{rng.random()}".encode("ascii")).hexdigest())
    rng.shuffle(padded)
    return padded


def run_dh_based(
    a_ids: Iterable[str],
    b_ids: Iterable[str],
    *,
    party_a: str = "oem_a",
    party_b: str = "oem_b",
    pad_to: int = DEFAULT_PADDED_TRANSCRIPT_SIZE,
    seed: str | None = None,
) -> ProtocolResult:
    a_sorted = sorted(set(a_ids))
    b_sorted = sorted(set(b_ids))
    # each party holds its own secret; neither is derived from the other's stream
    a_secret = _party_secret(seed, "a")
    b_secret = _party_secret(seed, "b")
    rng = random.SystemRandom() if seed is None else _fixture_rng(seed, "transcript-padding")
    padded_size = max(pad_to, len(a_sorted), len(b_sorted))

    a_once = {identifier: _blind(identifier, a_secret) for identifier in a_sorted}
    b_once = {identifier: _blind(identifier, b_secret) for identifier in b_sorted}
    a_twice_from_b = {
        identifier: _token(_blind_value(value, a_secret))
        for identifier, value in b_once.items()
    }
    b_twice_from_a = {
        identifier: _token(_blind_value(value, b_secret))
        for identifier, value in a_once.items()
    }
    common_tokens = set(a_twice_from_b.values()) & set(b_twice_from_a.values())
    intersection = tuple(
        sorted(
            identifier
            for identifier, token in a_twice_from_b.items()
            if token in common_tokens
        )
    )

    round_one_tokens = [_token(value) for value in a_once.values()]
    round_two_tokens = [_token(value) for value in b_once.values()]
    transcript = [
        {
            "phase": "secure_channel_open",
            "payload": "opaque",
            "group": GROUP_NAME,
            "padding_policy": f"fixed_min_{pad_to}",
        },
        {
            "phase": "encrypted_round_one",
            "payload_hash": hash_json(_pad_tokens(round_one_tokens, pad_to=padded_size, rng=rng)),
            "payload_slots": padded_size,
        },
        {
            "phase": "encrypted_round_two",
            "payload_hash": hash_json(_pad_tokens(round_two_tokens, pad_to=padded_size, rng=rng)),
            "payload_slots": padded_size,
        },
        {
            "phase": "result",
            "intersection_size": len(intersection),
        },
    ]
    started_at = _now()
    session_id = secrets.token_hex(16)
    session = _session_record(
        session_id=session_id,
        parties=(party_a, party_b),
        started_at=started_at,
        finished_at=started_at,
        intersection_size=len(intersection),
        transcript=transcript,
    )
    return ProtocolResult("dh_based", session, transcript, intersection, (len(a_sorted), len(b_sorted)))


def load_dictionary_ids(path: str | Path | None = None) -> list[str]:
    """Canonical ids in a supplier dictionary (default: the committed one)."""

    dictionary_path = Path(path) if path else repo_root() / "data" / "canonical_supplier_dict.json"
    data = json.loads(dictionary_path.read_text(encoding="utf-8"))
    return [entry["canonical_id"] for entry in data.get("entries", []) if isinstance(entry, dict)]


def max_query_set_size(dictionary_size: int, fraction: float = MAX_QUERY_FRACTION) -> int:
    """Largest query set a party may submit against a dictionary of this size."""

    return max(0, min(dictionary_size - 1, int(dictionary_size * fraction)))


def assert_leakage_boundary(
    result: ProtocolResult,
    *,
    dictionary_size: int | None = None,
    max_query_fraction: float = MAX_QUERY_FRACTION,
) -> None:
    """Check the dh_based run reveals only the intersection, and only to an honest-sized query.

    ``dictionary_size`` defaults to the committed canonical dictionary.
    """

    if result.mode != "dh_based":
        raise AssertionError("leakage boundary applies to dh_based mode only")
    encoded = canonical_json(result.transcript)
    for identifier in result.intersection_canonical_ids:
        if identifier in encoded:
            raise AssertionError("dh_based transcript contains canonical supplier ids")
    allowed_reveals = [
        message for message in result.transcript if message.get("phase") == "result"
    ]
    if allowed_reveals != [{"phase": "result", "intersection_size": result.intersection_size}]:
        raise AssertionError("dh_based transcript reveals more than intersection size")
    size = len(load_dictionary_ids()) if dictionary_size is None else dictionary_size
    limit = max_query_set_size(size, max_query_fraction)
    for party, submitted in zip(result.session["parties"], result.input_sizes):
        if submitted > limit:
            raise AssertionError(
                f"dictionary attack: {party['party_id']} submitted {submitted} ids against a "
                f"{size}-entry dictionary (limit {limit}); a query set that covers the "
                "dictionary returns the other party's whole set"
            )


def validate_session_record(session: dict[str, Any]) -> None:
    required = {
        "session_id",
        "protocol_version",
        "parties",
        "started_at",
        "finished_at",
        "intersection_size",
        "transcript_hash",
    }
    missing = required - set(session)
    if missing:
        raise ValueError(f"session missing required fields: {sorted(missing)}")
    if session["protocol_version"] != PROTOCOL_VERSION:
        raise ValueError("protocol_version mismatch")
    if not isinstance(session["parties"], list) or len(session["parties"]) != 2:
        raise ValueError("parties must contain two entries")
    if not isinstance(session["intersection_size"], int) or session["intersection_size"] < 0:
        raise ValueError("intersection_size must be a non-negative integer")
    if not isinstance(session["transcript_hash"], str) or len(session["transcript_hash"]) != 64:
        raise ValueError("transcript_hash must be a sha256 hex digest")


def run_fixture_session(*, mode: str, seed: str | None = None) -> ProtocolResult:
    from .party import Party

    root = repo_root()
    dictionary_path = root / "data" / "canonical_supplier_dict.json"
    party_a = Party.from_files(root / "data" / "oem_a_graph.json", dictionary_path)
    party_b = Party.from_files(root / "data" / "oem_b_graph.json", dictionary_path)
    a_ids = party_a.canonical_spof_ids()
    b_ids = party_b.canonical_spof_ids()
    if mode == "baseline":
        return run_baseline(a_ids, b_ids, party_a=party_a.party_id, party_b=party_b.party_id, seed=seed)
    if mode == "dh_based":
        return run_dh_based(a_ids, b_ids, party_a=party_a.party_id, party_b=party_b.party_id, seed=seed)
    raise argparse.ArgumentTypeError("mode must be baseline or dh_based")
