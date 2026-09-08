"""Tests for NEXUS POC 1: Lunar Spatial Knowledge Graph (SKG)."""

import json
from pathlib import Path
import pytest

from packages.nexus_core.poc1_knowledge_graph import (
    EdgeType,
    LunarEdge,
    LunarNode,
    LunarSpatialKnowledgeGraph,
    NodeType,
    build_boguslawsky_knowledge_graph,
)


def test_knowledge_graph_node_and_edge_addition():
    """Verify nodes and edges can be added and queried."""
    skg = LunarSpatialKnowledgeGraph(name="Test-SKG")

    crater = LunarNode(
        node_id="c_001",
        node_type=NodeType.CRATER,
        name="Test Crater",
        lat=-70.0,
        lon=40.0,
        elevation_m=-1500.0,
        properties={"diameter_km": 15.0},
    )
    site = LunarNode(
        node_id="site_001",
        node_type=NodeType.CANDIDATE_SITE,
        name="Candidate Alpha",
        lat=-70.05,
        lon=40.05,
        elevation_m=-1450.0,
        properties={"mean_slope_deg": 3.2},
    )
    skg.add_lunar_node(crater)
    skg.add_lunar_node(site)

    edge = LunarEdge(
        source_id="c_001",
        target_id="site_001",
        edge_type=EdgeType.LOCATED_NEAR,
        weight=0.9,
        properties={"distance_meters": 350.0},
    )
    skg.add_lunar_edge(edge)

    assert skg.num_nodes == 2
    assert skg.num_edges == 1
    assert skg.get_node("c_001").name == "Test Crater"


def test_invalid_edge_raises_keyerror():
    """Verify that creating an edge with non-existent node raises KeyError."""
    skg = LunarSpatialKnowledgeGraph()
    skg.add_lunar_node(
        LunarNode("n1", NodeType.LUNAR_REGION, "Region 1", -70.0, 40.0)
    )
    with pytest.raises(KeyError):
        skg.add_lunar_edge(LunarEdge("n1", "missing_node", EdgeType.CONTAINS))


def test_boguslawsky_knowledge_graph_structure():
    """Verify real-world Boguslawsky knowledge graph contains all necessary layers."""
    skg = build_boguslawsky_knowledge_graph()

    assert skg.num_nodes >= 12
    assert skg.num_edges >= 12

    # Check that core entities exist
    assert skg.get_node("region_boguslawsky") is not None
    assert skg.get_node("sensor_ohrc") is not None
    assert skg.get_node("obs_ch2_ohrc_boguslawsky_d18") is not None
    assert skg.get_node("crater_boguslawsky_main") is not None
    assert skg.get_node("site_candidate_01_north_rim") is not None
    assert skg.get_node("hazard_crater_wall_steep") is not None
    assert skg.get_node("spec_indicator_hydroxyl_rim") is not None


def test_site_context_and_hazard_constraints():
    """Verify spatial context retrieval for candidate sites."""
    skg = build_boguslawsky_knowledge_graph()

    # Query site 01 (North Rim)
    ctx1 = skg.get_site_context("site_candidate_01_north_rim")
    assert ctx1["site"]["name"] == "Candidate Site #01 (North Rim Plateau)"
    assert len(ctx1["suitable_components"]) >= 3
    assert len(ctx1["spectral_indicators"]) >= 1

    # Query site 02 (Floor - near boulder hazard)
    ctx2 = skg.get_site_context("site_candidate_02_floor")
    assert len(ctx2["hazards"]) >= 1
    assert len(ctx2["constraints"]) >= 1
    assert any("boulder" in h["hazard"]["name"].lower() for h in ctx2["hazards"])


def test_observation_lineage_tracing():
    """Verify that candidate site traces back to raw sensor observations."""
    skg = build_boguslawsky_knowledge_graph()
    lineage = skg.trace_observation_lineage("site_candidate_01_north_rim")

    assert lineage["site_id"] == "site_candidate_01_north_rim"
    assert len(lineage["observations"]) >= 2
    sensors = lineage["sensors"]
    assert "Chandrayaan-2 OHRC" in sensors or "Chandrayaan-2 TMC-2" in sensors


def test_geojson_and_network_json_export(tmp_path: Path):
    """Verify GeoJSON and network JSON exports produce valid specifications."""
    skg = build_boguslawsky_knowledge_graph()

    # GeoJSON FeatureCollection
    geojson = skg.to_geojson()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == skg.num_nodes
    first_feat = geojson["features"][0]
    assert "geometry" in first_feat
    assert len(first_feat["geometry"]["coordinates"]) == 3  # lon, lat, elevation

    # Network JSON export
    export_path = tmp_path / "boguslawsky_graph.json"
    skg.export_json(export_path)
    assert export_path.exists()

    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == skg.num_nodes
    assert len(data["edges"]) == skg.num_edges
