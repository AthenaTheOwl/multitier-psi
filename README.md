# multitier-psi

Two chipmakers each have a list of suppliers they can't replace. Neither will show
the other its list. Run the intersection and exactly one name comes back — phoenix
substrates in Taiwan, a single source for both — and nothing else crosses the wire.

## What it does

Tier-1 suppliers are visible. The danger lives two and three tiers down, where a
single substrate vendor or one adhesive plant quietly sits under a dozen products
that look unrelated on paper. Two companies can only find the shared chokepoint by
comparing supplier lists, and a supplier list is exactly the thing neither side will
hand over.

multitier-psi runs that comparison without the handover. It maps each party's local
supplier names to agreed canonical ids, walks the tier-2 and tier-3 dependencies to
build each party's single-source set, and intersects the two sets. The dh_based mode
returns only the overlap — the one shared single-source supplier — while each side's
own list stays private. On the committed fixtures, oem_a carries four single-source
suppliers and oem_b carries two; the intersection reveals one and hides the other
five.

It is a reference protocol package and a local testbed, not audited production
crypto. The baseline mode sends plaintext sets and exists only as a test oracle.

## Try it

`show` reads the committed fixtures and prints the ranked shared exposure. Read-only,
offline, no arguments:

```bash
python -m mtpsi show
```

```text
multitier-psi  shared single-source supplier exposure
parties: oem_a x oem_b
single-source ids: oem_a=4  oem_b=2  shared=1

exposure    juris  supplier                   canonical_id             
----------  -----  -------------------------  -------------------------
shared      TW     phoenix substrates taiwan  sup.tw.phoenix-substrates
oem_a only  JP     lens grind japan           sup.jp.lens-grind        
oem_a only  KR     substrate alternate korea  sup.kr.substrate-alt     
oem_a only  US     die adhesive usa           sup.us.die-adhesive      
oem_b only  MY     power ic malaysia          sup.my.power-ic          

finding: 1 supplier(s) are a single source for both parties. top shared exposure: phoenix substrates taiwan (TW, sup.tw.phoenix-substrates).
this is the only fact the dh_based intersection reveals; each party's own single-source list stays private.
committed session 202f13b16cc0 reports intersection_size=1.
```

The `shared` row is the only line the protocol would let one party learn about the
other. The four `oem_a only` and one `oem_b only` rows are shown here because the
fixtures are public; in the real flow they never leave their owner.

## Live demo

A Streamlit page renders the same shared exposure from the same committed data: pick
a slice (shared or per-party), see the ranked supplier table, read the headline
finding.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Deploy on Streamlit Cloud with these settings:

```text
repo: AthenaTheOwl/multitier-psi
branch: main
main file: streamlit_app.py
```

<!-- live-url: (paste the streamlit cloud url here once deployed) -->

## How it connects

multitier-psi is the privacy layer over the supplier graph the other repos draw:

- [chip-supply-chain-map](https://github.com/AthenaTheOwl/chip-supply-chain-map) —
  the public semiconductor supplier graph these tier-2/tier-3 dependencies are shaped
  like.
- [fab-risk-radar](https://github.com/AthenaTheOwl/fab-risk-radar) — scores the
  chokepoints a shared single-source supplier turns into.
- [mcp-security-lab](https://github.com/AthenaTheOwl/mcp-security-lab) /
  [agent-notary-layer](https://github.com/AthenaTheOwl/agent-notary-layer) — the same
  leakage-boundary discipline applied to agents instead of supplier sets.

## Run

```bash
python -m mtpsi validate
python -m mtpsi show
python -m mtpsi run --mode baseline --seed fixture-v0
python -m mtpsi run --mode dh_based --seed fixture-v0
```

Local gates:

```bash
uv run pytest
python scripts/voice_lint.py
python scripts/validate_schemas.py
python eval/determinism.py
python eval/leakage_bound.py
```

## Layout

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

## Security note

Baseline sends plaintext sets. Use it as a test oracle only.

dh_based is a reference mode: a commutative blinding flow with a padded mock
secure-channel transcript for the fixtures. Replace it with an audited two-party PSI
library before any live use.

## Docs

- `PRODUCT_BRIEF.md`
- `SYSTEM_MAP.md`
- `STATUS.md`
- `decisions/DEC-PSI-001-protocol-choice.md`
- `docs/security-disclosure.md`
- `docs/dev/protocol-walkthrough.md`

## License

MIT. See [LICENSE](LICENSE).
