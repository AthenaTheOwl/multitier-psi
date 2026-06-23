from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .party import (
    Party,
    load_canonical_dictionary,
    load_json,
    validate_supplier_graph,
)
from .protocol import (
    assert_leakage_boundary,
    run_baseline,
    run_dh_based,
    run_fixture_session,
    validate_session_record,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _canonical_metadata(dictionary_path: Path) -> dict[str, dict[str, str]]:
    """map canonical_id -> {display_name, jurisdiction} from the committed dictionary."""

    dictionary = load_json(dictionary_path)
    meta: dict[str, dict[str, str]] = {}
    for entry in dictionary.get("entries", []):
        canonical_id = entry.get("canonical_id")
        if not isinstance(canonical_id, str):
            continue
        meta[canonical_id] = {
            "display_name": entry.get("display_name", canonical_id),
            "jurisdiction": entry.get("jurisdiction", "??"),
        }
    return meta


def _read_committed_session(root: Path) -> dict | None:
    """return the first session record from the committed example jsonl, if any."""

    path = root / "examples" / "psi-session-baseline.jsonl"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            return json.loads(stripped)
    return None


def _cmd_show(_args: argparse.Namespace) -> int:
    """read the committed fixtures + session and print a ranked, readable result."""

    root = _repo_root()
    dictionary_path = root / "data" / "canonical_supplier_dict.json"
    graph_a = root / "data" / "oem_a_graph.json"
    graph_b = root / "data" / "oem_b_graph.json"
    if not (dictionary_path.exists() and graph_a.exists() and graph_b.exists()):
        print("no committed fixtures found under data/; nothing to show")
        return 0

    meta = _canonical_metadata(dictionary_path)
    party_a = Party.from_files(graph_a, dictionary_path)
    party_b = Party.from_files(graph_b, dictionary_path)
    a_ids = party_a.canonical_spof_ids()
    b_ids = party_b.canonical_spof_ids()
    shared = sorted(a_ids & b_ids)
    a_only = sorted(a_ids - b_ids)
    b_only = sorted(b_ids - a_ids)

    def _name(canonical_id: str) -> str:
        return meta.get(canonical_id, {}).get("display_name", canonical_id)

    def _juris(canonical_id: str) -> str:
        return meta.get(canonical_id, {}).get("jurisdiction", "??")

    print("multitier-psi  shared single-source supplier exposure")
    print(f"parties: {party_a.party_id} x {party_b.party_id}")
    print(
        f"single-source ids: {party_a.party_id}={len(a_ids)}  "
        f"{party_b.party_id}={len(b_ids)}  shared={len(shared)}"
    )
    print()

    # ranked result: shared exposures first (the finding), then each side's
    # private single-source ids that the intersection does not reveal.
    rows: list[tuple[str, str, str, str]] = []
    for cid in shared:
        rows.append(("shared", _juris(cid).upper(), _name(cid), cid))
    for cid in a_only:
        rows.append((f"{party_a.party_id} only", _juris(cid).upper(), _name(cid), cid))
    for cid in b_only:
        rows.append((f"{party_b.party_id} only", _juris(cid).upper(), _name(cid), cid))

    headers = ("exposure", "juris", "supplier", "canonical_id")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(line)
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    print()

    session = _read_committed_session(root)
    if shared:
        lead = shared[0]
        print(
            f"finding: {len(shared)} supplier(s) are a single source for both "
            f"parties. top shared exposure: {_name(lead)} "
            f"({_juris(lead).upper()}, {lead})."
        )
        print(
            "this is the only fact the dh_based intersection reveals; each party's "
            "own single-source list stays private."
        )
    else:
        print("finding: no shared single-source supplier between the two parties.")
    if session is not None:
        print(
            f"committed session {session['session_id'][:12]} reports "
            f"intersection_size={session['intersection_size']}."
        )
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    party_a = Party.from_files(args.graph_a, args.dictionary)
    party_b = Party.from_files(args.graph_b, args.dictionary)
    a_ids = party_a.canonical_spof_ids()
    b_ids = party_b.canonical_spof_ids()
    if args.mode == "baseline":
        result = run_baseline(a_ids, b_ids, party_a=party_a.party_id, party_b=party_b.party_id, seed=args.seed)
    else:
        result = run_dh_based(a_ids, b_ids, party_a=party_a.party_id, party_b=party_b.party_id, seed=args.seed)
    print(json.dumps(result.session, sort_keys=True))
    return 0


def _parse_jsonl(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                session = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid jsonl") from exc
            validate_session_record(session)


def _cmd_validate(_args: argparse.Namespace) -> int:
    root = _repo_root()
    dictionary_path = root / "data" / "canonical_supplier_dict.json"
    graph_paths = [
        root / "data" / "oem_a_graph.json",
        root / "data" / "oem_b_graph.json",
    ]

    for graph_path in graph_paths:
        validate_supplier_graph(load_json(graph_path))

    party_a = Party.from_files(graph_paths[0], dictionary_path)
    party_b = Party.from_files(graph_paths[1], dictionary_path)
    baseline = run_baseline(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )
    dh_based = run_dh_based(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )
    if baseline.intersection_size != dh_based.intersection_size:
        raise ValueError("baseline and dh_based intersection sizes differ")
    assert_leakage_boundary(dh_based)
    _parse_jsonl(root / "examples" / "psi-session-baseline.jsonl")

    print("ok: fixture graphs valid")
    print(f"ok: baseline and dh_based intersection_size={baseline.intersection_size}")
    print("ok: example session jsonl valid")
    return 0


def build_parser() -> argparse.ArgumentParser:
    root = _repo_root()
    parser = argparse.ArgumentParser(prog="mtpsi")
    subparsers = parser.add_subparsers(dest="command")

    version_parser = subparsers.add_parser("version", help="print package version")
    version_parser.set_defaults(func=_cmd_version)

    validate_parser = subparsers.add_parser("validate", help="validate committed fixtures")
    validate_parser.set_defaults(func=_cmd_validate)

    show_parser = subparsers.add_parser(
        "show", help="print the ranked shared single-source exposure from committed data"
    )
    show_parser.set_defaults(func=_cmd_show)

    run_parser = subparsers.add_parser("run", help="run one fixture or graph pair")
    run_parser.add_argument("--mode", choices=("baseline", "dh_based"), default="baseline")
    run_parser.add_argument("--graph-a", default=str(root / "data" / "oem_a_graph.json"))
    run_parser.add_argument("--graph-b", default=str(root / "data" / "oem_b_graph.json"))
    run_parser.add_argument("--dictionary", default=str(root / "data" / "canonical_supplier_dict.json"))
    run_parser.add_argument("--seed", default=None)
    run_parser.set_defaults(func=_cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))
