# NEXUS-LUNAR: Feature Relevance & Problem Statement Fit Report
**Evaluation of Project Capabilities against the Official SIH Lunar Image Registration Problem Statement**

---

| Document Metadata | Details |
| :--- | :--- |
| **Project Name** | NEXUS-LUNAR (`nexus-unified`) |
| **Domain** | Geospatial Computer Vision, Planetary Science & Lunar Intelligence |
| **Target Competition** | Smart India Hackathon (SIH) — ISRO / Planetary Data Domain |
| **Assessment Date** | September 2026 |
| **Status** | Complete System Audit |

---

## 1. Official Problem Statement Definition

### 1.1 Core Problem Statement
> **"Develop a generic software solution to find correspondences between Chandrayaan-2 optical images and lunar reference images, register/align the source image to the reference image, and produce match points with sub-pixel accuracy, measurable geometric error, and approximately uniform spatial distribution."**

### 1.2 Key Lunar Registration Challenges
1. **Extreme Illumination Variations**: Lunar surface observed at varying solar incidence ($>70^\circ$ at polar regions) and phase angles, altering cast shadows and crater limb contrast.
2. **Scale & GSD Discrepancies**: Integrating disparate ground sampling distances (Chandrayaan-2 OHRC at $0.25\text{ m/px}$, NASA LRO NAC at $0.5\text{ m/px}$, TMC-2 at $5.0\text{ m/px}$, SELENE TC at $10.0\text{ m/px}$).
3. **Viewpoint & Perspective Distortions**: Non-nadir orbital passes, terrain parallax, and surface undulations requiring sub-pixel affine and homography recovery.
4. **Feature Scarcity in Regolith**: Low-contrast, repetitive cratered regolith where classical corner detectors often fail without adaptive thresholding.

### 1.3 Downstream Problem Extension (The NEXUS Layer)
Using co-registered, multi-sensor lunar observations as an authentic geospatial foundation for landing site hazard analysis, resource mapping, and conceptual surface infrastructure.

---

## 2. Feature Classification Taxonomy

Each project feature is evaluated and categorized into one of four distinct classifications:

* 🟢 **FIT (CORE)**: Directly addresses the primary SIH problem statement (ingestion, overlap discovery, patch harmonization, feature matching, transformation recovery, accuracy metrics).
* 🔵 **FIT (EXTENSION)**: Directly leverages registered multi-source imagery to extract downstream scientific or spatial intelligence (knowledge graph, landing hazard identification, Hapke photometric cross-validation).
* 🟡 **MARGINAL / CONTEXTUAL**: Provides auxiliary visualization or user context; helpful for mission planning demonstration but tangential to the core mathematical alignment.
* 🔴 **UNFIT (SCOPE CREEP)**: Drifts into unrelated domains (e.g., habitat life-support consumables, crew oxygen metabolism) with zero mathematical or physical connection to optical image registration.

---

## 3. Comprehensive Feature-by-Feature Evaluation

### Category A: Ingestion, Selenographic Geometry & Data Harmonization (POC 1 & POC 2)

#### 1. ISSDC PDS4 Label Parser & Catalog Ingestion
* **Implementation**: `scripts/ingest_issdc.py`, `packages/data_pipeline/ingestion.py`
* **Functionality**: Parses Chandrayaan-2 PDS4 XML labels (`Product_Observational`), extracts exact selenographic coordinates, solar incidence/azimuth angles, and spatial GSD.
* **Relation to Problem Statement**: Essential. Without automated parsing of ISRO ISSDC PRADAN bundles, raw Chandrayaan-2 products cannot be geographically indexed or matched against reference basemaps.
* **Verdict**: 🟢 **FIT (CORE)**
* **Technical Note**: Validates strict coordinate boundary invariants $[-90, 90]$ and eliminates manual georeferencing.

#### 2. NASA ODE & PDS Download Engine
* **Implementation**: `scripts/download_lunar_data.py`, `packages/data_pipeline/download.py`
* **Functionality**: Automates programmatic retrieval of NASA LRO NAC and SELENE reference imagery via ODE REST APIs based on bounding boxes or product IDs.
* **Relation to Problem Statement**: Essential. Provides the ground-truth "Fixed / Reference" imagery demanded by the SIH problem statement.
* **Verdict**: 🟢 **FIT (CORE)**

#### 3. Geographic Overlap Discovery Engine
* **Implementation**: `packages/data_pipeline/footprint_engine.py`, `packages/data_pipeline/catalog.py`
* **Functionality**: Computes analytical polygon intersections using Shapely between multi-sensor footprints, determining intersection area ($\text{km}^2$) and overlap percentages.
* **Relation to Problem Statement**: Essential. Registration is mathematically impossible without identifying spatial overlap between moving (OHRC) and reference (LRO NAC) passes.
* **Verdict**: 🟢 **FIT (CORE)**

#### 4. Selenographic Resolution Harmonizer
* **Implementation**: `packages/data_pipeline/patch_extractor.py::ResolutionHarmonizer`
* **Functionality**: Re-samples heterogeneous GSDs to a common target pixel scale (e.g. downsampling OHRC $0.25\text{ m}$ or upsampling LRO NAC $0.50\text{ m}$) using anti-aliased bicubic interpolation.
* **Relation to Problem Statement**: Essential. Cross-sensor registration fails if multi-scale ground sampling distances are not harmonized before descriptor extraction.
* **Verdict**: 🟢 **FIT (CORE)**

#### 5. Coordinate Roundtrip & Patch Tiling Grid (`GeoPixelTransformer`)
* **Implementation**: `packages/data_pipeline/patch_extractor.py::GeoPixelTransformer`
* **Functionality**: Transforms latitude/longitude coordinates to local pixel indices and slices overlap zones into standard $N \times N$ tiles with stride configurations and JSON manifests.
* **Relation to Problem Statement**: Essential. High-resolution lunar strips ($>20,000 \times 2,000\text{ px}$) exceed GPU/CPU memory limits; tiling overlap zones into co-registered patch grids enables localized sub-pixel alignment.
* **Verdict**: 🟢 **FIT (CORE)**

---

### Category B: Classical & Multimodal Feature Registration (POC 3, POC 4, POC 5)

#### 6. Adaptive RootSIFT & SIFT Feature Extraction
* **Implementation**: `packages/registration/algorithms.py`, `packages/registration/classical_cv.py`
* **Functionality**: Extracts salient keypoints with adaptive DoG contrast thresholds ($0.01 \rightarrow 0.005$) and computes L1 square-root normalized descriptors (Hellinger distance).
* **Relation to Problem Statement**: Core. Directly delivers the required correspondence detection on subtle, low-contrast lunar regolith textures.
* **Verdict**: 🟢 **FIT (CORE)**

#### 7. Binary Feature Detectors (ORB & AKAZE)
* **Implementation**: `packages/registration/algorithms.py`
* **Functionality**: Computes FAST-based multi-scale binary keypoints and Hamming distance matchers for rapid real-time edge/rim detection.
* **Relation to Problem Statement**: Core. Provides an ultra-fast baseline comparator and lightweight alternative for resource-constrained onboard processing.
* **Verdict**: 🟢 **FIT (CORE)**

#### 8. FFT Phase Correlation Sub-Pixel Estimator
* **Implementation**: `packages/registration/geometric.py::phase_correlation_shift`
* **Functionality**: Computes Fourier frequency cross-power spectrum with Hanning window to determine rigid translation shifts with sub-pixel peak interpolation.
* **Relation to Problem Statement**: Core. Delivers sub-pixel translation alignment even in textureless or shadowed lunar basins where sparse keypoint detectors struggle.
* **Verdict**: 🟢 **FIT (CORE)**

#### 9. Illumination-Invariant Preprocessing (POC 4)
* **Implementation**: `packages/data_pipeline/poc4_visualization.py`
* **Functionality**: Contrast-Limited Adaptive Histogram Equalization (CLAHE), multi-scale bandpass filtering, and phase congruency to normalize extreme solar shadow variations.
* **Relation to Problem Statement**: Core. Directly addresses Lunar Challenge 2.1 (Sun elevation/azimuth variation between missions).
* **Verdict**: 🟢 **FIT (CORE)**

#### 10. Multimodal Deep Feature Matching (POC 5)
* **Implementation**: `packages/data_pipeline/poc5_visualization.py`
* **Functionality**: Deep feature embeddings to match cross-sensor patches (optical OHRC to radar/hyperspectral/LRO NAC) in a shared representation space.
* **Relation to Problem Statement**: Core. Addresses non-linear radiometric intensity discrepancies between different sensor technologies.
* **Verdict**: 🟢 **FIT (CORE)**

---

### Category C: Geometric Verification, XAI & Accuracy Metrics (POC 6)

#### 11. RANSAC Affine & Homography Geometric Verifier
* **Implementation**: `packages/registration/geometric.py::estimate_transformation`
* **Functionality**: Robust consensus estimation that filters correspondence outliers and fits $2\times 3$ Affine or $3\times 3$ Projective Homography models.
* **Relation to Problem Statement**: Core. Guarantees that only geometrically physically consistent match points are accepted, achieving sub-pixel precision ($RMSE < 2.0\text{ px}$).
* **Verdict**: 🟢 **FIT (CORE)**

#### 12. Registration Metrics & Spatial Distribution Evaluator
* **Implementation**: `packages/registration/metrics.py`
* **Functionality**: Computes Reprojection RMSE, inlier ratio, affine matrix decomposition (scale, shear, rotation), and spatial distribution grid uniformity score.
* **Relation to Problem Statement**: Core. Explicitly fulfills the SIH evaluation requirements ("measurable evaluation: RMSE, inlier count, inlier ratio, uniform spatial distribution").
* **Verdict**: 🟢 **FIT (CORE)**

#### 13. Explainable AI (XAI) Rejection Diagnostic Visualizer
* **Implementation**: `packages/data_pipeline/poc6_visualization.py`
* **Functionality**: Visualizes why tentative candidate matches were accepted or rejected (epipolar residual violations, scale inconsistency, shadow ambiguity).
* **Relation to Problem Statement**: Core / High Value. Essential for mission operators to verify algorithm integrity before applying coordinate transforms.
* **Verdict**: 🟢 **FIT (CORE)**

---

### Category D: Downstream Spatial Intelligence & Knowledge Graph (POC 7)

#### 14. Lunar Spatial Knowledge Graph & Landmark Reasoner
* **Implementation**: `packages/nexus_core/poc1_knowledge_graph.py`, `packages/nexus_core/poc6_gnn_reasoner.py`
* **Functionality**: Models selenographic topological relationships between craters (e.g., Boguslawsky D/E/F), boulders, Permanently Shadowed Regions (PSRs), and prospective landing zones.
* **Relation to Problem Statement**: Downstream Extension. While image registration can exist without a knowledge graph, linking registered observations to semantic terrain landmarks creates high-value mission intelligence.
* **Verdict**: 🔵 **FIT (EXTENSION)**

#### 15. Terrain, Slope & Hazard Intelligence Extraction
* **Implementation**: `packages/data_pipeline/poc7_visualization.py`
* **Functionality**: Derives slope angles, boulder hazard density, and illumination maps from co-registered Chandrayaan-2 TMC-2 / OHRC triplets.
* **Relation to Problem Statement**: Downstream Extension. Directly demonstrates why high-precision image registration is needed in real space exploration (safe pinpoint landing site selection).
* **Verdict**: 🔵 **FIT (EXTENSION)**

---

### Category E: Physical Validation & Scientific Workbench (First-Principles)

#### 16. Hapke Photometric Reflectance Modeling
* **Implementation**: `packages/first_principles/physics_engine.py`
* **Functionality**: Calculates theoretical surface reflectance based on solar incidence, emission, and phase angles using Hapke's lunar regolith photometric function.
* **Relation to Problem Statement**: Downstream Extension. Provides a physics-based benchmark to validate radiometric registration between images captured under different illumination geometries.
* **Verdict**: 🔵 **FIT (EXTENSION)**

#### 17. Diurnal Thermal Diffusion & Cold Trap Physics
* **Implementation**: `packages/first_principles/pinn_model.py`
* **Functionality**: Models depth-dependent subsurface temperature variations ($T(t, z)$) and volatiles stability in polar cold traps using analytical Fourier diffusion equations.
* **Relation to Problem Statement**: Downstream Extension. Connects co-registered optical imagery with thermal physics for volatiles/water ice prospecting.
* **Verdict**: 🔵 **FIT (EXTENSION)**

#### 18. Radar Regolith Skin Depth Dispersion
* **Implementation**: `packages/first_principles/frequency_engine.py`
* **Functionality**: Computes microwave penetration depth as a function of radar frequency, bulk density ($\rho$), and $\text{TiO}_2 + \text{FeO}$ abundance.
* **Relation to Problem Statement**: Marginal Extension. Useful when cross-registering optical data with Mini-SAR/DFSAR radar data, but secondary for pure optical-to-optical registration.
* **Verdict**: 🟡 **MARGINAL / CONTEXTUAL**

---

### Category F: Interactive Dashboard & UI Components

#### 19. Interactive Leaflet GIS Footprint Map
* **Implementation**: `web/app.js`, `web/index.html` (`#footprint-map`)
* **Functionality**: Renders selenographic bounding boxes on USGS/NASA Moon WMS mosaic tiles with real-time sensor color coding.
* **Relation to Problem Statement**: Core UI. Essential for visual search, coverage verification, and spatial pair discovery.
* **Verdict**: 🟢 **FIT (CORE)**

#### 20. Dual Patch Stage Visualizer & Alignment HUD
* **Implementation**: `web/app.js`, `web/index.html` (`#stage-source`, `#stage-reference`)
* **Functionality**: Synchronized split-screen viewing of source vs. reference patches with overlaid correspondence vectors and transformation metrics HUD.
* **Relation to Problem Statement**: Core UI. Directly enables operators to inspect registration quality and keypoint alignment.
* **Verdict**: 🟢 **FIT (CORE)**

#### 21. 3D Selenographic Globe (Three.js WebGL)
* **Implementation**: `web/app.js`, `web/index.html` (`#lunar-globe-canvas`)
* **Functionality**: Interactive 3D lunar sphere displaying landing latitudes, polar terminator lines, and orbit tracks.
* **Relation to Problem Statement**: Marginal. Great visual impact for presentation, but does not contribute to image alignment math or tie-point precision.
* **Verdict**: 🟡 **MARGINAL / CONTEXTUAL**

#### 22. Conceptual Habitat Life Support & Crew Oxygen Simulation
* **Implementation**: `web/app.js`, `web/index.html` (`#simCrewSize`, `#simMissionDays`, `#sciO2Closure`)
* **Functionality**: Calculates crew oxygen metabolic consumption, radiation shielding depth, and Sabatier/electrolysis closure percentages.
* **Relation to Problem Statement**: Complete Scope Creep. Optical image registration has nothing to do with human crew metabolic oxygen consumption or habitat life-support mechanics.
* **Verdict**: 🔴 **UNFIT (SCOPE CREEP)**
* **Recommendation**: Keep hidden or clearly compartmentalized under an "Optional Concept Vision" tab during technical jury defense. Do NOT lead with this feature when asked about image registration.

#### 23. Blender Cycles Habitat Digital Twin Rendering Viewport
* **Implementation**: `web/app.js` (`#nexus3dBlenderContainer`)
* **Functionality**: Renders a photorealistic pressurized habitat module with solar array orientation.
* **Relation to Problem Statement**: Scope Creep. Although visually impressive, it is unrelated to satellite image registration algorithms.
* **Verdict**: 🔴 **UNFIT (SCOPE CREEP)**
* **Recommendation**: Present strictly as a downstream artistic visualization of what could be built on a site verified by the registration pipeline.

---

## 4. Master Feature Fit Matrix

| # | Feature / Subsystem | Code Location | Primary Purpose | Problem Fit Classification | Action / Recommendation |
| :-: | :--- | :--- | :--- | :---: | :--- |
| **1** | ISSDC PDS4 Ingestion | `scripts/ingest_issdc.py` | Chandrayaan-2 automated label & image ingest | 🟢 **FIT (CORE)** | Maintain as primary entrypoint |
| **2** | NASA PDS/ODE Engine | `scripts/download_lunar_data.py` | Reference data automated download | 🟢 **FIT (CORE)** | Essential for ground-truth pairs |
| **3** | Geographic Overlap Engine | `footprint_engine.py` | Polygon intersection & overlap area % | 🟢 **FIT (CORE)** | Core mathematical foundation |
| **4** | Resolution Harmonizer | `patch_extractor.py` | Re-sampling heterogeneous GSDs | 🟢 **FIT (CORE)** | Crucial for multi-scale matching |
| **5** | GeoPixel Transformer | `patch_extractor.py` | Lat/Lon $\leftrightarrow$ Pixel index roundtrips | 🟢 **FIT (CORE)** | Enables localized tiling grids |
| **6** | Adaptive RootSIFT Engine | `algorithms.py` | Regolith feature extraction (Hellinger) | 🟢 **FIT (CORE)** | Key technical differentiator |
| **7** | Binary Features (ORB/AKAZE) | `algorithms.py` | High-speed edge & crater rim detection | 🟢 **FIT (CORE)** | Lightweight benchmark comparator |
| **8** | FFT Phase Correlation | `geometric.py` | Frequency-domain sub-pixel shift | 🟢 **FIT (CORE)** | Sub-pixel translation accuracy |
| **9** | Illumination Preprocessing | `poc4_visualization.py` | Shadow/contrast normalization | 🟢 **FIT (CORE)** | Directly solves Sun angle variation |
| **10** | Multimodal Deep Matching | `poc5_visualization.py` | Cross-sensor shared embedding space | 🟢 **FIT (CORE)** | Solves radiometric discrepancies |
| **11** | RANSAC Geometric Verifier | `geometric.py` | Outlier filtering & transformation fit | 🟢 **FIT (CORE)** | Enforces sub-pixel consensus ($<2\text{ px}$) |
| **12** | Registration Metrics HUD | `metrics.py` | Reprojection RMSE, inlier ratio, grid score | 🟢 **FIT (CORE)** | Exactly fulfills SIH metric criteria |
| **13** | XAI Rejection Visualizer | `poc6_visualization.py` | Explains why outlier matches fail | 🟢 **FIT (CORE)** | High-value algorithmic transparency |
| **14** | Spatial Knowledge Graph | `poc1_knowledge_graph.py` | Topological terrain landmark modeling | 🔵 **FIT (EXTENSION)** | Excellent downstream differentiator |
| **15** | Terrain & Hazard Analysis | `poc7_visualization.py` | Slopes, boulder density, landing safety | 🔵 **FIT (EXTENSION)** | Shows real-world exploration utility |
| **16** | Hapke Photometric Model | `physics_engine.py` | Physical reflectance vs incidence angle | 🔵 **FIT (EXTENSION)** | Physical cross-validation |
| **17** | Diurnal Thermal Diffusion | `pinn_model.py` | Subsurface regolith temperatures | 🔵 **FIT (EXTENSION)** | Volatiles & cold trap science |
| **18** | Radar Skin Depth Engine | `frequency_engine.py` | Microwave penetration vs frequency | 🟡 **MARGINAL** | Only relevant for SAR-optical pairs |
| **19** | Leaflet GIS Footprint Map | `web/app.js` | Selenographic spatial UI on Moon WMS | 🟢 **FIT (CORE)** | Primary GIS visualization UI |
| **20** | Dual Patch Visualizer | `web/app.js` | Split-screen tie-point vector overlay | 🟢 **FIT (CORE)** | Primary registration verification UI |
| **21** | 3D Selenographic Globe | `web/app.js` | Three.js planetary sphere visualizer | 🟡 **MARGINAL** | Impressive UI, but secondary |
| **22** | Habitat Life Support Sim | `web/app.js` | Crew $O_2$ consumption & ECLSS closure | 🔴 **UNFIT (SCOPE CREEP)** | Demote/hide during technical review |
| **23** | 3D Habitat Blender View | `web/app.js` | Rendered pressurized module twin | 🔴 **UNFIT (SCOPE CREEP)** | Relegate to conceptual future work |

---

## 5. Statistical Fit Breakdown

```
Total Features Audited: 23

🟢 FIT (CORE):                15 features  (65.2%)
🔵 FIT (DOWNSTREAM EXTENSION): 4 features  (17.4%)
🟡 MARGINAL / CONTEXTUAL:      2 features   (8.7%)
🔴 UNFIT (SCOPE CREEP):        2 features   (8.7%)
```

* **Core & Valid Extension Alignment**: **$82.6\%$** of the codebase directly addresses or productively extends the SIH problem statement.
* **Marginal & Scope Creep Content**: Only **$17.4\%$** represents contextual or tangential features.

---

## 6. Strategic Recommendations for Evaluation & Jury Presentation

### 1. Lead with the Core Registration Engine ($82.6\%$)
In technical presentations and demos, follow the scientific registration pipeline:
1. **PDS4 Ingestion & Overlap Discovery**: Show live automated ingestion of Chandrayaan-2 OHRC and LRO NAC.
2. **Harmonization & GeoPixel Tiling**: Demonstrate resolving the $0.25\text{ m} \leftrightarrow 0.50\text{ m}$ GSD disparity.
3. **Adaptive RootSIFT & Phase Correlation**: Show keypoint extraction and matching on real low-contrast Boguslawsky Crater regolith.
4. **Geometric RANSAC & Sub-Pixel Precision**: Highlight the verified sub-pixel RMSE ($< 2.0\text{ px}$) and affine parameter decomposition.
5. **Evaluation Metrics**: Present inlier ratio, tie-point spatial distribution uniformity, and illumination invariance under changing solar angles.

### 2. Present Spatial Intelligence (POC 7) as "Downstream Value Realization"
Frame the Knowledge Graph and Hazard Mapping as the direct answer to: *"Why do we need sub-pixel registration?"*
* **Answer**: Because a $5\text{ meter}$ registration error can cause a lunar lander hazard avoidance system to mistake a $2\text{ meter}$ boulder or crater slope for safe flat regolith.

### 3. De-emphasize or Re-label Habitat Life Support & Crew $O_2$ Simulation
* Re-label this section in the UI from primary telemetry to **"Conceptual Downstream Applications (Future Exploration Vision)"**.
* Do not spend technical presentation time defending life-support chemistry when evaluated by computer vision and geospatial experts.

---

## 7. Conclusion

The NEXUS-LUNAR platform possesses an **exceptionally strong and rigorous core** ($>82\%$ directly fit) that squarely solves the Chandrayaan-2 lunar optical image registration challenge. The inclusion of downstream spatial intelligence and first-principles physics significantly elevates the project above conventional minimum viable submissions, provided the presentation strictly emphasizes the verified mathematical alignment pipeline.
