#!/usr/bin/env python3
"""NEXUS POC 5 Demo: Explainable AI (XAI) Site Selection Engine.

Demonstrates:
1. Answering 'Why did NEXUS recommend this location?'
2. Constructing an additive waterfall score breakdown:
     SITE SCORE = 82
     Terrain: +25 | Solar: +21 | Resource: +12 | Hazard: -8 | Registration: +8
3. Tracing verifiable scientific evidence back to OHRC, TMC-2, and IIRS products
4. Exporting structured XAI explanations for mission planning interfaces
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.nexus_core.poc5_explainable_ai import (
    ExplainableSiteSelector,
)


def run_demo():
    print("=" * 72)
    print(" NEXUS POC 5: EXPLAINABLE AI (XAI) SITE SELECTION ENGINE")
    print("=" * 72)

    selector = ExplainableSiteSelector(base_score=50.0)

    # 1. Evaluate Site 01 (North Rim Plateau)
    print("\n[*] Generating XAI Recommendation for Candidate Site #01 (North Rim)...")
    site01_explanation = selector.explain_site(
        site_id="site_candidate_01_north_rim",
        site_name="Candidate Site #01 (Boguslawsky North Rim)",
        coordinates={"lat": -72.674, "lon": 43.478},
        terrain_profile={"slope": {"mean_deg": 2.38, "max_deg": 12.76}, "roughness_rms_m": 0.299},
        solar_profile={"illumination_fraction_pct": 72.2, "classification": "PEAK_OF_ETERNAL_LIGHT_CANDIDATE"},
        resource_profile={"hydroxyl_absorption_bd3000_pct": 7.04, "hydroxyl_indicator_confidence": 1.00},
        hazard_context={"nearest_hazard_distance_m": 850.0, "nearest_hazard_type": "Steep Escarpment"},
        registration_metrics={
            "ohrc_product_id": "ch2_ohr_ncp_20230915t041230_boguslawsky_d18",
            "tmc2_product_id": "ch2_tmc_ncn_20230915t041000_boguslawsky_triplet",
            "iirs_product_id": "ch2_iir_ncn_20230915_boguslawsky_hyperspectral",
            "rmse_px": 0.64,
            "inlier_ratio": 0.88,
        },
    )

    print(f"\n    FINAL SUITABILITY SCORE: {site01_explanation.final_score:.1f} / 100")
    print(f"    STATUS:                 {site01_explanation.recommendation}")
    print("\n    ┌─────────────────────────── WATERFALL SCORE BREAKDOWN ───────────────────────────┐")
    print(f"    │ Initial Neutral Prior:                                             {site01_explanation.base_score:+5.1f}   │")
    for f in site01_explanation.waterfall:
        print(f"    │   • {f.category:25s} [{f.delta_score:+4.1f}] -> {f.reason[:40]:40s}... │")
    print(f"    │ TOTAL COMPUTED SCORE:                                              {site01_explanation.final_score:5.1f}   │")
    print("    └─────────────────────────────────────────────────────────────────────────────────┘")

    print("\n    [+] Traceable Scientific Evidence Lineage:")
    for obs in site01_explanation.evidence_lineage["observations_grounding"]:
        print(f"        • [{obs['sensor']}] Product: {obs['product_id']}")
    fidelity = site01_explanation.evidence_lineage["registration_fidelity"]
    print(f"        • Cross-Modal Alignment Fidelity: RMSE {fidelity['rmse_pixels']} px, Inlier Ratio {fidelity['inlier_ratio']*100:.0f}%")

    print(f"\n    [+] Generated Natural-Language Decision Rationale:\n        \"{site01_explanation.summary_text}\"")

    # 2. Evaluate Site 02 (Steep Crater Wall - Rejected)
    print("\n" + "-" * 72)
    print("[*] Generating XAI Justification for Site Rejection (Crater Escarpment)...")
    site02_explanation = selector.explain_site(
        site_id="site_candidate_03_escarpment",
        site_name="Candidate Site #03 (South-West Escarpment)",
        coordinates={"lat": -72.875, "lon": 42.919},
        terrain_profile={"slope": {"mean_deg": 20.04}, "roughness_rms_m": 2.65},
        solar_profile={"illumination_fraction_pct": 25.0},
        resource_profile={"hydroxyl_absorption_bd3000_pct": 1.2, "hydroxyl_indicator_confidence": 0.05},
        hazard_context={"nearest_hazard_distance_m": 120.0, "nearest_hazard_type": "Boulder Field Escarpment"},
    )
    print(f"    FINAL SUITABILITY SCORE: {site02_explanation.final_score:.1f} / 100")
    print(f"    STATUS:                 {site02_explanation.recommendation}")
    print(f"    Rationale:              \"{site02_explanation.summary_text}\"")

    # 3. Export Artifacts
    out_dir = Path("outputs/nexus_xai")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "xai_site_selection_report.json"

    data_out = {
        "candidate_sites": [
            site01_explanation.to_dict(),
            site02_explanation.to_dict(),
        ]
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data_out, f, indent=2)

    print(f"\n[✓] XAI Explanation Report: {report_path}")
    print("=" * 72)
    print(" NEXUS POC 5 COMPLETED SUCCESSFULLY")
    print("=" * 72)


if __name__ == "__main__":
    run_demo()
