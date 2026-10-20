from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from mtpsi.party import Party
from mtpsi.protocol import (
    MAX_QUERY_FRACTION,
    assert_leakage_boundary,
    load_dictionary_ids,
    max_query_set_size,
    run_dh_based,
)


ROOT = Path(__file__).resolve().parents[1]
DICTIONARY = ROOT / "data" / "canonical_supplier_dict.json"
UNIVERSE = load_dictionary_ids(DICTIONARY)


def _spofs(name: str) -> set[str]:
    return Party.from_files(ROOT / "data" / f"{name}_graph.json", DICTIONARY).canonical_spof_ids()


def test_committed_dictionary_is_the_five_fixture_suppliers() -> None:
    assert len(UNIVERSE) == 5
    assert _spofs("oem_a") | _spofs("oem_b") == set(UNIVERSE)


@pytest.mark.parametrize("victim", ["oem_a", "oem_b"])
def test_dictionary_sweep_fails_the_leakage_boundary(victim: str) -> None:
    # Submitting the whole dictionary returns the victim's entire single-source
    # set; the transcript still carries no ids, so only a query-size bound can
    # catch it.
    victim_ids = _spofs(victim)
    result = run_dh_based(UNIVERSE, victim_ids, party_a="sweeper", party_b=victim, seed="fixture-v0")
    assert set(result.intersection_canonical_ids) == victim_ids
    with pytest.raises(AssertionError, match="dictionary attack: sweeper submitted 5 ids"):
        assert_leakage_boundary(result)


def test_honest_fixture_sets_stay_inside_the_bound() -> None:
    result = run_dh_based(_spofs("oem_a"), _spofs("oem_b"), seed="fixture-v0")
    assert result.input_sizes == (4, 2)
    assert_leakage_boundary(result)


def test_bound_is_documented_fraction_and_leaves_one_entry_out() -> None:
    assert MAX_QUERY_FRACTION == 0.8
    assert max_query_set_size(5) == 4
    assert max_query_set_size(100) == 80
    assert max_query_set_size(2) == 1
    assert max_query_set_size(1) == 0
    doc = (ROOT / "docs" / "security-disclosure.md").read_text(encoding="utf-8")
    assert "dictionary attack" in doc and "80%" in doc


def _sweep_graph() -> dict:
    """oem graph in which every dictionary supplier is a single source."""

    entries = json.loads(DICTIONARY.read_text(encoding="utf-8"))["entries"]
    nodes, edges = [], []
    for index, entry in enumerate(entries):
        component, tier1, tier2 = f"component.c{index}", f"sup.t1.{index}", f"sup.t2.{index}"
        nodes += [
            {"node_id": component, "type": "component", "display_name": f"c{index}", "party_local_id": f"c{index}"},
            {"node_id": tier1, "type": "tier1_supplier", "display_name": f"t1 {index}", "party_local_id": f"t1-{index}"},
            {"node_id": tier2, "type": "tier2_supplier", "display_name": entry["display_name"], "party_local_id": f"t2-{index}"},
        ]
        edges += [
            {"from": component, "to": tier1, "type": "sources_from"},
            {"from": tier1, "to": tier2, "type": "depends_on"},
        ]
    return {"schema_version": "1.0", "party_id": "oem_sweeper", "nodes": nodes, "edges": edges}


def test_cli_run_refuses_to_release_a_dictionary_sweep(tmp_path: Path) -> None:
    graph = tmp_path / "sweeper.json"
    graph.write_text(json.dumps(_sweep_graph()), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "mtpsi", "run", "--mode", "dh_based", "--graph-a", str(graph), "--seed", "fixture-v0"],
        cwd=ROOT,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0
    assert completed.stderr.startswith("error: refusing to release the dh_based result: dictionary attack")
    assert completed.stdout == ""
