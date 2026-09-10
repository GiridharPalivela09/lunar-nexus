"""Mathematical and Geometric Rigor Tests for Spatial Overlap Engine."""

import pytest
from shapely.geometry import Polygon, box
from packages.data_pipeline.footprint_engine import FootprintEngine
from packages.data_pipeline.overlap_engine import calculate_overlap, OverlapAnalysisResult


class TestSpatialOverlapMathematicalCorrectness:
    """Rigorous mathematical tests asserting exact overlap geometry and area ratios."""

    @pytest.fixture
    def engine(self):
        return FootprintEngine()

    def test_case_1_disjoint_footprints(self, engine):
        """Case 1: Two observations with zero geographic intersection -> overlap = 0.0."""
        # Source in Boguslawsky South Pole region
        src = box(24.0, -74.5, 28.0, -72.0)
        # Reference far away in Apollo 17 equatorial region
        ref = box(30.0, 20.0, 32.0, 22.0)

        result = calculate_overlap(src, ref, footprint_engine=engine)
        assert isinstance(result, OverlapAnalysisResult)
        assert result.intersects is False
        assert result.intersection_polygon is None
        assert result.intersection_area == 0.0
        assert result.overlap_ratio_source == 0.0
        assert result.overlap_ratio_reference == 0.0
        assert result.overlap_confidence == 0.0

    def test_case_2_partial_overlap_mathematical_precision(self, engine):
        """Case 2: Partial overlap with known geometric geometry.
        Assert exact mathematical area ratios:
        Src: [0, 0] to [2, 2] -> Area 4 deg^2
        Ref: [1, 0] to [3, 2] -> Area 4 deg^2
        Intersection: [1, 0] to [2, 2] -> Area 2 deg^2
        Expected: exactly 50% overlap for both source and reference.
        """
        src = box(0.0, 0.0, 2.0, 2.0)
        ref = box(1.0, 0.0, 3.0, 2.0)

        result = calculate_overlap(src, ref, footprint_engine=engine)
        assert result.intersects is True
        assert result.intersection_polygon is not None

        # Verify 50% source overlap and 50% reference overlap within spherical tolerance
        assert pytest.approx(result.overlap_ratio_source, 0.02) == 0.50
        assert pytest.approx(result.overlap_ratio_reference, 0.02) == 0.50
        assert result.overlap_confidence > 0.0

    def test_case_3_complete_containment_asymmetric_ratio(self, engine):
        """Case 3: One footprint completely contains another.
        Src: [1, 1] to [2, 2] (smaller, Area 1)
        Ref: [0, 0] to [4, 4] (larger, Area 16)
        Expected:
        - overlap_ratio_source == 1.0 (100% of source is inside reference)
        - overlap_ratio_reference == 1/16 ~ 0.0625 (6.25% of reference is covered)
        """
        src = box(1.0, 1.0, 2.0, 2.0)
        ref = box(0.0, 0.0, 4.0, 4.0)

        result = calculate_overlap(src, ref, footprint_engine=engine)
        assert result.intersects is True
        assert pytest.approx(result.overlap_ratio_source, 0.02) == 1.0
        assert pytest.approx(result.overlap_ratio_reference, 0.02) == (1.0 / 16.0)

    def test_case_4_identical_footprints(self, engine):
        """Case 4: Identical footprints -> exactly 100% overlap for both."""
        footprint = box(24.0, -74.5, 28.0, -72.0)
        result = calculate_overlap(footprint, footprint, footprint_engine=engine)

        assert result.intersects is True
        assert pytest.approx(result.overlap_ratio_source, 1e-4) == 1.0
        assert pytest.approx(result.overlap_ratio_reference, 1e-4) == 1.0
        assert result.overlap_confidence > 0.90

    def test_case_5_edge_touching_zero_area(self, engine):
        """Case 5: Touching at the border only (line intersection, 0 area) -> treated as non-overlapping."""
        src = box(0.0, 0.0, 2.0, 2.0)
        ref = box(2.0, 0.0, 4.0, 2.0)  # Touches along line x=2.0

        result = calculate_overlap(src, ref, footprint_engine=engine)
        assert result.intersects is False
        assert result.intersection_area == 0.0
        assert result.overlap_ratio_source == 0.0

    def test_case_6_empty_or_invalid_geometry_handling(self, engine):
        """Case 6: Empty geometries must be handled gracefully without crashing."""
        empty_poly = Polygon()
        valid_poly = box(0.0, 0.0, 2.0, 2.0)

        res1 = calculate_overlap(empty_poly, valid_poly, footprint_engine=engine)
        assert res1.intersects is False
        assert res1.intersection_area == 0.0

        res2 = calculate_overlap(valid_poly, empty_poly, footprint_engine=engine)
        assert res2.intersects is False

    def test_case_7_invalid_types_raise_type_error(self, engine):
        """Case 7: Unsupported data types raise TypeError."""
        valid_poly = box(0.0, 0.0, 2.0, 2.0)
        with pytest.raises(TypeError):
            calculate_overlap("not_a_polygon", valid_poly, footprint_engine=engine)

        with pytest.raises(TypeError):
            calculate_overlap(valid_poly, {"invalid": "dict"}, footprint_engine=engine)
