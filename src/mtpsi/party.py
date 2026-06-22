from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPLIER_TYPES = {"tier1_supplier", "tier2_supplier", "tier3_supplier"}
NODE_TYPES = SUPPLIER_TYPES | {"brand", "component"}
EDGE_TYPES = {"sources_from", "depends_on"}


class GraphValidationError(ValueError):
    """raised when a supplier graph does not match the v0 schema."""


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_string(value: dict[str, Any], key: str, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise GraphValidationError(f"{context}.{key} must be a non-empty string")
    return item


def validate_supplier_graph(graph: dict[str, Any]) -> None:
    if not isinstance(graph, dict):
        raise GraphValidationError("graph must be an object")

    for key in ("schema_version", "party_id", "nodes", "edges"):
        if key not in graph:
            raise GraphValidationError(f"graph missing required field: {key}")

    if graph["schema_version"] != "1.0":
        raise GraphValidationError("schema_version must be 1.0")

    if not isinstance(graph["party_id"], str) or not graph["party_id"].strip():
        raise GraphValidationError("party_id must be a non-empty string")

    nodes = graph["nodes"]
    edges = graph["edges"]
    if not isinstance(nodes, list) or not nodes:
        raise GraphValidationError("nodes must be a non-empty array")
    if not isinstance(edges, list):
        raise GraphValidationError("edges must be an array")

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise GraphValidationError(f"nodes[{index}] must be an object")
        node_id = _require_string(node, "node_id", f"nodes[{index}]")
        node_type = _require_string(node, "type", f"nodes[{index}]")
        _require_string(node, "display_name", f"nodes[{index}]")
        _require_string(node, "party_local_id", f"nodes[{index}]")
        if node_type not in NODE_TYPES:
            raise GraphValidationError(f"nodes[{index}].type is not allowed")
        if node_id in node_ids:
            raise GraphValidationError(f"duplicate node_id: {node_id}")
        node_ids.add(node_id)
        canonical_id = node.get("canonical_id")
        if canonical_id is not None and not isinstance(canonical_id, str):
            raise GraphValidationError(f"nodes[{index}].canonical_id must be string or null")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise GraphValidationError(f"edges[{index}] must be an object")
        source = _require_string(edge, "from", f"edges[{index}]")
        target = _require_string(edge, "to", f"edges[{index}]")
        edge_type = _require_string(edge, "type", f"edges[{index}]")
        if source not in node_ids:
            raise GraphValidationError(f"edges[{index}].from references missing node")
        if target not in node_ids:
            raise GraphValidationError(f"edges[{index}].to references missing node")
        if edge_type not in EDGE_TYPES:
            raise GraphValidationError(f"edges[{index}].type is not allowed")


def _norm(value: str) -> str:
    return " ".join(value.casefold().replace("_", " ").replace("-", " ").split())


def load_canonical_dictionary(path: str | Path) -> dict[str, str]:
    dictionary = load_json(path)
    if not isinstance(dictionary, dict):
        raise GraphValidationError("canonical dictionary must be an object")
    entries = dictionary.get("entries")
    if not isinstance(entries, list):
        raise GraphValidationError("canonical dictionary entries must be an array")

    aliases: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise GraphValidationError(f"dictionary entries[{index}] must be an object")
        canonical_id = _require_string(entry, "canonical_id", f"entries[{index}]")
        display_name = _require_string(entry, "display_name", f"entries[{index}]")
        aliases[_norm(display_name)] = canonical_id
        for alias in entry.get("aliases", []):
            if not isinstance(alias, str) or not alias.strip():
                raise GraphValidationError(f"entries[{index}].aliases must contain strings")
            aliases[_norm(alias)] = canonical_id
    return aliases


def canonicalize_graph(graph: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    validate_supplier_graph(graph)
    canonicalized = json.loads(json.dumps(graph))
    for node in canonicalized["nodes"]:
        if node["type"] not in SUPPLIER_TYPES:
            continue
        if node.get("canonical_id"):
            continue
        candidates = (
            node.get("display_name", ""),
            node.get("party_local_id", ""),
        )
        for candidate in candidates:
            canonical_id = aliases.get(_norm(candidate))
            if canonical_id:
                node["canonical_id"] = canonical_id
                break
    return canonicalized


@dataclass(frozen=True)
class Party:
    party_id: str
    graph: dict[str, Any]

    @classmethod
    def from_files(cls, graph_path: str | Path, dictionary_path: str | Path) -> "Party":
        graph = load_json(graph_path)
        aliases = load_canonical_dictionary(dictionary_path)
        canonicalized = canonicalize_graph(graph, aliases)
        return cls(party_id=canonicalized["party_id"], graph=canonicalized)

    def canonical_spof_ids(self, tiers: tuple[int, ...] = (2, 3)) -> set[str]:
        from .protocol import enumerate_tier_spofs

        return enumerate_tier_spofs(self.graph, tiers=tiers)
