from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtpsi.protocol import assert_leakage_boundary, run_fixture_session


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("dh_based",), default="dh_based")
    args = parser.parse_args(argv)
    result = run_fixture_session(mode=args.mode, seed="fixture-v0")
    assert_leakage_boundary(result)
    print("ok: dh_based transcript reveals only intersection size under the v0 padded transcript model")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
