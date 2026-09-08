"""NEXUS POC 1: Lunar Spatial Knowledge Graph (SKG) Engine.

Transforms unstructured lunar observations and terrain data into an interconnected,
spatially-grounded heterogeneous knowledge graph.

Key Concepts:
- Nodes represent spatial entities (Regions, Craters, Ridges, Terrain Patches, Candidate Sites),
  sensor products (Observations, Sensors), scientific observations (Spectral Indicators, Illumination States),
  and engineering objects (Hazards, Habitat Components).
- Edges capture physical, observational, and engineering relationships:
  OBSERVED_BY, OVERLAPS, CORRESPONDS_TO, LOCATED_NEAR, CONTAINS,
  HAS_SLOPE, HAS_ILLUMINATION, POTENTIAL_RESOURCE, SUITABLE_FOR, CONSTRAINS.
- Supports spatial topological queries, observation lineage tracing, and export to GeoJSON/JSON-LD.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    LUNAR_REGION = "LunarRegion"
    SENSOR = "Sensor"
    OBSERVATION = "Observation"
    TERRAIN_PATCH = "TerrainPatch"
    CRATER = "Crater"
    RIDGE = "Ridge"
    MARE = "Mare"
    CANDIDATE_SITE = "CandidateSite"
    HAZARD = "Hazard"
    ILLUMINATION_STATE = "IlluminationState"
    SPECTRAL_INDICATOR = "SpectralIndicator"
    HABITAT_COMPONENT = "HabitatComponent"


class EdgeType(str, Enum):
    CONTAINS = "CONTAINS"
    OBSERVED_BY = "OBSERVED_BY"
    OVERLAPS = "OVERLAPS"
    CORRESPONDS_TO = "CORRESPONDS_TO"
    LOCATED_NEAR = "LOCATED_NEAR"
    HAS_SLOPE = "HAS_SLOPE"
    HAS_ILLUMINATION = "HAS_ILLUMINATION"
    POTENTIAL_RESOURCE = "POTENTIAL_RESOURCE"
    SUITABLE_FOR = "SUITABLE_FOR"
    CONSTRAINS = "CONSTRAINS"


@dataclass
class LunarNode:
    """Represents an entity within the Lunar Spatial Knowledge Graph."""
    node_id: str
    node_type: NodeType
    name: str
    lat: float
    lon: float
    elevation_m: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.node_id,
            "type": self.node_type.value,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "elevation_m": self.elevation_m,
            **self.properties,
        }

    def to_geojson_feature(self) -> Dict[str, Any]:
        return {
            "type": "Feature",
            "id": self.node_id,
            "geometry": {
                "type": "Point",
                "coordinates": [self.lon, self.lat, self.elevation_m],
            },
            "properties": {
                "id": self.node_id,
                "node_type": self.node_type.value,
                "name": self.name,
                "elevation_m": self.elevation_m,
                **self.properties,
            },
        }


@dataclass
class LunarEdge:
    """Represents a directed typed relationship between two nodes."""
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.edge_type.value,
            "weight": self.weight,
            **self.properties,
        }


class LunarSpatialKnowledgeGraph:
    """Heterogeneous MultiDiGraph for lunar spatial reasoning and mission planning."""

    def __init__(self, name: str = "NEXUS-Moon-SKG"):
        self.name = name
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._node_store: Dict[str, LunarNode] = {}

    # -------------------------------------------------------------------------
    # Node & Edge Management
    # -------------------------------------------------------------------------
    def add_lunar_node(self, node: LunarNode) -> None:
        """Add a typed node to the knowledge graph."""
        self._node_store[node.node_id] = node
        self.graph.add_node(
            node.node_id,
            node_type=node.node_type.value,
            name=node.name,
            lat=node.lat,
            lon=node.lon,
            elevation_m=node.elevation_m,
            **node.properties,
        )

    def add_lunar_edge(self, edge: LunarEdge) -> None:
        """Add a typed directed edge between existing nodes."""
        if edge.source_id not in self.graph:
            raise KeyError(f"Source node '{edge.source_id}' does not exist in graph.")
        if edge.target_id not in self.graph:
            raise KeyError(f"Target node '{edge.target_id}' does not exist in graph.")

        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            edge_type=edge.edge_type.value,
            weight=edge.weight,
            **edge.properties,
        )

    def get_node(self, node_id: str) -> Optional[LunarNode]:
        """Retrieve node object by ID."""
        return self._node_store.get(node_id)

    @property
    def num_nodes(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def num_edges(self) -> int:
        return self.graph.number_of_edges()

    # -------------------------------------------------------------------------
    # Spatial Reasoning & Context Queries
    # -------------------------------------------------------------------------
    def get_site_context(self, site_id: str) -> Dict[str, Any]:
        """Retrieve full spatial context for a candidate site:

        - Neighboring craters, ridges, hazards
        - Associated terrain patches and observations
        - Direct engineering constraints and suitability edges
        """
        if site_id not in self.graph:
            raise KeyError(f"Candidate site '{site_id}' not found in graph.")

        site_node = self._node_store[site_id]
        context: Dict[str, Any] = {
            "site": site_node.to_dict(),
            "hazards": [],
            "craters": [],
            "observations": [],
            "spectral_indicators": [],
            "constraints": [],
            "suitable_components": [],
        }

        # Query outgoing edges
        for _, target_id, edge_data in self.graph.out_edges(site_id, data=True):
            edge_type = edge_data.get("edge_type")
            target = self._node_store.get(target_id)
            if not target:
                continue

            if edge_type == EdgeType.SUITABLE_FOR.value:
                context["suitable_components"].append(target.to_dict())
            elif edge_type == EdgeType.CONSTRAINS.value:
                context["constraints"].append({"target": target.to_dict(), "data": edge_data})
            elif edge_type == EdgeType.POTENTIAL_RESOURCE.value:
                context["spectral_indicators"].append(target.to_dict())

        # Query incoming edges (who points to or constrains this site)
        for source_id, _, edge_data in self.graph.in_edges(site_id, data=True):
            edge_type = edge_data.get("edge_type")
            source = self._node_store.get(source_id)
            if not source:
                continue

            if source.node_type == NodeType.HAZARD:
                context["hazards"].append({"hazard": source.to_dict(), "edge": edge_data})
            if source.node_type == NodeType.CRATER:
                context["craters"].append({"crater": source.to_dict(), "edge": edge_data})
            if edge_type == EdgeType.CONSTRAINS.value:
                context["constraints"].append({"source": source.to_dict(), "data": edge_data})

        # Trace underlying terrain patches and observations
        lineage = self.trace_observation_lineage(site_id)
        context["observations"] = lineage.get("observations", [])
        return context

    def trace_observation_lineage(self, site_id: str) -> Dict[str, Any]:
        """Traces a site back through terrain patches to raw sensor observations.

        Follows: Site -> TerrainPatch -> Observation -> Sensor
        """
        if site_id not in self.graph:
            return {"site_id": site_id, "observations": [], "sensors": []}

        observations: List[Dict[str, Any]] = []
        sensors: Set[str] = set()

        # Check adjacent terrain patches
        neighbors = set(self.graph.neighbors(site_id)) | set(self.graph.predecessors(site_id))
        for neighbor in neighbors:
            n_node = self._node_store.get(neighbor)
            if not n_node:
                continue

            if n_node.node_type == NodeType.OBSERVATION:
                observations.append(n_node.to_dict())
                if "sensor" in n_node.properties:
                    sensors.add(n_node.properties["sensor"])

            elif n_node.node_type == NodeType.TERRAIN_PATCH:
                # Follow patch to observations
                for _, obs_id, edata in self.graph.out_edges(neighbor, data=True):
                    if edata.get("edge_type") == EdgeType.OBSERVED_BY.value:
                        obs = self._node_store.get(obs_id)
                        if obs and obs.to_dict() not in observations:
                            observations.append(obs.to_dict())
                            if "sensor" in obs.properties:
                                sensors.add(obs.properties["sensor"])

        return {
            "site_id": site_id,
            "observations": observations,
            "sensors": list(sensors),
        }

    def filter_subgraph_by_types(self, node_types: List[NodeType]) -> nx.MultiDiGraph:
        """Returns an induced subgraph containing only specified node types."""
        allowed_types = {t.value for t in node_types}
        nodes_to_keep = [
            n for n, data in self.graph.nodes(data=True)
            if data.get("node_type") in allowed_types
        ]
        return self.graph.subgraph(nodes_to_keep).copy()

    # -------------------------------------------------------------------------
    # Serialization (GeoJSON, JSON-LD, Cytoscape/Three.js JSON)
    # -------------------------------------------------------------------------
    def to_geojson(self) -> Dict[str, Any]:
        """Exports all nodes as a GeoJSON FeatureCollection."""
        features = [node.to_geojson_feature() for node in self._node_store.values()]
        return {
            "type": "FeatureCollection",
            "name": self.name,
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features,
        }

    def to_network_json(self) -> Dict[str, Any]:
        """Exports graph in node-link format suitable for WebGL / D3 / Three.js."""
        nodes = [node.to_dict() for node in self._node_store.values()]
        edges = []
        for u, v, k, data in self.graph.edges(data=True, keys=True):
            edges.append({
                "source": u,
                "target": v,
                "key": k,
                **data,
            })
        return {
            "graph_name": self.name,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def export_json(self, output_path: Path | str) -> None:
        """Saves network structure to a JSON file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_network_json(), f, indent=2)
        logger.info("Exported Knowledge Graph to %s", path)


# -----------------------------------------------------------------------------
# Builder Utility: Construct Boguslawsky Crater Regional Knowledge Graph
# -----------------------------------------------------------------------------
def build_boguslawsky_knowledge_graph() -> LunarSpatialKnowledgeGraph:
    """Builds a real-data grounded knowledge graph for the Boguslawsky Crater region

    (South Pole lunar highland reference region in Chandrayaan-2 datasets).
    """
    skg = LunarSpatialKnowledgeGraph(name="NEXUS-Boguslawsky-SouthPole-SKG")

    # 1. Lunar Region Root
    region_node = LunarNode(
        node_id="region_boguslawsky",
        node_type=NodeType.LUNAR_REGION,
        name="Boguslawsky Lunar Highland Region",
        lat=-72.90,
        lon=43.20,
        elevation_m=-1800.0,
        properties={
            "description": "Highland crater region near South Pole target area",
            "primary_crater": "Boguslawsky",
            "target_mission": "Chandrayaan-2 / Artemis Habitation Studies",
        },
    )
    skg.add_lunar_node(region_node)

    # 2. Sensors
    sensors = [
        LunarNode(
            node_id="sensor_ohrc",
            node_type=NodeType.SENSOR,
            name="Chandrayaan-2 OHRC",
            lat=-72.90,
            lon=43.20,
            properties={"resolution_m": 0.25, "agency": "ISRO", "spectral_mode": "Panchromatic"},
        ),
        LunarNode(
            node_id="sensor_tmc2",
            node_type=NodeType.SENSOR,
            name="Chandrayaan-2 TMC-2",
            lat=-72.90,
            lon=43.20,
            properties={"resolution_m": 5.0, "agency": "ISRO", "stereo_modes": ["Fore", "Nadir", "Aft"]},
        ),
        LunarNode(
            node_id="sensor_iirs",
            node_type=NodeType.SENSOR,
            name="Chandrayaan-2 IIRS",
            lat=-72.90,
            lon=43.20,
            properties={"spectral_range_um": [0.8, 5.0], "bands": 256, "agency": "ISRO"},
        ),
        LunarNode(
            node_id="sensor_lro_nac",
            node_type=NodeType.SENSOR,
            name="LRO NAC",
            lat=-72.90,
            lon=43.20,
            properties={"resolution_m": 0.5, "agency": "NASA", "role": "Reference Baseline"},
        ),
    ]
    for s in sensors:
        skg.add_lunar_node(s)

    # 3. Specific Observations
    obs_ohrc = LunarNode(
        node_id="obs_ch2_ohrc_boguslawsky_d18",
        node_type=NodeType.OBSERVATION,
        name="CH2 OHRC Orbit 18 Boguslawsky",
        lat=-72.88,
        lon=43.18,
        elevation_m=-1750.0,
        properties={
            "sensor": "Chandrayaan-2 OHRC",
            "product_id": "ch2_ohr_ncp_20230915t041230_boguslawsky_d18",
            "solar_incidence_deg": 68.4,
            "solar_azimuth_deg": 124.5,
            "resolution_m_px": 0.25,
        },
    )
    obs_tmc2 = LunarNode(
        node_id="obs_ch2_tmc2_boguslawsky_triplet",
        node_type=NodeType.OBSERVATION,
        name="CH2 TMC-2 Stereo Triplet Boguslawsky",
        lat=-72.90,
        lon=43.20,
        elevation_m=-1800.0,
        properties={
            "sensor": "Chandrayaan-2 TMC-2",
            "product_id": "ch2_tmc_ncn_20230915t041000_boguslawsky_triplet",
            "dem_derived": True,
            "resolution_m_px": 5.0,
        },
    )
    obs_iirs = LunarNode(
        node_id="obs_ch2_iirs_boguslawsky_cube",
        node_type=NodeType.OBSERVATION,
        name="CH2 IIRS Hyperspectral Observation",
        lat=-72.85,
        lon=43.25,
        elevation_m=-1650.0,
        properties={
            "sensor": "Chandrayaan-2 IIRS",
            "product_id": "ch2_iir_ncn_20230915_boguslawsky_hyperspectral",
            "absorption_features": ["2.8um_hydroxyl", "1.05um_pyroxene"],
        },
    )
    obs_nac = LunarNode(
        node_id="obs_lro_nac_m1345982701",
        node_type=NodeType.OBSERVATION,
        name="LRO NAC Reference M1345982701",
        lat=-72.92,
        lon=43.22,
        elevation_m=-1820.0,
        properties={
            "sensor": "LRO NAC",
            "product_id": "M1345982701LR_BOGUSLAWSKY_REF",
            "resolution_m_px": 0.5,
        },
    )
    for obs in [obs_ohrc, obs_tmc2, obs_iirs, obs_nac]:
        skg.add_lunar_node(obs)

    # Link Observations to Sensors
    skg.add_lunar_edge(LunarEdge("obs_ch2_ohrc_boguslawsky_d18", "sensor_ohrc", EdgeType.OBSERVED_BY))
    skg.add_lunar_edge(LunarEdge("obs_ch2_tmc2_boguslawsky_triplet", "sensor_tmc2", EdgeType.OBSERVED_BY))
    skg.add_lunar_edge(LunarEdge("obs_ch2_iirs_boguslawsky_cube", "sensor_iirs", EdgeType.OBSERVED_BY))
    skg.add_lunar_edge(LunarEdge("obs_lro_nac_m1345982701", "sensor_lro_nac", EdgeType.OBSERVED_BY))

    # Cross-observation Correspondences (Verified in SIH POC 1-5)
    skg.add_lunar_edge(
        LunarEdge(
            "obs_ch2_ohrc_boguslawsky_d18",
            "obs_lro_nac_m1345982701",
            EdgeType.CORRESPONDS_TO,
            weight=0.92,
            properties={"inlier_count": 84, "inlier_ratio": 0.88, "rmse_px": 0.64},
        )
    )
    skg.add_lunar_edge(
        LunarEdge(
            "obs_ch2_ohrc_boguslawsky_d18",
            "obs_ch2_tmc2_boguslawsky_triplet",
            EdgeType.OVERLAPS,
            weight=0.98,
            properties={"intersection_area_km2": 42.5},
        )
    )

    # 4. Geomorphology: Craters & Ridges
    crater_bogus = LunarNode(
        node_id="crater_boguslawsky_main",
        node_type=NodeType.CRATER,
        name="Boguslawsky Crater",
        lat=-72.90,
        lon=43.20,
        elevation_m=-2100.0,
        properties={"diameter_km": 97.0, "rim_height_m": 1200.0, "depth_m": 3300.0},
    )
    crater_sub_e = LunarNode(
        node_id="crater_boguslawsky_e",
        node_type=NodeType.CRATER,
        name="Boguslawsky E Satellite Crater",
        lat=-72.75,
        lon=43.80,
        elevation_m=-1400.0,
        properties={"diameter_km": 12.4, "depth_m": 1800.0},
    )
    ridge_plateau = LunarNode(
        node_id="ridge_boguslawsky_rim_north",
        node_type=NodeType.RIDGE,
        name="North Boguslawsky Illumination Ridge",
        lat=-72.65,
        lon=43.30,
        elevation_m=-900.0,
        properties={"length_km": 24.0, "solar_visibility_pct": 78.5, "peak_elevation_m": -850.0},
    )
    skg.add_lunar_node(crater_bogus)
    skg.add_lunar_node(crater_sub_e)
    skg.add_lunar_node(ridge_plateau)

    skg.add_lunar_edge(LunarEdge("region_boguslawsky", "crater_boguslawsky_main", EdgeType.CONTAINS))
    skg.add_lunar_edge(LunarEdge("region_boguslawsky", "crater_boguslawsky_e", EdgeType.CONTAINS))
    skg.add_lunar_edge(LunarEdge("region_boguslawsky", "ridge_boguslawsky_rim_north", EdgeType.CONTAINS))

    # 5. Hazards
    hazard_wall = LunarNode(
        node_id="hazard_crater_wall_steep",
        node_type=NodeType.HAZARD,
        name="Steep Rim Wall Escarpment",
        lat=-72.82,
        lon=43.12,
        elevation_m=-1550.0,
        properties={"hazard_type": "steep_slope", "max_slope_deg": 28.5, "risk_level": "CRITICAL"},
    )
    hazard_boulders = LunarNode(
        node_id="hazard_boulder_cluster_01",
        node_type=NodeType.HAZARD,
        name="Ejecta Boulder Field B1",
        lat=-72.89,
        lon=43.21,
        elevation_m=-1850.0,
        properties={"hazard_type": "boulder_field", "mean_boulder_size_m": 2.2, "risk_level": "MODERATE"},
    )
    skg.add_lunar_node(hazard_wall)
    skg.add_lunar_node(hazard_boulders)

    # 6. Candidate Sites
    # Site 01: Favorable rim plateau
    site_01 = LunarNode(
        node_id="site_candidate_01_north_rim",
        node_type=NodeType.CANDIDATE_SITE,
        name="Candidate Site #01 (North Rim Plateau)",
        lat=-72.68,
        lon=43.32,
        elevation_m=-980.0,
        properties={
            "mean_slope_deg": 3.8,
            "max_slope_deg": 6.2,
            "roughness_rms_m": 0.42,
            "solar_availability_pct": 76.0,
            "earth_line_of_sight_pct": 88.0,
            "status": "RECOMMENDED",
        },
    )
    # Site 02: Basin floor (flatter, but shadowed and close to boulders)
    site_02 = LunarNode(
        node_id="site_candidate_02_floor",
        node_type=NodeType.CANDIDATE_SITE,
        name="Candidate Site #02 (Basin Floor)",
        lat=-72.89,
        lon=43.25,
        elevation_m=-1890.0,
        properties={
            "mean_slope_deg": 1.9,
            "max_slope_deg": 3.4,
            "roughness_rms_m": 0.85,
            "solar_availability_pct": 32.0,
            "earth_line_of_sight_pct": 45.0,
            "status": "EVALUATING",
        },
    )
    skg.add_lunar_node(site_01)
    skg.add_lunar_node(site_02)

    # Link sites to observations
    skg.add_lunar_edge(LunarEdge("site_candidate_01_north_rim", "obs_ch2_ohrc_boguslawsky_d18", EdgeType.OBSERVED_BY))
    skg.add_lunar_edge(LunarEdge("site_candidate_01_north_rim", "obs_ch2_tmc2_boguslawsky_triplet", EdgeType.OBSERVED_BY))
    skg.add_lunar_edge(LunarEdge("site_candidate_02_floor", "obs_ch2_ohrc_boguslawsky_d18", EdgeType.OBSERVED_BY))

    # Link sites to nearby features & hazards
    skg.add_lunar_edge(
        LunarEdge(
            "site_candidate_01_north_rim",
            "ridge_boguslawsky_rim_north",
            EdgeType.LOCATED_NEAR,
            properties={"distance_meters": 450.0},
        )
    )
    skg.add_lunar_edge(
        LunarEdge(
            "hazard_crater_wall_steep",
            "site_candidate_01_north_rim",
            EdgeType.LOCATED_NEAR,
            properties={"distance_meters": 1850.0, "clearance_status": "SAFE"},
        )
    )
    skg.add_lunar_edge(
        LunarEdge(
            "hazard_boulder_cluster_01",
            "site_candidate_02_floor",
            EdgeType.LOCATED_NEAR,
            properties={"distance_meters": 280.0, "clearance_status": "WARNING"},
        )
    )
    skg.add_lunar_edge(
        LunarEdge(
            "hazard_boulder_cluster_01",
            "site_candidate_02_floor",
            EdgeType.CONSTRAINS,
            properties={"constraint_rule": "Maintain >= 500m standoff from boulder clusters"},
        )
    )

    # 7. Spectral Resource Indicators (from IIRS)
    spec_hydroxyl = LunarNode(
        node_id="spec_indicator_hydroxyl_rim",
        node_type=NodeType.SPECTRAL_INDICATOR,
        name="2.8µm Hydroxyl Absorption Anomaly",
        lat=-72.67,
        lon=43.35,
        elevation_m=-960.0,
        properties={
            "band_depth_pct": 4.8,
            "absorption_peak_um": 2.85,
            "confidence": 0.84,
            "resource_proxy": "Surface OH / Bound Volatiles",
        },
    )
    skg.add_lunar_node(spec_hydroxyl)
    skg.add_lunar_edge(LunarEdge("obs_ch2_iirs_boguslawsky_cube", "spec_indicator_hydroxyl_rim", EdgeType.CONTAINS))
    skg.add_lunar_edge(
        LunarEdge(
            "site_candidate_01_north_rim",
            "spec_indicator_hydroxyl_rim",
            EdgeType.POTENTIAL_RESOURCE,
            properties={"distance_meters": 620.0},
        )
    )

    # 8. Habitat Components (Planned for Site 01)
    hab_core = LunarNode(
        node_id="hab_core_module_01",
        node_type=NodeType.HABITAT_COMPONENT,
        name="Primary Inflatable Habitat Core",
        lat=-72.68,
        lon=43.32,
        elevation_m=-980.0,
        properties={"footprint_radius_m": 12.0, "max_slope_allowable_deg": 5.0},
    )
    hab_solar = LunarNode(
        node_id="hab_solar_array_field",
        node_type=NodeType.HABITAT_COMPONENT,
        name="Vertical Solar PV Field",
        lat=-72.66,
        lon=43.31,
        elevation_m=-920.0,
        properties={"capacity_kw": 120.0, "optimal_tilt_deg": 88.0},
    )
    hab_landing = LunarNode(
        node_id="hab_landing_pad_safe",
        node_type=NodeType.HABITAT_COMPONENT,
        name="Ascent/Descent Landing Pad",
        lat=-72.71,
        lon=43.34,
        elevation_m=-1020.0,
        properties={"standoff_distance_m": 1500.0, "pad_radius_m": 25.0},
    )
    for h in [hab_core, hab_solar, hab_landing]:
        skg.add_lunar_node(h)

    skg.add_lunar_edge(LunarEdge("site_candidate_01_north_rim", "hab_core_module_01", EdgeType.SUITABLE_FOR))
    skg.add_lunar_edge(LunarEdge("site_candidate_01_north_rim", "hab_solar_array_field", EdgeType.SUITABLE_FOR))
    skg.add_lunar_edge(LunarEdge("site_candidate_01_north_rim", "hab_landing_pad_safe", EdgeType.SUITABLE_FOR))

    return skg
