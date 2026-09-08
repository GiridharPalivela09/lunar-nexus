"""Tests for NEXUS POC 5: Explainable AI (XAI) Site Selection Engine."""

import pytest

from packages.nexus_core.poc5_explainable_ai import (
    ExplainableSiteSelector,
    XAISiteExplanation,
)


def test_explainable_site_selector_initialization():
    selector = ExplainableSiteSelector(base_score=50.0)
    assert selector.base_score == 50.0


def test_site_01_north_rim_favorable_attribution():
    """Verify that Site 01 (North Rim Plateau) receives high recommendation and balanced waterfall."""
    selector = ExplainableSiteSelector(base_score=50.0)

    terrain_prof = {"slope": {"mean_deg": 2.38}, "roughness_rms_m": 0.29}
    solar_prof = {"illumination_fraction_pct": 72.2}
    resource_prof = {"hydroxyl_absorption_bd3000_pct": 7.04, "hydroxyl_indicator_confidence": 0.95}
    hazard_ctx = {"nearest_hazard_distance_m": 850.0, "nearest_hazard_type": "Steep Rim Escarpment"}
    reg_metrics = {"rmse_px": 0.64, "inlier_ratio": 0.88}

    explanation = selector.explain_site(
        site_id="site_01",
        site_name="Candidate Site #01 (North Rim)",
        coordinates={"lat": -72.674, "lon": 43.478},
        terrain_profile=terrain_prof,
        solar_profile=solar_prof,
        resource_profile=resource_prof,
        hazard_context=hazard_ctx,
        registration_metrics=reg_metrics,
    )

    assert isinstance(explanation, XAISiteExplanation)
    # Expected: 50 + 25 (terrain) + 21 (solar) + 12 (resource) - 8 (hazard) + 8 (reg) = 108 -> clipped to 100 or >= 85
    assert explanation.final_score >= 80.0
    assert explanation.recommendation == "HIGHLY_RECOMMENDED"
    assert len(explanation.waterfall) == 5

    categories = [f.category for f in explanation.waterfall]
    assert "Terrain Stability" in categories
    assert "Solar Illumination" in categories
    assert "Hazard Clearance" in categories

    # Evidence lineage must have all 3 sensors
    grounding = explanation.evidence_lineage["observations_grounding"]
    sensors = [g["sensor"] for g in grounding]
    assert "Chandrayaan-2 OHRC" in sensors
    assert "Chandrayaan-2 TMC-2" in sensors
    assert "Chandrayaan-2 IIRS" in sensors


def test_site_rejection_in_hazardous_psr():
    """Verify that a steep, permanently shadowed crater floor is rejected with clear negative attribution."""
    selector = ExplainableSiteSelector(base_score=50.0)

    terrain_prof = {"slope": {"mean_deg": 18.5}, "roughness_rms_m": 2.5}
    solar_prof = {"illumination_fraction_pct": 0.0}
    resource_prof = {"hydroxyl_absorption_bd3000_pct": 1.2, "hydroxyl_indicator_confidence": 0.1}
    hazard_ctx = {"nearest_hazard_distance_m": 150.0, "nearest_hazard_type": "Boulder Field"}

    explanation = selector.explain_site(
        site_id="site_bad",
        site_name="Steep Crater Wall",
        coordinates={"lat": -72.85, "lon": 43.10},
        terrain_profile=terrain_prof,
        solar_profile=solar_prof,
        resource_profile=resource_prof,
        hazard_context=hazard_ctx,
    )

    # All factors negative: 50 - 30 (terrain) - 20 (solar) - 4 (resource) - 25 (hazard) < 0 -> 0.0
    assert explanation.final_score < 40.0
    assert explanation.recommendation == "REJECTED_UNSUITABLE"
    assert "Steep slope" in explanation.summary_text or "Excessive slope" in explanation.summary_text
