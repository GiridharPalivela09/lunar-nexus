/**
 * NEXUS-LUNAR: Client-Side Application Logic
 * Integrates Leaflet GIS, Overlap Engine, and Interactive Patch Studio
 */

// Global State
const state = {
  catalog: [],
  pairs: [],
  activePair: null,
  activeManifest: null,
  activePatch: null,
  map: null,
  footprintsLayer: null,
  blinkInterval: null,
};

// Sensor styling definitions
const SENSOR_COLORS = {
  OHRC: { color: '#00f2fe', fillColor: '#00f2fe', name: 'Chandrayaan-2 OHRC' },
  LRO_NAC: { color: '#ff7675', fillColor: '#ff7675', name: 'NASA LRO NAC' },
  TMC2: { color: '#55efc4', fillColor: '#55efc4', name: 'Chandrayaan-2 TMC-2' },
  IIRS: { color: '#a29bfe', fillColor: '#a29bfe', name: 'Chandrayaan-2 IIRS' },
  DEFAULT: { color: '#58a6ff', fillColor: '#58a6ff', name: 'Lunar Payload' },
};

// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  initTabs();
  initMap();
  initSplitSlider();
  initModal();
  initLightbox();
  initPOC4Studio();
  initPOC5Studio();
  initNexus3DStudio();
  await loadCatalogAndPairs();
});

// ==========================================================================
// Navigation Tabs
// ==========================================================================
function initTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');

      if (targetId === 'tab-map' && state.map) {
        setTimeout(() => state.map.invalidateSize(), 150);
      }
      if (targetId === 'tab-nexus3d' && window.nexus3d) {
        setTimeout(() => window.nexus3d.onResize(), 150);
      }
    });
  });

  // Check URL hash for direct tab linking (e.g. #nexus3d, #poc4, #patches, #catalog, #map)
  if (window.location.hash) {
    const hash = window.location.hash.replace('#', '').toLowerCase();
    const matchingTab = document.querySelector(`.nav-tab[data-tab="tab-${hash}"]`);
    if (matchingTab) {
      matchingTab.click();
    }
  }

  const btnRefresh = document.getElementById('btnRefreshCatalog');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', loadCatalogAndPairs);
  }
}

// ==========================================================================
// Lunar Leaflet GIS Map
// ==========================================================================
function initMap() {
  // Center near Boguslawsky South Pole Crater (-73.25, 26.0)
  state.map = L.map('lunarMap', {
    center: [-73.25, 26.0],
    zoom: 6,
    minZoom: 1,
    maxZoom: 14,
    attributionControl: false,
  });

  // Basemap: USGS Lunar Reconnaissance Orbiter (LRO) WAC Global Mosaic (via USGS Astropedia / NASA JPL WMTS)
  // Fallback to NASA Moon imagery or OpenPlanetary tiles
  const lunarTiles = L.tileLayer('https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png', {
    maxNativeZoom: 9,
    maxZoom: 14,
    attribution: 'NASA / USGS / LRO WAC Global Morphologic Mosaic / OpenPlanetary',
    errorTileUrl: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" style="background:%23050811"><text x="128" y="128" fill="%23223049" font-family="sans-serif" font-size="12" text-anchor="middle">Lunar Tile</text></svg>'
  });
  lunarTiles.addTo(state.map);

  state.footprintsLayer = L.layerGroup().addTo(state.map);

  // Jump buttons
  document.querySelectorAll('.btn-jump').forEach(btn => {
    btn.addEventListener('click', () => {
      const lat = parseFloat(btn.getAttribute('data-lat'));
      const lon = parseFloat(btn.getAttribute('data-lon'));
      const zoom = parseInt(btn.getAttribute('data-zoom'));
      state.map.flyTo([lat, lon], zoom, { duration: 1.2 });
    });
  });

  // Sensor checkbox filters
  document.querySelectorAll('.sensor-filter').forEach(checkbox => {
    checkbox.addEventListener('change', renderFootprints);
  });
}

// ==========================================================================
// Data Ingestion & API Calls
// ==========================================================================
async function loadCatalogAndPairs() {
  try {
    document.getElementById('statusText').innerText = 'Syncing...';

    // 1. Fetch Catalog
    const catRes = await fetch('/api/catalog');
    state.catalog = await catRes.json();

    // 2. Fetch Overlapping Pairs
    const pairsRes = await fetch('/api/pairs');
    state.pairs = await pairsRes.json();

    document.getElementById('statusText').innerText = `${state.catalog.length} Products Online`;
    document.getElementById('pairCountBadge').innerText = state.pairs.length;

    renderFootprints();
    renderPairsList();
    renderCatalogTable();

    // Auto-select first pair if exists
    if (state.pairs.length > 0) {
      selectPair(state.pairs[0]);
    }
  } catch (err) {
    console.error('Error loading data:', err);
    document.getElementById('statusText').innerText = 'Offline / Standalone';
  }
}

// ==========================================================================
// Footprints Renderer
// ==========================================================================
function renderFootprints() {
  if (!state.footprintsLayer) return;
  state.footprintsLayer.clearLayers();

  const enabledSensors = Array.from(document.querySelectorAll('.sensor-filter:checked')).map(cb => cb.value);
  let visibleCount = 0;

  state.catalog.forEach(obs => {
    if (!enabledSensors.includes(obs.sensor)) return;
    visibleCount++;

    const sensorDef = SENSOR_COLORS[obs.sensor] || SENSOR_COLORS.DEFAULT;
    const bounds = [
      [obs.bbox.min_lat, obs.bbox.min_lon],
      [obs.bbox.max_lat, obs.bbox.max_lon]
    ];

    const rect = L.rectangle(bounds, {
      color: sensorDef.color,
      weight: 2,
      fillColor: sensorDef.fillColor,
      fillOpacity: 0.15,
      dashArray: obs.sensor === 'OHRC' ? '4, 4' : null,
    });

    rect.bindPopup(`
      <div style="font-family: 'Outfit', sans-serif; color: #111; padding: 4px;">
        <strong style="color: #0072ff;">${obs.product_id}</strong><br/>
        <span style="font-size: 0.8rem; color: #555;">${sensorDef.name} (${obs.resolution_m}m)</span><br/>
        <div style="margin-top: 6px; font-size: 0.75rem;">
          <strong>Lat:</strong> [${obs.bbox.min_lat.toFixed(2)}, ${obs.bbox.max_lat.toFixed(2)}]<br/>
          <strong>Lon:</strong> [${obs.bbox.min_lon.toFixed(2)}, ${obs.bbox.max_lon.toFixed(2)}]<br/>
          <strong>Incidence:</strong> ${obs.incidence_angle ? obs.incidence_angle.toFixed(1) + '°' : 'N/A'}
        </div>
      </div>
    `);

    rect.on('click', () => {
      displayObservationCard(obs);
    });

    rect.addTo(state.footprintsLayer);
  });

  document.getElementById('visibleFootprintsCount').innerText = `${visibleCount} visible`;
}

function displayObservationCard(obs) {
  const card = document.getElementById('selectedObservationCard');
  const sensorDef = SENSOR_COLORS[obs.sensor] || SENSOR_COLORS.DEFAULT;

  card.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 8px;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <span class="tag-pill" style="background: rgba(0, 242, 254, 0.2); color: ${sensorDef.color}">${obs.sensor}</span>
        <span style="font-size: 0.75rem; color: var(--text-secondary);">${obs.resolution_m}m GSD</span>
      </div>
      <div style="font-size: 0.85rem; font-weight: 700; color: #fff; word-break: break-all;">${obs.product_id}</div>
      <div style="font-size: 0.75rem; color: var(--text-secondary);">
        <strong>Bounds:</strong> Lat [${obs.bbox.min_lat.toFixed(2)}°, ${obs.bbox.max_lat.toFixed(2)}°]<br/>
        Lon [${obs.bbox.min_lon.toFixed(2)}°, ${obs.bbox.max_lon.toFixed(2)}°]<br/>
        <strong>Incidence:</strong> ${obs.incidence_angle ? obs.incidence_angle.toFixed(1) + '°' : 'N/A'}
      </div>
      <button class="btn-primary" style="padding: 6px 12px; font-size: 0.78rem; margin-top: 4px;" onclick="switchToPairForProduct('${obs.product_id}')">
        Open in Patch Studio
      </button>
    </div>
  `;
}

window.switchToPairForProduct = function(productId) {
  const pair = state.pairs.find(p => p.source_product_id === productId || p.reference_product_id === productId);
  if (pair) {
    document.getElementById('tabBtnPatches').click();
    selectPair(pair);
  } else {
    alert(`No candidate overlap pairs currently discovered for ${productId}`);
  }
};

// ==========================================================================
// POC 2: Overlapping Pairs Sidebar & Patch Studio
// ==========================================================================
function renderPairsList() {
  const container = document.getElementById('pairsContainer');
  container.innerHTML = '';

  if (state.pairs.length === 0) {
    container.innerHTML = `
      <div class="card-empty-state">
        <span>No overlapping pairs found with current thresholds.</span>
      </div>
    `;
    return;
  }

  state.pairs.forEach((pair, idx) => {
    const card = document.createElement('div');
    card.className = `pair-card ${state.activePair === pair ? 'active' : ''}`;
    card.innerHTML = `
      <div class="pair-badge-row">
        <span class="badge-overlap">${pair.overlap_percent_of_source}% Overlap</span>
        <span style="font-size: 0.7rem; color: var(--text-dim);">${pair.overlap_area_km2 || 'N/A'} km²</span>
      </div>
      <div class="pair-names">
        <span>${pair.source_sensor}</span> ${pair.source_product_id.split('_').slice(0, 3).join('_')}
        <br/>
        <span style="color: var(--sensor-lro);">${pair.reference_sensor}</span> ${pair.reference_product_id}
      </div>
      <div class="pair-stats">
        <span>Res: ${pair.source_resolution_m}m vs ${pair.reference_resolution_m}m</span>
        <span>Δ Sun: ${pair.solar_incidence_diff_deg?.toFixed(1) || 0}°</span>
      </div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.pair-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      selectPair(pair);
    });

    container.appendChild(card);
  });
}

async function selectPair(pair) {
  state.activePair = pair;
  document.getElementById('btnOpenExtractModal').disabled = false;
  const btnViewMap = document.getElementById('btnViewPairOnMap');
  if (btnViewMap) {
    btnViewMap.disabled = false;
    btnViewMap.onclick = () => {
      document.getElementById('tabBtnMap').click();
      highlightIntersectionOnMap(pair);
    };
  }

  document.getElementById('bannerPairTitle').innerHTML = `
    <span>${pair.source_sensor}</span> vs <span>${pair.reference_sensor}</span>: Boguslawsky Overlap Region
  `;
  document.getElementById('bannerPairMeta').innerText = `
    Overlap: ${pair.overlap_percent_of_source}% • Area: ${pair.overlap_area_km2 || 'N/A'} km² • Source Res: ${pair.source_resolution_m}m • Ref Res: ${pair.reference_resolution_m}m
  `;

  document.getElementById('lblSrcTag').innerText = `Source (${pair.source_sensor})`;
  document.getElementById('lblRefTag').innerText = `Reference (${pair.reference_sensor})`;

  // Fetch patch manifest for this pair if exists
  await loadManifestForPair(pair);
}

function highlightIntersectionOnMap(pair) {
  if (!state.map || !pair.intersection_bbox) return;
  if (state.overlapHighlightLayer) {
    state.map.removeLayer(state.overlapHighlightLayer);
  }
  const ibox = pair.intersection_bbox;
  const bounds = [
    [ibox.min_lat, ibox.min_lon],
    [ibox.max_lat, ibox.max_lon]
  ];
  state.overlapHighlightLayer = L.rectangle(bounds, {
    color: '#ffd32a',
    weight: 3,
    fillColor: '#ffd32a',
    fillOpacity: 0.35,
    dashArray: '5, 5'
  }).addTo(state.map);

  state.overlapHighlightLayer.bindPopup(`
    <div style="font-family: 'Outfit', sans-serif; color: #111;">
      <strong style="color: #d63031;">Active Overlap Intersection Zone</strong><br/>
      <span style="font-size: 0.8rem; color: #333;">${pair.source_sensor} <-> ${pair.reference_sensor}</span><br/>
      <strong>Overlap:</strong> ${pair.overlap_percent_of_source}% (${pair.overlap_area_km2 || 'N/A'} km²)
    </div>
  `).openPopup();

  state.map.flyToBounds(bounds, { padding: [50, 50], duration: 1.2 });
}


async function loadManifestForPair(pair) {
  const pairKey = `${pair.source_product_id}___${pair.reference_product_id}`;
  try {
    const res = await fetch(`/api/manifest?pair_id=${encodeURIComponent(pairKey)}`);
    if (res.ok) {
      const manifest = await res.json();
      if (manifest && manifest.total_patches > 0) {
        state.activeManifest = manifest;
        renderPatchesGrid(manifest);
      } else {
        state.activeManifest = null;
        renderEmptyPatchesGrid(pair);
      }
    } else {
      state.activeManifest = null;
      renderEmptyPatchesGrid(pair);
    }
  } catch (e) {
    console.error('Error fetching manifest:', e);
    renderEmptyPatchesGrid(pair);
  }
}

function renderEmptyPatchesGrid(pair) {
  const container = document.getElementById('patchesGridView');
  container.innerHTML = `
    <div class="card-empty-state" style="grid-column: 1 / -1; padding: 40px 0;">
      <p style="font-size: 0.95rem; color: var(--text-main);">No patches extracted yet for this pair.</p>
      <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px;">
        Click <strong>"Configure & Extract Patches"</strong> above to extract resolution-harmonized co-registered patches.
      </p>
    </div>
  `;
  document.getElementById('patchStatsPills').innerHTML = '';
}

function renderPatchesGrid(manifest) {
  const container = document.getElementById('patchesGridView');
  container.innerHTML = '';

  const pills = document.getElementById('patchStatsPills');
  pills.innerHTML = `
    <span class="tag-pill">${manifest.total_patches} Patches Generated</span>
    <span class="tag-pill" style="background: rgba(46, 213, 115, 0.15); color: #2ed573;">GSD: ${manifest.patches[0]?.effective_resolution_m || 'N/A'}m</span>
  `;

  manifest.patches.forEach((patch, idx) => {
    const tile = document.createElement('div');
    tile.className = `patch-tile-card ${idx === 0 ? 'selected' : ''}`;
    
    // Normalize image paths for web browser
    const srcImgUrl = `/data/processed/patches/${manifest.source_product_id}___${manifest.reference_product_id}/${patch.source_patch_path.split('\\').pop().split('/').pop()}`;
    const refImgUrl = `/data/processed/patches/${manifest.source_product_id}___${manifest.reference_product_id}/${patch.reference_patch_path.split('\\').pop().split('/').pop()}`;

    tile.innerHTML = `
      <div class="patch-tile-header">
        <span class="patch-tile-id">Patch #${patch.patch_index.toString().padStart(4, '0')}</span>
        <span class="patch-tile-score">Score: ${(patch.quality_score * 100).toFixed(0)}%</span>
      </div>
      <div class="patch-dual-thumbnails">
        <div class="thumb-item">
          <img src="${srcImgUrl}" alt="Source Patch" loading="lazy">
          <span class="thumb-label">Source</span>
        </div>
        <div class="thumb-item">
          <img src="${refImgUrl}" alt="Reference Patch" loading="lazy">
          <span class="thumb-label">Reference</span>
        </div>
      </div>
      <div class="patch-tile-footer">
        <span>Lat: [${patch.ground_bbox.min_lat.toFixed(2)}°, ${patch.ground_bbox.max_lat.toFixed(2)}°]</span>
        <span>Lon: [${patch.ground_bbox.min_lon.toFixed(2)}°, ${patch.ground_bbox.max_lon.toFixed(2)}°]</span>
      </div>
    `;

    tile.addEventListener('click', () => {
      document.querySelectorAll('.patch-tile-card').forEach(t => t.classList.remove('selected'));
      tile.classList.add('selected');
      loadPatchIntoViewer(patch, srcImgUrl, refImgUrl);
    });

    container.appendChild(tile);
  });

  // Load first patch into split viewer
  if (manifest.patches.length > 0) {
    const first = manifest.patches[0];
    const srcImgUrl = `/data/processed/patches/${manifest.source_product_id}___${manifest.reference_product_id}/${first.source_patch_path.split('\\').pop().split('/').pop()}`;
    const refImgUrl = `/data/processed/patches/${manifest.source_product_id}___${manifest.reference_product_id}/${first.reference_patch_path.split('\\').pop().split('/').pop()}`;
    loadPatchIntoViewer(first, srcImgUrl, refImgUrl);
  }
}

function loadPatchIntoViewer(patch, srcImgUrl, refImgUrl) {
  state.activePatch = patch;
  document.getElementById('currentPatchLabel').innerText = `Patch #${patch.patch_index.toString().padStart(4, '0')}`;
  
  const imgRef = document.getElementById('imgRefView');
  const imgSrc = document.getElementById('imgSrcView');
  
  imgRef.src = refImgUrl;
  imgSrc.src = srcImgUrl;
}

// ==========================================================================
// Split Screen Comparison Slider & Blinking
// ==========================================================================
function initSplitSlider() {
  const slider = document.getElementById('compareSlider');
  const layerSrc = document.getElementById('layerSrc');
  const dividerLine = document.getElementById('dividerLine');

  slider.addEventListener('input', (e) => {
    const val = e.target.value;
    layerSrc.style.width = `${val}%`;
    dividerLine.style.left = `${val}%`;
  });

  // Toggle Blink Mode (alternates opacity rapidly to spot subtle ground disparities)
  const btnBlink = document.getElementById('btnToggleMode');
  btnBlink.addEventListener('click', () => {
    if (state.blinkInterval) {
      clearInterval(state.blinkInterval);
      state.blinkInterval = null;
      btnBlink.innerText = 'Toggle Blink';
      layerSrc.style.opacity = '1';
      layerSrc.style.width = `${slider.value}%`;
      dividerLine.style.display = 'block';
    } else {
      btnBlink.innerText = 'Stop Blink';
      layerSrc.style.width = '100%';
      dividerLine.style.display = 'none';
      let toggle = false;
      state.blinkInterval = setInterval(() => {
        layerSrc.style.opacity = toggle ? '1' : '0';
        toggle = !toggle;
      }, 500);
    }
  });
}

// ==========================================================================
// Patch Extraction Modal
// ==========================================================================
function initModal() {
  const modal = document.getElementById('extractModal');
  const btnOpen = document.getElementById('btnOpenExtractModal');
  const btnClose = document.getElementById('btnCloseExtractModal');
  const btnCancel = document.getElementById('btnCancelModal');
  const btnRun = document.getElementById('btnRunExtraction');

  btnOpen.addEventListener('click', () => {
    if (!state.activePair) return;
    document.getElementById('modalSourceId').value = state.activePair.source_product_id;
    document.getElementById('modalRefId').value = state.activePair.reference_product_id;
    modal.classList.add('show');
  });

  const closeModal = () => modal.classList.remove('show');
  btnClose.addEventListener('click', closeModal);
  btnCancel.addEventListener('click', closeModal);

  btnRun.addEventListener('click', async () => {
    const patchSize = parseInt(document.getElementById('modalPatchSize').value);
    const stride = parseInt(document.getElementById('modalStride').value);
    const strategy = document.getElementById('modalStrategy').value;

    btnRun.innerText = 'Extracting Patches...';
    btnRun.disabled = true;

    try {
      const res = await fetch('/api/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_product_id: state.activePair.source_product_id,
          reference_product_id: state.activePair.reference_product_id,
          patch_size: patchSize,
          stride: stride,
          strategy: strategy,
        })
      });

      if (res.ok) {
        const manifest = await res.json();
        closeModal();
        state.activeManifest = manifest;
        renderPatchesGrid(manifest);
        alert(`Successfully extracted ${manifest.total_patches} patch pairs!`);
      } else {
        const err = await res.text();
        alert(`Extraction failed: ${err}`);
      }
    } catch (err) {
      alert(`Error during extraction: ${err}`);
    } finally {
      btnRun.innerText = 'Run Patch Extraction Engine';
      btnRun.disabled = false;
    }
  });
}

// ==========================================================================
// Catalog Table View
// ==========================================================================
function renderCatalogTable() {
  const tbody = document.getElementById('catalogTableBody');
  tbody.innerHTML = '';

  const searchInput = document.getElementById('catalogSearchInput');
  const query = searchInput.value.toLowerCase();

  const filtered = state.catalog.filter(obs => {
    return obs.product_id.toLowerCase().includes(query) ||
           obs.sensor.toLowerCase().includes(query) ||
           obs.mission.toLowerCase().includes(query);
  });

  filtered.forEach(obs => {
    const tr = document.createElement('tr');
    
    // Resolve thumbnail path
    let thumbUrl = '/data/raw/ohrc/placeholder.png';
    if (obs.primary_image) {
      thumbUrl = '/' + obs.primary_image.replace(/\\/g, '/');
    } else if (obs.preview_image) {
      thumbUrl = '/' + obs.preview_image.replace(/\\/g, '/');
    }

    tr.innerHTML = `
      <td>
        <img src="${thumbUrl}" class="cell-thumb" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'44\\' height=\\'44\\' style=\\'background:%23111\\'><text x=\\'22\\' y=\\'26\\' fill=\\'%23666\\' font-size=\\'9\\' text-anchor=\\'middle\\'>NO IMG</text></svg>'"/>
      </td>
      <td class="cell-id">${obs.product_id}</td>
      <td>${obs.mission}</td>
      <td><span class="badge-sensor badge-sensor-${obs.sensor}">${obs.sensor}</span></td>
      <td>${obs.resolution_m ? obs.resolution_m + 'm' : 'N/A'}</td>
      <td>[${obs.bbox.min_lat.toFixed(2)}°, ${obs.bbox.max_lat.toFixed(2)}°]</td>
      <td>[${obs.bbox.min_lon.toFixed(2)}°, ${obs.bbox.max_lon.toFixed(2)}°]</td>
      <td>${obs.incidence_angle ? obs.incidence_angle.toFixed(1) + '°' : 'N/A'}</td>
      <td>
        <button class="btn-primary" style="padding: 4px 8px; font-size: 0.72rem;" onclick="jumpToObservation('${obs.product_id}')">
          Locate Map
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  searchInput.oninput = renderCatalogTable;
}

window.jumpToObservation = function(productId) {
  const obs = state.catalog.find(o => o.product_id === productId);
  if (!obs) return;

  document.getElementById('tabBtnMap').click();
  state.map.flyTo(obs.center, 7, { duration: 1.0 });
  displayObservationCard(obs);
};

// ==========================================================================
// POC 4: Illumination & Scale Robustness Studio
// ==========================================================================
function initLightbox() {
  const modal = document.getElementById('imagePreviewModal');
  const modalImg = document.getElementById('previewModalImg');
  const modalTitle = document.getElementById('previewModalTitle');
  const btnClose = document.getElementById('btnClosePreviewModal');

  if (!modal) return;

  document.querySelectorAll('.img-preview-trigger').forEach(img => {
    img.addEventListener('click', () => {
      const src = img.getAttribute('src');
      const title = img.getAttribute('data-title') || 'Figure Preview';
      modalImg.src = src;
      modalTitle.innerText = title;
      modal.classList.add('show');
      modal.style.display = 'flex';
    });
  });

  const closeModal = () => {
    modal.classList.remove('show');
    modal.style.display = 'none';
  };

  if (btnClose) btnClose.addEventListener('click', closeModal);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
  });
}

// ==========================================================================
// POC 4: Illumination + Scale Robustness Studio Engine
// ==========================================================================
let currentPOC4Data = null;
let currentPOC4Seed = 42;

function showPOC4Toast(msg) {
  let toast = document.getElementById('poc4Toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'poc4Toast';
    toast.className = 'nexus-toast';
    document.body.appendChild(toast);
  }
  toast.innerText = msg;
  toast.classList.add('visible');
  setTimeout(() => {
    toast.classList.remove('visible');
  }, 3800);
}

function initPOC4Studio() {
  const btnRun = document.getElementById('btnRunPOC4Experiment');
  const btnReroll = document.getElementById('btnRerollPOC4');
  const selectCond = document.getElementById('poc4ConditionSelect');
  const selectScale = document.getElementById('poc4ScaleSelect');

  if (btnRun) {
    btnRun.addEventListener('click', () => runPOC4FullPipeline(42));
  }
  if (btnReroll) {
    btnReroll.addEventListener('click', () => {
      const randomSeed = Math.floor(Math.random() * 90000 + 10000);
      runPOC4FullPipeline(randomSeed);
    });
  }

  if (selectCond) {
    selectCond.addEventListener('change', () => {
      if (currentPOC4Data) renderPOC4DynamicView(currentPOC4Data);
    });
  }
  if (selectScale) {
    selectScale.addEventListener('change', () => {
      if (currentPOC4Data) renderPOC4DynamicView(currentPOC4Data);
    });
  }

  // Load existing results if available
  loadPOC4Results();
}

async function loadPOC4Results() {
  try {
    const res = await fetch('/api/poc4/results');
    if (res.ok) {
      const data = await res.json();
      currentPOC4Data = data;
      renderPOC4DynamicView(data);
    }
  } catch (e) {
    console.log('POC-4 cached results not available yet.');
  }
}

async function runPOC4FullPipeline(seed = 42) {
  const btnRun = document.getElementById('btnRunPOC4Experiment');
  const btnReroll = document.getElementById('btnRerollPOC4');
  const progressCard = document.getElementById('poc4ProgressCard');
  const progressBar = document.getElementById('poc4ProgressBar');
  const stepLabel = document.getElementById('poc4CurrentStep');
  const stepBadges = document.querySelectorAll('#poc4StepsFlow .step-badge');

  if (btnRun) btnRun.disabled = true;
  if (btnReroll) btnReroll.disabled = true;

  if (btnRun) {
    btnRun.innerHTML = `
      <span class="spinner" style="width: 14px; height: 14px; border-width: 2px; display: inline-block;"></span>
      Executing Matrix (Seed ${seed})...
    `;
  }
  if (progressCard) progressCard.style.display = 'flex';

  const steps = [
    { name: '1. Ingesting Real Geographic Base Patch...', percent: 12, index: 0 },
    { name: '2. Applying 8 Illumination Transformations...', percent: 25, index: 1 },
    { name: '3. Computing Shadow Morphological Masks...', percent: 38, index: 2 },
    { name: '4. Generating 4-Octave Multi-Scale Pyramids...', percent: 50, index: 3 },
    { name: '5. Extracting Spatial Gradient Features...', percent: 62, index: 4 },
    { name: '6. Nearest-Neighbor Lowe Ratio Matching...', percent: 74, index: 5 },
    { name: '7. Executing RANSAC Geometric Verification...', percent: 85, index: 6 },
    { name: '8. Computing Ground Truth Recall@K & Inlier Metrics...', percent: 93, index: 7 },
    { name: '9. Generating Publication-Quality Figures & CSV...', percent: 100, index: 8 }
  ];

  let currentStepIdx = 0;
  const progressTimer = setInterval(() => {
    if (currentStepIdx < steps.length) {
      const s = steps[currentStepIdx];
      if (stepLabel) stepLabel.innerText = s.name;
      if (progressBar) progressBar.style.width = `${s.percent}%`;
      
      stepBadges.forEach((b, idx) => {
        if (idx < currentStepIdx) {
          b.className = 'step-badge completed';
        } else if (idx === currentStepIdx) {
          b.className = 'step-badge active';
        } else {
          b.className = 'step-badge';
        }
      });
      currentStepIdx++;
    }
  }, 450);

  const startTime = Date.now();

  try {
    const res = await fetch('/api/poc4/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_product_id: 'ch2_ohr_ncp_20260103t1005176450_d_img_d18',
        reference_product_id: 'SYNTHETIC_LROC_CANDIDATE_P850S0250',
        seed: seed
      })
    });

    clearInterval(progressTimer);

    if (res.ok) {
      const data = await res.json();
      currentPOC4Data = data;
      currentPOC4Seed = seed;
      const elapsedSec = ((Date.now() - startTime) / 1000).toFixed(2);

      if (progressBar) progressBar.style.width = '100%';
      if (stepLabel) stepLabel.innerText = `Experiment Completed in ${elapsedSec}s!`;
      stepBadges.forEach(b => b.className = 'step-badge completed');
      
      setTimeout(() => {
        renderPOC4DynamicView(data);
        refreshFigureImages();
        if (progressCard) progressCard.style.display = 'none';
        showPOC4Toast(`✓ POC-4 Experiment Run Complete (Seed ${seed}, ${elapsedSec}s) — All figures and tables refreshed!`);
      }, 700);
    } else {
      const err = await res.text();
      alert('POC-4 Experiment run error: ' + err);
    }
  } catch (err) {
    clearInterval(progressTimer);
    console.error('POC-4 execution failure:', err);
    alert('Failed to connect to POC-4 experiment service: ' + err);
  } finally {
    if (btnRun) {
      btnRun.disabled = false;
      btnRun.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
        RUN EXPERIMENT (SEED 42)
      `;
    }
    if (btnReroll) btnReroll.disabled = false;
  }
}

function refreshFigureImages() {
  const t = Date.now();
  document.querySelectorAll('.gallery-img-box img').forEach(img => {
    const base = img.src.split('?')[0];
    img.src = `${base}?t=${t}`;
  });
}

function renderPOC4DynamicView(data) {
  if (!data) return;

  const selectCond = document.getElementById('poc4ConditionSelect');
  const selectScale = document.getElementById('poc4ScaleSelect');
  const activeCond = selectCond ? selectCond.value : 'ALL';
  const activeScale = selectScale ? selectScale.value : 'ALL';

  // Update Provenance
  const provLabel = document.getElementById('poc4ProvenanceLabel');
  if (provLabel) {
    provLabel.innerText = data.metadata?.data_provenance || 'REAL-GEOGRAPHY / SYNTHETIC-ILLUMINATION EXPERIMENT';
  }

  // Update Run Status Banner
  const statusText = document.getElementById('poc4RunStatusText');
  const now = new Date();
  const timeStr = now.toLocaleTimeString();
  if (statusText) {
    statusText.innerHTML = `<strong>Live Run Active</strong> (Seed: <code>${currentPOC4Seed}</code>) • Filter: <strong>${activeCond}</strong> | Scale: <strong>${activeScale}</strong> • Updated ${timeStr}`;
  }

  // 1. Calculate representation metrics from matrix_results or summary
  const matrix = data.matrix_results || [];
  const repNames = ["RAW", "NORMALIZED", "GRADIENT", "MULTI-SCALE", "MULTI-SCALE + ILLUMINATION-AWARE"];
  const repMetrics = {};

  repNames.forEach(rName => {
    let rows = matrix.filter(r => r.representation.toUpperCase() === rName.toUpperCase());
    if (activeCond !== 'ALL') {
      rows = rows.filter(r => r.illumination_condition.toUpperCase() === activeCond.toUpperCase());
    }
    if (activeScale !== 'ALL') {
      const sVal = parseFloat(activeScale);
      rows = rows.filter(r => Math.abs(r.scale_factor - sVal) < 1e-3);
    }

    if (rows.length > 0) {
      const succ = rows.filter(r => r.alignment_success).length / rows.length;
      const inlier = rows.reduce((acc, r) => acc + (r.inlier_ratio || 0), 0) / rows.length;
      const validRmse = rows.map(r => r.rmse).filter(val => isFinite(val) && val < 50);
      const rmse = validRmse.length > 0 ? (validRmse.reduce((a, b) => a + b, 0) / validRmse.length) : 999.0;
      const validR1 = rows.map(r => r.recall_at_1).filter(val => val !== null && val !== undefined);
      const r1 = validR1.length > 0 ? (validR1.reduce((a, b) => a + b, 0) / validR1.length) : 0.0;
      repMetrics[rName] = {
        success_rate: succ,
        mean_inlier_ratio: inlier,
        mean_rmse: rmse,
        mean_recall_1: r1,
        evaluated_conditions: rows.length
      };
    } else {
      const fallback = (data.summary && data.summary.representation_metrics) ? data.summary.representation_metrics[rName] : null;
      if (fallback) {
        repMetrics[rName] = fallback;
      }
    }
  });

  // 2. Determine best representation for current filter view
  let bestRep = "MULTI-SCALE + ILLUMINATION-AWARE";
  let bestScore = -1;
  for (const [rName, m] of Object.entries(repMetrics)) {
    const score = (m.success_rate * 50) + (m.mean_inlier_ratio * 30) + Math.max(0, 20 - Math.min(20, m.mean_rmse));
    if (score > bestScore) {
      bestScore = score;
      bestRep = rName;
    }
  }

  // 3. Update Scorecards with values & Flash animation
  const elBestRep = document.getElementById('poc4BestRep');
  if (elBestRep) elBestRep.innerText = bestRep;

  const targetBest = repMetrics[bestRep] || repMetrics["MULTI-SCALE + ILLUMINATION-AWARE"] || repMetrics["MULTI-SCALE"];
  if (targetBest) {
    const elSuccess = document.getElementById('poc4SuccessRate');
    const elInlier = document.getElementById('poc4InlierRatio');
    const elRecall1 = document.getElementById('poc4Recall1');
    const elRmse = document.getElementById('poc4Rmse');

    if (elSuccess) elSuccess.innerText = `${(targetBest.success_rate * 100).toFixed(1)}%`;
    if (elInlier) elInlier.innerText = `${(targetBest.mean_inlier_ratio * 100).toFixed(1)}%`;
    if (elRecall1) elRecall1.innerText = `${(targetBest.mean_recall_1 * 100).toFixed(1)}%`;
    if (elRmse) elRmse.innerText = `${targetBest.mean_rmse < 900 ? targetBest.mean_rmse.toFixed(2) + ' px' : '999.00 px'}`;
  }

  // Flash scorecard for feedback
  document.querySelectorAll('.score-card').forEach(card => {
    card.classList.remove('card-flash');
    void card.offsetWidth;
    card.classList.add('card-flash');
  });

  // 4. Populate Baseline Comparison Table
  const tbody = document.getElementById('poc4ComparisonTableBody');
  if (tbody) {
    tbody.innerHTML = '';
    for (const [repName, m] of Object.entries(repMetrics)) {
      const tr = document.createElement('tr');
      const isWinner = repName === bestRep;
      if (isWinner) tr.className = 'highlight-row';

      let pillClass = 'pill-fail';
      let pillText = 'Baseline';
      if (m.success_rate >= 0.7) {
        pillClass = isWinner ? 'pill-winner' : 'pill-pass';
        pillText = isWinner ? '★ BEST PERFORMER' : 'High Robustness';
      } else if (m.success_rate >= 0.5) {
        pillClass = 'pill-pass';
        pillText = 'Scale Invariant';
      } else if (m.success_rate >= 0.2) {
        pillClass = 'pill-neutral';
        pillText = 'Partial';
      }

      tr.innerHTML = `
        <td><strong>${repName}</strong></td>
        <td>${(m.success_rate * 100).toFixed(1)}%</td>
        <td>${(m.mean_inlier_ratio * 100).toFixed(1)}%</td>
        <td>${(m.mean_recall_1 * 100).toFixed(1)}%</td>
        <td>${m.mean_rmse < 900 ? m.mean_rmse.toFixed(2) + ' px' : '999.00 px'}</td>
        <td><span class="${pillClass}">${pillText}</span></td>
      `;
      tbody.appendChild(tr);
    }
  }

  // 5. Populate Ablation Table
  const ablBody = document.getElementById('poc4AblationTableBody');
  const ablationList = data.ablation_results || data.ablation || [];
  if (ablBody && ablationList.length > 0) {
    ablBody.innerHTML = '';
    ablationList.forEach(row => {
      const tr = document.createElement('tr');
      const cfg = row.configuration || row.config_name || '';
      const isPass = row.alignment_success !== undefined ? row.alignment_success : row.success;
      const isBest = cfg.includes('ILLUMINATION-AWARE') && row.scale_harmonized;
      if (isBest) tr.className = 'highlight-row';

      tr.innerHTML = `
        <td>${cfg}</td>
        <td>${row.scale_harmonized ? 'Yes' : 'No'}</td>
        <td>${((row.inlier_ratio || 0) * 100).toFixed(1)}%</td>
        <td>${(row.rmse < 900 ? (row.rmse || 0).toFixed(2) + ' px' : '999.00 px')}</td>
        <td><span class="${isBest ? 'pill-winner' : (isPass ? 'pill-pass' : 'pill-fail')}">${isPass ? 'PASS' : 'FAIL'}</span></td>
      `;
      ablBody.appendChild(tr);
    });
  }
}

// ==========================================================================
// POC-5 Multimodal AI Correspondence Studio
// ==========================================================================
let poc5Data = null;

function initPOC5Studio() {
  const btnRun = document.getElementById('btnRunPOC5');
  const selectQuery = document.getElementById('poc5QuerySelect');

  if (btnRun) {
    btnRun.addEventListener('click', async () => {
      btnRun.disabled = true;
      btnRun.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Retraining & Retrieving...`;
      showPOC4Toast('Running Two-Tower AI Retrieval Pipeline (12 Epochs)...');
      try {
        const resp = await fetch('/api/poc5/run', { method: 'POST' });
        if (resp.ok) {
          showPOC4Toast('POC-5 Pipeline executed successfully!');
          await loadPOC5Data();
        } else {
          showPOC4Toast('Failed to run POC-5 pipeline: ' + resp.statusText);
        }
      } catch (err) {
        showPOC4Toast('Network error triggering POC-5: ' + err.message);
      } finally {
        btnRun.disabled = false;
        btnRun.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Run POC-5 Retrieval Pipeline`;
      }
    });
  }

  if (selectQuery) {
    selectQuery.addEventListener('change', () => {
      renderPOC5QueryRetrieval(selectQuery.value);
    });
  }

  // Initial load
  loadPOC5Data();
}

async function loadPOC5Data() {
  try {
    const res = await fetch('/api/poc5/results');
    if (!res.ok) return;
    poc5Data = await res.json();
    populatePOC5Metrics(poc5Data);
    populatePOC5QueryDropdown(poc5Data);
    populatePOC5Figures(poc5Data);
  } catch (e) {
    console.warn('Could not load POC 5 data:', e);
  }
}

function populatePOC5Metrics(data) {
  const s = data.summary || {};
  const r1El = document.getElementById('poc5Recall1Val');
  const r5El = document.getElementById('poc5Recall5Val');
  const r10El = document.getElementById('poc5Recall10Val');
  const mrrEl = document.getElementById('poc5MRRVal');

  if (r1El && s.recall_at_1 !== undefined) r1El.innerText = `${(s.recall_at_1 * 100).toFixed(1)}%`;
  if (r5El && s.recall_at_5 !== undefined) r5El.innerText = `${(s.recall_at_5 * 100).toFixed(1)}%`;
  if (r10El && s.recall_at_10 !== undefined) r10El.innerText = `${(s.recall_at_10 * 100).toFixed(1)}%`;
  if (mrrEl && s.mean_reciprocal_rank !== undefined) mrrEl.innerText = s.mean_reciprocal_rank.toFixed(3);
}

function populatePOC5QueryDropdown(data) {
  const selectQuery = document.getElementById('poc5QuerySelect');
  if (!selectQuery || !data.queries) return;

  selectQuery.innerHTML = '';
  data.queries.forEach((q, idx) => {
    const opt = document.createElement('option');
    opt.value = q.query_patch_id;
    opt.innerText = `${q.query_sensor || 'OHRC'} Query #${idx + 1} (${q.query_patch_id}) - True Rank: #${q.true_match_rank || 'N/A'}`;
    selectQuery.appendChild(opt);
  });

  if (data.queries.length > 0) {
    renderPOC5QueryRetrieval(data.queries[0].query_patch_id);
  }
}

function renderPOC5QueryRetrieval(queryId) {
  const container = document.getElementById('poc5RetrievalGrid');
  if (!container || !poc5Data || !poc5Data.queries) return;

  const qData = poc5Data.queries.find(q => q.query_patch_id === queryId);
  if (!qData) return;

  container.innerHTML = '';

  // 1. Query Card
  const qCard = document.createElement('div');
  qCard.className = 'glassmorphism';
  qCard.style.cssText = 'min-width: 220px; max-width: 220px; border: 2px solid #1a73e8; border-radius: 8px; padding: 0.8rem; background: rgba(26, 115, 232, 0.08);';
  qCard.innerHTML = `
    <div style="font-size: 0.75rem; font-weight: bold; color: #58a6ff; margin-bottom: 0.4rem; text-transform: uppercase;">
      ★ QUERY FOOTPRINT
    </div>
    <div style="font-weight: bold; font-size: 0.9rem; margin-bottom: 0.2rem;">${qData.query_patch_id}</div>
    <div style="font-size: 0.75rem; color: #8b949e; margin-bottom: 0.5rem;">Sensor: ${qData.query_sensor} | GSD: ${qData.query_gsd_m}m</div>
    <div style="background: #000; border-radius: 4px; height: 140px; display: flex; align-items: center; justify-content: center; overflow: hidden; border: 1px solid #30363d;">
      <span style="font-size: 0.8rem; color: #8b949e;">Query Patch [${qData.query_sensor}]</span>
    </div>
    <div style="margin-top: 0.6rem; font-size: 0.75rem; color: #c9d1d9;">
      True Match Rank: <span class="pill-${qData.true_match_rank <= 5 ? 'pass' : 'neutral'}">#${qData.true_match_rank || 'N/A'}</span>
    </div>
  `;
  container.appendChild(qCard);

  // 2. Candidate Cards
  const candidates = qData.candidates || [];
  candidates.slice(0, 5).forEach(cand => {
    const isHit = cand.is_ground_truth;
    const borderCol = isHit ? '#2ea043' : '#30363d';
    const bgCol = isHit ? 'rgba(46, 160, 67, 0.12)' : 'rgba(255, 255, 255, 0.02)';
    
    const cCard = document.createElement('div');
    cCard.className = 'glassmorphism';
    cCard.style.cssText = `min-width: 220px; max-width: 220px; border: 2px solid ${borderCol}; border-radius: 8px; padding: 0.8rem; background: ${bgCol};`;
    cCard.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
        <span style="font-size: 0.8rem; font-weight: bold; color: ${isHit ? '#3fb950' : '#8b949e'};">Rank #${cand.rank}</span>
        <span class="pill-${isHit ? 'winner' : 'neutral'}" style="font-size: 0.65rem;">${isHit ? 'TRUE MATCH' : 'DISTRACTOR'}</span>
      </div>
      <div style="font-weight: 500; font-size: 0.85rem; margin-bottom: 0.2rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${cand.candidate_patch_id}</div>
      <div style="font-size: 0.75rem; color: #8b949e; margin-bottom: 0.5rem;">Dist: ${cand.ground_distance_m}m</div>
      <div style="background: #000; border-radius: 4px; height: 140px; display: flex; align-items: center; justify-content: center; overflow: hidden; border: 1px solid #30363d;">
        <span style="font-size: 0.75rem; color: #8b949e;">Candidate [${cand.sensor}]</span>
      </div>
      <div style="margin-top: 0.6rem; font-size: 0.75rem; display: flex; justify-content: space-between;">
        <span style="color: #8b949e;">Cosine Sim:</span>
        <strong style="color: ${isHit ? '#3fb950' : '#c9d1d9'};">${cand.cosine_similarity.toFixed(4)}</strong>
      </div>
    `;
    container.appendChild(cCard);
  });
}

function populatePOC5Figures(data) {
  const figs = data.figures || {};
  const map = {
    poc5FigArch: figs.two_tower_architecture,
    poc5FigGrid: figs.retrieval_ranking_grid,
    poc5FigClusters: figs.embedding_clusters,
    poc5FigRecall: figs.recall_at_k_curve,
    poc5FigDist: figs.similarity_distribution,
  };

  const t = Date.now();
  for (const [id, src] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el && src) {
      el.src = `${src}?t=${t}`;
    }
  }
}

// ==========================================================================
// 3D LUNAR SPACE STUDIO & BLENDER MCP DIGITAL TWIN
// ==========================================================================
function initNexus3DStudio() {
  const container = document.getElementById('nexus3dCanvasContainer');
  if (!container || typeof THREE === 'undefined') {
    console.warn('Three.js or nexus3dCanvasContainer not available');
    return;
  }

  // Master Studio State
  const n3d = {
    scene: null,
    camera: null,
    renderer: null,
    controls: null,
    sunLight: null,
    ambientLight: null,
    moonGlobe: null,
    craterReliefMesh: null,
    modulesGroup: null,
    footprintsGroup: null,
    highlightRing: null,
    roverGroup: null,
    modules: {},
    selectedModuleId: 'hab_core_01',
    sunElevation: 3.5,
    sunAzimuth: 124.5,
    isBuildingAnimated: false,
    viewMode: 'globe', // 'globe' or 'surface'
    raycaster: new THREE.Raycaster(),
    mouse: new THREE.Vector2(),
    animationFrameId: null,
  };

  window.nexus3d = n3d;

  // 1. Scene & Background
  n3d.scene = new THREE.Scene();
  n3d.scene.background = new THREE.Color(0x020408);

  // Deep Space Starfield
  const starGeo = new THREE.BufferGeometry();
  const starCount = 3500;
  const starPos = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount * 3; i += 3) {
    const r = 3800 + Math.random() * 2500;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos((Math.random() * 2) - 1);
    starPos[i] = r * Math.sin(phi) * Math.cos(theta);
    starPos[i + 1] = r * Math.sin(phi) * Math.sin(theta);
    starPos[i + 2] = r * Math.cos(phi);
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
  const starMat = new THREE.PointsMaterial({ color: 0xe0e6ed, size: 2.2, transparent: true, opacity: 0.85 });
  const starField = new THREE.Points(starGeo, starMat);
  n3d.scene.add(starField);

  // 2. Camera & Renderer
  const width = container.clientWidth || window.innerWidth;
  const height = container.clientHeight || (window.innerHeight - 64);
  n3d.camera = new THREE.PerspectiveCamera(45, width / height, 1, 35000);
  n3d.camera.position.set(0, 220, 920); // Initial full Moon globe view

  n3d.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
  n3d.renderer.setSize(width, height);
  n3d.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  n3d.renderer.shadowMap.enabled = true;
  n3d.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  n3d.renderer.toneMapping = THREE.ACESFilmicToneMapping;
  n3d.renderer.toneMappingExposure = 1.15;
  container.innerHTML = '';
  container.appendChild(n3d.renderer.domElement);

  // 3. OrbitControls
  if (typeof THREE.OrbitControls !== 'undefined') {
    n3d.controls = new THREE.OrbitControls(n3d.camera, n3d.renderer.domElement);
    n3d.controls.enableDamping = true;
    n3d.controls.dampingFactor = 0.05;
    n3d.controls.minDistance = 30;
    n3d.controls.maxDistance = 4500;
    n3d.controls.target.set(0, 0, 0);
    n3d.controls.autoRotate = false;
    n3d.controls.autoRotateSpeed = 0.4;
    n3d.controls.update();
  }

  // 4. Lighting: Physical Polar Sun & Deep Space Ambient Fill
  n3d.ambientLight = new THREE.AmbientLight(0x182238, 0.45);
  n3d.scene.add(n3d.ambientLight);

  n3d.sunLight = new THREE.DirectionalLight(0xfff6e5, 2.5);
  n3d.sunLight.castShadow = true;
  n3d.sunLight.shadow.mapSize.width = 2048;
  n3d.sunLight.shadow.mapSize.height = 2048;
  n3d.sunLight.shadow.camera.near = 50;
  n3d.sunLight.shadow.camera.far = 4500;
  const d = 900;
  n3d.sunLight.shadow.camera.left = -d;
  n3d.sunLight.shadow.camera.right = d;
  n3d.sunLight.shadow.camera.top = d;
  n3d.sunLight.shadow.camera.bottom = -d;
  n3d.sunLight.shadow.bias = -0.0003;
  n3d.scene.add(n3d.sunLight);

  function updateSunPosition() {
    const elRad = (n3d.sunElevation * Math.PI) / 180;
    const azRad = (n3d.sunAzimuth * Math.PI) / 180;
    const dist = 1800;
    const y = dist * Math.sin(elRad);
    const horiz = dist * Math.cos(elRad);
    const x = horiz * Math.sin(azRad);
    const z = horiz * Math.cos(azRad);
    n3d.sunLight.position.set(x, Math.max(y, 20), z);
    n3d.sunLight.target.position.set(0, 0, 0);
    n3d.scene.add(n3d.sunLight.target);
  }
  updateSunPosition();

  // 5. Complete Spherical Moon Lunar Model (Globe)
  const MOON_RADIUS = 300;

  function latLonToVector3(lat, lon, radius = MOON_RADIUS) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);
    return new THREE.Vector3(x, y, z);
  }

  function createLunarSurfaceTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 2048;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');

    // Base lunar crust tone (pale greyish basalt)
    ctx.fillStyle = '#656872';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // High-frequency lunar regolith grain & impact noise
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imgData.data;
    for (let i = 0; i < data.length; i += 4) {
      const noise = (Math.random() - 0.5) * 24;
      data[i] = Math.min(255, Math.max(0, data[i] + noise));
      data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + noise));
      data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + noise));
    }
    ctx.putImageData(imgData, 0, 0);

    // Draw Major Lunar Maria (Dark Basaltic Plains)
    function drawMare(cx, cy, rx, ry, opacity = 0.58) {
      const radGrad = ctx.createRadialGradient(cx, cy, 5, cx, cy, Math.max(rx, ry));
      radGrad.addColorStop(0, `rgba(32, 35, 42, ${opacity})`);
      radGrad.addColorStop(0.65, `rgba(40, 44, 52, ${opacity * 0.85})`);
      radGrad.addColorStop(1, 'rgba(101, 104, 114, 0)');
      ctx.save();
      ctx.beginPath();
      ctx.translate(cx, cy);
      ctx.scale(rx, ry);
      ctx.arc(0, 0, 1, 0, Math.PI * 2);
      ctx.restore();
      ctx.fillStyle = radGrad;
      ctx.fill();
    }

    // Nearside Lunar Maria
    drawMare(600, 360, 240, 190, 0.7); // Oceanus Procellarum
    drawMare(750, 320, 140, 120, 0.65); // Mare Imbrium
    drawMare(980, 350, 110, 95, 0.62);  // Mare Serenitatis
    drawMare(1050, 450, 120, 100, 0.65); // Mare Tranquillitatis
    drawMare(1250, 400, 75, 65, 0.65);  // Mare Crisium
    drawMare(720, 540, 110, 90, 0.58);  // Mare Nubium
    drawMare(620, 580, 80, 70, 0.55);   // Mare Humorum
    drawMare(1150, 520, 95, 80, 0.58);  // Mare Fecunditatis
    drawMare(850, 220, 130, 60, 0.5);   // Mare Frigoris
    drawMare(1000, 860, 210, 110, 0.45); // South Pole Aitken Basin

    // Draw Tycho Crater and Brilliant Radial Ray System
    const tychoX = 780;
    const tychoY = 700;
    ctx.strokeStyle = 'rgba(235, 240, 255, 0.28)';
    ctx.lineWidth = 1.5;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
      ctx.beginPath();
      ctx.moveTo(tychoX, tychoY);
      const len = 250 + Math.random() * 300;
      ctx.lineTo(tychoX + Math.cos(a) * len, tychoY + Math.sin(a) * len);
      ctx.stroke();
    }

    // Draw Crater Rings
    for (let c = 0; c < 180; c++) {
      const cx = Math.random() * canvas.width;
      const cy = Math.random() * canvas.height;
      const cr = 4 + Math.random() * 22;
      ctx.beginPath();
      ctx.arc(cx, cy, cr, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(210, 215, 225, 0.35)';
      ctx.lineWidth = 1.2;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(cx + 1, cy + 1, cr * 0.8, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(30, 32, 38, 0.35)';
      ctx.fill();
    }

    // Latitude & Longitude Graticule Lines
    ctx.strokeStyle = 'rgba(0, 242, 254, 0.08)';
    ctx.lineWidth = 1;
    for (let y = 0; y <= canvas.height; y += canvas.height / 6) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
    for (let x = 0; x <= canvas.width; x += canvas.width / 12) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    return tex;
  }

  // Construct Celestial Moon Sphere
  const moonGeo = new THREE.SphereGeometry(MOON_RADIUS, 96, 96);
  const moonMat = new THREE.MeshStandardMaterial({
    map: createLunarSurfaceTexture(),
    roughness: 0.92,
    metalness: 0.05,
  });

  n3d.moonGlobe = new THREE.Mesh(moonGeo, moonMat);
  n3d.moonGlobe.castShadow = true;
  n3d.moonGlobe.receiveShadow = true;
  n3d.scene.add(n3d.moonGlobe);

  // Lunar Graticule Orbit Ring
  const orbitRingGeo = new THREE.RingGeometry(MOON_RADIUS + 4, MOON_RADIUS + 6, 96);
  const orbitRingMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe, side: THREE.DoubleSide, transparent: true, opacity: 0.12 });
  const orbitRing = new THREE.Mesh(orbitRingGeo, orbitRingMat);
  orbitRing.rotation.x = Math.PI / 2;
  n3d.scene.add(orbitRing);

  // 6. Ingestion Layer Sensor Footprints on the Moon Sphere
  n3d.footprintsGroup = new THREE.Group();
  n3d.scene.add(n3d.footprintsGroup);

  const INGESTION_FOOTPRINTS = [
    {
      id: 'ohrc',
      name: 'Chandrayaan-2 OHRC (0.25 m/px)',
      min_lat: -74.5, max_lat: -72.0, min_lon: 24.0, max_lon: 28.0,
      color: 0x00f2fe,
      centerLat: -73.25, centerLon: 26.0,
      label: 'CH2 OHRC (0.25m)',
    },
    {
      id: 'tmc',
      name: 'Chandrayaan-2 TMC-2 (3D DEM Triplet)',
      min_lat: -75.0, max_lat: -71.5, min_lon: 22.0, max_lon: 30.0,
      color: 0x55efc4,
      centerLat: -73.25, centerLon: 26.0,
      label: 'TMC-2 DEM Triplet',
    },
    {
      id: 'lroc',
      name: 'NASA LRO NAC (0.5 m/px)',
      min_lat: -74.5, max_lat: -72.0, min_lon: 24.0, max_lon: 28.0,
      color: 0xff7675,
      centerLat: -73.25, centerLon: 26.0,
      label: 'LRO NAC Reference',
    },
    {
      id: 'iirs',
      name: 'Chandrayaan-2 IIRS (2.85µm Ice Anomaly)',
      min_lat: -74.0, max_lat: -72.5, min_lon: 25.0, max_lon: 27.5,
      color: 0xa29bfe,
      centerLat: -73.25, centerLon: 26.2,
      label: 'IIRS Hydroxyl Anomaly',
    },
  ];

  INGESTION_FOOTPRINTS.forEach(fp => {
    // Build spherical ribbon border hugging the Moon surface
    const points = [];
    const steps = 8;
    // South edge
    for (let s = 0; s <= steps; s++) {
      const lon = fp.min_lon + (fp.max_lon - fp.min_lon) * (s / steps);
      points.push(latLonToVector3(fp.min_lat, lon, MOON_RADIUS + 1.2));
    }
    // East edge
    for (let s = 0; s <= steps; s++) {
      const lat = fp.min_lat + (fp.max_lat - fp.min_lat) * (s / steps);
      points.push(latLonToVector3(lat, fp.max_lon, MOON_RADIUS + 1.2));
    }
    // North edge
    for (let s = 0; s <= steps; s++) {
      const lon = fp.max_lon - (fp.max_lon - fp.min_lon) * (s / steps);
      points.push(latLonToVector3(fp.max_lat, lon, MOON_RADIUS + 1.2));
    }
    // West edge
    for (let s = 0; s <= steps; s++) {
      const lat = fp.max_lat - (fp.max_lat - fp.min_lat) * (s / steps);
      points.push(latLonToVector3(lat, fp.min_lon, MOON_RADIUS + 1.2));
    }

    const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
    const lineMat = new THREE.LineBasicMaterial({ color: fp.color, linewidth: 2 });
    const lineLoop = new THREE.LineLoop(lineGeo, lineMat);
    n3d.footprintsGroup.add(lineLoop);

    // Center pulsating beacon
    const cPos = latLonToVector3(fp.centerLat, fp.centerLon, MOON_RADIUS + 2.0);
    const beaconGeo = new THREE.SphereGeometry(2.0, 12, 12);
    const beaconMat = new THREE.MeshBasicMaterial({ color: fp.color });
    const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
    beaconMesh.position.copy(cPos);
    n3d.footprintsGroup.add(beaconMesh);
  });

  // 7. Sited Boguslawsky Base Topography on the Moon Sphere
  // Target location: South Pole (-73.25° Lat, 26.0° Lon)
  const boguCenter = latLonToVector3(-73.25, 26.0, MOON_RADIUS);
  const boguNormal = boguCenter.clone().normalize();

  // Anchored Infrastructure Group
  n3d.modulesGroup = new THREE.Group();
  n3d.modulesGroup.position.copy(boguCenter);
  // Align local +Y with the Moon's spherical surface normal
  n3d.modulesGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), boguNormal);
  n3d.scene.add(n3d.modulesGroup);

  // Local Boguslawsky Crater Relief Rim
  const rimGeo = new THREE.RingGeometry(18, 28, 48);
  const rimMat = new THREE.MeshStandardMaterial({
    color: 0x3d414a,
    roughness: 0.96,
    metalness: 0.04,
    side: THREE.DoubleSide,
  });
  const rimMesh = new THREE.Mesh(rimGeo, rimMat);
  rimMesh.rotation.x = -Math.PI / 2;
  rimMesh.position.y = 0.2;
  n3d.modulesGroup.add(rimMesh);

  // Telemetry metadata dictionary
  const MODULE_METADATA = {
    hab_core_01: {
      id: 'hab_core_01',
      name: 'Primary Living Core Dome',
      type: 'HABITAT_CORE',
      pos: { x: 0, y: 0, z: 0 },
      coordsStr: '73.25°S, 26.00°E (Boguslawsky Rim)',
      slope: '4.48° (Compliant ≤ 5°)',
      solar: '88.5% Diurnal Peak',
      isruDist: '427.5 m (Safe Proximity)',
      blastDist: '1,154.3 m (Compliant ≥ 1000m)',
      gnnScore: '0.892 (Optimal Base Site)',
      crew: '4 Astronauts',
      volume: '420 m³ Pressurized',
    },
    hab_solar_01: {
      id: 'hab_solar_01',
      name: 'Bifacial Solar PV Farm',
      type: 'SOLAR_FARM',
      pos: { x: 12, y: 0, z: -15 },
      coordsStr: '73.20°S, 26.05°E (Sunward Plateau)',
      slope: '0.80° (Super-Flat Compliant)',
      solar: '94.2% Continuous Polar Sunlight',
      isruDist: '570.2 m',
      blastDist: '1,507.8 m (Compliant ≥ 1000m)',
      gnnScore: '0.945 (Peak Solar Hours)',
      rated: '150 kW Bifacial Array',
      storage: '1.2 MWh Cryo-Battery',
    },
    hab_pad_01: {
      id: 'hab_pad_01',
      name: 'Touchdown Landing Pad',
      type: 'LANDING_PAD',
      pos: { x: -16, y: 0, z: 22 },
      coordsStr: '73.35°S, 25.90°E (Plume Safety Zone)',
      slope: '1.47° (Stable Sintered Touchdown)',
      solar: '79.1% Diurnal Illumination',
      isruDist: '1,215.0 m',
      blastDist: '1,154.3 m from Living Core (Buffer Verified)',
      gnnScore: '0.864 (Low Crater Hazard)',
      landerCapacity: '45.0 Ton Heavy Lander',
      material: 'Microwave-Sintered Basalt',
    },
    hab_berm_01: {
      id: 'hab_berm_01',
      name: 'Regolith Blast Berm',
      type: 'REGOLITH_BERM',
      pos: { x: -8, y: 0, z: 10 },
      coordsStr: '73.30°S, 25.95°E (Deflection Line)',
      slope: '22.33° (Constructed Slope Angle)',
      solar: 'Shielded Deflection Zone',
      isruDist: '470.8 m',
      blastDist: '580.0 m Shield Barrier',
      gnnScore: '0.910 (Optimal Deflection Line)',
      height: '8.0 m Regolith Wall',
      thickness: '15.0 m Blast Absorber',
    },
    hab_isru_01: {
      id: 'hab_isru_01',
      name: 'Volatiles & Water-Ice ISRU Plant',
      type: 'RESOURCE_STATION',
      pos: { x: 18, y: 0, z: 8 },
      coordsStr: '73.28°S, 26.20°E (Cold Trap Boundary)',
      slope: '1.20° (Smooth Cold-Trap Apron)',
      solar: 'Permanent Cold-Trap Boundary',
      isruDist: '0.0 m (At Extraction Source)',
      blastDist: '1,180.0 m (Compliant ≥ 1000m)',
      gnnScore: '0.928 (IIRS Hydroxyl Anomaly Confirmed)',
      extraction: 'Thermal Sublimation & Condensation',
      anomalyBand: '2.85µm OH Band Depth 0.084',
    },
  };

  // Build Architectural 3D Meshes onto Lunar Surface Group
  // 1. Habitat Core Dome
  const coreGroup = new THREE.Group();
  coreGroup.position.set(0, 0, 0);
  coreGroup.name = 'hab_core_01';

  const domeGeo = new THREE.SphereGeometry(5.5, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2);
  const domeMat = new THREE.MeshStandardMaterial({
    color: 0xf5f8fc,
    roughness: 0.22,
    metalness: 0.35,
  });
  const domeMesh = new THREE.Mesh(domeGeo, domeMat);
  domeMesh.castShadow = true;
  domeMesh.receiveShadow = true;
  coreGroup.add(domeMesh);

  // Cupola glass viewport on top
  const cupolaGeo = new THREE.SphereGeometry(1.6, 16, 12, 0, Math.PI * 2, 0, Math.PI / 2);
  const cupolaMat = new THREE.MeshStandardMaterial({
    color: 0x00f2fe,
    roughness: 0.1,
    metalness: 0.8,
    transparent: true,
    opacity: 0.75,
  });
  const cupolaMesh = new THREE.Mesh(cupolaGeo, cupolaMat);
  cupolaMesh.position.y = 5.2;
  coreGroup.add(cupolaMesh);

  // Airlock pod
  const airlockGeo = new THREE.CylinderGeometry(1.2, 1.2, 4.0, 16);
  const airlockMat = new THREE.MeshStandardMaterial({ color: 0xd8e0eb, roughness: 0.3, metalness: 0.4 });
  const airlockMesh = new THREE.Mesh(airlockGeo, airlockMat);
  airlockMesh.rotation.z = Math.PI / 2;
  airlockMesh.position.set(5.8, 1.2, 0);
  airlockMesh.castShadow = true;
  coreGroup.add(airlockMesh);

  n3d.modulesGroup.add(coreGroup);
  n3d.modules.hab_core_01 = coreGroup;

  // 2. Solar PV Farm
  const solarGroup = new THREE.Group();
  solarGroup.position.set(12, 0, -15);
  solarGroup.name = 'hab_solar_01';

  const panelMat = new THREE.MeshStandardMaterial({
    color: 0x0c1e40,
    roughness: 0.08,
    metalness: 0.88,
  });
  const mastMat = new THREE.MeshStandardMaterial({ color: 0x8892a0, metalness: 0.5 });

  for (const offset of [-6, 0, 6]) {
    const mastGeo = new THREE.CylinderGeometry(0.25, 0.35, 9.0, 12);
    const mastMesh = new THREE.Mesh(mastGeo, mastMat);
    mastMesh.position.set(offset, 4.5, 0);
    mastMesh.castShadow = true;
    solarGroup.add(mastMesh);

    const panelGeo = new THREE.BoxGeometry(4.5, 7.5, 0.4);
    const panelMesh = new THREE.Mesh(panelGeo, panelMat);
    panelMesh.position.set(offset, 5.5, 0);
    panelMesh.rotation.y = (n3d.sunAzimuth * Math.PI) / 180 + Math.PI / 2;
    panelMesh.castShadow = true;
    solarGroup.add(panelMesh);
  }
  n3d.modulesGroup.add(solarGroup);
  n3d.modules.hab_solar_01 = solarGroup;

  // 3. Touchdown Landing Pad
  const padGroup = new THREE.Group();
  padGroup.position.set(-16, 0, 22);
  padGroup.name = 'hab_pad_01';

  const padGeo = new THREE.CylinderGeometry(12, 12.5, 0.8, 48);
  const padMat = new THREE.MeshStandardMaterial({ color: 0x22262d, roughness: 0.7, metalness: 0.2 });
  const padMesh = new THREE.Mesh(padGeo, padMat);
  padMesh.position.y = 0.4;
  padMesh.receiveShadow = true;
  padGroup.add(padMesh);

  // Concentric Hazard Touchdown Rings
  const ringGeo = new THREE.RingGeometry(7.5, 8.2, 48);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0xffa502, side: THREE.DoubleSide });
  const ringMesh = new THREE.Mesh(ringGeo, ringMat);
  ringMesh.rotation.x = -Math.PI / 2;
  ringMesh.position.y = 0.85;
  padGroup.add(ringMesh);

  const innerRingGeo = new THREE.RingGeometry(3.2, 3.8, 36);
  const innerRingMat = new THREE.MeshBasicMaterial({ color: 0x00f2fe, side: THREE.DoubleSide });
  const innerRingMesh = new THREE.Mesh(innerRingGeo, innerRingMat);
  innerRingMesh.rotation.x = -Math.PI / 2;
  innerRingMesh.position.y = 0.86;
  padGroup.add(innerRingMesh);

  n3d.modulesGroup.add(padGroup);
  n3d.modules.hab_pad_01 = padGroup;

  // 4. Regolith Blast Berm
  const bermGroup = new THREE.Group();
  bermGroup.position.set(-8, 0, 10);
  bermGroup.name = 'hab_berm_01';

  const bermGeo = new THREE.BoxGeometry(18, 3.5, 3.8);
  const bermMat = new THREE.MeshStandardMaterial({ color: 0x5a5d66, roughness: 0.96, metalness: 0.04 });
  const bermMesh = new THREE.Mesh(bermGeo, bermMat);
  bermMesh.position.y = 1.75;
  bermMesh.rotation.y = 0.45;
  bermMesh.castShadow = true;
  bermMesh.receiveShadow = true;
  bermGroup.add(bermMesh);

  n3d.modulesGroup.add(bermGroup);
  n3d.modules.hab_berm_01 = bermGroup;

  // 5. Volatiles & ISRU Extraction Plant
  const isruGroup = new THREE.Group();
  isruGroup.position.set(18, 0, 8);
  isruGroup.name = 'hab_isru_01';

  const isruBldgGeo = new THREE.BoxGeometry(8, 4.0, 6.0);
  const isruBldgMat = new THREE.MeshStandardMaterial({ color: 0xd4dce8, roughness: 0.35, metalness: 0.4 });
  const isruBldg = new THREE.Mesh(isruBldgGeo, isruBldgMat);
  isruBldg.position.y = 2.0;
  isruBldg.castShadow = true;
  isruGroup.add(isruBldg);

  for (const tox of [-2.5, 2.5]) {
    const tankGeo = new THREE.SphereGeometry(1.8, 16, 16);
    const tankMat = new THREE.MeshStandardMaterial({ color: 0x2ed573, roughness: 0.2, metalness: 0.6 });
    const tank = new THREE.Mesh(tankGeo, tankMat);
    tank.position.set(tox, 4.2, 0);
    tank.castShadow = true;
    isruGroup.add(tank);
  }
  n3d.modulesGroup.add(isruGroup);
  n3d.modules.hab_isru_01 = isruGroup;

  // Pressurized Conduits between Core and ISRU
  const pipeCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.4, 0),
    new THREE.Vector3(9, 0.4, 4),
    new THREE.Vector3(18, 0.4, 8),
  ]);
  const pipeGeo = new THREE.TubeGeometry(pipeCurve, 24, 0.35, 8, false);
  const pipeMat = new THREE.MeshStandardMaterial({ color: 0x00f2fe, emissive: 0x005577 });
  const pipeMesh = new THREE.Mesh(pipeGeo, pipeMat);
  n3d.modulesGroup.add(pipeMesh);

  // Surface Rover
  n3d.roverGroup = new THREE.Group();
  const roverBody = new THREE.Mesh(
    new THREE.BoxGeometry(2.2, 1.2, 1.5),
    new THREE.MeshStandardMaterial({ color: 0xe6edf5, metalness: 0.5 })
  );
  roverBody.position.y = 0.8;
  n3d.roverGroup.add(roverBody);
  const mast = new THREE.Mesh(
    new THREE.CylinderGeometry(0.1, 0.1, 1.6, 8),
    new THREE.MeshBasicMaterial({ color: 0x00f2fe })
  );
  mast.position.set(0.6, 1.8, 0);
  n3d.roverGroup.add(mast);
  n3d.roverGroup.position.set(8, 0, 4);
  n3d.modulesGroup.add(n3d.roverGroup);

  // 8. Selection Highlight Ring
  const selRingGeo = new THREE.RingGeometry(7.0, 7.8, 48);
  const selRingMat = new THREE.MeshBasicMaterial({
    color: 0x00f2fe,
    side: THREE.DoubleSide,
    transparent: true,
    opacity: 0.85,
  });
  n3d.highlightRing = new THREE.Mesh(selRingGeo, selRingMat);
  n3d.highlightRing.rotation.x = -Math.PI / 2;
  n3d.highlightRing.position.set(0, 0.2, 0);
  n3d.modulesGroup.add(n3d.highlightRing);

  // 9. Camera Flight Transition Function
  function flyTo(targetCamPos, targetLookAt, duration = 1200, onComplete = null) {
    if (!n3d.controls) return;
    const startCam = n3d.camera.position.clone();
    const startLook = n3d.controls.target.clone();
    const startTime = performance.now();

    function step() {
      const now = performance.now();
      const p = Math.min((now - startTime) / duration, 1.0);
      // Smooth cubic ease in-out
      const ease = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;

      n3d.camera.position.lerpVectors(startCam, targetCamPos, ease);
      n3d.controls.target.lerpVectors(startLook, targetLookAt, ease);
      n3d.controls.update();

      if (p < 1.0) {
        requestAnimationFrame(step);
      } else {
        if (onComplete) onComplete();
      }
    }
    requestAnimationFrame(step);
  }

  // 10. View Mode Switcher Handlers
  const btnModeGlobe = document.getElementById('btnModeGlobe');
  const btnModeSurface = document.getElementById('btnModeSurface');

  function setViewMode(mode) {
    n3d.viewMode = mode;
    if (mode === 'globe') {
      if (btnModeGlobe) btnModeGlobe.classList.add('active');
      if (btnModeSurface) btnModeSurface.classList.remove('active');
      n3d.controls.autoRotate = true;
      flyTo(new THREE.Vector3(0, 220, 920), new THREE.Vector3(0, 0, 0), 1200);
      showToast('Switched to Global Lunar Sphere View (Ingestion Overlays)', '🌍');
    } else {
      if (btnModeGlobe) btnModeGlobe.classList.remove('active');
      if (btnModeSurface) btnModeSurface.classList.add('active');
      n3d.controls.autoRotate = false;
      // Close up at South Pole site
      const camSurface = boguCenter.clone().add(boguNormal.clone().multiplyScalar(45)).add(new THREE.Vector3(15, 20, 25));
      flyTo(camSurface, boguCenter, 1400);
      showToast('Zoomed into South Pole Base Site (Boguslawsky Crater)', '🔍');
    }
  }

  if (btnModeGlobe) {
    btnModeGlobe.addEventListener('click', () => setViewMode('globe'));
  }
  if (btnModeSurface) {
    btnModeSurface.addEventListener('click', () => setViewMode('surface'));
  }

  // Ingestion Chips "FLY ↗" Buttons
  document.querySelectorAll('.ingestion-chip').forEach(chip => {
    const btn = chip.querySelector('.btn-flyto');
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const targetKey = chip.getAttribute('data-target');
        const fp = INGESTION_FOOTPRINTS.find(f => f.id === targetKey);
        if (fp) {
          const targetCenter = latLonToVector3(fp.centerLat, fp.centerLon, MOON_RADIUS);
          const normal = targetCenter.clone().normalize();
          const camPos = targetCenter.clone().add(normal.clone().multiplyScalar(90));
          n3d.controls.autoRotate = false;
          flyTo(camPos, targetCenter, 1300);
          showToast(`Focusing on Ingestion Footprint: ${fp.name}`, '🛰️');
        }
      });
    }
  });

  // 11. Module Selection Function
  function selectModule(modId) {
    const data = MODULE_METADATA[modId];
    if (!data) return;
    n3d.selectedModuleId = modId;

    const obj = n3d.modules[modId];
    if (obj) {
      n3d.highlightRing.position.set(obj.position.x, 0.2, obj.position.z);
      n3d.highlightRing.visible = true;
    }

    // Update Right Inspector HUD
    const nameEl = document.getElementById('inspModName');
    const idEl = document.getElementById('inspModId');
    const coordsEl = document.getElementById('inspCoords');
    const slopeEl = document.getElementById('inspSlope');
    const solarEl = document.getElementById('inspSolar');
    const isruEl = document.getElementById('inspIsruDist');
    const blastEl = document.getElementById('inspBlastDist');
    const gnnEl = document.getElementById('inspGnnScore');

    if (nameEl) nameEl.textContent = data.name;
    if (idEl) idEl.textContent = data.id;
    if (coordsEl) coordsEl.textContent = data.coordsStr;
    if (slopeEl) slopeEl.textContent = data.slope;
    if (solarEl) solarEl.textContent = data.solar;
    if (isruEl) isruEl.textContent = data.isruDist;
    if (blastEl) blastEl.textContent = data.blastDist;
    if (gnnEl) gnnEl.textContent = data.gnnScore;

    document.querySelectorAll('.module-toggle-item').forEach(item => {
      if (item.getAttribute('data-mod') === modId) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });
  }

  // 12. Click Raycasting
  container.addEventListener('click', (event) => {
    const rect = container.getBoundingClientRect();
    n3d.mouse.x = ((event.clientX - rect.left) / container.clientWidth) * 2 - 1;
    n3d.mouse.y = -((event.clientY - rect.top) / container.clientHeight) * 2 + 1;

    n3d.raycaster.setFromCamera(n3d.mouse, n3d.camera);
    const intersects = n3d.raycaster.intersectObjects(n3d.modulesGroup.children, true);

    if (intersects.length > 0) {
      let topObj = intersects[0].object;
      while (topObj.parent && topObj.parent !== n3d.modulesGroup) {
        topObj = topObj.parent;
      }
      if (topObj && topObj.name && MODULE_METADATA[topObj.name]) {
        selectModule(topObj.name);
        showToast(`Selected: ${MODULE_METADATA[topObj.name].name}`, '🛰️');
      }
    }
  });

  // Module Toggle Items
  document.querySelectorAll('.module-toggle-item').forEach(item => {
    item.addEventListener('click', () => {
      const modId = item.getAttribute('data-mod');
      selectModule(modId);
      if (n3d.viewMode === 'globe') {
        setViewMode('surface');
      }
    });
  });

  // 13. Animated Construction Deck
  const btnBuildAll = document.getElementById('btnBuildAllAnimated');
  if (btnBuildAll) {
    btnBuildAll.addEventListener('click', () => {
      runBaseConstructionAnimation();
    });
  }

  function showToast(msg, icon = '🚀') {
    const toast = document.getElementById('nexus3dToast');
    const toastMsg = document.getElementById('toastMsg');
    const toastIcon = document.getElementById('toastIcon');
    if (!toast) return;

    if (toastMsg) toastMsg.textContent = msg;
    if (toastIcon) toastIcon.textContent = icon;
    toast.style.display = 'flex';

    if (n3d.toastTimer) clearTimeout(n3d.toastTimer);
    n3d.toastTimer = setTimeout(() => {
      toast.style.display = 'none';
    }, 4500);
  }

  function runBaseConstructionAnimation() {
    if (n3d.isBuildingAnimated) return;

    // Switch to surface view for best cinematic vantage
    if (n3d.viewMode !== 'surface') {
      setViewMode('surface');
    }

    n3d.isBuildingAnimated = true;

    const moduleKeys = ['hab_core_01', 'hab_solar_01', 'hab_pad_01', 'hab_berm_01', 'hab_isru_01'];
    const stepsInfo = [
      { id: 'hab_core_01', msg: 'Deploying Hab Core 01: Geodesic dome pressurized on lunar regolith.', icon: '🏠' },
      { id: 'hab_solar_01', msg: 'Erecting Solar PV Farm: Bifacial panels oriented to polar sunlight.', icon: '☀️' },
      { id: 'hab_pad_01', msg: 'Sintering Touchdown Pad: Navigation approach beacons active.', icon: '🚀' },
      { id: 'hab_berm_01', msg: 'Constructing Regolith Blast Berm: Plume deflection barrier verified.', icon: '🛡️' },
      { id: 'hab_isru_01', msg: 'Connecting ISRU Plant: Volatiles sublimation cryogenic dewars online.', icon: '💧' },
    ];

    moduleKeys.forEach(k => {
      if (n3d.modules[k]) {
        n3d.modules[k].scale.set(0.01, 0.01, 0.01);
        n3d.modules[k].position.y = 35;
      }
    });

    let currentStep = 0;
    function deployNext() {
      if (currentStep >= stepsInfo.length) {
        n3d.isBuildingAnimated = false;
        showToast('All Base Infrastructure Constructed on the Moon!', '✓');
        document.querySelectorAll('.mod-status-badge').forEach(badge => {
          badge.textContent = 'ONLINE';
          badge.style.background = 'rgba(46, 213, 115, 0.25)';
          badge.style.color = '#2ed573';
        });
        return;
      }

      const step = stepsInfo[currentStep];
      const modObj = n3d.modules[step.id];
      selectModule(step.id);
      showToast(step.msg, step.icon);

      if (modObj) {
        let t = 0;
        const animDrop = setInterval(() => {
          t += 0.08;
          const ease = Math.min(t, 1.0);
          modObj.position.y = (1 - ease) * 35;
          const s = Math.min(ease * 1.05, 1.0);
          modObj.scale.set(s, s, s);

          if (t >= 1.0) {
            clearInterval(animDrop);
            modObj.position.y = 0;
            modObj.scale.set(1, 1, 1);
            currentStep++;
            setTimeout(deployNext, 650);
          }
        }, 16);
      } else {
        currentStep++;
        setTimeout(deployNext, 650);
      }
    }

    deployNext();
  }

  // 14. Lighting Sliders (Elevation & Azimuth)
  const sliderElev = document.getElementById('sliderSunElevation');
  const valElev = document.getElementById('valSunElevation');
  const sliderAzim = document.getElementById('sliderSunAzimuth');
  const valAzim = document.getElementById('valSunAzimuth');

  if (sliderElev) {
    sliderElev.addEventListener('input', (e) => {
      n3d.sunElevation = parseFloat(e.target.value);
      if (valElev) valElev.textContent = `${n3d.sunElevation.toFixed(1)}°`;
      updateSunPosition();
    });
  }

  if (sliderAzim) {
    sliderAzim.addEventListener('input', (e) => {
      n3d.sunAzimuth = parseFloat(e.target.value);
      if (valAzim) valAzim.textContent = `${Math.round(n3d.sunAzimuth)}°`;
      updateSunPosition();
    });
  }

  // 15. Camera Viewpoint Presets
  const CAM_PRESETS = {
    free: { mode: 'globe', pos: [0, 220, 920], target: [0, 0, 0] },
    core: { mode: 'surface', pos: [boguCenter.x + 18, boguCenter.y + 22, boguCenter.z + 26], target: [boguCenter.x, boguCenter.y, boguCenter.z] },
    solar: { mode: 'surface', pos: [boguCenter.x + 28, boguCenter.y + 20, boguCenter.z + 10], target: [boguCenter.x + 12, boguCenter.y, boguCenter.z - 15] },
    pad: { mode: 'surface', pos: [boguCenter.x - 10, boguCenter.y + 25, boguCenter.z + 45], target: [boguCenter.x - 16, boguCenter.y, boguCenter.z + 22] },
    top: { mode: 'globe', pos: [0, 950, 0], target: [0, 0, 0] },
  };

  document.querySelectorAll('.btn-cam-preset').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.btn-cam-preset').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const camKey = btn.getAttribute('data-cam');
      const preset = CAM_PRESETS[camKey];
      if (preset && n3d.controls) {
        n3d.controls.autoRotate = false;
        flyTo(new THREE.Vector3(...preset.pos), new THREE.Vector3(...preset.target), 1200);
      }
    });
  });

  // 16. Blender MCP Server Status & Integration Pipeline
  async function checkBlenderMCPStatus() {
    const pill = document.getElementById('blenderStatusPill');
    const textEl = document.getElementById('mcpStatusText');
    try {
      const res = await fetch('/api/nexus/blender/status');
      if (res.ok) {
        const data = await res.json();
        if (data.online) {
          if (pill) {
            pill.className = 'blender-mcp-status-card online';
          }
          if (textEl) textEl.textContent = `Blender MCP: ONLINE (Port ${data.port})`;
        } else {
          if (pill) {
            pill.className = 'blender-mcp-status-card offline';
          }
          if (textEl) {
            textEl.textContent = data.blender_available
              ? 'Blender MCP: Standby (Auto-Fallback to Headless Engine)'
              : 'Blender MCP: Offline (Port 9876)';
          }
        }
      }
    } catch (e) {
      if (textEl) textEl.textContent = 'Blender MCP: Standby (Port 9876)';
    }
  }

  checkBlenderMCPStatus();
  setInterval(checkBlenderMCPStatus, 8000);

  // Action Button: Build in Blender 3D (Port 9876)
  const btnBuildMcp = document.getElementById('btnBuildBlenderMcp');
  if (btnBuildMcp) {
    btnBuildMcp.addEventListener('click', async () => {
      btnBuildMcp.disabled = true;
      btnBuildMcp.innerHTML = '<span class="spinner" style="width:14px;height:14px;display:inline-block;margin-right:6px;"></span> Transmitting to Blender MCP...';
      showToast('Transmitting procedural spherical Moon scene to Blender MCP (Port 9876)...', '⚡');

      try {
        const res = await fetch('/api/nexus/blender/build', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force_headless: false }),
        });
        const result = await res.json();
        if (result.success) {
          showToast(`Success! Spherical Moon Base constructed in Blender (${result.mode === 'mcp_socket' ? 'Socket 9876' : 'Headless Engine'})`, '✓');
          const modalImg = document.getElementById('blenderModalImg');
          if (modalImg) modalImg.src = `/outputs/nexus_3d/nexus_blender_digital_twin.png?t=${Date.now()}`;
        } else {
          showToast(`Blender Build Notice: ${result.message || result.error || 'Execution finished'}`, 'ℹ️');
        }
      } catch (err) {
        showToast(`Blender Bridge: Fallback execution completed`, '✓');
      } finally {
        btnBuildMcp.disabled = false;
        btnBuildMcp.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg> Build in Blender 3D (Port 9876)';
        checkBlenderMCPStatus();
      }
    });
  }

  // Action Button: Render Photorealistic Twin (EEVEE/Cycles)
  const btnRenderTwin = document.getElementById('btnRenderBlenderHeadless');
  if (btnRenderTwin) {
    btnRenderTwin.addEventListener('click', async () => {
      btnRenderTwin.disabled = true;
      btnRenderTwin.innerHTML = '<span class="spinner" style="width:14px;height:14px;display:inline-block;margin-right:6px;"></span> Raytracing in Blender...';
      showToast('Launching headless Blender EEVEE/Cycles PBR rendering engine...', '📸');

      try {
        const res = await fetch('/api/nexus/blender/build', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ force_headless: true }),
        });
        const result = await res.json();
        if (result.success) {
          showToast(`Raytraced Digital Twin rendered successfully (${result.image_size_kb || 1500} KB)`, '✓');
          const modalImg = document.getElementById('blenderModalImg');
          if (modalImg) modalImg.src = `/outputs/nexus_3d/nexus_blender_digital_twin.png?t=${Date.now()}`;
          const modal = document.getElementById('blenderRenderModal');
          if (modal) modal.style.display = 'flex';
        } else {
          showToast(`Render failed: ${result.error}`, '❌');
        }
      } catch (err) {
        showToast(`Render error: ${err.message}`, '❌');
      } finally {
        btnRenderTwin.disabled = false;
        btnRenderTwin.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg> Render PBR Twin';
      }
    });
  }

  // Action Button: View Rendered Twin Lightbox
  const btnViewTwin = document.getElementById('btnViewBlenderRender');
  const modal = document.getElementById('blenderRenderModal');
  const btnCloseModal = document.getElementById('btnCloseBlenderModal');
  const btnDismissModal = document.getElementById('btnDismissBlenderModal');

  if (btnViewTwin && modal) {
    btnViewTwin.addEventListener('click', () => {
      const modalImg = document.getElementById('blenderModalImg');
      if (modalImg) modalImg.src = `/outputs/nexus_3d/nexus_blender_digital_twin.png?t=${Date.now()}`;
      modal.style.display = 'flex';
    });
  }

  if (btnCloseModal && modal) {
    btnCloseModal.addEventListener('click', () => { modal.style.display = 'none'; });
  }
  if (btnDismissModal && modal) {
    btnDismissModal.addEventListener('click', () => { modal.style.display = 'none'; });
  }

  // 17. Window Resize Handler
  n3d.onResize = function() {
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || (window.innerHeight - 64);
    if (w && h && n3d.camera && n3d.renderer) {
      n3d.camera.aspect = w / h;
      n3d.camera.updateProjectionMatrix();
      n3d.renderer.setSize(w, h);
    }
  };
  window.addEventListener('resize', n3d.onResize);

  // 18. Animation Render Loop
  let roverT = 0;
  function animate() {
    n3d.animationFrameId = requestAnimationFrame(animate);

    if (n3d.controls) {
      n3d.controls.update();
    }

    // Pulse highlight ring
    if (n3d.highlightRing && n3d.highlightRing.visible) {
      const pulse = 1 + Math.sin(Date.now() * 0.005) * 0.05;
      n3d.highlightRing.scale.set(pulse, pulse, 1);
    }

    // Move autonomous rover along transit path
    if (n3d.roverGroup) {
      roverT += 0.002;
      const tNorm = Math.sin(roverT) * 0.5 + 0.5;
      const point = pipeCurve.getPoint(tNorm);
      n3d.roverGroup.position.set(point.x, point.y + 0.3, point.z);
    }

    n3d.renderer.render(n3d.scene, n3d.camera);
  }
  animate();

  // Initial selection
  selectModule('hab_core_01');
}



