# AGENTS.md — multitier-psi

Operating contract for AI agents (Claude, Codex, Cursor) working in
this repo. Same conventions as the rest of the AthenaTheOwl
portfolio. An agent trained on chip-supply-chain-map will recognize
the supplier-graph shape.

## What this repo is

A Private Set Intersection runtime tuned for supplier-graph
problems. The PSI primitive itself is borrowed from public research
(ECDH-based PSI per the ScienceDirect Jan 2026 paper). The novelty
is the supplier-graph schema, the tier-N traversal preprocessing,
and the canonical-supplier-id dictionary that lets two parties run
the intersection over agreed-on identifiers.

## Roles you may see in tasks

| Role | What they do |
|---|---|
| `graph-loader` | Reads a per-party supplier graph; validates against schema |
| `canonicalizer` | Maps party-local supplier names to canonical supplier ids |
| `traverser` | Walks tier-N relationships to enumerate the per-party SPOF set |
| `psi-protocol` | Runs the cryptographic intersection over the two SPOF sets |
| `leakage-auditor` | Gate: asserts only intersection size leaks |
| `transport` | Carries protocol messages between the two parties |

## Voice constraints

- Plain assertions. No marketing words. The banned set lands in
  `scripts/voice_lint.py::BANNED_FAIL` in spec 0002.
- No antithetical reversals as a structural device.
- Security claims are conditional. The v0 PSI implementation is a
  reference, not a deployment. Documentation must say so.

## Gates (will land in spec 0002)

```bash
uv run pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py
python eval/leakage_bound.py
python eval/determinism.py
```

The leakage-bound gate runs an adversary that records all on-wire
messages and asserts the adversary cannot recover more than the
intersection size.

## Out of scope

- Multi-party PSI (only two-party in v0).
- Hosted matching service. Both parties run their own runtime in v0.
- Production-grade cryptographic deployment. Use an audited PSI
  library (Google PSI, Microsoft APSI) for production.
- Real customer supplier graphs. Public fixtures only in this repo.
