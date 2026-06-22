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
DH_PRIME = (2**255) - 19
DH_GENERATOR_FALLBACK = 5
DEFAULT_PADDED_TRANSCRIPT_SIZE = 8


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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
    return ProtocolResult("baseline", session, transcript, intersection)


def _id_to_group_value(identifier: str) -> int:
    digest = hashlib.sha256(identifier.encode("utf-8")).digest()
    value = int.from_bytes(digest, "big") % DH_PRIME
    return value or DH_GENERATOR_FALLBACK


def _blind(identifier: str, scalar: int) -> int:
    return pow(_id_to_group_value(identifier), scalar, DH_PRIME)


def _blind_value(value: int, scalar: int) -> int:
    return pow(value, scalar, DH_PRIME)


def _token(value: int) -> str:
    return hashlib.sha256(str(value).encode("ascii")).hexdigest()


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
    rng = random.Random(seed) if seed is not None else random.Random(secrets.randbits(128))
    a_secret = rng.randrange(2, DH_PRIME - 2)
    b_secret = rng.randrange(2, DH_PRIME - 2)
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
    return ProtocolResult("dh_based", session, transcript, intersection)


def assert_leakage_boundary(result: ProtocolResult) -> None:
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
