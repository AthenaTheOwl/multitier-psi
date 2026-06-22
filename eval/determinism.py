from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtpsi.protocol import canonical_json, run_fixture_session


def main() -> int:
    first = run_fixture_session(mode="baseline", seed="fixture-v0").session
    second = run_fixture_session(mode="baseline", seed="fixture-v0").session
    if canonical_json(first) != canonical_json(second):
        print("error: baseline session records diverged")
        return 1
    print("ok: baseline session record is deterministic for seed fixture-v0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
