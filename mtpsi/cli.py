from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .party import Party, validate_supplier_graph, load_json
from .protocol import (
    assert_leakage_boundary,
    run_baseline,
    run_dh_based,
    run_fixture_session,
    validate_session_record,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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
