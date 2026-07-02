from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mtpsi.party import (
    Party,
    canonicalize_graph,
    load_canonical_dictionary,
    load_json,
    validate_supplier_graph,
)
from mtpsi.protocol import (
    assert_leakage_boundary,
    canonical_json,
    enumerate_tier_spofs,
    run_baseline,
    run_dh_based,
    validate_session_record,
)


ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = ROOT / "data" / "canonical_supplier_dict.json"


def test_fixture_graphs_validate() -> None:
    validate_supplier_graph(load_json(ROOT / "data" / "oem_a_graph.json"))
    validate_supplier_graph(load_json(ROOT / "data" / "oem_b_graph.json"))


def test_party_prepares_canonical_spof_set() -> None:
    party_a = Party.from_files(ROOT / "data" / "oem_a_graph.json", DICTIONARY)
    party_b = Party.from_files(ROOT / "data" / "oem_b_graph.json", DICTIONARY)

    assert party_a.canonical_spof_ids() == {
        "sup.jp.lens-grind",
        "sup.kr.substrate-alt",
        "sup.tw.phoenix-substrates",
        "sup.us.die-adhesive",
    }
    assert party_b.canonical_spof_ids() == {
        "sup.my.power-ic",
        "sup.tw.phoenix-substrates",
    }


def test_baseline_and_dh_based_return_same_fixture_size() -> None:
    party_a = Party.from_files(ROOT / "data" / "oem_a_graph.json", DICTIONARY)
    party_b = Party.from_files(ROOT / "data" / "oem_b_graph.json", DICTIONARY)
    baseline = run_baseline(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )
    dh_based = run_dh_based(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )

    assert baseline.intersection_size == 1
    assert dh_based.intersection_size == baseline.intersection_size


def test_baseline_session_is_deterministic_with_seed() -> None:
    party_a = Party.from_files(ROOT / "data" / "oem_a_graph.json", DICTIONARY)
    party_b = Party.from_files(ROOT / "data" / "oem_b_graph.json", DICTIONARY)
    first = run_baseline(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )
    second = run_baseline(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )

    assert canonical_json(first.session) == canonical_json(second.session)


def test_leakage_boundary_matches_security_doc() -> None:
    party_a = Party.from_files(ROOT / "data" / "oem_a_graph.json", DICTIONARY)
    party_b = Party.from_files(ROOT / "data" / "oem_b_graph.json", DICTIONARY)
    result = run_dh_based(
        party_a.canonical_spof_ids(),
        party_b.canonical_spof_ids(),
        party_a=party_a.party_id,
        party_b=party_b.party_id,
        seed="fixture-v0",
    )

    assert_leakage_boundary(result)
    doc = (ROOT / "docs" / "security-disclosure.md").read_text(encoding="utf-8")
    assert "the dh_based transcript reveals the intersection size" in doc
    assert "baseline sends plaintext sets" in doc


def test_example_session_jsonl_parses() -> None:
    lines = (ROOT / "examples" / "psi-session-baseline.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    session = json.loads(lines[0])
    validate_session_record(session)
    assert session["intersection_size"] == 1


def test_python_module_validate_no_args() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "mtpsi", "validate"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "intersection_size=1" in completed.stdout


def test_python_module_show_no_args() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "mtpsi", "show"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    out = completed.stdout
    # the no-arg show verb is read-only, exits 0, and names the shared exposure.
    assert "shared single-source supplier exposure" in out
    assert "phoenix substrates taiwan" in out
    assert "sup.tw.phoenix-substrates" in out
    assert "shared=1" in out
    # ranked: the shared row appears before either party-only row.
    assert out.index("shared") < out.index("oem_a only")
    assert "intersection_size=1" in out


def _component_reaches_two_tier2_ids() -> dict:
    """one component that sources from a tier1 with two distinct tier2 suppliers."""

    return {
        "schema_version": "1.0",
        "party_id": "oem_test",
        "nodes": [
            {"node_id": "component.c1", "type": "component", "display_name": "c1", "party_local_id": "c1"},
            {"node_id": "sup.t1", "type": "tier1_supplier", "display_name": "t1", "party_local_id": "t1"},
            {"node_id": "sup.t2a", "type": "tier2_supplier", "display_name": "t2a", "party_local_id": "t2a", "canonical_id": "sup.aa"},
            {"node_id": "sup.t2b", "type": "tier2_supplier", "display_name": "t2b", "party_local_id": "t2b", "canonical_id": "sup.bb"},
        ],
        "edges": [
            {"from": "component.c1", "to": "sup.t1", "type": "sources_from"},
            {"from": "sup.t1", "to": "sup.t2a", "type": "depends_on"},
            {"from": "sup.t1", "to": "sup.t2b", "type": "depends_on"},
        ],
    }


def test_spof_requires_exactly_one_source_at_tier() -> None:
    # two distinct tier-2 canonical ids for one component is multi-source, not a spof.
    # pins the len == 1 boundary: a >= 1 rule would wrongly flag both ids here.
    multi = _component_reaches_two_tier2_ids()
    assert enumerate_tier_spofs(multi) == set()

    # dropping the second tier-2 supplier leaves a genuine single source.
    single = _component_reaches_two_tier2_ids()
    single["nodes"] = [n for n in single["nodes"] if n["node_id"] != "sup.t2b"]
    single["edges"] = [e for e in single["edges"] if e["to"] != "sup.t2b"]
    assert enumerate_tier_spofs(single) == {"sup.aa"}


def test_norm_folds_case_and_separators() -> None:
    # a display_name that differs from the dictionary alias only by case and a
    # '-' separator must still resolve; an identity _norm would leave it unmatched.
    aliases = load_canonical_dictionary(DICTIONARY)
    graph = {
        "schema_version": "1.0",
        "party_id": "oem_test",
        "nodes": [
            {"node_id": "component.c1", "type": "component", "display_name": "c1", "party_local_id": "c1"},
            {"node_id": "sup.x", "type": "tier2_supplier", "display_name": "Phoenix-Substrates", "party_local_id": "x"},
        ],
        "edges": [
            {"from": "component.c1", "to": "sup.x", "type": "sources_from"},
        ],
    }
    canonicalized = canonicalize_graph(graph, aliases)
    assert canonicalized["nodes"][1]["canonical_id"] == "sup.tw.phoenix-substrates"


def _valid_session_record() -> dict:
    return run_baseline(["a", "b"], ["b"], seed="fixture-v0").session


def test_validate_session_record_rejects_negative_size() -> None:
    session = _valid_session_record()
    session["intersection_size"] = -1
    with pytest.raises(ValueError, match="intersection_size must be a non-negative integer"):
        validate_session_record(session)


def test_run_reports_clean_error_on_missing_graph() -> None:
    # bad --graph input must surface as one 'error:' line on stderr with a
    # non-zero exit, not a python traceback.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "mtpsi", "run", "--graph-a", str(ROOT / "data" / "does_not_exist.json")],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0
    assert completed.stderr.startswith("error:")
    assert "does_not_exist.json" in completed.stderr
    assert "Traceback" not in completed.stderr
