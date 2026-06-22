from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mtpsi.party import load_json, validate_supplier_graph
from mtpsi.protocol import validate_session_record


def _load_schema(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)


def _validate_jsonl(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                validate_session_record(json.loads(stripped))
            except Exception as exc:
                raise ValueError(f"{path}:{line_number}: invalid session record") from exc


def main() -> int:
    _load_schema(ROOT / "schemas" / "supplier_graph.schema.json")
    _load_schema(ROOT / "schemas" / "psi_session.schema.json")
    validate_supplier_graph(load_json(ROOT / "data" / "oem_a_graph.json"))
    validate_supplier_graph(load_json(ROOT / "data" / "oem_b_graph.json"))
    _validate_jsonl(ROOT / "examples" / "psi-session-baseline.jsonl")
    print("ok: schemas, fixture graphs, and example session parse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
