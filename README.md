# NEXUS-LUNAR: Lunar Data Ingestion & Download Pipeline

This module provides an automated acquisition, parsing, and spatial catalog indexing pipeline for:
- **Chandrayaan-2**: OHRC (0.25m), TMC-2 (5m), IIRS (80m, hyperspectral) from ISRO ISSDC PRADAN.
- **NASA LRO**: LRO NAC (Narrow Angle Camera, 0.5m) from NASA PDS & ASU LROC archive.
- **JAXA SELENE (Kaguya)**: Terrain Camera (TC, 10m) and Multiband Imager (MI).

---

## 1. Installation

Install required dependencies:
```bash

python3 -m pip install -r requirements.txt
```

---

## 2. Interactive Web UI Dashboard & Overlap Studio

Launch the full-screen interactive Lunar Intelligence Dashboard with Lunar GIS footprint map, catalog browser, and POC 2 Patch Studio:
```bash
python scripts/launch_dashboard.py
```
Open **[http://localhost:8000](http://localhost:8000)** in any browser.

---

## 3. Quick Start: Benchmark Dataset Generation

Generate co-registered benchmark observations (Chandrayaan-2 OHRC + LRO NAC + TMC-2 over the Lunar South Pole Boguslawsky region):
```bash
python scripts/download_lunar_data.py --benchmark
```


---

## 3. NASA PDS & LRO NAC Direct Downloads

Download LRO NAC or SELENE reference observations by bounding box or product ID via NASA ODE REST API:

### Search & download by region (e.g. South Pole):
```bash
python3 scripts/download_lunar_data.py \
  --sensor LRO_NAC \
  --min-lat -85.0 --max-lat -80.0 \
  --min-lon 0.0 --max-lon 30.0 \
  --limit 5
```

### Download specific product:
```bash
python3 scripts/download_lunar_data.py \
  --sensor LRO_NAC \
  --product-id M1144485705LR
```

---

## 4. Chandrayaan-2 ISSDC PRADAN Ingestion

When downloading data bundles from [ISRO ISSDC PRADAN](https://chmapbrowse.issdc.gov.in/):

### Ingest downloaded ZIP/TAR bundle:
```bash
python3 scripts/ingest_issdc.py --input /path/to/downloaded_ch2_bundle.zip
```

### Ingest folder containing PDS4 XML labels and images:
```bash
python3 scripts/ingest_issdc.py --input /path/to/ch2_raw_folder/
```

The pipeline automatically:
1. Parses PDS4 XML labels (`Product_Observational`, `Observation_Area`, `Discipline_Area`, `Geometry`).
2. Extracts bounding coordinates, spatial resolution, and solar illumination angles (incidence, azimuth, phase).
3. Generates 8-bit normalized preview images.
4. Indexes observations into `data/catalog.json`.

---

## 5. Catalog Search & Overlapping Pair Discovery

### List all indexed observations:
```bash
python3 scripts/query_catalog.py --list
```

### Find candidate co-registration pairs between OHRC and LRO NAC:
```bash
python3 scripts/query_catalog.py --find-pairs --source OHRC --reference LRO_NAC --min-overlap 5.0
```

### Spatial query inside a bounding box:
```bash
python3 scripts/query_catalog.py --min-lat -75 --max-lat -70 --min-lon 20 --max-lon 35
```

---

## 6. POC 2: Geographic Overlap & Resolution-Aware Patch Extraction

Extract physical co-registered image patches between multi-sensor observations (e.g., Chandrayaan-2 OHRC vs. LRO NAC):

### Extract patches for all overlapping pairs in catalog:
```bash
python scripts/extract_overlap_patches.py --all-pairs --patch-size 512 --stride 256
```

### Extract patches for specific observation IDs:
```bash
python scripts/extract_overlap_patches.py \
  --source-id ch2_ohr_ncp_20230915t041230_boguslawsky_d18 \
  --reference-id M1345982701LR_BOGUSLAWSKY_REF \
  --patch-size 256 --stride 128 \
  --strategy match_coarser
```

### Output:
- Saves paired patches (`patch_0001_src.png`, `patch_0001_ref.png`) to `data/processed/patches/<pair_id>/`.
- Generates `patch_manifest.json` containing ground coordinates, resolution, overlap percentage, and confidence score.

---

## 7. Directory Layout


```text
SIH-Lunar/
├── packages/
│   └── data_pipeline/
│       ├── __init__.py
│       ├── models.py             # Pydantic schemas (LunarObservation, BoundingBox, etc.)
│       ├── pds_ode_client.py     # NASA ODE REST API & ASU LROC client
│       ├── issdc_client.py       # Chandrayaan-2 PDS4 parser & unzipper
│       ├── metadata_parser.py    # Unified PDS3/PDS4/GeoTIFF metadata parser
│       ├── catalog.py            # Spatial index & polygon overlap engine
│       └── sample_benchmark.py   # Ground-truth test region generator
├── scripts/
│   ├── download_lunar_data.py   # Multi-sensor download CLI
│   ├── ingest_issdc.py          # ISSDC bulk ingest CLI
│   └── query_catalog.py         # Overlap pair finder CLI
├── data/
│   ├── raw/                     # Sensor-organized raw data (ohrc/, tmc2/, lro/, etc.)
│   ├── processed/
│   └── catalog.json             # Spatial index database
└── requirements.txt
```
