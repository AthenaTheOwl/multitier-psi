# multitier-psi

private set intersection over public supplier graph fixtures.

this repo is a reference protocol package. it shows how two parties can map
party-local supplier names to agreed canonical ids, traverse tier-2 and tier-3
supplier dependencies, and run a two-party intersection over the resulting
single-source supplier sets.

the package is useful as a local testbed. it is not audited production crypto.

## current behavior

- `mtpsi` python package with `__version__`.
- `python -m mtpsi validate` runs with no arguments.
- supplier graph and psi session schemas.
- canonical supplier dictionary and two public fixture graphs.
- baseline plaintext mode for deterministic tests.
- dh_based reference mode with a padded mock secure-channel transcript.
- local gates for schemas, determinism, leakage boundary, voice, and tests.

the committed fixtures return intersection size 1 in both modes.

## run

```bash
python -m mtpsi validate
python -m mtpsi run --mode baseline --seed fixture-v0
python -m mtpsi run --mode dh_based --seed fixture-v0
```

local gates:

```bash
uv run pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py
python eval/determinism.py
python eval/leakage_bound.py
```

## layout

```text
src/mtpsi/
  cli.py
  party.py
  protocol.py
schemas/
  supplier_graph.schema.json
  psi_session.schema.json
data/
  canonical_supplier_dict.json
  oem_a_graph.json
  oem_b_graph.json
examples/
  psi-session-baseline.jsonl
eval/
  determinism.py
  leakage_bound.py
scripts/
  validate_schemas.py
  voice_lint.py
tests/
  test_protocol.py
```

## security note

baseline sends plaintext sets. use it as a test oracle only.

dh_based is a reference mode. it uses a commutative blinding flow and a padded
mock secure-channel transcript for fixtures. replace it with an audited
two-party psi library before live use.

## docs

- `PRODUCT_BRIEF.md`
- `SYSTEM_MAP.md`
- `STATUS.md`
- `decisions/DEC-PSI-001-protocol-choice.md`
- `docs/security-disclosure.md`
- `docs/dev/protocol-walkthrough.md`
