# Spec 0001 — Foundation requirements

The first spec for MultiTierPSI. Names the supplier-graph schema,
the canonical-id dictionary, the PSI protocol contract, the leakage
bound, and the worked example.

## Requirements

- **R-PSI-001** — The repo MUST expose an `mtpsi` Python package
  with `__version__` and a CLI entry point.

- **R-PSI-002** — A supplier graph MUST conform to
  `schemas/supplier_graph.schema.json` with node types
  `{brand, tier1_supplier, tier2_supplier, tier3_supplier, component}`
  and edge types `{sources_from, depends_on}`. Each node carries a
  `party_local_id` and an optional `canonical_id` field.

- **R-PSI-003** — A canonical supplier dictionary at
  `data/canonical_supplier_dict.json` MUST map party-local supplier
  names to stable canonical ids. Both parties consult the same
  dictionary version before running PSI.

- **R-PSI-004** — The tier-N traversal MUST enumerate, for each
  party, the set of canonical supplier ids that are
  single-points-of-failure (no in-graph substitute). This set is the
  PSI input.

- **R-PSI-005** — A PSI session MUST conform to
  `schemas/psi_session.schema.json` with fields: `session_id`,
  `protocol_version`, `parties` (two entries), `started_at`,
  `finished_at`, `intersection_size`, `transcript_hash`.

- **R-PSI-006** — The PSI implementation MUST provide two modes:
  `baseline` (plaintext set-intersection for testing) and `dh_based`
  (ECDH-based PSI per the published primitive). Both return
  identical intersection sizes against the same inputs.

- **R-PSI-007** — The leakage gate MUST run a passive adversary that
  records all on-wire messages and run an assertion that no extra
  bit of either party's input set is recoverable beyond
  intersection size.

- **R-PSI-008** — Determinism: given identical inputs and an explicit
  seed, two `baseline` runs MUST produce byte-identical session
  records. The `dh_based` mode is non-deterministic on transcript by
  construction, but the intersection-size output MUST be
  deterministic.

- **R-PSI-009** — The worked example MUST include two fixture
  supplier graphs (`data/oem_a_graph.json`, `data/oem_b_graph.json`)
  that share at least one canonical tier-2 supplier and produce a
  non-zero intersection size.

- **R-PSI-010** — All documentation MUST disclose that the v0
  cryptographic implementation is a reference, not an audited
  deployment.

- **R-PSI-011** — No network or live cryptographic libraries beyond
  Python stdlib and `cryptography` package. No accidental dependency
  on a private repository or paid service.

- **R-PSI-012** — The repo MUST include
  `decisions/DEC-PSI-001-protocol-choice.md` documenting why
  ECDH-based PSI is chosen for the reference and what would need to
  change to swap in OPRF-based or HE-based PSI later.
