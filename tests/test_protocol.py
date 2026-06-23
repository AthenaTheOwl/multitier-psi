from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from mtpsi.party import Party, load_json, validate_supplier_graph
from mtpsi.protocol import (
    assert_leakage_boundary,
    canonical_json,
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
