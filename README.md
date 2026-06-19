# MultiTierPSI

Private Set Intersection on supplier graphs. Two brands run a
cryptographic intersection of their tier-2 and tier-3 supplier
dependencies and learn only "do we share single-point-of-failure
suppliers, and how many," without revealing supplier lists.

## What this is

Post-COVID and post-Ukraine, shared-SPOF discovery is a board-level
question at every concentrated supply chain (auto OEMs, smartphone
OEMs, defense primes, pharma). Brands cannot share supplier lists
(competitive risk, legal risk) but desperately want the answer. PSI
primitives are now production-ready (Google, Signal already deploy
them at scale).

MultiTierPSI fuses the PSI primitive with a supplier-graph schema
borrowed from chip-supply-chain-map. The generic PSI library is
commodity; the procurement-relevant schema, the tier-N traversal
rules, and the worked Tier-2 datasets are not.

The first artifact is an open-source PSI runtime plus a
supplier-graph schema plus a worked example: OEM A and OEM B
discover that they share a single Taiwanese substrate vendor as a
tier-2 dependency, without revealing the size of either supplier
list.

Buyers: chief procurement officers and supply-chain risk leads at
competing brands in concentrated supply chains. Defense-industrial
buyers in particular.

## Status

v0 scaffold. No implementation. The repo holds the README, the
license, the agents contract, the foundation spec, and the literal
first PR plan. The first runnable PR after this scaffold lands the
supplier-graph schema and a deterministic baseline-intersection (not
yet cryptographic) the PSI implementation can be tested against.

## How to run

Placeholder. After implementation lands:

```bash
uv run mtpsi serve --party A --graph data/oem_a_graph.json --port 7777
uv run mtpsi connect --party B --graph data/oem_b_graph.json --peer localhost:7777
# Both sides print: "Shared tier-2 SPOFs: 3"
```

## Layout

```
multitier-psi/
  README.md
  LICENSE
  AGENTS.md
  .gitignore
  specs/
    0001-foundation/
      requirements.md          # R-PSI-NNN
      design.md
      tasks.md
      acceptance.md
  docs/
    first-pr.md
```

Downstream additions:

```
  src/mtpsi/
    graph/loader.py
    graph/canonicalize.py        # produces stable supplier ids both parties agree on
    graph/traverse.py            # tier-N traversal
    psi/baseline.py              # plaintext baseline for testing
    psi/dh_based.py              # ECDH-based PSI per ScienceDirect Jan 2026
    psi/protocol.py              # protocol message types
    transport/sockets.py
    cli.py
  schemas/
    supplier_graph.schema.json
    psi_session.schema.json
    intersection_result.schema.json
  data/
    oem_a_graph.json             # worked-example fixtures
    oem_b_graph.json
    canonical_supplier_dict.json
  eval/
    leakage_bound.py             # asserts protocol leaks only intersection size
    determinism.py
```

## Security note

The PSI primitive is a research-grade reference implementation in
v0. It is not a substitute for an audited cryptographic deployment.
The leakage-bound proof lands in spec 0002.

## License

MIT. See [LICENSE](LICENSE).
