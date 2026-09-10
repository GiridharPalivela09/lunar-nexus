# NEXUS-LUNAR: End-to-End Test Traceability Matrix

This document establishes the bidirectional traceability from project requirements to software components, test cases, and verification outcomes.

| Requirement ID | Feature Area | Technical Component | Test Suite & Method | Verification Objective | Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **REQ-GEO-01** | Data Pipeline | `packages/data_pipeline/models.py` | `test_observation_models.py` | Lunar coordinate bounds [-90, 90] & schema validation | ✅ PASSED |
| **REQ-GEO-02** | Spatial Math | `packages/data_pipeline/footprint_engine.py` | `test_spatial_overlap_math.py` | Disjoint, partial, containment, identical intersection math | ✅ PASSED |
| **REQ-GEO-03** | Observation Catalog | `packages/data_pipeline/catalog.py` | `test_catalog_system.py` | Catalog search, bounding box spatial query, overlapping pairs | ✅ PASSED |
| **REQ-GEO-04** | Patch Harmonization | `packages/data_pipeline/patch_extractor.py` | `test_patch_extraction_pipeline.py` | GeoPixelTransformer roundtrip & ResolutionHarmonizer GSD | ✅ PASSED |
| **REQ-CV-01** | Feature Detection | `packages/registration/algorithms.py` | `test_cv_registration_pipeline.py` | SIFT, RootSIFT L1-sqrt norm, ORB, AKAZE extraction | ✅ PASSED |
| **REQ-CV-02** | Transformation Estimation | `packages/registration/geometric.py` | `test_cv_registration_pipeline.py` | RANSAC affine recovery with RMSE < 2.0 px & Phase Correlation | ✅ PASSED |
| **REQ-API-01** | Dashboard REST API | `scripts/launch_dashboard.py` | `test_dashboard_api.py` | REST endpoints (/api/catalog, /api/pairs, /api/manifest, static PNG) | ✅ PASSED |
| **REQ-REL-01** | Project Relevance | Full Pipeline Integration | `test_dashboard_project_relevance.py` | Traceability: Obs -> Footprint -> Overlap -> Patch -> CV -> PINN | ✅ PASSED |
| **REQ-E2E-01** | Browser UI Automation | `web/index.html`, `web/app.js` | `test_playwright_e2e.py` | Tab switching, map display, 3D globe, patch visualizer | ✅ PASSED |
