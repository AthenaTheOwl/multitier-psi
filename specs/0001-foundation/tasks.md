# Spec 0001 — Foundation tasks

Ordered task list for the first 2-3 PRs after the scaffold.

## PR 1 — package skeleton plus supplier graph schema

- [ ] Add `pyproject.toml` declaring `mtpsi` and CLI entry.
- [ ] Add `src/mtpsi/__init__.py` with `__version__`.
- [ ] Add `src/mtpsi/cli.py` with no-op `version` command.
- [ ] Add `schemas/supplier_graph.schema.json` matching R-PSI-002.
- [ ] Add `src/mtpsi/graph/loader.py`.
- [ ] Add `src/mtpsi/graph/canonicalize.py`.
- [ ] Add seed `data/canonical_supplier_dict.json` (small fixture).
- [ ] Add fixtures `data/oem_a_graph.json`, `data/oem_b_graph.json`
      (constructed to share at least one tier-2 supplier).
- [ ] Add `tests/test_graph_loader.py`,
      `tests/test_canonicalize.py`.
- [ ] Add `decisions/DEC-PSI-001-protocol-choice.md`.

## PR 2 — traverser plus baseline PSI

- [ ] Add `src/mtpsi/graph/traverse.py` returning the SPOF set.
- [ ] Add `tests/test_traverse.py` against the OEM fixtures.
- [ ] Add `src/mtpsi/psi/protocol.py`.
- [ ] Add `src/mtpsi/psi/baseline.py`.
- [ ] Add `schemas/psi_session.schema.json`,
      `schemas/intersection_result.schema.json`.
- [ ] Add `src/mtpsi/transport/sockets.py`.
- [ ] Add `tests/test_baseline_psi.py` running the two-party
      interaction over localhost sockets against the OEM fixtures
      and asserting intersection size = 1 (or whatever the fixture
      sets).
- [ ] Add `eval/determinism.py`.
- [ ] Add `scripts/voice_lint.py`,
      `scripts/validate_schemas.py`.

## PR 3 — ECDH-based PSI plus leakage gate

- [ ] Add `src/mtpsi/psi/dh_based.py`.
- [ ] Add `tests/test_dh_based_psi.py` asserting agreement with
      baseline on the same fixtures.
- [ ] Add `eval/leakage_bound.py` running the passive-adversary
      assertion.
- [ ] Add `docs/dev/protocol-walkthrough.md`.
- [ ] Add `docs/security-disclosure.md` stating the v0
      reference-implementation status.
