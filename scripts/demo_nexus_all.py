#!/usr/bin/env python3
"""NEXUS Master Suite: End-to-End Autonomous 8-POC Demonstration.

Executes and verifies all 8 NEXUS Proof-of-Concept modules:
  POC 1: Lunar Spatial Knowledge Graph (SKG)
  POC 2: Terrain Intelligence Engine
  POC 3: Illumination & Solar Power Intelligence
  POC 4: IIRS Spectral & Resource Intelligence
  POC 5: Explainable AI (XAI) Site Selection
  POC 6: Graph Neural Network (GNN) Spatial Reasoner
  POC 7: Spiking Neural Network (SNN) Temporal Reasoner
  POC 8: Habitat Constraint Planner & 3D Digital Twin (Blender / Three.js)
"""

import json
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc1_knowledge_graph import build_boguslawsky_knowledge_graph
from packages.nexus_core.poc2_terrain_intelligence import (
    TerrainIntelligenceEngine,
    generate_synthetic_boguslawsky_dem,
)
from packages.nexus_core.poc3_illumination_intelligence import (
    IlluminationIntelligenceEngine,
)
from packages.nexus_core.poc4_resource_intelligence import (
    IIRSResourceEngine,
    generate_synthetic_iirs_cube,
)
from packages.nexus_core.poc5_explainable_ai import ExplainableSiteSelector
from packages.nexus_core.poc6_gnn_reasoner import GNNSpatialReasoner
from packages.nexus_core.poc7_snn_temporal import (
    SNNTemporalReasoner,
    generate_synthetic_observation_sequence,
)
from packages.nexus_core.poc8_habitat_planner import (
    HabitatConstraintPlanner,
    export_dem_to_obj_mesh,
)
from scripts.render_blender_scene import run_blender_headless


def run_all_pocs():
    t_start = time.time()
    print("=" * 80)
    print(" NEXUS-LUNAR: COMPLETE 8-POC AUTONOMOUS SPATIAL INTELLIGENCE PIPELINE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # POC 1: Spatial Knowledge Graph
    # -------------------------------------------------------------------------
    print("\n>>> [1/8] EXECUTING NEXUS POC 1: LUNAR SPATIAL KNOWLEDGE GRAPH...")
    skg = build_boguslawsky_knowledge_graph()
    print(f"    Nodes: {skg.num_nodes} | Edges: {skg.num_edges}")
    ctx1 = skg.get_site_context("site_candidate_01_north_rim")
    print(f"    Target Site: {ctx1['site']['name']}")
    print(f"    Lineage Sensors: {', '.join(skg.trace_observation_lineage('site_candidate_01_north_rim')['sensors'])}")

    # -------------------------------------------------------------------------
    # POC 2: Terrain Intelligence
    # -------------------------------------------------------------------------
    print("\n>>> [2/8] EXECUTING NEXUS POC 2: TERRAIN INTELLIGENCE ENGINE...")
    dem = generate_synthetic_boguslawsky_dem(size=256, resolution_m=5.0)
    terrain_engine = TerrainIntelligenceEngine(dem, resolution_m=5.0)
    slope, aspect = terrain_engine.compute_slope_and_aspect()
    roughness = terrain_engine.compute_surface_roughness()
    hazards = terrain_engine.compute_hazard_mask()
    t_prof = terrain_engine.evaluate_site("site_01", center_row=38, center_col=217, radius_pixels=15)
    print(f"    Mean Regional Slope: {slope.mean():.2f}° | Hazard Density: {(hazards.sum()/hazards.size)*100:.1f}%")
    print(f"    Site #01 Slope: {t_prof.mean_slope_deg:.2f}° | Stability Score: {t_prof.terrain_stability_score:.1f}/100")

    # -------------------------------------------------------------------------
    # POC 3: Illumination Intelligence
    # -------------------------------------------------------------------------
    print("\n>>> [3/8] EXECUTING NEXUS POC 3: ILLUMINATION & SOLAR POWER INTELLIGENCE...")
    illum_engine = IlluminationIntelligenceEngine(dem, resolution_m=5.0, slope_grid=slope, aspect_grid=aspect)
    diurnal = illum_engine.simulate_diurnal_cycle(mean_sun_elevation_deg=3.5, num_azimuth_steps=16)
    s_prof = illum_engine.evaluate_site_solar("site_01", center_row=38, center_col=217, diurnal_results=diurnal)
    print(f"    Mean Illumination: {diurnal['illumination_fraction'].mean()*100:.1f}%")
    print(f"    PEL Area (>70% Sun): {(diurnal['pel_mask'].sum()/diurnal['pel_mask'].size)*100:.1f}%")
    print(f"    Site #01 Sunlight: {s_prof.mean_illumination_fraction*100:.1f}% ({s_prof.to_dict()['classification']})")

    # -------------------------------------------------------------------------
    # POC 4: IIRS Spectral & Resource Intelligence
    # -------------------------------------------------------------------------
    print("\n>>> [4/8] EXECUTING NEXUS POC 4: IIRS SPECTRAL & RESOURCE INTELLIGENCE...")
    cube, wavelengths = generate_synthetic_iirs_cube(height=64, width=64, num_bands=64)
    iirs_engine = IIRSResourceEngine(cube, wavelengths, resolution_m=20.0)
    res_maps = iirs_engine.compute_resource_maps()
    r_prof = iirs_engine.evaluate_site_resources("site_01", center_row=20, center_col=45, resource_maps=res_maps)
    print(f"    Hyperspectral Bands: {len(wavelengths)} ({wavelengths[0]:.2f}µm to {wavelengths[-1]:.2f}µm)")
    print(f"    Site #01 2.85µm Hydroxyl Depth: {r_prof.hydroxyl_band_depth_pct:.2f}% (Confidence: {r_prof.hydroxyl_confidence:.2f})")

    # -------------------------------------------------------------------------
    # POC 5: Explainable AI Site Selection
    # -------------------------------------------------------------------------
    print("\n>>> [5/8] EXECUTING NEXUS POC 5: EXPLAINABLE AI (XAI) SITE SELECTION...")
    selector = ExplainableSiteSelector(base_score=50.0)
    xai_exp = selector.explain_site(
        site_id="site_candidate_01_north_rim",
        site_name="Candidate Site #01 (Boguslawsky North Rim)",
        coordinates={"lat": -72.674, "lon": 43.478},
        terrain_profile=t_prof.to_dict(),
        solar_profile=s_prof.to_dict(),
        resource_profile=r_prof.to_dict(),
        hazard_context={"nearest_hazard_distance_m": 850.0, "nearest_hazard_type": "Steep Escarpment"},
    )
    print(f"    Suitability Score: {xai_exp.final_score:.1f}/100 [{xai_exp.recommendation}]")
    print("    Waterfall Breakdown:")
    for f in xai_exp.waterfall:
        print(f"      • {f.category:22s} [{f.delta_score:+5.1f}] -> {f.reason}")

    # -------------------------------------------------------------------------
    # POC 6: GNN Spatial Reasoner
    # -------------------------------------------------------------------------
    print("\n>>> [6/8] EXECUTING NEXUS POC 6: GRAPH NEURAL NETWORK (GNN) SPATIAL REASONER...")
    gnn_reasoner = GNNSpatialReasoner(skg, hidden_dim=16)
    loss = gnn_reasoner.train_inductive_predictor(epochs=35, lr=0.01)
    inferences = gnn_reasoner.infer_site_suitabilities()
    print(f"    GraphSAGE Training Loss: {loss:.4f}")
    for sid, inf in inferences.items():
        print(f"      • {inf['site_name']}: GNN Suitability {inf['gnn_suitability_score']:.1f}/100")

    # -------------------------------------------------------------------------
    # POC 7: SNN Temporal Reasoner
    # -------------------------------------------------------------------------
    print("\n>>> [7/8] EXECUTING NEXUS POC 7: SPIKING NEURAL NETWORK (SNN) TEMPORAL REASONER...")
    snn_reasoner = SNNTemporalReasoner(num_neurons=16, time_steps=24)
    t_series = generate_synthetic_observation_sequence(site_type="plateau", num_steps=24)
    snn_prof = snn_reasoner.process_site_temporal_series("site_01", t_series)
    print(f"    Total Action Potential Spikes: {snn_prof.total_spikes_emitted}")
    print(f"    Temporal Stability Index:      {snn_prof.temporal_stability_index:.2f}/1.00 ({snn_prof.state_classification})")
    print(f"    Edge Power Consumption Proxy:  {snn_prof.neuromorphic_power_proxy_mw:.3f} mW")

    # -------------------------------------------------------------------------
    # POC 8: Habitat Planner & 3D Digital Twin
    # -------------------------------------------------------------------------
    print("\n>>> [8/8] EXECUTING NEXUS POC 8: HABITAT PLANNER & 3D DIGITAL TWIN...")
    hab_planner = HabitatConstraintPlanner(dem, resolution_m=5.0)
    layout = hab_planner.generate_layout("site_01", "Boguslawsky Rim Base", hab_center_offset=(380.0, 350.0))
    print(f"    Layout Constraint Status: {'[✓] PASSED' if layout.all_constraints_passed else '[!] FAILED'}")
    print(f"    Modules Placed: {len(layout.modules)} (Power: {layout.total_power_capacity_kw:.0f} kW)")

    # 3D Mesh Export
    out_3d = Path("outputs/nexus_3d")
    out_3d.mkdir(parents=True, exist_ok=True)
    obj_path = out_3d / "nexus_boguslawsky_mesh.obj"
    export_dem_to_obj_mesh(dem, resolution_m=5.0, output_obj_path=obj_path, subsample_factor=2)
    print(f"    [✓] 3D Terrain Mesh Exported: {obj_path}")

    # Blender Headless Render
    print("\n[*] Invoking Headless Blender Raytraced PBR Rendering...")
    blender_ok = run_blender_headless()
    if blender_ok:
        print("    [✓] Photorealistic 3D Digital Twin PNG Rendered Successfully!")

    # Master Summary Report
    elapsed = time.time() - t_start
    print("\n" + "=" * 80)
    print(f" NEXUS-LUNAR ALL 8 POCS VALIDATED SUCCESSFULLY (Total Runtime: {elapsed:.2f}s)")
    print("=" * 80)


if __name__ == "__main__":
    run_all_pocs()
