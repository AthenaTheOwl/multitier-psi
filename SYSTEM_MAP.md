# system map

## package

`src/mtpsi/party.py` loads fixture graphs, validates the schema shape, and
maps supplier names to canonical supplier ids.

`src/mtpsi/protocol.py` owns tier traversal, baseline set intersection,
dh_based reference intersection, session records, and the leakage assertion.

`src/mtpsi/cli.py` exposes `python -m mtpsi validate` and `python -m mtpsi run`.

## data

`schemas/supplier_graph.schema.json` defines the supplier graph shape.

`schemas/psi_session.schema.json` defines the committed session record shape.

`data/canonical_supplier_dict.json` holds the fixture dictionary.

`data/oem_a_graph.json` and `data/oem_b_graph.json` are public fixture graphs.

`examples/psi-session-baseline.jsonl` records one deterministic baseline run.

## gates

`scripts/validate_schemas.py` checks schema json, fixture graphs, and example
session records.

`eval/determinism.py` checks seeded baseline determinism.

`eval/leakage_bound.py` checks the dh_based transcript boundary.

`scripts/voice_lint.py` checks the new v0.1 docs for lowercase voice and banned
terms.
