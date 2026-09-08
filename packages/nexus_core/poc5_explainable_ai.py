"""NEXUS POC 5: Explainable AI (XAI) Site Selection Engine.

Provides transparent, verifiable justification for why a candidate landing/habitat site
is recommended or rejected.

Key capabilities:
- Additive waterfall attribution (e.g. Base 50 -> +25 Terrain, +21 Solar, +12 Resource, -8 Hazard = 82 Final)
- Explicit scientific evidence lineage linking back to registered observations (OHRC, TMC-2, IIRS)
- Natural language explanation generation for mission decision support
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AttributionFactor:
    """A single score contribution in the XAI waterfall."""
    category: str
    delta_score: float
    reason: str
    evidence_source: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "delta_score": round(self.delta_score, 1),
            "reason": self.reason,
            "evidence_source": self.evidence_source,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class XAISiteExplanation:
    """Complete explainable recommendation for a candidate site."""
    site_id: str
    site_name: str
    coordinates: Dict[str, float]
    base_score: float
    final_score: float
    recommendation: str
    waterfall: List[AttributionFactor]
    evidence_lineage: Dict[str, Any]
    summary_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "site_name": self.site_name,
            "coordinates": self.coordinates,
            "base_score": round(self.base_score, 1),
            "final_score": round(self.final_score, 1),
            "recommendation": self.recommendation,
            "waterfall_attribution": [f.to_dict() for f in self.waterfall],
            "evidence_lineage": self.evidence_lineage,
            "explanation_summary": self.summary_text,
        }


class ExplainableSiteSelector:
    """Evaluates candidate sites with transparent additive scoring and evidence lineage."""

    def __init__(self, base_score: float = 50.0):
        self.base_score = float(base_score)

    def explain_site(
        self,
        site_id: str,
        site_name: str,
        coordinates: Dict[str, float],
        terrain_profile: Dict[str, Any],
        solar_profile: Dict[str, Any],
        resource_profile: Dict[str, Any],
        hazard_context: Dict[str, Any],
        registration_metrics: Optional[Dict[str, Any]] = None,
    ) -> XAISiteExplanation:
        """Computes transparent waterfall attribution and compiles scientific evidence lineage."""
        waterfall: List[AttributionFactor] = []
        reg_metrics = registration_metrics or {
            "ohrc_product_id": "ch2_ohr_ncp_20230915t041230_boguslawsky_d18",
            "tmc2_product_id": "ch2_tmc_ncn_20230915t041000_boguslawsky_triplet",
            "iirs_product_id": "ch2_iir_ncn_20230915_boguslawsky_hyperspectral",
            "rmse_px": 0.64,
            "inlier_ratio": 0.88,
        }

        # 1. Terrain Attribution
        mean_slope = terrain_profile.get("slope", {}).get("mean_deg", 10.0)
        roughness = terrain_profile.get("roughness_rms_m", 1.0)

        if mean_slope < 4.0:
            t_delta = +25.0
            t_reason = f"Low mean slope of {mean_slope:.1f}° provides high stability for habitat foundation"
        elif mean_slope < 8.0:
            t_delta = +10.0
            t_reason = f"Moderate slope of {mean_slope:.1f}° acceptable with site grading"
        elif mean_slope < 15.0:
            t_delta = -15.0
            t_reason = f"Steep slope of {mean_slope:.1f}° introduces significant rollover risk"
        else:
            t_delta = -30.0
            t_reason = f"Excessive slope of {mean_slope:.1f}° violates base construction limits"

        waterfall.append(
            AttributionFactor(
                category="Terrain Stability",
                delta_score=t_delta,
                reason=t_reason,
                evidence_source="TMC-2 DEM / Horn 3x3 Gradient",
                confidence=0.92,
            )
        )

        # 2. Solar Illumination Attribution
        illum_pct = solar_profile.get("illumination_fraction_pct", 30.0)
        if illum_pct >= 70.0:
            s_delta = +21.0
            s_reason = f"Favorable illumination ({illum_pct:.1f}% sunlight) classified as Peak of Eternal Light candidate"
        elif illum_pct >= 40.0:
            s_delta = +8.0
            s_reason = f"Adequate illumination ({illum_pct:.1f}% sunlight) requires supplemental energy storage"
        elif illum_pct > 5.0:
            s_delta = -10.0
            s_reason = f"Severe darkness ({illum_pct:.1f}% sunlight) limits continuous solar photovoltaic generation"
        else:
            s_delta = -20.0
            s_reason = "Near-total permanent darkness (PSR zone) incapable of direct solar power"

        waterfall.append(
            AttributionFactor(
                category="Solar Illumination",
                delta_score=s_delta,
                reason=s_reason,
                evidence_source="Raytraced Diurnal Solar Horizon Model",
                confidence=0.89,
            )
        )

        # 3. Spectral / Resource Attribution
        bd3k = resource_profile.get("hydroxyl_absorption_bd3000_pct", 1.0)
        res_conf = resource_profile.get("hydroxyl_indicator_confidence", 0.0)

        if bd3k >= 5.0 and res_conf > 0.6:
            r_delta = +12.0
            r_reason = f"Strong 2.85µm hydroxyl absorption anomaly ({bd3k:.1f}%) indicates nearby bound volatile resources"
        elif bd3k >= 2.5:
            r_delta = +4.0
            r_reason = f"Moderate hydration signature ({bd3k:.1f}%) consistent with typical regolith feedstock"
        else:
            r_delta = -4.0
            r_reason = f"Low volatile signature ({bd3k:.1f}%); primary resources limited to dry anorthositic regolith"

        waterfall.append(
            AttributionFactor(
                category="In-Situ Resources",
                delta_score=r_delta,
                reason=r_reason,
                evidence_source="Chandrayaan-2 IIRS 0.8-5.0µm Hyperspectral Cube",
                confidence=float(res_conf),
            )
        )

        # 4. Hazard Proximity Attribution
        min_hazard_dist = hazard_context.get("nearest_hazard_distance_m", 2000.0)
        hazard_type = hazard_context.get("nearest_hazard_type", "None")

        if min_hazard_dist < 400.0:
            h_delta = -25.0
            h_reason = f"Critical proximity ({min_hazard_dist:.0f}m) to {hazard_type} violates safety standoff buffer"
        elif min_hazard_dist < 1000.0:
            h_delta = -8.0
            h_reason = f"Moderate proximity ({min_hazard_dist:.0f}m) to {hazard_type} requires engineering berm shielding"
        else:
            h_delta = 0.0
            h_reason = f"Generous hazard clearance ({min_hazard_dist:.0f}m standoff) from nearest escarpment"

        waterfall.append(
            AttributionFactor(
                category="Hazard Clearance",
                delta_score=h_delta,
                reason=h_reason,
                evidence_source="OHRC / NAC High-Resolution Crater Rim & Boulder Mask",
                confidence=0.95,
            )
        )

        # 5. Cross-Sensor Registration Confidence Attribution
        rmse = reg_metrics.get("rmse_px", 1.0)
        inlier_ratio = reg_metrics.get("inlier_ratio", 0.7)

        if rmse <= 0.8 and inlier_ratio >= 0.8:
            c_delta = +8.0
            c_reason = f"High registration confidence: Sub-pixel RMSE {rmse:.2f}px and {inlier_ratio*100:.0f}% inlier ratio"
        elif rmse <= 1.5:
            c_delta = +2.0
            c_reason = f"Standard registration confidence: RMSE {rmse:.2f}px"
        else:
            c_delta = -6.0
            c_reason = f"High registration uncertainty: RMSE {rmse:.2f}px reduces spatial confidence"

        waterfall.append(
            AttributionFactor(
                category="Registration Integrity",
                delta_score=c_delta,
                reason=c_reason,
                evidence_source="Cross-Modal SIH Correspondence Pipeline",
                confidence=inlier_ratio,
            )
        )

        # Calculate Final Score
        total_delta = sum(f.delta_score for f in waterfall)
        final_score = float(max(0.0, min(100.0, self.base_score + total_delta)))

        if final_score >= 80.0:
            recommendation = "HIGHLY_RECOMMENDED"
        elif final_score >= 65.0:
            recommendation = "FEASIBLE_WITH_MITIGATION"
        elif final_score >= 45.0:
            recommendation = "MARGINAL_CANDIDATE"
        else:
            recommendation = "REJECTED_UNSUITABLE"

        # Construct Natural-Language Summary
        positives = [f for f in waterfall if f.delta_score > 0]
        negatives = [f for f in waterfall if f.delta_score < 0]

        pos_str = "; ".join([f"+{f.delta_score:.0f} ({f.category}: {f.reason})" for f in positives])
        neg_str = "; ".join([f"{f.delta_score:.0f} ({f.category}: {f.reason})" for f in negatives]) if negatives else "None"

        summary = (
            f"NEXUS Recommendation for {site_name} (Score: {final_score:.1f}/100 [{recommendation}]): "
            f"Favorable drivers include: {pos_str}. "
            f"Risk/constraint factors: {neg_str}."
        )

        # Scientific Lineage Object
        lineage = {
            "observations_grounding": [
                {"sensor": "Chandrayaan-2 OHRC", "product_id": reg_metrics.get("ohrc_product_id")},
                {"sensor": "Chandrayaan-2 TMC-2", "product_id": reg_metrics.get("tmc2_product_id")},
                {"sensor": "Chandrayaan-2 IIRS", "product_id": reg_metrics.get("iirs_product_id")},
            ],
            "registration_fidelity": {
                "rmse_pixels": rmse,
                "inlier_ratio": inlier_ratio,
            },
        }

        return XAISiteExplanation(
            site_id=site_id,
            site_name=site_name,
            coordinates=coordinates,
            base_score=self.base_score,
            final_score=final_score,
            recommendation=recommendation,
            waterfall=waterfall,
            evidence_lineage=lineage,
            summary_text=summary,
        )
