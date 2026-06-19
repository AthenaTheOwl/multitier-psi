# First PR after the scaffold

Branch: `feat/0001-supplier-graph`

## Scope

Land the package skeleton, the supplier-graph schema, the loader,
the canonicalizer, and the two OEM-fixture graphs that PR 2 and PR 3
will exercise.

### Files added

- `pyproject.toml` — declares `mtpsi`, CLI entry
  `mtpsi = "mtpsi.cli:main"`, dev deps (pytest, jsonschema, click,
  cryptography).
- `src/mtpsi/__init__.py` — `__version__ = "0.0.1"`.
- `src/mtpsi/cli.py` — Click app with `version` command.
- `src/mtpsi/graph/__init__.py`
- `src/mtpsi/graph/loader.py` — `load_graph(path)` returning a
  `SupplierGraph`.
- `src/mtpsi/graph/canonicalize.py` —
  `canonicalize(graph, dict_path)` fills `canonical_id` on suppliers.
- `schemas/supplier_graph.schema.json` — per R-PSI-002.
- `data/canonical_supplier_dict.json` — fixture with about 12
  canonical-supplier entries plus aliases.
- `data/oem_a_graph.json` — OEM A's tier-1/2/3 graph. Includes a
  Taiwanese substrate vendor as a tier-2 SPOF.
- `data/oem_b_graph.json` — OEM B's graph. Also depends on the
  same Taiwanese substrate vendor.
- `tests/test_graph_loader.py` — schema validation tests.
- `tests/test_canonicalize.py` — three tests: a known supplier gets
  the right canonical id, an unknown supplier is left blank, an
  alias resolves to its canonical id.
- `decisions/DEC-PSI-001-protocol-choice.md` — names ECDH-based PSI
  per ScienceDirect Jan 2026, lists the alternatives (OPRF-based,
  HE-based) and the swap criteria.

### Files NOT touched

- `src/mtpsi/psi/` — empty until PR 2.
- `src/mtpsi/transport/` — empty until PR 2.
- `src/mtpsi/graph/traverse.py` — empty until PR 2.
- `eval/` — empty until PR 2.

## Verification

```bash
uv pip install -e .[dev]
python -m mtpsi version
# expect: mtpsi 0.0.1

uv run pytest
# expect: 5 tests pass (2 loader + 3 canonicalize)

python -c "
from mtpsi.graph.loader import load_graph
from mtpsi.graph.canonicalize import canonicalize
g = load_graph('data/oem_a_graph.json')
canonicalize(g, 'data/canonical_supplier_dict.json')
print(sum(1 for n in g.nodes if n.canonical_id), 'canonicalized of', len(g.nodes))
"
```

## Out of scope for this PR

- Any PSI protocol code.
- The traverser. Just a schema-validated graph for now.
- Transport sockets.
- voice_lint, leakage_bound, determinism scripts.
