"""multitier-psi shared single-source exposure browser.

reads the committed supplier-graph fixtures and the example psi session record
directly from disk (paths relative to this file). no network, no secrets.
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DICTIONARY = DATA / "canonical_supplier_dict.json"
GRAPH_A = DATA / "oem_a_graph.json"
GRAPH_B = DATA / "oem_b_graph.json"
SESSION = ROOT / "examples" / "psi-session-baseline.jsonl"


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


SUPPLIER_TYPES = {"tier1_supplier", "tier2_supplier", "tier3_supplier"}


def _norm(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").replace("-", " ").split())


def _aliases(dictionary: dict) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for entry in dictionary.get("entries", []):
        cid = entry.get("canonical_id")
        if not isinstance(cid, str):
            continue
        aliases[_norm(entry.get("display_name", ""))] = cid
        for alias in entry.get("aliases", []):
            if isinstance(alias, str) and alias.strip():
                aliases[_norm(alias)] = cid
    return aliases


def _canonical_spof_ids(graph: dict, aliases: dict[str, str]) -> set[str]:
    """tier-2/3 suppliers that are the single source for a component.

    mirrors mtpsi.protocol.enumerate_tier_spofs over the committed fixtures.
    """

    from collections import defaultdict

    node_by_id = {n["node_id"]: n for n in graph["nodes"]}

    def canonical_of(node: dict) -> str | None:
        if node.get("canonical_id"):
            return node["canonical_id"]
        for candidate in (node.get("display_name", ""), node.get("party_local_id", "")):
            cid = aliases.get(_norm(candidate))
            if cid:
                return cid
        return None

    def tier(node_type: str) -> int | None:
        return {"tier1_supplier": 1, "tier2_supplier": 2, "tier3_supplier": 3}.get(node_type)

    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in graph["edges"]:
        outgoing[edge["from"]].append(edge["to"])

    component_ids = [n["node_id"] for n in graph["nodes"] if n["type"] == "component"]
    spofs: set[str] = set()
    for component_id in component_ids:
        seen: set[tuple[str, int]] = set()
        tier_to_ids: dict[int, set[str]] = defaultdict(set)
        stack: list[tuple[str, int]] = [(component_id, 0)]
        while stack:
            node_id, depth = stack.pop()
            if (node_id, depth) in seen:
                continue
            seen.add((node_id, depth))
            node = node_by_id[node_id]
            t = tier(node["type"])
            if t in (2, 3):
                cid = canonical_of(node)
                if cid:
                    tier_to_ids[t].add(cid)
            if depth >= 4:
                continue
            for target_id in outgoing.get(node_id, []):
                if node_by_id[target_id]["type"] in SUPPLIER_TYPES:
                    stack.append((target_id, depth + 1))
        for t in (2, 3):
            ids = tier_to_ids.get(t, set())
            if len(ids) == 1:
                spofs.update(ids)
    return spofs


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
aliases = _aliases(dictionary)
graph_a = _load_json(GRAPH_A)
graph_b = _load_json(GRAPH_B)

party_a = graph_a["party_id"]
party_b = graph_b["party_id"]
a_ids = _canonical_spof_ids(graph_a, aliases)
b_ids = _canonical_spof_ids(graph_b, aliases)
shared = sorted(a_ids & b_ids)
a_only = sorted(a_ids - b_ids)
b_only = sorted(b_ids - a_ids)


def name_of(cid: str) -> str:
    return meta.get(cid, {}).get("display_name", cid)


def juris_of(cid: str) -> str:
    return meta.get(cid, {}).get("jurisdiction", "??").upper()


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
