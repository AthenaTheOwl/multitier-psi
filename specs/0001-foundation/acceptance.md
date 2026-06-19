# Spec 0001 — Foundation acceptance

## What "v0 done" means

Spec 0001 is closed when:

1. The three PRs in `tasks.md` are merged.
2. `uv pip install -e .[dev]` succeeds on a fresh venv.
3. `python -m mtpsi --help` prints the CLI surface.
4. The two-party worked example runs end to end on localhost and
   reports the expected intersection size.
5. The baseline mode and the dh_based mode return identical
   intersection sizes on the same fixtures.
6. The leakage-bound gate passes for the dh_based mode.
7. All local gates pass.

## Commands to run

```bash
uv pip install -e .[dev]
python -m mtpsi --help

uv run pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py

# Two-party worked example (in two terminals)
python -m mtpsi serve --party A --graph data/oem_a_graph.json \
  --dict data/canonical_supplier_dict.json --mode dh_based --port 7777

python -m mtpsi connect --party B --graph data/oem_b_graph.json \
  --dict data/canonical_supplier_dict.json --mode dh_based \
  --peer localhost:7777

python eval/determinism.py
python eval/leakage_bound.py --mode dh_based
```

## Gates

| Gate | Source | Blocks merge when |
|---|---|---|
| pytest | `tests/` | any test fails |
| voice_lint | `scripts/voice_lint.py` | banned term anywhere |
| schemas | `scripts/validate_schemas.py` | any fixture or session record fails |
| determinism | `eval/determinism.py` | baseline runs diverge under same seed |
| leakage | `eval/leakage_bound.py` | dh_based mode leaks more than intersection size |

## What v0 explicitly does NOT include

- Multi-party PSI.
- Production cryptographic deployment. Use audited libraries.
- TLS or auth.
- Real customer supplier graphs.
- A hosted matching service.
