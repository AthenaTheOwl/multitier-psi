from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtpsi.party import Party
from mtpsi.protocol import (
    assert_leakage_boundary,
    load_dictionary_ids,
    run_dh_based,
    run_fixture_session,
)


def _sweep_is_rejected() -> bool:
    """A party that submits the whole dictionary must fail the boundary."""

    dictionary_path = ROOT / "data" / "canonical_supplier_dict.json"
    honest = Party.from_files(ROOT / "data" / "oem_b_graph.json", dictionary_path)
    sweep = run_dh_based(
        load_dictionary_ids(dictionary_path),
        honest.canonical_spof_ids(),
        party_a="sweeper",
        party_b=honest.party_id,
        seed="fixture-v0",
    )
    try:
        assert_leakage_boundary(sweep)
    except AssertionError:
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dh_based",), default="dh_based")
    args = parser.parse_args(argv)
    result = run_fixture_session(mode=args.mode, seed="fixture-v0")
    assert_leakage_boundary(result)
    print("ok: dh_based transcript reveals only intersection size under the v0 padded transcript model")
    if not _sweep_is_rejected():
        print("error: a query set covering the whole dictionary passed the leakage boundary")
        return 1
    print("ok: a query set covering the dictionary is rejected as a dictionary attack")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
