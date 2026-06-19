# Spec 0001 — Foundation design

## Shape

A Python CLI plus three layers: a supplier-graph loader plus
canonicalizer, a tier-N traverser, and the PSI protocol itself in
two modes (baseline plaintext for testing, ECDH-based for the
reference implementation).

## Components

### Graph layer (`src/mtpsi/graph/`)

- `loader.py` — reads a JSON supplier graph; validates against
  `schemas/supplier_graph.schema.json`; returns a `SupplierGraph`
  object.
- `canonicalize.py` — given a `SupplierGraph` and the canonical
  dictionary at `data/canonical_supplier_dict.json`, fills in
  `canonical_id` on every supplier node that has a known mapping.
  Nodes without a mapping are excluded from PSI (logged separately).
- `traverse.py` — enumerates SPOFs. A supplier is a SPOF when no
  in-graph substitute path exists for any component it supplies.
  Returns the set of canonical-ids that are SPOFs for the party.

### PSI layer (`src/mtpsi/psi/`)

- `protocol.py` — dataclasses for protocol messages
  (`HelloMessage`, `RoundOneMessage`, `RoundTwoMessage`,
  `IntersectionResultMessage`).
- `baseline.py` — plaintext set-intersection. Both parties send
  their sets in clear; the runtime computes `|A & B|`. For testing
  only.
- `dh_based.py` — ECDH-based PSI:
  - Both parties hash each canonical-id to a curve point.
  - Party A multiplies each point by secret `a`, sends to B.
  - Party B multiplies each received point by secret `b`, returns.
  - Party B multiplies each of its own points by `b`, then by `a`
    (via interaction), and intersects on the doubly-blinded points.
  - Both parties learn the intersection size and (optionally) the
    intersecting canonical-ids.

### Transport (`src/mtpsi/transport/`)

- `sockets.py` — plain TCP sockets for the two-party reference
  runtime. Localhost only in v0; TLS termination is the operator's
  problem outside this repo.

### Leakage gate (`eval/leakage_bound.py`)

Spawns the two-party runtime under a passive adversary that records
all on-wire bytes. Runs the assertion: for the baseline mode the
adversary trivially recovers both sets and the test passes (gating
that baseline is correctly labeled non-secure); for dh_based the
adversary should recover only intersection size and intersecting
canonical-ids.

### Determinism gate (`eval/determinism.py`)

Two consecutive baseline runs against identical fixtures and seed
produce byte-identical `psi_session` records.

## Data model

```
SupplierGraph (per party)
  party_id
  nodes: {brand, tier1_supplier, tier2_supplier, tier3_supplier, component}
  edges: {sources_from, depends_on}

CanonicalSupplierDict
  version
  entries: { canonical_id: { display_name, jurisdiction, aliases[] } }

PsiSession
  session_id, protocol_version
  parties: [ { party_id, set_size_input } ]
  started_at, finished_at
  intersection_size, intersection_canonical_ids?  (optional)
  transcript_hash
```

## Out of scope for spec 0001

- Multi-party (>2) PSI.
- TLS, mutual auth, key management. Operator runs over a trusted
  channel in v0.
- Hosted matching service. Both parties run their own runtime.
- Real customer supplier graphs.
- Production cryptographic deployment. Use audited libraries.
