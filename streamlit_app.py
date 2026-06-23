"""multitier-psi shared single-source exposure browser + live psi runner.

reads the committed supplier-graph fixtures and the example psi session record
directly from disk, then lets the user edit a party's supplier graph and re-run
the REAL psi pipeline (mtpsi.party + mtpsi.protocol) on that input. no network,
no secrets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DICTIONARY = DATA / "canonical_supplier_dict.json"
GRAPH_A = DATA / "oem_a_graph.json"
GRAPH_B = DATA / "oem_b_graph.json"
SESSION = ROOT / "examples" / "psi-session-baseline.jsonl"

# make the real package importable whether installed (wheel from src/) or run
# straight from the repo checkout on streamlit cloud.
for candidate in (ROOT, ROOT / "src"):
    p = str(candidate)
    if candidate.exists() and p not in sys.path:
        sys.path.insert(0, p)

# the real engine. these are the exact functions the cli `run`/`show` verbs drive.
from mtpsi.party import (  # noqa: E402
    GraphValidationError,
    Party,
    canonicalize_graph,
    load_canonical_dictionary,
    validate_supplier_graph,
)
from mtpsi.protocol import (  # noqa: E402
    assert_leakage_boundary,
    enumerate_tier_spofs,
    run_dh_based,
)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_meta(dictionary: dict) -> dict[str, dict[str, str]]:
    meta: dict[str, dict[str, str]] = {}
    for entry in dictionary.get("entries", []):
        cid = entry.get("canonical_id")
        if isinstance(cid, str):
            meta[cid] = {
                "display_name": entry.get("display_name", cid),
                "jurisdiction": entry.get("jurisdiction", "??"),
            }
    return meta


st.set_page_config(page_title="multitier-psi", layout="centered")
st.title("multitier-psi")
st.caption(
    "shared single-source supplier exposure between two oems, computed over "
    "committed supplier-graph fixtures."
)

missing = [p.name for p in (DICTIONARY, GRAPH_A, GRAPH_B) if not p.exists()]
if missing:
    st.warning(f"missing committed data files: {', '.join(missing)}")
    st.stop()

dictionary = _load_json(DICTIONARY)
meta = _canonical_meta(dictionary)
aliases = load_canonical_dictionary(DICTIONARY)
graph_a_raw = _load_json(GRAPH_A)
graph_b_raw = _load_json(GRAPH_B)


def name_of(cid: str) -> str:
    return meta.get(cid, {}).get("display_name", cid)


def juris_of(cid: str) -> str:
    return meta.get(cid, {}).get("jurisdiction", "??").upper()


def spofs_for(raw_graph: dict) -> tuple[str, set[str]]:
    """run the real canonicalize + spof enumeration on a raw graph dict.

    returns (party_id, canonical single-source ids).
    """
    canonical = canonicalize_graph(raw_graph, aliases)
    return canonical["party_id"], enumerate_tier_spofs(canonical)


# ----- committed-artifact view (unchanged behaviour, now via the real engine) -----

party_a, a_ids = spofs_for(graph_a_raw)
party_b, b_ids = spofs_for(graph_b_raw)
shared = sorted(a_ids & b_ids)
a_only = sorted(a_ids - b_ids)
b_only = sorted(b_ids - a_ids)

col1, col2, col3 = st.columns(3)
col1.metric(f"{party_a} single-source ids", len(a_ids))
col2.metric(f"{party_b} single-source ids", len(b_ids))
col3.metric("shared exposure", len(shared))

rows = []
for cid in shared:
    rows.append({"exposure": "shared", "juris": juris_of(cid), "supplier": name_of(cid), "canonical_id": cid})
for cid in a_only:
    rows.append({"exposure": f"{party_a} only", "juris": juris_of(cid), "supplier": name_of(cid), "canonical_id": cid})
for cid in b_only:
    rows.append({"exposure": f"{party_b} only", "juris": juris_of(cid), "supplier": name_of(cid), "canonical_id": cid})

filter_choice = st.radio(
    "show",
    options=["all", "shared only", f"{party_a} only", f"{party_b} only"],
    horizontal=True,
)
if filter_choice == "shared only":
    view = [r for r in rows if r["exposure"] == "shared"]
elif filter_choice == f"{party_a} only":
    view = [r for r in rows if r["exposure"] == f"{party_a} only"]
elif filter_choice == f"{party_b} only":
    view = [r for r in rows if r["exposure"] == f"{party_b} only"]
else:
    view = rows

st.dataframe(view, use_container_width=True, hide_index=True)

if shared:
    lead = shared[0]
    st.info(
        f"finding: {len(shared)} supplier(s) are a single source for both "
        f"{party_a} and {party_b}. top shared exposure: {name_of(lead)} "
        f"({juris_of(lead)}, {lead}). this is the only fact the dh_based "
        f"intersection reveals; each party's own single-source list stays private."
    )
else:
    st.info("finding: no shared single-source supplier between the two parties.")

if SESSION.exists():
    line = next((ln for ln in SESSION.read_text(encoding="utf-8").splitlines() if ln.strip()), None)
    if line:
        session = json.loads(line)
        st.caption(
            f"committed session {session['session_id'][:12]} reports "
            f"intersection_size={session['intersection_size']}. baseline is a "
            "plaintext test oracle; dh_based is a reference mode, not audited "
            "production crypto."
        )


# ----------------------- interactive: run the real psi yourself ----------------------

st.divider()
st.header("run the psi yourself")
st.caption(
    "edit one party's supplier graph below and re-run the REAL pipeline live: "
    "canonicalize_graph -> enumerate_tier_spofs -> run_dh_based. the other party "
    "stays fixed to its committed graph. only the intersection size + the shared "
    "ids you also hold are revealed; the counterparty's private single-source "
    "list never appears in the transcript."
)

st.markdown(
    "a supplier is a **single source** when it is the only canonical supplier at "
    "its tier (2 or 3) for some component. add a second tier-2/3 supplier to a "
    "component to remove an exposure; remove peers to create one. edit the json, "
    "then press **run psi**."
)

counterparty = st.radio(
    "hold this party fixed (committed graph); you edit the other",
    options=[party_b, party_a],
    horizontal=True,
    help="you edit the non-fixed party's graph below.",
)
if counterparty == party_b:
    editable_label, editable_raw = party_a, graph_a_raw
    fixed_label, fixed_raw = party_b, graph_b_raw
else:
    editable_label, editable_raw = party_b, graph_b_raw
    fixed_label, fixed_raw = party_a, graph_a_raw

st.caption(f"editing **{editable_label}** graph; **{fixed_label}** held to its committed graph.")

if "graph_text" not in st.session_state or st.session_state.get("graph_party") != editable_label:
    st.session_state["graph_text"] = json.dumps(editable_raw, indent=2)
    st.session_state["graph_party"] = editable_label

graph_text = st.text_area(
    f"{editable_label} supplier graph (json)",
    key="graph_text",
    height=320,
)

seed = st.text_input(
    "psi seed (deterministic dh_based session)",
    value="streamlit-live",
    help="same seed + same inputs -> reproducible blinding scalars and session.",
)

run = st.button("run psi", type="primary")

if run:
    # 1. parse the user's json
    try:
        user_graph = json.loads(graph_text)
    except json.JSONDecodeError as exc:
        st.error(f"invalid json: {exc}")
        st.stop()

    # 2. drive the REAL validator
    try:
        validate_supplier_graph(user_graph)
    except GraphValidationError as exc:
        st.error(f"graph rejected by validate_supplier_graph: {exc}")
        st.stop()

    # 3. drive the REAL canonicalize + spof enumeration on the edited party
    try:
        edited_party, edited_ids = spofs_for(user_graph)
    except (GraphValidationError, KeyError) as exc:
        st.error(f"engine error on edited graph: {exc}")
        st.stop()

    # fixed counterparty via the same real path
    fixed_party, fixed_ids = spofs_for(fixed_raw)

    # 4. drive the REAL dh_based psi protocol
    if counterparty == party_b:
        result = run_dh_based(
            edited_ids, fixed_ids, party_a=edited_party, party_b=fixed_party, seed=seed
        )
    else:
        result = run_dh_based(
            fixed_ids, edited_ids, party_a=fixed_party, party_b=edited_party, seed=seed
        )

    # the protocol's own leakage check — proves the transcript reveals only size
    leakage_ok = True
    leakage_msg = ""
    try:
        assert_leakage_boundary(result)
    except AssertionError as exc:  # pragma: no cover - defensive
        leakage_ok = False
        leakage_msg = str(exc)

    intersection = list(result.intersection_canonical_ids)

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{edited_party} single-source", len(edited_ids))
    m2.metric(f"{fixed_party} single-source", len(fixed_ids))
    m3.metric("shared (intersection)", result.intersection_size)

    if intersection:
        st.error(
            f"{result.intersection_size} shared single-source exposure(s): "
            + ", ".join(f"{name_of(c)} ({juris_of(c)})" for c in intersection)
        )
    else:
        st.success("no shared single-source supplier — no joint exposure on this run.")

    st.markdown(f"**{edited_party} single-source ids you control**")
    st.dataframe(
        [{"juris": juris_of(c), "supplier": name_of(c), "canonical_id": c} for c in sorted(edited_ids)]
        or [{"juris": "", "supplier": "(none)", "canonical_id": ""}],
        use_container_width=True,
        hide_index=True,
    )

    if leakage_ok:
        st.caption(
            "leakage check passed (assert_leakage_boundary): the dh_based transcript "
            "below carries no canonical supplier ids — only the intersection size is "
            f"revealed. {fixed_party}'s private single-source list never appears."
        )
    else:
        st.warning(f"leakage boundary failed: {leakage_msg}")

    with st.expander("session record (the only audit artifact the protocol emits)"):
        st.json(result.session)
    with st.expander("dh_based transcript (opaque payloads + size reveal)"):
        st.json(result.transcript)
