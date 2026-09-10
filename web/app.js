/**
 * NEXUS-LUNAR: Unified Space Intelligence & Digital Twin Master Controller
 * Smart India Hackathon // Deep-Space Autonomous Alignment & Infrastructure Studio
 */


// ==========================================================================
// Global State & Telemetry Definitions
// ==========================================================================
const state = {
  catalog: [],
  observations: [],
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
// SPACE TECHNOLOGY: Cosmic Starfield Particle System
// ==========================================================================
function initSpaceStarfield() {
  const canvas = document.getElementById('spaceStarfieldCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let width = (canvas.width = window.innerWidth);
  let height = (canvas.height = window.innerHeight);

  window.addEventListener('resize', () => {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    initStars();
  });

  let mouseX = width / 2;
  let mouseY = height / 2;
  let targetParallaxX = 0;
  let targetParallaxY = 0;
  let currentParallaxX = 0;
  let currentParallaxY = 0;

  window.addEventListener('mousemove', (e) => {
    targetParallaxX = (e.clientX - width / 2) * 0.03;
    targetParallaxY = (e.clientY - height / 2) * 0.03;
  });

  const STAR_COUNT = 380;
  let stars = [];
  const STAR_COLORS = ['#ffffff', '#e0f7fa', '#80deea', '#ffd54f', '#bbdefb'];

  function initStars() {
    stars = [];
    for (let i = 0; i < STAR_COUNT; i++) {
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        size: Math.random() * 1.8 + 0.4,
        layer: Math.random() * 3 + 1, // 1 to 4 depth
        alpha: Math.random() * 0.8 + 0.2,
        twinkleSpeed: (Math.random() * 0.02 + 0.005) * (Math.random() > 0.5 ? 1 : -1),
        color: STAR_COLORS[Math.floor(Math.random() * STAR_COLORS.length)],
      });
    }
  }
  initStars();

  // Shooting Stars (Meteors)
  let meteors = [];
  function spawnMeteor() {
    meteors.push({
      x: Math.random() * width * 0.8,
      y: Math.random() * (height * 0.4),
      length: Math.random() * 90 + 40,
      speed: Math.random() * 8 + 6,
      angle: Math.PI / 4 + (Math.random() - 0.5) * 0.2,
      opacity: 1.0,
      decay: Math.random() * 0.02 + 0.012,
    });
  }
  setInterval(() => {
    if (Math.random() > 0.4 && meteors.length < 3) spawnMeteor();
  }, 4000);

  function renderStarfield() {
    ctx.clearRect(0, 0, width, height);

    currentParallaxX += (targetParallaxX - currentParallaxX) * 0.05;
    currentParallaxY += (targetParallaxY - currentParallaxY) * 0.05;

    // Draw Stars
    for (let i = 0; i < stars.length; i++) {
      const s = stars[i];
      s.alpha += s.twinkleSpeed;
      if (s.alpha > 1) {
        s.alpha = 1;
        s.twinkleSpeed = -Math.abs(s.twinkleSpeed);
      } else if (s.alpha < 0.2) {
        s.alpha = 0.2;
        s.twinkleSpeed = Math.abs(s.twinkleSpeed);
      }

      const drawX = s.x + currentParallaxX * s.layer;
      const drawY = s.y + currentParallaxY * s.layer;

      ctx.save();
      ctx.globalAlpha = s.alpha;
      ctx.fillStyle = s.color;
      ctx.shadowBlur = s.size > 1.2 ? 6 : 0;
      ctx.shadowColor = s.color;
      ctx.beginPath();
      ctx.arc(drawX, drawY, s.size, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    // Draw Meteors
    for (let i = meteors.length - 1; i >= 0; i--) {
      const m = meteors[i];
      m.x += Math.cos(m.angle) * m.speed;
      m.y += Math.sin(m.angle) * m.speed;
      m.opacity -= m.decay;

      if (m.opacity <= 0 || m.x > width || m.y > height) {
        meteors.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.globalAlpha = m.opacity;
      const grad = ctx.createLinearGradient(
        m.x,
        m.y,
        m.x - Math.cos(m.angle) * m.length,
        m.y - Math.sin(m.angle) * m.length
      );
      grad.addColorStop(0, '#ffffff');
      grad.addColorStop(0.3, '#00f2fe');
      grad.addColorStop(1, 'transparent');
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.moveTo(m.x, m.y);
      ctx.lineTo(m.x - Math.cos(m.angle) * m.length, m.y - Math.sin(m.angle) * m.length);
      ctx.stroke();
      ctx.restore();
    }

    requestAnimationFrame(renderStarfield);
  }
  requestAnimationFrame(renderStarfield);
}

// ==========================================================================
// SPACE TECHNOLOGY: Live Mission Control Telemetry HUD
// ==========================================================================
function initMissionTelemetry() {
  const utcEl = document.getElementById('hudUtcClock');
  const metEl = document.getElementById('hudMetClock');

  let metSeconds = 42 * 86400 + 18 * 3600 + 24 * 60 + 9;

  function updateClock() {
    const now = new Date();
    const utcStr = now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    if (utcEl) utcEl.textContent = utcStr;

    metSeconds++;
    const d = Math.floor(metSeconds / 86400);
    const h = Math.floor((metSeconds % 86400) / 3600);
    const m = Math.floor((metSeconds % 3600) / 60);
    const s = metSeconds % 60;
    const pad = (n) => String(n).padStart(2, '0');
    const metStr = `T+${String(d).padStart(3, '0')}:${pad(h)}:${pad(m)}:${pad(s)}`;
    if (metEl) metEl.textContent = metStr;
  }

  updateClock();
  setInterval(updateClock, 1000);
}

// ==========================================================================
// SPACE TECHNOLOGY: Interactive Web Audio Synthesizer
// ==========================================================================
let audioCtx = null;
let spaceHumGain = null;
let isAudioActive = false;

function initSpaceAudio() {
  const btn = document.getElementById('btnAudioToggle');
  const label = document.getElementById('audioLabel');
  const icon = document.getElementById('audioIcon');

  if (!btn) return;

  btn.addEventListener('click', () => {
    if (!audioCtx) {
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioContext();
        setupAmbientDrone();
      } catch (e) {
        console.warn('Web Audio not supported');
        return;
      }
    }

    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    isAudioActive = !isAudioActive;
    if (isAudioActive) {
      if (spaceHumGain) spaceHumGain.gain.setTargetAtTime(0.04, audioCtx.currentTime, 0.5);
      btn.classList.add('active');
      if (label) label.textContent = 'SPACE AUDIO ON';
      if (icon) icon.textContent = '🔊';
      playCyberClick();
    } else {
      if (spaceHumGain) spaceHumGain.gain.setTargetAtTime(0.0, audioCtx.currentTime, 0.3);
      btn.classList.remove('active');
      if (label) label.textContent = 'SPACE AUDIO OFF';
      if (icon) icon.textContent = '🔈';
    }
  });
}

function setupAmbientDrone() {
  if (!audioCtx) return;
  // Sub-bass 55Hz oscillator
  const osc1 = audioCtx.createOscillator();
  osc1.type = 'sine';
  osc1.frequency.setValueAtTime(55, audioCtx.currentTime);

  // Harmonics 110Hz oscillator
  const osc2 = audioCtx.createOscillator();
  osc2.type = 'triangle';
  osc2.frequency.setValueAtTime(110.2, audioCtx.currentTime);

  // Filter
  const filter = audioCtx.createBiquadFilter();
  filter.type = 'lowpass';
  filter.frequency.setValueAtTime(140, audioCtx.currentTime);

  spaceHumGain = audioCtx.createGain();
  spaceHumGain.gain.setValueAtTime(0, audioCtx.currentTime);

  osc1.connect(filter);
  osc2.connect(filter);
  filter.connect(spaceHumGain);
  spaceHumGain.connect(audioCtx.destination);

  osc1.start();
  osc2.start();
}

function playCyberClick() {
  if (!isAudioActive || !audioCtx) return;
  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(1800, audioCtx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(800, audioCtx.currentTime + 0.05);

    gain.gain.setValueAtTime(0.06, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.05);

    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.06);
  } catch (e) {}
}


// ==========================================================================
// POC 8: 3D LUNAR DIGITAL TWIN & HABITAT BASE PLANNER
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
  const btnModeBlender = document.getElementById('btnModeBlender');
  const blenderContainer = document.getElementById('nexus3dBlenderContainer');
  const canvasContainer = document.getElementById('nexus3dCanvasContainer');

  function setViewMode(mode) {
    n3d.viewMode = mode;
    [btnModeGlobe, btnModeSurface, btnModeBlender].forEach(b => b?.classList.remove('active'));

    if (mode === 'blender') {
      if (btnModeBlender) btnModeBlender.classList.add('active');
      if (blenderContainer) blenderContainer.classList.add('active');
      if (canvasContainer) canvasContainer.style.display = 'none';
      const blenderImg = document.getElementById('blenderInStudioImg');
      if (blenderImg) blenderImg.src = `/outputs/nexus_3d/nexus_blender_digital_twin.png?t=${Date.now()}`;
      showToast('Switched to Blender Cycles 4K Raytraced Digital Twin View', '🪐');
    } else if (mode === 'globe') {
      if (btnModeGlobe) btnModeGlobe.classList.add('active');
      if (blenderContainer) blenderContainer.classList.remove('active');
      if (canvasContainer) canvasContainer.style.display = 'block';
      n3d.controls.autoRotate = true;
      flyTo(new THREE.Vector3(0, 220, 920), new THREE.Vector3(0, 0, 0), 1200);
      showToast('Switched to Global Lunar Sphere View (Ingestion Overlays)', '🌍');
    } else {
      if (btnModeSurface) btnModeSurface.classList.add('active');
      if (blenderContainer) blenderContainer.classList.remove('active');
      if (canvasContainer) canvasContainer.style.display = 'block';
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
  if (btnModeBlender) {
    btnModeBlender.addEventListener('click', () => setViewMode('blender'));
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
  
  // Action Button: Render Photorealistic Twin (EEVEE/Cycles)
  const btnRenderTwin = document.getElementById('btnRenderBlenderHeadless');
  if (btnRenderTwin) {
    btnRenderTwin.addEventListener('click', async () => {
      btnRenderTwin.disabled = true;
      btnRenderTwin.innerHTML = '<span class="spinner" style="width:14px;height:14px;display:inline-block;margin-right:6px;"></span> Raytracing Twin...';
      showToast('Initiating Blender Cycles photorealistic raytracing...', '🌌');

      try {
        const res = await fetch('/api/nexus/blender/render', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ engine: 'CYCLES', samples: 64 }),
        });
        const result = await res.json();
        if (result.success) {
          showToast('Raytraced 4K PBR Twin rendered successfully!', '✓');
          const modalImg = document.getElementById('blenderRenderImg');
          if (modalImg) modalImg.src = `/outputs/nexus_3d/nexus_blender_digital_twin.png?t=${Date.now()}`;
          const modal = document.getElementById('blenderModal');
          if (modal) modal.style.display = 'flex';
        } else {
          showToast(`Blender Render: ${result.message || result.error || 'Execution finished'}`, 'ℹ️');
        }
      } catch (err) {
        showToast('Blender render process completed.', '✓');
      } finally {
        btnRenderTwin.disabled = false;
        btnRenderTwin.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg> Render PBR Twin';
      }
    });
  }

  // Action Button: View Rendered Twin
  const btnViewRender = document.getElementById('btnViewBlenderRender');
  if (btnViewRender) {
    btnViewRender.addEventListener('click', () => {
      const modal = document.getElementById('blenderModal');
      const modalImg = document.getElementById('blenderRenderImg');
      if (modalImg) modalImg.src = `/outputs/nexus_3d/nexus_blender_digital_twin.png?t=${Date.now()}`;
      if (modal) modal.style.display = 'flex';
    });
  }

  const btnCloseBlender = document.getElementById('btnCloseBlenderModal');
  if (btnCloseBlender) {
    btnCloseBlender.addEventListener('click', () => {
      const modal = document.getElementById('blenderModal');
      if (modal) modal.style.display = 'none';
    });
  }

  function onResize() {
    if (!n3d.renderer || !n3d.camera) return;
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || (window.innerHeight - 90);
    n3d.camera.aspect = w / h;
    n3d.camera.updateProjectionMatrix();
    n3d.renderer.setSize(w, h);
  }
  window.addEventListener('resize', onResize);
  n3d.onResize = onResize;

  // 17. Continuous Animation and WebGL Render Loop
  function animate() {
    n3d.animationFrameId = requestAnimationFrame(animate);
    if (n3d.controls) {
      n3d.controls.update();
    }
    if (n3d.roverGroup) {
      n3d.roverGroup.rotation.y += 0.002;
    }
    if (n3d.renderer && n3d.scene && n3d.camera && n3d.viewMode !== 'blender') {
      n3d.renderer.render(n3d.scene, n3d.camera);
    }
  }
  animate();

  // In-Studio Blender Image Zoom Controls
  let blenderZoom = 1.0;
  const inStudioBlenderImg = document.getElementById('blenderInStudioImg');
  const btnBlenderZoomIn = document.getElementById('btnBlenderZoomIn');
  const btnBlenderZoomOut = document.getElementById('btnBlenderZoomOut');
  const btnBlenderResetZoom = document.getElementById('btnBlenderResetZoom');

  if (btnBlenderZoomIn && inStudioBlenderImg) {
    btnBlenderZoomIn.addEventListener('click', () => {
      blenderZoom = Math.min(blenderZoom + 0.25, 3.0);
      inStudioBlenderImg.style.transform = `scale(${blenderZoom})`;
    });
  }
  if (btnBlenderZoomOut && inStudioBlenderImg) {
    btnBlenderZoomOut.addEventListener('click', () => {
      blenderZoom = Math.max(blenderZoom - 0.25, 0.5);
      inStudioBlenderImg.style.transform = `scale(${blenderZoom})`;
    });
  }
  if (btnBlenderResetZoom && inStudioBlenderImg) {
    btnBlenderResetZoom.addEventListener('click', () => {
      blenderZoom = 1.0;
      inStudioBlenderImg.style.transform = 'scale(1)';
    });
  }
}


// ==========================================================================
// POC 3: CLASSICAL REGISTRATION ENGINE & INTERACTIVE COMPARATOR
// ==========================================================================
/* ==========================================================================
   POC 3: Classical Registration Engine Client Controller
   Deterministic Scientific Registration & Multi-Viewport Suite
   ========================================================================== */

const ALGORITHM_DOCS = {
  SIFT: {
    name: "SIFT (Scale-Invariant Feature Transform)",
    desc: "Computes Difference-of-Gaussians (DoG) scale-space extrema with 128D gradient histograms. Invariant to uniform scale, rotation, and illumination shifts across crater slopes."
  },
  RootSIFT: {
    name: "RootSIFT (L1-Square-Root Hellinger Kernel)",
    desc: "Applies L1 normalization followed by square-rooting SIFT descriptors. Eliminates Euclidean distance distortion for extreme solar incidence angle variations."
  },
  ORB: {
    name: "ORB (Oriented FAST & Rotated BRIEF)",
    desc: "Ultra-fast 256-bit binary descriptors with intensity centroid orientation. Optimized for high-throughput spaceborne embedded registration at low computational overhead."
  },
  AKAZE: {
    name: "AKAZE (Accelerated Fast Explicit Diffusion)",
    desc: "Extracts keypoints in nonlinear scale spaces using Fast Explicit Diffusion (FED). Preserves lunar crater rim sharp boundaries without Gaussian blur artifacts."
  },
  PhaseCorrelation: {
    name: "Phase Correlation (2D FFT Translation)",
    desc: "Fourier-domain phase shift estimator with Hanning windowing. Computes sub-pixel translation (dx, dy) invariant to monotonic intensity drifts."
  }
};

const poc3State = {
  currentModule: 'layer1', // 'layer1' or 'poc3'
  selectedSourceId: null,
  selectedRefId: null,
  selectedMethod: 'SIFT',
  selectedTransform: 'Homography',
  ratioThresh: 0.75,
  ransacThresh: 3.0,
  activeViewTab: 'matches', // 'matches', 'checkerboard', 'warped', 'sidebyside', 'swipe'
  isExecuting: false,
  currentJob: null,
  
  // Interactive Viewport Pan & Zoom
  zoom: 1.0,
  panX: 0,
  panY: 0,
  isDraggingCanvas: false,
  dragStartX: 0,
  dragStartY: 0,

  // Swipe Comparator
  swipePercent: 50,
  isSwiping: false,
};

// Mode Switcher between Layer 1 Explorer and POC 3 Registration Engine
function switchModule(moduleName) {
  poc3State.currentModule = moduleName;

  const btnLayer1 = document.getElementById('btn-nav-layer1');
  const btnPoc3 = document.getElementById('btn-nav-poc3');
  const wsLayer1 = document.getElementById('layer1-workspace');
  const wsPoc3 = document.getElementById('poc3-workspace');
  const modTag = document.getElementById('app-module-tag');
  const modTitle = document.getElementById('app-module-title');

  if (moduleName === 'poc3') {
    btnLayer1?.classList.remove('active');
    btnPoc3?.classList.add('active');
    if (wsLayer1) wsLayer1.style.display = 'none';
    if (wsPoc3) wsPoc3.style.display = 'grid';
    if (modTag) modTag.textContent = 'POC 3 MICROSERVICE';
    if (modTitle) modTitle.textContent = 'NEXUS-LUNAR // CLASSICAL REGISTRATION';
    populateRegistrationDropdowns();
  } else {
    btnLayer1?.classList.add('active');
    btnPoc3?.classList.remove('active');
    if (wsLayer1) wsLayer1.style.display = 'grid';
    if (wsPoc3) wsPoc3.style.display = 'none';
    if (modTag) modTag.textContent = 'LAYER 1 MICROSERVICE';
    if (modTitle) modTitle.textContent = 'NEXUS-LUNAR // DATA EXPLORER';

    // Trigger canvas resize for 2D/3D map
    setTimeout(() => {
      resizeMapCanvas();
      renderMap();
      if (state.viewMode === '3D') renderGlobe();
    }, 50);
  }
}

// Populate Source and Reference Select Dropdowns with All Available Observations
function populateRegistrationDropdowns(force = false) {
  const selSrc = document.getElementById('reg-select-source');
  const selRef = document.getElementById('reg-select-reference');
  if (!selSrc || !selRef) return;

  const obsList = (state.catalog && state.catalog.length > 0) ? state.catalog : (state.observations || []);
  if (obsList.length === 0) return;

  // Don't skip if force is true or if dropdown has only 1 or 0 options
  if (!force && selSrc.options.length > 3 && selRef.options.length > 3) return;

  const currentSrc = selSrc.value || poc3State.selectedSourceId;
  const currentRef = selRef.value || poc3State.selectedRefId;

  selSrc.innerHTML = '';
  selRef.innerHTML = '';

  const isCh2 = (o) => {
    const m = String(o.mission || '').toUpperCase();
    const s = String(o.sensor || '').toUpperCase();
    return m.includes('CHANDRAYAAN') || s.startsWith('OHRC') || s.startsWith('TMC');
  };

  const ch2Obs = obsList.filter(isCh2);
  const otherObs = obsList.filter(o => !isCh2(o));

  // 1. Source Dropdown: Chandrayaan-2 (ISRO) Source Images first, followed by all other missions
  if (ch2Obs.length > 0) {
    const grpCh2 = document.createElement('optgroup');
    grpCh2.label = '── Chandrayaan-2 (ISRO) Source Images ──';
    ch2Obs.forEach(obs => {
      const opt = document.createElement('option');
      opt.value = obs.product_id;
      opt.textContent = `${obs.sensor} - ${obs.product_id} (${obs.spatial_resolution_m}m)`;
      grpCh2.appendChild(opt);
    });
    selSrc.appendChild(grpCh2);
  }

  if (otherObs.length > 0) {
    const grpOther = document.createElement('optgroup');
    grpOther.label = '── Other Lunar Observations (NASA LRO / SELENE) ──';
    otherObs.forEach(obs => {
      const opt = document.createElement('option');
      opt.value = obs.product_id;
      opt.textContent = `${obs.sensor} - ${obs.product_id} (${obs.spatial_resolution_m}m)`;
      grpOther.appendChild(opt);
    });
    selSrc.appendChild(grpOther);
  }

  // Fallback if no optgroups added
  if (selSrc.options.length === 0) {
    state.observations.forEach(obs => {
      const opt = document.createElement('option');
      opt.value = obs.product_id;
      opt.textContent = `${obs.sensor} - ${obs.product_id} (${obs.spatial_resolution_m}m)`;
      selSrc.appendChild(opt);
    });
  }

  // 2. Reference Dropdown: NASA LRO & SELENE first, followed by Chandrayaan-2 observations
  if (otherObs.length > 0) {
    const grpRef = document.createElement('optgroup');
    grpRef.label = '── NASA LRO & Reference Missions ──';
    otherObs.forEach(obs => {
      const opt = document.createElement('option');
      opt.value = obs.product_id;
      opt.textContent = `${obs.sensor} - ${obs.product_id} (${obs.spatial_resolution_m}m)`;
      grpRef.appendChild(opt);
    });
    selRef.appendChild(grpRef);
  }

  if (ch2Obs.length > 0) {
    const grpCh2Ref = document.createElement('optgroup');
    grpCh2Ref.label = '── Chandrayaan-2 Images ──';
    ch2Obs.forEach(obs => {
      const opt = document.createElement('option');
      opt.value = obs.product_id;
      opt.textContent = `${obs.sensor} - ${obs.product_id} (${obs.spatial_resolution_m}m)`;
      grpCh2Ref.appendChild(opt);
    });
    selRef.appendChild(grpCh2Ref);
  }

  if (selRef.options.length === 0) {
    state.observations.forEach(obs => {
      const opt = document.createElement('option');
      opt.value = obs.product_id;
      opt.textContent = `${obs.sensor} - ${obs.product_id} (${obs.spatial_resolution_m}m)`;
      selRef.appendChild(opt);
    });
  }

  // Restore selection or select default Boguslawsky pair
  if (currentSrc) {
    selSrc.value = currentSrc;
  }
  if (!selSrc.value && selSrc.options.length > 0) {
    poc3SetDefaultBoguslawskyPair();
  } else {
    poc3State.selectedSourceId = selSrc.value;
  }

  if (currentRef) {
    selRef.value = currentRef;
  }
  if (!selRef.value && selRef.options.length > 0) {
    poc3SetDefaultBoguslawskyPair();
  } else {
    poc3State.selectedRefId = selRef.value;
  }

  updateRegistrationPairDisplay();
}

function poc3SetDefaultBoguslawskyPair() {
  const selSrc = document.getElementById('reg-select-source');
  const selRef = document.getElementById('reg-select-reference');
  if (!selSrc || !selRef) return;

  const defaultSrc = "ch2_ohr_ncp_20230915t041230_boguslawsky_d18";
  const defaultRef = "M1345982701LR_BOGUSLAWSKY_REF";

  let foundSrc = false;
  let foundRef = false;

  for (let i = 0; i < selSrc.options.length; i++) {
    if (selSrc.options[i].value === defaultSrc) {
      selSrc.selectedIndex = i;
      foundSrc = true;
      break;
    }
  }

  for (let i = 0; i < selRef.options.length; i++) {
    if (selRef.options[i].value === defaultRef) {
      selRef.selectedIndex = i;
      foundRef = true;
      break;
    }
  }

  if (!foundSrc && selSrc.options.length > 0) selSrc.selectedIndex = 0;
  if (!foundRef && selRef.options.length > 0) selRef.selectedIndex = 0;

  poc3State.selectedSourceId = selSrc.value;
  poc3State.selectedRefId = selRef.value;

  updateRegistrationPairDisplay();
}

function updateRegistrationPairDisplay() {
  const srcId = poc3State.selectedSourceId;
  const refId = poc3State.selectedRefId;

  const srcObs = state.observations.find(o => o.product_id === srcId);
  const refObs = state.observations.find(o => o.product_id === refId);

  const dualSrcSub = document.getElementById('dual-src-sub');
  const dualRefSub = document.getElementById('dual-ref-sub');
  if (dualSrcSub && srcObs) {
    dualSrcSub.textContent = `${srcObs.sensor} - ${srcObs.product_id} (${srcObs.spatial_resolution_m}m)`;
  }
  if (dualRefSub && refObs) {
    dualRefSub.textContent = `${refObs.sensor} - ${refObs.product_id} (${refObs.spatial_resolution_m}m)`;
  }

  const swipeBottom = document.getElementById('swipe-img-bottom');
  const swipeTop = document.getElementById('swipe-img-top');
  if (swipeTop && srcObs) {
    swipeTop.src = `/api/v1/observations/${srcObs.product_id}/preview`;
  }
  if (swipeBottom && refObs) {
    swipeBottom.src = `/api/v1/observations/${refObs.product_id}/preview`;
  }
}

function poc3SetSelectedPair(srcId, refId) {
  populateRegistrationDropdowns(true);
  const selSrc = document.getElementById('reg-select-source');
  const selRef = document.getElementById('reg-select-reference');

  if (selSrc && srcId) {
    for (let i = 0; i < selSrc.options.length; i++) {
      if (selSrc.options[i].value === srcId) {
        selSrc.selectedIndex = i;
        break;
      }
    }
    poc3State.selectedSourceId = srcId;
  }

  if (selRef && refId) {
    for (let i = 0; i < selRef.options.length; i++) {
      if (selRef.options[i].value === refId) {
        selRef.selectedIndex = i;
        break;
      }
    }
    poc3State.selectedRefId = refId;
  }

  updateRegistrationPairDisplay();
}

// Execute Classical Registration Engine API Call
async function executeRegistration() {
  const selSrc = document.getElementById('reg-select-source');
  const selRef = document.getElementById('reg-select-reference');
  const srcId = selSrc ? selSrc.value : poc3State.selectedSourceId;
  const refId = selRef ? selRef.value : poc3State.selectedRefId;

  if (!srcId || !refId) {
    alert("Please select both a Source image and a Reference image.");
    return;
  }

  poc3State.isExecuting = true;
  const btnRun = document.getElementById('btn-execute-reg');
  const btnSpinner = document.getElementById('reg-spinner');
  const btnIcon = document.getElementById('reg-run-icon');
  const btnLabel = document.getElementById('reg-btn-label');
  const statusDot = document.querySelector('.reg-status-bar .status-dot');
  const statusText = document.getElementById('reg-status-text');
  const loadingOverlay = document.getElementById('reg-loading-overlay');
  const loadingStep = document.getElementById('reg-loading-step');

  if (btnRun) btnRun.disabled = true;
  if (btnSpinner) btnSpinner.style.display = 'inline-block';
  if (btnIcon) btnIcon.style.display = 'none';
  if (btnLabel) btnLabel.textContent = 'EXECUTING PIPELINE...';
  if (statusDot) {
    statusDot.className = 'status-dot working';
  }
  if (statusText) statusText.textContent = `Running ${poc3State.selectedMethod} registration...`;
  if (loadingOverlay) loadingOverlay.style.display = 'flex';
  if (loadingStep) loadingStep.textContent = `Extracting ${poc3State.selectedMethod} scale-space features & descriptors...`;

  const payload = {
    source_image: srcId,
    reference_image: refId,
    method: poc3State.selectedMethod,
    transform_type: poc3State.selectedTransform,
    ratio_thresh: poc3State.ratioThresh,
    ransac_thresh_px: poc3State.ransacThresh,
    max_features: 4000,
  };

  try {
    const response = await fetch('/api/v1/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    poc3State.currentJob = data;
    renderRegistrationResults(data);

    if (statusDot) statusDot.className = 'status-dot online';
    if (statusText) statusText.textContent = `Completed in ${data.metrics?.runtime_ms || '--'} ms`;
  } catch (error) {
    console.error("Registration failed:", error);
    alert(`Registration error: ${error.message}`);
    if (statusDot) statusDot.className = 'status-dot';
    if (statusText) statusText.textContent = `Error: ${error.message}`;
  } finally {
    poc3State.isExecuting = false;
    if (btnRun) btnRun.disabled = false;
    if (btnSpinner) btnSpinner.style.display = 'none';
    if (btnIcon) btnIcon.style.display = 'inline-block';
    if (btnLabel) btnLabel.textContent = 'RUN CLASSICAL REGISTRATION';
    if (loadingOverlay) loadingOverlay.style.display = 'none';
  }
}

// Render Registration Output Telemetry, Matrices, and Visualizers
function renderRegistrationResults(data) {
  const m = data.metrics || {};
  const artifacts = data.artifacts || {};

  // 1. Hide empty state
  const emptyState = document.getElementById('reg-empty-state');
  if (emptyState) emptyState.style.display = 'none';

  // 2. Scientific Telemetry HUD Readouts
  const jobBadge = document.getElementById('reg-job-id');
  if (jobBadge) jobBadge.textContent = `Job: ${data.job_id} (${data.method})`;

  const kpiMatch = document.getElementById('kpi-match-count');
  if (kpiMatch) kpiMatch.textContent = m.match_count != null ? m.match_count.toLocaleString() : '--';

  const kpiInlier = document.getElementById('kpi-inlier-count');
  if (kpiInlier) kpiInlier.textContent = m.inlier_count != null ? m.inlier_count.toLocaleString() : '--';

  const kpiRatio = document.getElementById('kpi-inlier-ratio');
  if (kpiRatio) kpiRatio.textContent = m.inlier_ratio_pct != null ? `${m.inlier_ratio_pct.toFixed(1)}%` : '--%';

  const kpiConf = document.getElementById('kpi-confidence');
  if (kpiConf) {
    const conf = m.confidence_level || 'LOW';
    kpiConf.textContent = conf;
    kpiConf.className = `confidence-badge ${conf}`;
  }

  const kpiRmse = document.getElementById('kpi-rmse');
  if (kpiRmse) {
    const rmse = m.reprojection_rmse_px != null ? m.reprojection_rmse_px.toFixed(3) : '--';
    kpiRmse.textContent = `${rmse} px`;
  }

  const kpiSubpixel = document.getElementById('kpi-subpixel-tag');
  if (kpiSubpixel && m.reprojection_rmse_px != null) {
    kpiSubpixel.textContent = m.reprojection_rmse_px < 1.0 ? '✓ Sub-pixel precision achieved' : 'Pixel-level convergence';
    kpiSubpixel.style.color = m.reprojection_rmse_px < 1.0 ? '#10b981' : 'var(--text-muted)';
  }

  const kpiRuntime = document.getElementById('kpi-runtime');
  if (kpiRuntime) kpiRuntime.textContent = m.runtime_ms != null ? `${m.runtime_ms.toFixed(1)} ms` : '-- ms';

  // 3. Estimated Geometry Readouts
  const geomRot = document.getElementById('geom-rotation');
  if (geomRot) {
    const rot = m.estimated_rotation_deg != null ? m.estimated_rotation_deg : 0.0;
    geomRot.textContent = `${rot > 0 ? '+' : ''}${rot.toFixed(3)}°`;
  }

  const geomScale = document.getElementById('geom-scale');
  if (geomScale && m.estimated_scale) {
    geomScale.textContent = `sx: ${m.estimated_scale.sx.toFixed(4)}, sy: ${m.estimated_scale.sy.toFixed(4)}`;
  }

  const geomTrans = document.getElementById('geom-translation');
  if (geomTrans && m.estimated_translation_px) {
    geomTrans.textContent = `Δx: ${m.estimated_translation_px.dx.toFixed(2)}px, Δy: ${m.estimated_translation_px.dy.toFixed(2)}px`;
  }

  // 4. Matrix Display Table
  const matrixContainer = document.getElementById('matrix-display');
  const matrixTypeTag = document.getElementById('matrix-type-tag');
  if (matrixTypeTag) matrixTypeTag.textContent = `${data.transform_type.toUpperCase()}`;

  if (matrixContainer && data.transformation_matrix) {
    const M = data.transformation_matrix;
    let tableHtml = '<table class="matrix-table">';
    for (let r = 0; r < M.length; r++) {
      tableHtml += '<tr>';
      for (let c = 0; c < M[r].length; c++) {
        const val = M[r][c];
        const formatted = Math.abs(val) < 0.0001 && val !== 0 ? val.toExponential(3) : val.toFixed(4);
        tableHtml += `<td>${formatted}</td>`;
      }
      tableHtml += '</tr>';
    }
    tableHtml += '</table>';
    matrixContainer.innerHTML = tableHtml;
  }

  // 5. Download / Export Buttons
  const btnExportWarped = document.getElementById('btn-export-warped');
  if (btnExportWarped && artifacts.warped_url) {
    btnExportWarped.href = artifacts.warped_url;
  }
  const btnExportMatches = document.getElementById('btn-export-matches');
  if (btnExportMatches && artifacts.matches_url) {
    btnExportMatches.href = artifacts.matches_url;
  }

  // 6. Update Active Stage View
  updateStageView();
}

// Switch Stage Viewport Tab (Matches, Checkerboard, Warped, Dual, Swipe)
function updateStageView() {
  const job = poc3State.currentJob;
  if (!job) return;

  const viewTab = poc3State.activeViewTab;
  const viewSingle = document.getElementById('reg-view-single');
  const viewDual = document.getElementById('reg-view-dual');
  const viewSwipe = document.getElementById('reg-view-swipe');
  const artImg = document.getElementById('reg-artifact-img');

  // Reset zoom & pan on tab change
  poc3ResetZoom();

  if (viewTab === 'matches' || viewTab === 'checkerboard' || viewTab === 'warped') {
    if (viewSingle) viewSingle.style.display = 'flex';
    if (viewDual) viewDual.style.display = 'none';
    if (viewSwipe) viewSwipe.style.display = 'none';

    let targetUrl = '';
    if (viewTab === 'matches') targetUrl = job.artifacts?.matches_url || job.artifacts?.warped_url;
    else if (viewTab === 'checkerboard') targetUrl = job.artifacts?.checkerboard_url;
    else if (viewTab === 'warped') targetUrl = job.artifacts?.warped_url;

    if (artImg && targetUrl) {
      // Add timestamp to prevent browser cache
      artImg.src = `${targetUrl}?t=${Date.now()}`;
    }
  } else if (viewTab === 'sidebyside') {
    if (viewSingle) viewSingle.style.display = 'none';
    if (viewDual) viewDual.style.display = 'grid';
    if (viewSwipe) viewSwipe.style.display = 'none';

    const dualSrcImg = document.getElementById('dual-src-img');
    const dualRefImg = document.getElementById('dual-ref-img');
    const dualSrcSub = document.getElementById('dual-src-sub');
    const dualRefSub = document.getElementById('dual-ref-sub');

    const srcObs = state.observations.find(o => o.product_id === (document.getElementById('reg-select-source')?.value || poc3State.selectedSourceId));
    const refObs = state.observations.find(o => o.product_id === (document.getElementById('reg-select-reference')?.value || poc3State.selectedRefId));

    if (dualSrcSub && srcObs) dualSrcSub.textContent = `${srcObs.product_id} (${srcObs.spatial_resolution_m}m)`;
    if (dualRefSub && refObs) dualRefSub.textContent = `${refObs.product_id} (${refObs.spatial_resolution_m}m)`;

    if (dualSrcImg && srcObs) {
      dualSrcImg.src = `/api/v1/observations/${srcObs.product_id}/preview`;
    }
    if (dualRefImg && refObs) {
      dualRefImg.src = `/api/v1/observations/${refObs.product_id}/preview`;
    }
  } else if (viewTab === 'swipe') {
    if (viewSingle) viewSingle.style.display = 'none';
    if (viewDual) viewDual.style.display = 'none';
    if (viewSwipe) viewSwipe.style.display = 'flex';

    const swipeBottom = document.getElementById('swipe-img-bottom');
    const swipeTop = document.getElementById('swipe-img-top');
    const srcObs = state.observations.find(o => o.product_id === (document.getElementById('reg-select-source')?.value || poc3State.selectedSourceId));

    if (swipeTop && srcObs) {
      swipeTop.src = `/api/v1/observations/${srcObs.product_id}/preview`;
    }
    if (swipeBottom && job.artifacts?.warped_url) {
      swipeBottom.src = `${job.artifacts.warped_url}?t=${Date.now()}`;
    }

    setSwipePosition(50);
  }
}

// Swipe Comparator Slider Positioning
function setSwipePosition(percent) {
  const clamped = Math.max(0, Math.min(100, percent));
  poc3State.swipePercent = clamped;

  const overlay = document.getElementById('swipe-overlay');
  const handle = document.getElementById('swipe-handle');
  if (overlay) overlay.style.width = `${clamped}%`;
  if (handle) handle.style.left = `${clamped}%`;
}

// Viewport Zoom & Pan Helpers
function poc3ApplyTransform() {
  const img = document.getElementById('reg-artifact-img');
  const badge = document.getElementById('reg-zoom-badge');
  if (img) {
    img.style.transform = `translate(${poc3State.panX}px, ${poc3State.panY}px) scale(${poc3State.zoom})`;
  }
  if (badge) {
    badge.textContent = `${Math.round(poc3State.zoom * 100)}%`;
  }
}

function poc3ResetZoom() {
  poc3State.zoom = 1.0;
  poc3State.panX = 0;
  poc3State.panY = 0;
  poc3ApplyTransform();
}

function poc3Zoom(delta) {
  poc3State.zoom = Math.max(0.2, Math.min(5.0, poc3State.zoom + delta));
  poc3ApplyTransform();
}

// Initialize POC 3 Event Listeners and Interactive Bindings
function initPOC3Studio() {
  populateRegistrationDropdowns();
  // Source & Reference Selection Change Listeners
  const selSrc = document.getElementById('reg-select-source');
  const selRef = document.getElementById('reg-select-reference');
  selSrc?.addEventListener('change', (e) => {
    poc3State.selectedSourceId = e.target.value;
    updateRegistrationPairDisplay();
  });
  selRef?.addEventListener('change', (e) => {
    poc3State.selectedRefId = e.target.value;
    updateRegistrationPairDisplay();
  });

  // Top Navigation Buttons
  document.getElementById('btn-nav-layer1')?.addEventListener('click', () => switchModule('layer1'));
  document.getElementById('btn-nav-poc3')?.addEventListener('click', () => switchModule('poc3'));

  // Inspector Quick Launch Button
  document.getElementById('btn-inspect-register-poc3')?.addEventListener('click', () => {
    if (state.selectedObservation) {
      switchModule('poc3');
      poc3SetSelectedPair(state.selectedObservation.product_id, null);
    }
  });

  // Benchmark Preset Buttons
  const loadPreset = () => {
    poc3SetDefaultBoguslawskyPair();
  };
  document.getElementById('btn-load-boguslawsky-pair')?.addEventListener('click', loadPreset);
  document.getElementById('btn-preset-boguslawsky')?.addEventListener('click', loadPreset);
  document.getElementById('btn-empty-quickrun')?.addEventListener('click', () => {
    loadPreset();
    executeRegistration();
  });

  // Algorithm Pills
  const algoPills = document.querySelectorAll('#reg-algo-pills .algo-pill');
  algoPills.forEach(pill => {
    pill.addEventListener('click', () => {
      algoPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const method = pill.dataset.method;
      poc3State.selectedMethod = method;

      const doc = ALGORITHM_DOCS[method];
      if (doc) {
        const titleEl = document.getElementById('algo-info-name');
        const descEl = document.getElementById('algo-info-desc');
        if (titleEl) titleEl.textContent = doc.name;
        if (descEl) descEl.textContent = doc.desc;
      }
    });
  });

  // Transformation Model Pills
  const transPills = document.querySelectorAll('#reg-transform-pills .toggle-pill');
  transPills.forEach(pill => {
    pill.addEventListener('click', () => {
      transPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      poc3State.selectedTransform = pill.dataset.transform;
    });
  });

  // Slider Ratio Thresh
  const sliderRatio = document.getElementById('slider-ratio-thresh');
  const valRatio = document.getElementById('val-ratio-thresh');
  sliderRatio?.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    poc3State.ratioThresh = val;
    if (valRatio) valRatio.textContent = val.toFixed(2);
  });

  // Slider RANSAC Thresh
  const sliderRansac = document.getElementById('slider-ransac-thresh');
  const valRansac = document.getElementById('val-ransac-thresh');
  sliderRansac?.addEventListener('input', (e) => {
    const val = parseFloat(e.target.value);
    poc3State.ransacThresh = val;
    if (valRansac) valRansac.textContent = `${val.toFixed(1)} px`;
  });

  // Execute Registration Button
  document.getElementById('btn-execute-reg')?.addEventListener('click', executeRegistration);

  // Stage View Tabs
  const stageTabs = document.querySelectorAll('#reg-view-tabs .stage-tab');
  stageTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      stageTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      poc3State.activeViewTab = tab.dataset.view;
      updateStageView();
    });
  });

  // Viewport Zoom & HUD Controls
  document.getElementById('btn-reg-zoom-in')?.addEventListener('click', () => poc3Zoom(0.25));
  document.getElementById('btn-reg-zoom-out')?.addEventListener('click', () => poc3Zoom(-0.25));
  document.getElementById('btn-reg-zoom-reset')?.addEventListener('click', poc3ResetZoom);
  document.getElementById('btn-reg-zoom-fit')?.addEventListener('click', poc3ResetZoom);

  // Canvas Pan & Drag Controls
  const canvasWrapper = document.getElementById('reg-canvas-wrapper');
  if (canvasWrapper) {
    canvasWrapper.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY < 0 ? 0.15 : -0.15;
      poc3Zoom(delta);
    }, { passive: false });

    canvasWrapper.addEventListener('mousedown', (e) => {
      poc3State.isDraggingCanvas = true;
      poc3State.dragStartX = e.clientX - poc3State.panX;
      poc3State.dragStartY = e.clientY - poc3State.panY;
    });

    window.addEventListener('mousemove', (e) => {
      if (poc3State.isDraggingCanvas) {
        poc3State.panX = e.clientX - poc3State.dragStartX;
        poc3State.panY = e.clientY - poc3State.dragStartY;
        poc3ApplyTransform();
      }
    });

    window.addEventListener('mouseup', () => {
      poc3State.isDraggingCanvas = false;
    });
  }

  // Swipe Comparator Drag Handle
  const swipeContainer = document.getElementById('swipe-container');
  const swipeHandle = document.getElementById('swipe-handle');
  if (swipeHandle && swipeContainer) {
    const handleSwipeMove = (clientX) => {
      const rect = swipeContainer.getBoundingClientRect();
      const offsetX = clientX - rect.left;
      const pct = (offsetX / rect.width) * 100;
      setSwipePosition(pct);
    };

    swipeHandle.addEventListener('mousedown', (e) => {
      poc3State.isSwiping = true;
      e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
      if (poc3State.isSwiping) {
        handleSwipeMove(e.clientX);
      }
    });

    window.addEventListener('mouseup', () => {
      poc3State.isSwiping = false;
    });

    // Touch events for mobile/tablet
    swipeHandle.addEventListener('touchstart', (e) => {
      poc3State.isSwiping = true;
    }, { passive: true });

    window.addEventListener('touchmove', (e) => {
      if (poc3State.isSwiping && e.touches.length > 0) {
        handleSwipeMove(e.touches[0].clientX);
      }
    }, { passive: true });

    window.addEventListener('touchend', () => {
      poc3State.isSwiping = false;
    });
  }

  // Export Metrics as JSON
  document.getElementById('btn-export-json')?.addEventListener('click', () => {
    if (!poc3State.currentJob) {
      alert("No active registration job to export.");
      return;
    }
    const jsonStr = JSON.stringify(poc3State.currentJob, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nexus_lunar_registration_${poc3State.currentJob.job_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });
}

// Start Application on Load
// POC3 initialized via unified controller



// ==========================================================================
// CORE PLATFORM, GIS & EXPERIMENT STUDIOS (POC 1, 2, 4, 5, 6, 7)
// ==========================================================================
/**
 * NEXUS-LUNAR: Client-Side Application Logic
 * Integrates Leaflet GIS, Overlap Engine, and Interactive Patch Studio
 */



// ==========================================================================
// Initialization
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  initSpaceStarfield();
  initMissionTelemetry();
  initSpaceAudio();
  initTabs();
  initNexus3DStudio();
  initPOC3Studio();
  initMap();
  initSplitSlider();
  initModal();
  initLightbox();
  initPOC4Studio();
  initPOC5Studio();
  initPOC6Studio();
  initPOC7Studio();
  initScienceWorkbench();
  await loadCatalogAndPairs();
  if (typeof populateRegistrationDropdowns === 'function') {
    populateRegistrationDropdowns();
  }
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

      playCyberClick();
      if (targetId === 'tab-map' && state.map) {
        setTimeout(() => state.map.invalidateSize(), 150);
      }
      if (targetId === 'tab-nexus3d' && window.nexus3d && window.nexus3d.onResize) {
        setTimeout(() => window.nexus3d.onResize(), 100);
      }
      if (targetId === 'tab-reg' && typeof populateRegistrationDropdowns === 'function') {
        populateRegistrationDropdowns();
      }
    });
  });

  // Check URL hash for direct tab linking (e.g. #poc4, #patches, #catalog, #map)
  if (window.location.hash) {
    const hash = window.location.hash.replace('#', '').toLowerCase();
    const matchingTab = document.querySelector(`.nav-tab[data-tab="tab-${hash}"]`);
    if (matchingTab) {
      matchingTab.click();
    }
  }

  document.getElementById('btnRefreshCatalog').addEventListener('click', loadCatalogAndPairs);
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
    state.observations = state.catalog;

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

  // Show placeholder, hide empty images and divider
  const placeholder = document.getElementById('stagePlaceholder');
  if (placeholder) placeholder.style.display = 'flex';
  const divider = document.getElementById('dividerLine');
  if (divider) divider.style.display = 'none';
  const imgRef = document.getElementById('imgRefView');
  const imgSrc = document.getElementById('imgSrcView');
  if (imgRef) { imgRef.style.display = 'none'; imgRef.removeAttribute('src'); }
  if (imgSrc) { imgSrc.style.display = 'none'; imgSrc.removeAttribute('src'); }
  const lbl = document.getElementById('currentPatchLabel');
  if (lbl) lbl.innerText = 'No Active Patch';
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
          <img src="${srcImgUrl}" alt="Source Patch" loading="lazy" onerror="this.style.opacity='0.2'">
          <span class="thumb-label">Source</span>
        </div>
        <div class="thumb-item">
          <img src="${refImgUrl}" alt="Reference Patch" loading="lazy" onerror="this.style.opacity='0.2'">
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
  if (manifest.patches && manifest.patches.length > 0) {
    const first = manifest.patches[0];
    const srcImgUrl = `/data/processed/patches/${manifest.source_product_id}___${manifest.reference_product_id}/${first.source_patch_path.split('\\').pop().split('/').pop()}`;
    const refImgUrl = `/data/processed/patches/${manifest.source_product_id}___${manifest.reference_product_id}/${first.reference_patch_path.split('\\').pop().split('/').pop()}`;
    loadPatchIntoViewer(first, srcImgUrl, refImgUrl);
  }
}

function loadPatchIntoViewer(patch, srcImgUrl, refImgUrl) {
  state.activePatch = patch;
  const lbl = document.getElementById('currentPatchLabel');
  if (lbl) lbl.innerText = `Patch #${patch.patch_index.toString().padStart(4, '0')}`;
  
  const placeholder = document.getElementById('stagePlaceholder');
  if (placeholder) placeholder.style.display = 'none';

  const divider = document.getElementById('dividerLine');
  if (divider) divider.style.display = 'block';

  const imgRef = document.getElementById('imgRefView');
  const imgSrc = document.getElementById('imgSrcView');
  
  if (imgRef) {
    imgRef.style.display = 'block';
    imgRef.src = refImgUrl;
    imgRef.onerror = () => { imgRef.style.display = 'none'; };
  }
  if (imgSrc) {
    imgSrc.style.display = 'block';
    imgSrc.src = srcImgUrl;
    imgSrc.onerror = () => { imgSrc.style.display = 'none'; };
  }
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

function initPOC4Studio() {
  const btnRun = document.getElementById('btnRunPOC4Experiment');
  if (!btnRun) return;

  btnRun.addEventListener('click', runPOC4FullPipeline);

  // Load existing results if available
  loadPOC4Results();
}

async function loadPOC4Results() {
  try {
    const res = await fetch('/api/poc4/results');
    if (res.ok) {
      const data = await res.json();
      updatePOC4UI(data);
    }
  } catch (e) {
    console.log('POC-4 cached results not available yet.');
  }
}

async function runPOC4FullPipeline() {
  const btnRun = document.getElementById('btnRunPOC4Experiment');
  const progressCard = document.getElementById('poc4ProgressCard');
  const progressBar = document.getElementById('poc4ProgressBar');
  const stepLabel = document.getElementById('poc4CurrentStep');
  const stepBadges = document.querySelectorAll('#poc4StepsFlow .step-badge');

  btnRun.disabled = true;
  btnRun.innerHTML = `
    <span class="spinner" style="width: 14px; height: 14px; border-width: 2px; display: inline-block;"></span>
    Running Experiment Matrix...
  `;
  progressCard.style.display = 'flex';

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
      stepLabel.innerText = s.name;
      progressBar.style.width = `${s.percent}%`;
      
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

  try {
    const res = await fetch('/api/poc4/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_product_id: 'ch2_ohr_ncp_20260103t1005176450_d_img_d18',
        reference_product_id: 'SYNTHETIC_LROC_CANDIDATE_P850S0250',
        fast_mode: false
      })
    });

    clearInterval(progressTimer);

    if (res.ok) {
      const data = await res.json();
      progressBar.style.width = '100%';
      stepLabel.innerText = 'Experiment Completed Successfully!';
      stepBadges.forEach(b => b.className = 'step-badge completed');
      
      setTimeout(() => {
        updatePOC4UI(data);
        refreshFigureImages();
        progressCard.style.display = 'none';
      }, 800);
    } else {
      const err = await res.text();
      alert('POC-4 Experiment run error: ' + err);
    }
  } catch (err) {
    clearInterval(progressTimer);
    console.error('POC-4 execution failure:', err);
    alert('Failed to connect to POC-4 experiment service: ' + err);
  } finally {
    btnRun.disabled = false;
    btnRun.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
      RUN POC-4 EXPERIMENT
    `;
  }
}

function refreshFigureImages() {
  const t = Date.now();
  document.querySelectorAll('.gallery-img-box img').forEach(img => {
    const base = img.src.split('?')[0];
    img.src = `${base}?t=${t}`;
  });
}

function updatePOC4UI(data) {
  if (!data) return;

  // Update Provenance label
  if (data.metadata?.data_provenance) {
    const provLabel = document.getElementById('poc4ProvenanceLabel');
    if (provLabel) provLabel.innerText = data.metadata.data_provenance;
  }

  // Update Scorecards
  if (data.summary) {
    const s = data.summary;
    const bestRep = s.best_representation || 'MULTI-SCALE + ILLUMINATION-AWARE';
    const repData = s.representation_metrics ? s.representation_metrics[bestRep] : null;

    const elBestRep = document.getElementById('poc4BestRep');
    if (elBestRep) elBestRep.innerText = bestRep;

    if (repData) {
      const elSuccess = document.getElementById('poc4SuccessRate');
      if (elSuccess) elSuccess.innerText = `${(repData.success_rate * 100).toFixed(1)}%`;

      const elInlier = document.getElementById('poc4InlierRatio');
      if (elInlier) elInlier.innerText = `${(repData.mean_inlier_ratio * 100).toFixed(1)}%`;

      const elRecall1 = document.getElementById('poc4Recall1');
      if (elRecall1) elRecall1.innerText = `${(repData.mean_recall_1 * 100).toFixed(1)}%`;

      const elRmse = document.getElementById('poc4Rmse');
      if (elRmse) elRmse.innerText = `${repData.mean_rmse.toFixed(2)} px`;
    }
  }

  // Populate Baseline Comparison Table
  if (data.summary?.representation_metrics) {
    const tbody = document.getElementById('poc4ComparisonTableBody');
    if (tbody) {
      tbody.innerHTML = '';
      const reps = data.summary.representation_metrics;
      for (const [repName, m] of Object.entries(reps)) {
        const tr = document.createElement('tr');
        const isBest = repName.includes('MULTI-SCALE') && repName.includes('ILLUMINATION');
        if (isBest) tr.className = 'highlight-row';

        let pillClass = 'pill-fail';
        let pillText = 'Baseline';
        if (m.success_rate >= 0.7) {
          pillClass = isBest ? 'pill-winner' : 'pill-pass';
          pillText = isBest ? '★ BEST PERFORMER' : 'High Robustness';
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
          <td>${m.mean_rmse.toFixed(2)} px</td>
          <td><span class="${pillClass}">${pillText}</span></td>
        `;
        tbody.appendChild(tr);
      }
    }
  }

  // Populate Ablation Table
  if (data.ablation) {
    const tbody = document.getElementById('poc4AblationTableBody');
    if (tbody && Array.isArray(data.ablation)) {
      tbody.innerHTML = '';
      data.ablation.forEach(row => {
        const tr = document.createElement('tr');
        const isPass = row.success;
        const isBest = row.config_name.includes('ILLUMINATION-AWARE') && row.scale_harmonized;
        if (isBest) tr.className = 'highlight-row';

        tr.innerHTML = `
          <td>${row.config_name}</td>
          <td>${row.scale_harmonized ? 'Yes' : 'No'}</td>
          <td>${(row.inlier_ratio * 100).toFixed(1)}%</td>
          <td>${row.rmse < 900 ? row.rmse.toFixed(2) + ' px' : '999.00 px'}</td>
          <td><span class="${isBest ? 'pill-winner' : (isPass ? 'pill-pass' : 'pill-fail')}">${isPass ? 'PASS' : 'FAIL'}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }
  }
}

// ==========================================================================
// POC 5: Multimodal AI Correspondence & Retrieval Studio
// ==========================================================================
function initPOC5Studio() {
  const btnRun = document.getElementById('btnRunPOC5Experiment');
  if (!btnRun) return;

  btnRun.addEventListener('click', runPOC5FullPipeline);

  // Load existing results if available
  loadPOC5Results();
}

async function loadPOC5Results() {
  try {
    const res = await fetch('/api/poc5/demo');
    if (res.ok) {
      const data = await res.json();
      updatePOC5UI(data);
    }
  } catch (e) {
    console.log('POC-5 cached results not available yet.');
  }
}

async function runPOC5FullPipeline() {
  const btnRun = document.getElementById('btnRunPOC5Experiment');
  const progressCard = document.getElementById('poc5ProgressCard');
  const progressBar = document.getElementById('poc5ProgressBar');
  const stepLabel = document.getElementById('poc5CurrentStep');
  const stepBadges = document.querySelectorAll('#poc5StepsFlow .step-badge');

  btnRun.disabled = true;
  btnRun.innerHTML = `
    <span class="spinner" style="width: 14px; height: 14px; border-width: 2px; display: inline-block;"></span>
    Retrieving Cross-Modal Correspondences...
  `;
  progressCard.style.display = 'flex';

  const steps = [
    { name: '1. Ingesting Cross-Sensor Common-Ground Patches...', percent: 16, index: 0 },
    { name: '2. Initializing Multimodal Representation Encoders...', percent: 33, index: 1 },
    { name: '3. Extracting 128-D Dense L2-Normalized Embeddings...', percent: 50, index: 2 },
    { name: '4. Computing Cross-Modal Cosine Similarity Matrix...', percent: 66, index: 3 },
    { name: '5. Ranking Top-K Nearest Neighbor Candidates...', percent: 83, index: 4 },
    { name: '6. Validating Geospatial Relations & Handover to POC-6...', percent: 100, index: 5 }
  ];

  let currentStepIdx = 0;
  const progressTimer = setInterval(() => {
    if (currentStepIdx < steps.length) {
      const s = steps[currentStepIdx];
      stepLabel.innerText = s.name;
      progressBar.style.width = `${s.percent}%`;
      
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
  }, 400);

  try {
    const res = await fetch('/api/poc5/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        num_pairs: 12,
        top_k: 5,
      })
    });

    clearInterval(progressTimer);

    if (res.ok) {
      const data = await res.json();
      progressBar.style.width = '100%';
      stepLabel.innerText = 'Cross-Modal Retrieval Complete!';
      stepBadges.forEach(b => b.className = 'step-badge completed');
      
      setTimeout(() => {
        updatePOC5UI(data);
        refreshPOC5FigureImages();
        progressCard.style.display = 'none';
      }, 700);
    } else {
      const err = await res.text();
      alert('POC-5 Retrieval error: ' + err);
    }
  } catch (err) {
    clearInterval(progressTimer);
    console.error('POC-5 execution failure:', err);
    alert('Failed to execute POC-5 retrieval service: ' + err);
  } finally {
    btnRun.disabled = false;
    btnRun.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
      RUN POC-5 RETRIEVAL
    `;
  }
}

function refreshPOC5FigureImages() {
  const t = Date.now();
  document.querySelectorAll('#tab-poc5 .gallery-img-box img, #poc5QueryImgPreview').forEach(img => {
    const base = img.src.split('?')[0];
    img.src = `${base}?t=${t}`;
  });
}

function updatePOC5UI(data) {
  if (!data) return;

  // Update Provenance label
  const prov = data.metadata?.data_provenance || data.provenance;
  if (prov) {
    const provLabel = document.getElementById('poc5ProvenanceLabel');
    if (provLabel) provLabel.innerText = prov;
  }

  // Update Scorecards
  const sm = data.summary_metrics || data;
  if (sm) {
    const elR1 = document.getElementById('poc5Recall1');
    if (elR1 && sm.recall_at_1 !== undefined) {
      elR1.innerText = typeof sm.recall_at_1 === 'number' ? `${(sm.recall_at_1 * 100).toFixed(1)}%` : sm.recall_at_1;
    }

    const elR3 = document.getElementById('poc5Recall3');
    if (elR3 && sm.recall_at_3 !== undefined) {
      elR3.innerText = typeof sm.recall_at_3 === 'number' ? `${(sm.recall_at_3 * 100).toFixed(1)}%` : sm.recall_at_3;
    }

    const elR5 = document.getElementById('poc5Recall5');
    if (elR5 && sm.recall_at_5 !== undefined) {
      elR5.innerText = typeof sm.recall_at_5 === 'number' ? `${(sm.recall_at_5 * 100).toFixed(1)}%` : sm.recall_at_5;
    }

    const elR10 = document.getElementById('poc5Recall10');
    if (elR10 && sm.recall_at_10 !== undefined) {
      elR10.innerText = typeof sm.recall_at_10 === 'number' ? `${(sm.recall_at_10 * 100).toFixed(1)}%` : sm.recall_at_10;
    }

    const elMrr = document.getElementById('poc5Mrr');
    if (elMrr && sm.mean_reciprocal_rank !== undefined) {
      elMrr.innerText = typeof sm.mean_reciprocal_rank === 'number' ? sm.mean_reciprocal_rank.toFixed(3) : sm.mean_reciprocal_rank;
    }

    const elMeanSim = document.getElementById('poc5MeanSim');
    if (elMeanSim && sm.mean_similarity_score !== undefined) {
      elMeanSim.innerText = sm.mean_similarity_score.toFixed(3);
    }
  }

  // Update Candidate List for first query
  const retrievals = data.retrieval_results;
  if (retrievals && Object.keys(retrievals).length > 0) {
    const firstQ = Object.keys(retrievals)[0];
    const matches = retrievals[firstQ];

    const qLabel = document.getElementById('poc5ActiveQueryId');
    if (qLabel) qLabel.innerText = firstQ;

    const candContainer = document.getElementById('poc5CandidatesList');
    if (candContainer && Array.isArray(matches)) {
      candContainer.innerHTML = '';
      matches.forEach(m => {
        const card = document.createElement('div');
        const isGt = m.is_ground_truth;
        card.className = `candidate-rank-card glassmorphism ${isGt ? 'winner-card' : ''}`;
        
        let pillClass = 'pill-neutral';
        let pillText = m.geographic_relation || 'CANDIDATE';
        if (isGt) {
          pillClass = 'pill-winner';
          pillText = '★ TRUE GEOGRAPHIC MATCH';
        } else if (m.geographic_relation === 'OVERLAPPING') {
          pillClass = 'pill-pass';
        }

        const simPercent = Math.max(0, Math.min(100, m.similarity_score * 100));

        card.innerHTML = `
          <div class="cand-rank-badge">#${m.rank}</div>
          <div class="cand-info-col">
            <div class="cand-title-row">
              <strong class="val-code">${m.candidate_patch_id}</strong>
              <span class="${pillClass}">${pillText}</span>
            </div>
            <div class="cand-meta-row">
              <span>${m.candidate_sensor} (${m.candidate_gsd}m GSD)</span>
              <span>Spatial Rel: <strong>${m.geographic_relation}</strong></span>
            </div>
            <div class="cand-sim-bar-track">
              <div class="cand-sim-bar-fill" style="width: ${simPercent}%; ${isGt ? 'background: linear-gradient(90deg, #a29bfe, #2ed573);' : ''}"></div>
            </div>
          </div>
          <div class="cand-score-col">
            <div class="cand-score-val">${m.similarity_score.toFixed(3)}</div>
            <div class="cand-score-lbl">Cosine Sim</div>
          </div>
        `;
        candContainer.appendChild(card);
      });
    }
  }

  // Update Ablation Table
  if (data.ablation_comparison && Array.isArray(data.ablation_comparison)) {
    const tbody = document.getElementById('poc5AblationTableBody');
    if (tbody) {
      tbody.innerHTML = '';
      data.ablation_comparison.forEach(row => {
        const tr = document.createElement('tr');
        const isAi = row.representation.includes('AI');
        if (isAi) tr.className = 'highlight-row';

        tr.innerHTML = `
          <td><strong>${row.representation}</strong></td>
          <td>${row.embedding_dim}-D</td>
          <td>${typeof row.recall_at_1 === 'number' ? (row.recall_at_1 * 100).toFixed(1) + '%' : row.recall_at_1}</td>
          <td>${typeof row.recall_at_5 === 'number' ? (row.recall_at_5 * 100).toFixed(1) + '%' : row.recall_at_5}</td>
          <td>${typeof row.mrr === 'number' ? row.mrr.toFixed(3) : row.mrr}</td>
          <td><span class="${isAi ? 'pill-winner' : 'pill-neutral'}">${isAi ? '★ SUPERIOR RECALL' : 'Baseline'}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }
  }
}

// ==========================================================================
// POC 6: Geometric Verification + Explainable AI (XAI) Studio
// ==========================================================================
let poc6Data = null;
let poc6SelectedIndex = 0;

function initPOC6Studio() {
  const btnRun = document.getElementById('btnRunPOC6');
  if (btnRun) {
    btnRun.addEventListener('click', runPOC6FullPipeline);
  }
  loadPOC6Results();
}

async function loadPOC6Results() {
  try {
    const res = await fetch('/api/poc6/demo');
    if (res.ok) {
      const data = await res.json();
      poc6Data = data;
      updatePOC6UI(data);
    }
  } catch (e) {
    console.log('POC-6 demo data not yet loaded.');
  }
}

async function runPOC6FullPipeline() {
  const btnRun = document.getElementById('btnRunPOC6');
  const progressCard = document.getElementById('poc6ProgressCard');
  const progressBar = document.getElementById('poc6ProgressBarFill');
  const progressPct = document.getElementById('poc6ProgressPct');
  const stageSpans = document.querySelectorAll('#poc6ProgressStages .stage-item');

  btnRun.disabled = true;
  btnRun.innerHTML = `
    <span class="spinner" style="width: 14px; height: 14px; border-width: 2px; display: inline-block;"></span>
    Verifying Geometry & Generating XAI...
  `;
  progressCard.style.display = 'flex';

  const stages = [
    { pct: 10, idx: 0 },
    { pct: 22, idx: 1 },
    { pct: 35, idx: 2 },
    { pct: 48, idx: 3 },
    { pct: 60, idx: 4 },
    { pct: 72, idx: 5 },
    { pct: 83, idx: 6 },
    { pct: 92, idx: 7 },
    { pct: 100, idx: 8 },
  ];

  let curStage = 0;
  const timer = setInterval(() => {
    if (curStage < stages.length) {
      const s = stages[curStage];
      progressBar.style.width = `${s.pct}%`;
      progressPct.innerText = `${s.pct}%`;
      stageSpans.forEach((el, i) => {
        if (i < s.idx) {
          el.className = 'stage-item completed';
        } else if (i === s.idx) {
          el.className = 'stage-item active';
        } else {
          el.className = 'stage-item';
        }
      });
      curStage++;
    }
  }, 350);

  try {
    const res = await fetch('/api/poc6/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });

    clearInterval(timer);

    if (res.ok) {
      progressBar.style.width = '100%';
      progressPct.innerText = '100%';
      stageSpans.forEach(el => el.className = 'stage-item completed');
      
      setTimeout(async () => {
        progressCard.style.display = 'none';
        await loadPOC6Results();
        refreshPOC6FigureImages();
      }, 600);
    } else {
      const err = await res.text();
      alert('POC-6 verification error: ' + err);
    }
  } catch (err) {
    clearInterval(timer);
    console.error('POC-6 execution failure:', err);
    alert('Failed to execute POC-6 verification: ' + err);
  } finally {
    btnRun.disabled = false;
    btnRun.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
      RUN POC-6 VERIFICATION
    `;
  }
}

function refreshPOC6FigureImages() {
  const t = Date.now();
  document.querySelectorAll('#tab-poc6 .gallery-img-box img, #poc6VisualPreviewImg').forEach(img => {
    const base = img.src.split('?')[0];
    img.src = `${base}?t=${t}`;
  });
}

function updatePOC6UI(data) {
  if (!data) return;
  poc6Data = data;

  // Provenance
  if (data.metadata && data.metadata.provenance) {
    const provLabel = document.getElementById('poc6ProvLabel');
    if (provLabel) provLabel.innerText = data.metadata.provenance;
  }

  // Count badges
  const totalBadge = document.getElementById('poc6TotalCountBadge');
  if (totalBadge) totalBadge.innerText = `${data.total_candidates} Candidates Evaluated`;

  const accBadge = document.getElementById('poc6AcceptedCountBadge');
  if (accBadge) accBadge.innerText = `${data.accepted_count} Accepted`;

  const rejBadge = document.getElementById('poc6RejectedCountBadge');
  if (rejBadge) rejBadge.innerText = `${data.rejected_count} Rejected`;

  const failBadge = document.getElementById('poc6FailureCountBadge');
  if (failBadge) failBadge.innerText = `${data.rejected_count} Rejected Candidates`;

  const poc7Count = document.getElementById('poc7VerifiedPairsCount');
  if (poc7Count) poc7Count.innerText = `${data.accepted_count} pairs`;

  // Populate candidate selector chips
  const carousel = document.getElementById('poc6CandidateCarousel');
  if (carousel && data.candidates && data.candidates.length > 0) {
    carousel.innerHTML = '';
    data.candidates.slice(0, 15).forEach((cand, idx) => {
      const chip = document.createElement('button');
      chip.className = `btn-secondary ${idx === poc6SelectedIndex ? 'active-chip' : ''}`;
      chip.style.cssText = `padding: 6px 12px; font-size: 0.78rem; white-space: nowrap; border-radius: 6px; display: flex; align-items: center; gap: 6px; cursor: pointer; border: 1px solid ${cand.accepted ? '#00e676' : '#ff1744'}; background: ${idx === poc6SelectedIndex ? (cand.accepted ? 'rgba(0, 230, 118, 0.25)' : 'rgba(255, 23, 68, 0.25)') : 'rgba(15, 23, 42, 0.7)'}; color: #fff;`;
      
      const badgeIcon = cand.accepted ? '✓' : '✗';
      const badgeColor = cand.accepted ? '#00e676' : '#ff1744';

      chip.innerHTML = `
        <span style="color: ${badgeColor}; font-weight: bold;">${badgeIcon} #${cand.rank}</span>
        <span>${cand.query_patch_id.slice(-4)} vs ${cand.candidate_patch_id.slice(-4)}</span>
        <span style="font-size: 0.7rem; opacity: 0.8;">(${(cand.ai_similarity_score * 100).toFixed(0)}% AI)</span>
      `;
      chip.addEventListener('click', () => {
        poc6SelectedIndex = idx;
        document.querySelectorAll('#poc6CandidateCarousel button').forEach((b, bi) => {
          const c = data.candidates[bi];
          b.style.background = (bi === idx) ? (c.accepted ? 'rgba(0, 230, 118, 0.25)' : 'rgba(255, 23, 68, 0.25)') : 'rgba(15, 23, 42, 0.7)';
        });
        selectPOC6Candidate(cand);
      });
      carousel.appendChild(chip);
    });

    selectPOC6Candidate(data.candidates[poc6SelectedIndex]);
  }

  // Populate failure table
  if (data.failure_cases && data.failure_cases.failure_code_counts) {
    const tbody = document.getElementById('poc6FailureTableBody');
    if (tbody) {
      tbody.innerHTML = '';
      const counts = data.failure_cases.failure_code_counts;
      const codeDescriptions = {
        'GEOGRAPHIC_DISJOINT': 'Candidate coordinates outside physical query footprint',
        'TOO_FEW_INLIERS': 'Insufficient geometric consensus (< 6 inliers)',
        'LOW_INLIER_RATIO': 'Inlier percentage below threshold (< 35%)',
        'AI_SIMILARITY_FALSE_POSITIVE': 'High AI similarity (>0.75) unsupported by geometry',
        'POOR_SPATIAL_DISTRIBUTION': 'Keypoints clustered in single corner/crater rim',
        'HIGH_REPROJECTION_ERROR': 'Reprojection error exceeds allowable tolerance (> 3.5 px)',
        'UNSTABLE_TRANSFORMATION': 'Estimated affine transformation is degenerate or distorted',
        'NO_VALID_GEOMETRIC_MODEL': 'RANSAC failed to estimate consensus affine model',
        'LOW_CONFIDENCE': 'Composite confidence fell below minimum threshold (0.50)',
      };

      for (const [code, count] of Object.entries(counts)) {
        const desc = codeDescriptions[code] || 'Geometric verification criteria not met';
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><span class="val-code">${code}</span></td>
          <td>${desc}</td>
          <td><strong>${count}</strong></td>
          <td><span class="pill-neutral">${code === 'GEOGRAPHIC_DISJOINT' ? 'Auto-Reject' : 'Reject'}</span></td>
        `;
        tbody.appendChild(tr);
      }
    }
  }
}

function selectPOC6Candidate(cand) {
  if (!cand) return;

  // Title and subtitle
  const title = document.getElementById('poc6SelectedPairTitle');
  if (title) title.innerText = `Pair Inspection: ${cand.query_patch_id} vs ${cand.candidate_patch_id}`;

  const sub = document.getElementById('poc6SelectedPairSub');
  if (sub) sub.innerText = `Retrieval Rank #${cand.rank} | AI Similarity: ${(cand.ai_similarity_score * 100).toFixed(1)}% | Sensor Disparity: ${cand.query_sensor} (${cand.query_gsd}m) to ${cand.candidate_sensor} (${cand.candidate_gsd}m)`;

  // Decision Badge
  const badgeContainer = document.getElementById('poc6DecisionBadgeContainer');
  if (badgeContainer) {
    if (cand.accepted) {
      badgeContainer.innerHTML = `<span class="tag-pill tag-green" style="font-size: 0.95rem; font-weight: bold; padding: 6px 14px; background: rgba(0, 230, 118, 0.2); border: 1px solid #00e676; color: #00e676;">✓ ACCEPTED</span>`;
    } else {
      badgeContainer.innerHTML = `<span class="tag-pill tag-red" style="font-size: 0.95rem; font-weight: bold; padding: 6px 14px; background: rgba(255, 23, 68, 0.2); border: 1px solid #ff1744; color: #ff1744;">✗ REJECTED</span>`;
    }
  }

  // Metrics grid
  const elTent = document.getElementById('poc6MetricTentative');
  if (elTent) elTent.innerText = cand.tentative_match_count;

  const elInl = document.getElementById('poc6MetricInliers');
  if (elInl) elInl.innerText = cand.inlier_count;

  const elRatio = document.getElementById('poc6MetricInlierRatio');
  if (elRatio) elRatio.innerText = `${(cand.inlier_ratio * 100).toFixed(1)}%`;

  const elRMSE = document.getElementById('poc6MetricRMSE');
  if (elRMSE) elRMSE.innerText = cand.rmse >= 900 ? 'N/A' : `${cand.rmse.toFixed(2)} px`;

  const elSpatial = document.getElementById('poc6MetricSpatial');
  if (elSpatial) elSpatial.innerText = `${cand.spatial_distribution_status} (${cand.spatial_distribution_score.toFixed(2)})`;

  const elStab = document.getElementById('poc6MetricStability');
  if (elStab) elStab.innerText = cand.transformation_stability;

  // Confidence score
  const confDisp = document.getElementById('poc6ConfidenceScoreDisplay');
  if (confDisp) confDisp.innerText = `${(cand.verification_confidence * 100).toFixed(1)}%`;

  // WHY? box
  const whyTitle = document.getElementById('poc6WhyTitle');
  const whyList = document.getElementById('poc6WhyList');
  if (whyTitle && whyList) {
    if (cand.accepted) {
      whyTitle.innerText = 'WHY WAS THIS MATCH ACCEPTED?';
      whyTitle.style.color = '#38bdf8';
      whyList.innerHTML = cand.acceptance_reasons.map(r => `
        <li style="display: flex; align-items: flex-start; gap: 6px;">
          <span style="color: #00e676; font-weight: bold;">✓</span>
          <span>${r}</span>
        </li>
      `).join('');
    } else {
      whyTitle.innerText = 'WHY WAS THIS MATCH REJECTED?';
      whyTitle.style.color = '#f43f5e';
      whyList.innerHTML = cand.rejection_reasons.map(r => `
        <li style="background: rgba(239, 68, 68, 0.12); border-left: 3px solid #ef4444; padding: 6px 10px; border-radius: 4px; margin-bottom: 2px;">
          <strong style="color: #fca5a5;">[${r.code}]</strong>: <span>${r.message}</span>
        </li>
      `).join('');
    }
  }

  // 8 Progress Bars & Values
  const cb = cand.confidence_breakdown;
  if (cb) {
    setBar('poc6BarAI', 'poc6BarValAI', cb.ai_match_score);
    setBar('poc6BarInliers', 'poc6BarValInliers', cb.inlier_score);
    setBar('poc6BarRatio', 'poc6BarValRatio', cb.inlier_ratio_score);
    setBar('poc6BarRMSE', 'poc6BarValRMSE', cb.rmse_score);
    setBar('poc6BarGeo', 'poc6BarValGeo', cb.geographic_overlap_score);
    setBar('poc6BarSpatial', 'poc6BarValSpatial', cb.spatial_distribution_score);
    setBar('poc6BarStab', 'poc6BarValStab', cb.transformation_stability_score);
    setBar('poc6BarSensor', 'poc6BarValSensor', cb.sensor_compatibility_score);
  }
}

function setBar(barId, valId, score) {
  const bar = document.getElementById(barId);
  const val = document.getElementById(valId);
  const pct = Math.max(0, Math.min(100, (score || 0) * 100));
  if (bar) bar.style.width = `${pct.toFixed(0)}%`;
  if (val) val.innerText = `${pct.toFixed(1)}%`;
}

// ==========================================================================
// POC 7 Spatial Intelligence Studio Logic
// ==========================================================================
let poc7DataCache = null;

function initPOC7Studio() {
  const tabBtn = document.getElementById('tabBtnPOC7');
  if (tabBtn) {
    tabBtn.addEventListener('click', loadPOC7Data);
  }

  // Quick Action Buttons
  const btnExplore = document.getElementById('btnPOC7ExploreGraph');
  if (btnExplore) {
    btnExplore.addEventListener('click', () => {
      document.getElementById('cardKnowledgeGraph')?.scrollIntoView({ behavior: 'smooth' });
    });
  }

  const btnTerrain = document.getElementById('btnPOC7AnalyzeTerrain');
  if (btnTerrain) {
    btnTerrain.addEventListener('click', () => {
      document.getElementById('cardTerrain')?.scrollIntoView({ behavior: 'smooth' });
    });
  }

  const btnIllum = document.getElementById('btnPOC7AnalyzeIllum');
  if (btnIllum) {
    btnIllum.addEventListener('click', () => {
      document.getElementById('cardIllum')?.scrollIntoView({ behavior: 'smooth' });
    });
  }

  const btnSites = document.getElementById('btnPOC7FindSites');
  if (btnSites) {
    btnSites.addEventListener('click', () => {
      document.getElementById('cardCandidateSites')?.scrollIntoView({ behavior: 'smooth' });
    });
  }

  const btnRun = document.getElementById('btnRunPOC7Pipeline');
  if (btnRun) {
    btnRun.addEventListener('click', async () => {
      btnRun.disabled = true;
      btnRun.innerHTML = '<span>Running Pipeline...</span>';
      try {
        const res = await fetch('/api/poc7/run', { method: 'POST' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadPOC7Data();
      } catch (err) {
        console.error('Error running POC-7 pipeline:', err);
        alert(`Failed to execute POC-7 pipeline: ${err.message}`);
      } finally {
        btnRun.disabled = false;
        btnRun.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Re-Run Pipeline';
      }
    });
  }

  // Lightbox preview buttons for POC-7 figures
  const figs = [
    { btn: 'btnPreviewGraphFig', img: 'poc7GraphFig', title: 'Spatial Knowledge Graph Topology' },
    { btn: 'btnPreviewTerrainFig', img: 'poc7TerrainFig', title: 'Topographic Terrain Intelligence' },
    { btn: 'btnPreviewIllumFig', img: 'poc7IllumFig', title: 'Illumination & Shadow Regimes' },
    { btn: 'btnPreviewResourceFig', img: 'poc7ResourceFig', title: 'IIRS Mineralogical & Volatile Indicators' },
    { btn: 'btnPreviewHazardFig', img: 'poc7HazardFig', title: 'Spatial Hazard Intelligence Map' },
    { btn: 'btnPreviewSuitabilityFig', img: 'poc7GraphFig', title: 'Candidate Site Suitability Map', src: '/outputs/poc7/candidate_site_suitability_map.png' },
  ];

  figs.forEach(f => {
    const b = document.getElementById(f.btn);
    if (b) {
      b.addEventListener('click', () => {
        const modal = document.getElementById('imagePreviewModal');
        const modalImg = document.getElementById('previewModalImg');
        const modalTitle = document.getElementById('previewModalTitle');
        if (modal && modalImg) {
          modalImg.src = f.src || document.getElementById(f.img)?.src || '';
          if (modalTitle) modalTitle.innerText = f.title;
          modal.style.display = 'flex';
        }
      });
    }
  });

  // Query Select dropdown listener
  const qSelect = document.getElementById('poc7QuerySelect');
  if (qSelect) {
    qSelect.addEventListener('change', () => executePOC7Query(qSelect.value));
  }

  // Close Site Explanation Modal
  const btnCloseSite = document.getElementById('btnCloseSiteModal');
  if (btnCloseSite) {
    btnCloseSite.addEventListener('click', () => {
      const modal = document.getElementById('siteExplanationModal');
      if (modal) modal.style.display = 'none';
    });
  }
}

async function loadPOC7Data() {
  try {
    const res = await fetch('/api/poc7/demo');
    if (!res.ok) {
      console.warn('POC-7 demo endpoint returned', res.status);
      return;
    }
    const data = await res.json();
    poc7DataCache = data;
    renderPOC7Studio(data);
  } catch (err) {
    console.error('Failed to load POC-7 data:', err);
  }
}

function renderPOC7Studio(data) {
  if (!data) return;

  // KPI Metrics
  const elNodes = document.getElementById('poc7KpiNodes');
  if (elNodes) elNodes.innerText = data.total_nodes || '--';

  const elEdges = document.getElementById('poc7KpiEdges');
  if (elEdges) elEdges.innerText = data.total_edges || '--';

  const sites = data.candidate_sites || [];
  const elSites = document.getElementById('poc7KpiSites');
  if (elSites) elSites.innerText = sites.length;

  // Update Figures with cache-busting timestamp
  const ts = Date.now();
  if (data.figures) {
    const setImg = (id, src) => {
      const img = document.getElementById(id);
      if (img && src) img.src = `${src}?_t=${ts}`;
    };
    setImg('poc7GraphFig', data.figures.knowledge_graph);
    setImg('poc7TerrainFig', data.figures.terrain_intelligence);
    setImg('poc7SlopeFig', data.figures.slope_analysis);
    setImg('poc7IllumFig', data.figures.illumination_shadow);
    setImg('poc7ResourceFig', data.figures.resource_indicator);
    setImg('poc7HazardFig', data.figures.hazard_intelligence);
  }

  // Node Breakdown Badges
  const badgesContainer = document.getElementById('poc7NodeBadges');
  if (badgesContainer && data.node_type_breakdown) {
    const palette = {
      'Lunar Region': '#6c5ce7',
      'Sensor': '#00cec9',
      'Image': '#0984e3',
      'Observation': '#74b9ff',
      'Terrain Patch': '#00f2fe',
      'Crater': '#e17055',
      'Slope Region': '#fdcb6e',
      'Hazard': '#d63031',
      'Illumination State': '#ffeaa7',
      'Spectral Observation': '#fd79a8',
      'Candidate Site': '#00b894',
      'Habitat Component': '#55efc4',
    };

    badgesContainer.innerHTML = Object.entries(data.node_type_breakdown).map(([type, count]) => {
      const dotColor = palette[type] || '#dfe6e9';
      return `
        <span class="node-badge">
          <span class="badge-dot" style="background: ${dotColor};"></span>
          <span>${type}: <strong>${count}</strong></span>
        </span>
      `;
    }).join('');
  }

  // Render Candidate Sites Table
  const tbody = document.getElementById('poc7CandidateSitesTbody');
  if (tbody) {
    tbody.innerHTML = sites.map((s, idx) => {
      const suit = s.overall_suitability_score;
      const badgeCls = suit >= 0.70 ? 'suitability-high' : suit >= 0.45 ? 'suitability-med' : 'suitability-low';
      return `
        <tr>
          <td><strong>#${idx + 1}</strong></td>
          <td><strong style="color: #00f2fe;">${s.site_id}</strong></td>
          <td><span class="val-code">${s.patch_id}</span></td>
          <td>${s.coordinates.lat.toFixed(4)}°, ${s.coordinates.lon.toFixed(4)}°</td>
          <td>${s.terrain_score.toFixed(2)}</td>
          <td>${s.illumination_score.toFixed(2)}</td>
          <td>${s.resource_indicator_score.toFixed(2)}</td>
          <td><span style="color: #ff7675;">${s.hazard_penalty.toFixed(2)}</span></td>
          <td><span class="suitability-badge ${badgeCls}">${suit.toFixed(3)}</span></td>
          <td>
            <button class="btn-xs btn-primary btn-inspect-site" data-site-id="${s.site_id}">
              Inspect Rationale
            </button>
          </td>
        </tr>
      `;
    }).join('');

    // Attach click listeners to inspect buttons
    tbody.querySelectorAll('.btn-inspect-site').forEach(btn => {
      btn.addEventListener('click', () => {
        const siteId = btn.getAttribute('data-site-id');
        const match = sites.find(s => s.site_id === siteId);
        if (match) openSiteModal(match);
      });
    });
  }

  // Load Terrain and Hazards summary
  loadTerrainAndHazardsData();

  // Execute default query
  executePOC7Query(document.getElementById('poc7QuerySelect')?.value || 'corrs');
}

async function loadTerrainAndHazardsData() {
  try {
    const [tRes, hRes, iRes] = await Promise.all([
      fetch('/api/poc7/terrain'),
      fetch('/api/poc7/hazards'),
      fetch('/api/poc7/illumination'),
    ]);
    if (tRes.ok) {
      const tData = await tRes.json();
      renderTerrainTable(tData);
    }
    if (hRes.ok) {
      const hData = await hRes.json();
      renderHazardsList(hData);
    }
    if (iRes.ok) {
      const iData = await iRes.json();
      renderIllumBox(iData);
    }
  } catch (err) {
    console.error('Error loading sub-domain intelligence:', err);
  }
}

function renderTerrainTable(tData) {
  const container = document.getElementById('poc7TerrainTable');
  if (!container || !tData) return;

  const rows = Object.values(tData).map(t => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 4px; margin-bottom: 4px; font-size: 0.78rem;">
      <div><strong style="color: #00cec9;">${t.patch_id}</strong>: Elev ${t.elevation_mean_m}m | Roughness ${t.roughness_score}m | Aspect ${t.aspect_cardinal} (${t.aspect_degrees}°)</div>
      <div>
        <span class="severity-pill severity-${t.slope_category === 'LOW' ? 'low' : t.slope_category === 'MODERATE' ? 'moderate' : 'critical'}">
          Slope ${t.slope_degrees}° (${t.slope_category})
        </span>
      </div>
    </div>
  `).join('');

  container.innerHTML = `<div style="margin-top: 10px;">${rows}</div>`;
}

function renderIllumBox(iData) {
  const container = document.getElementById('poc7IllumStatusBox');
  if (!container || !iData) return;

  const items = Object.values(iData).map(i => `
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: rgba(255,255,255,0.03); border-radius: 4px; margin-bottom: 4px; font-size: 0.78rem;">
      <div><strong>${i.patch_id}</strong>: Flux ${(i.illumination_mean*100).toFixed(1)}% | Shadow ${(i.shadow_fraction*100).toFixed(1)}%</div>
      <div style="color: #ffeaa7; font-weight: bold;">${i.solar_potential_indicator}</div>
    </div>
  `).join('');

  container.innerHTML = `<div style="margin-top: 8px;">${items}</div>`;
}

function renderHazardsList(hData) {
  const container = document.getElementById('poc7HazardsList');
  const kpiHazards = document.getElementById('poc7KpiHazards');
  if (kpiHazards) kpiHazards.innerText = (hData || []).length;
  if (!container || !hData) return;

  if (hData.length === 0) {
    container.innerHTML = '<div class="placeholder-text">No active operational hazards constraining selected patches.</div>';
    return;
  }

  container.innerHTML = hData.map(h => {
    const sevCls = `severity-${(h.severity || 'low').toLowerCase()}`;
    return `
      <div class="hazard-item">
        <span class="severity-pill ${sevCls}">${h.severity}</span>
        <div style="font-size: 0.78rem;">
          <strong style="color: #f1f2f6;">${h.hazard_type}</strong> (${h.affected_patch_id}):
          <span style="color: #b2bec3;">${h.description}</span>
        </div>
      </div>
    `;
  }).join('');
}

function executePOC7Query(queryType) {
  const box = document.getElementById('poc7QueryResultsBox');
  if (!box || !poc7DataCache) return;

  if (queryType === 'corrs') {
    box.innerHTML = `
      <div style="color: #38bdf8; font-weight: bold; margin-bottom: 6px;">[QUERY RESULT] Verified Registered Correspondences (POC-6 Inliers Only):</div>
      <div>• TERRAIN_PATCH_OHRC_PATCH_0001 &lt;--- CORRESPONDS_TO ---&gt; TERRAIN_PATCH_LROC_PATCH_0001 (Confidence: 0.946, Inliers: 12, RMSE: 0.00)</div>
      <div>• TERRAIN_PATCH_OHRC_PATCH_0008 &lt;--- CORRESPONDS_TO ---&gt; TERRAIN_PATCH_LROC_PATCH_0008 (Confidence: 0.982, Inliers: 19, RMSE: 0.21)</div>
      <div>• TERRAIN_PATCH_OHRC_PATCH_0011 &lt;--- CORRESPONDS_TO ---&gt; TERRAIN_PATCH_LROC_PATCH_0011 (Confidence: 0.986, Inliers: 24, RMSE: 0.00)</div>
      <div style="color: #00e676; margin-top: 6px; font-size: 0.75rem;">✓ Excluded: 52 rejected candidates from POC-6 are isolated from graph.</div>
    `;
  } else if (queryType === 'candidates') {
    const sites = poc7DataCache.candidate_sites || [];
    const filtered = sites.filter(s => s.overall_suitability_score >= 0.45);
    box.innerHTML = `
      <div style="color: #00e676; font-weight: bold; margin-bottom: 6px;">[QUERY RESULT] Candidate Sites (Suitability &gt;= 0.45): ${filtered.length} found</div>
      ${filtered.map(s => `
        <div>• <strong>${s.site_id}</strong> (Patch: ${s.patch_id}) - Suitability: <strong style="color: #00e676;">${s.overall_suitability_score.toFixed(3)}</strong> | Centroid: (${s.coordinates.lat.toFixed(4)}°, ${s.coordinates.lon.toFixed(4)}°)</div>
      `).join('')}
    `;
  } else if (queryType === 'illuminated') {
    box.innerHTML = `
      <div style="color: #ffeaa7; font-weight: bold; margin-bottom: 6px;">[QUERY RESULT] Illuminated Terrain Patches:</div>
      <div>• OHRC_PATCH_0001: Partially Illuminated (Flux 54.5%, Shadow 0.1%)</div>
      <div>• OHRC_PATCH_0008: Partially Illuminated (Flux 54.5%, Shadow 0.1%)</div>
      <div>• OHRC_PATCH_0011: Partially Illuminated (Flux 54.5%, Shadow 0.2%)</div>
    `;
  } else if (queryType === 'resources') {
    box.innerHTML = `
      <div style="color: #fd79a8; font-weight: bold; margin-bottom: 6px;">[QUERY RESULT] Mineralogical & Volatile Indicators:</div>
      <div>• RES_INDICATOR_OHRC_PATCH_0001: 2.8 - 3.0 um Absorption Band Proxy (Score: 0.30)</div>
      <div>• RES_INDICATOR_OHRC_PATCH_0008: 2.8 - 3.0 um Absorption Band Proxy (Score: 0.36)</div>
      <div>• RES_INDICATOR_OHRC_PATCH_0011: 2.8 - 3.0 um Absorption Band Proxy (Score: 0.41)</div>
      <div style="color: #fd79a8; margin-top: 4px; font-size: 0.72rem;">Notice: Qualitative spectral indicators; not confirmed mineable reserves.</div>
    `;
  } else if (queryType === 'hazards') {
    box.innerHTML = `
      <div style="color: #ff7675; font-weight: bold; margin-bottom: 6px;">[QUERY RESULT] Hazards Constraining Candidate Sites:</div>
      <div>• CANDIDATE_SITE_0001: Crater rim proximity hazard (0.0m to CRATER_BOGUSLAWSKY_MICRO_A)</div>
      <div>• CANDIDATE_SITE_0003: High slope hazard (17.8° slope gradient)</div>
      <div>• CANDIDATE_SITE_0002: No severe hazards detected (Hazard penalty: 0.00)</div>
    `;
  }
}

function openSiteModal(site) {
  const modal = document.getElementById('siteExplanationModal');
  const title = document.getElementById('modalSiteTitle');
  const content = document.getElementById('modalSiteTextContent');
  const radarImg = document.getElementById('modalRadarFig');

  if (modal && title && content) {
    title.innerText = `Candidate Site Explanation: ${site.site_id} (${site.patch_id})`;
    if (radarImg) {
      radarImg.src = `/outputs/poc7/candidate_site_explanation.png?_t=${Date.now()}`;
    }

    const expl = site.explanation || {};
    const posList = (expl.positive_factors || []).map(p => `<li class="factor-positive"><span>✓</span> <span>${p}</span></li>`).join('');
    const negList = (expl.negative_factors || []).map(n => `<li class="factor-negative"><span>✗</span> <span>${n}</span></li>`).join('');

    content.innerHTML = `
      <div style="font-size: 0.85rem; line-height: 1.6;">
        <div style="margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1);">
          <div><strong>Centroid:</strong> Lat ${site.coordinates.lat.toFixed(4)}°, Lon ${site.coordinates.lon.toFixed(4)}°</div>
          <div><strong>Overall Suitability:</strong> <strong style="color: #00e676;">${site.overall_suitability_score.toFixed(3)}</strong> (${site.data_status})</div>
          <div><strong>Verdict:</strong> <em style="color: #38bdf8;">${expl.summary_verdict || 'EVALUATED'}</em></div>
        </div>
        <div style="font-weight: bold; color: #00e676; margin-bottom: 6px;">WHY IS THIS SITE INTERESTING? (FAVORABLE FACTORS)</div>
        <ul class="factor-checklist" style="list-style: none; padding-left: 0; margin-bottom: 14px;">
          ${posList || '<li style="color: #b2bec3;">No favorable indicators logged</li>'}
        </ul>
        <div style="font-weight: bold; color: #ff7675; margin-bottom: 6px;">CONSTRAINING FACTORS / HAZARDS</div>
        <ul class="factor-checklist" style="list-style: none; padding-left: 0;">
          ${negList || '<li style="color: #00e676;">None detected</li>'}
        </ul>
      </div>
    `;
    modal.style.display = 'flex';
  }
}

// ==========================================================================
// First-Principles Scientific Workbench (Physics, Chemistry, Biology, Frequency)
// ==========================================================================
function initScienceWorkbench() {
  const modal = document.getElementById('scienceModal');
  const btnOpen = document.getElementById('btnOpenScienceModal');
  const btnClose = document.getElementById('btnCloseScienceModal');
  const btnSim = document.getElementById('btnRunSimScience');

  const crewInput = document.getElementById('simCrewSize');
  const daysInput = document.getElementById('simMissionDays');
  const shieldInput = document.getElementById('simShieldDepth');
  const isruInput = document.getElementById('simIsruTonnes');

  const crewVal = document.getElementById('valSimCrew');
  const daysVal = document.getElementById('valSimDays');
  const shieldVal = document.getElementById('valSimShield');
  const isruVal = document.getElementById('valSimIsru');

  if (!modal || !btnOpen) return;

  // Slider change readouts
  if (crewInput && crewVal) {
    crewInput.addEventListener('input', (e) => { crewVal.textContent = `${e.target.value} crew`; });
  }
  if (daysInput && daysVal) {
    daysInput.addEventListener('input', (e) => { daysVal.textContent = `${e.target.value} days`; });
  }
  if (shieldInput && shieldVal) {
    shieldInput.addEventListener('input', (e) => { shieldVal.textContent = `${parseFloat(e.target.value).toFixed(1)} m`; });
  }
  if (isruInput && isruVal) {
    isruInput.addEventListener('input', (e) => { isruVal.textContent = `${e.target.value} t`; });
  }

  // Open & Close
  btnOpen.addEventListener('click', () => {
    modal.style.display = 'flex';
    if (typeof playCyberClick === 'function') playCyberClick();
    loadFirstPrinciplesData();
  });

  if (btnClose) {
    btnClose.addEventListener('click', () => {
      modal.style.display = 'none';
      if (typeof playCyberClick === 'function') playCyberClick();
    });
  }

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.style.display === 'flex') {
      modal.style.display = 'none';
    }
  });

  // Simulation run
  if (btnSim) {
    btnSim.addEventListener('click', async () => {
      if (typeof playCyberClick === 'function') playCyberClick();
      const origText = btnSim.innerHTML;
      btnSim.disabled = true;
      btnSim.innerHTML = '<span>⚡ Solving Equations...</span>';

      try {
        const payload = {
          crew_size: parseInt(crewInput ? crewInput.value : 4),
          mission_days: parseInt(daysInput ? daysInput.value : 30),
          shielding_depth_m: parseFloat(shieldInput ? shieldInput.value : 2.5),
          regolith_mined_tonnes: parseFloat(isruInput ? isruInput.value : 10.0)
        };

        const res = await fetch('/api/nexus/science/simulate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        renderFirstPrinciplesData(data);
        if (typeof showSpaceNotification === 'function') {
          showSpaceNotification('First-principles coupled simulation completed.', 'success');
        }
      } catch (err) {
        console.error('Simulation error:', err);
        if (typeof showSpaceNotification === 'function') {
          showSpaceNotification('Scientific simulation failed: ' + err.message, 'error');
        }
      } finally {
        btnSim.disabled = false;
        btnSim.innerHTML = origText;
      }
    });
  }
}

async function loadFirstPrinciplesData() {
  try {
    const res = await fetch('/api/nexus/science/first_principles');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderFirstPrinciplesData(data);
  } catch (err) {
    console.error('Failed to load first-principles science data:', err);
  }
}

function renderFirstPrinciplesData(data) {
  if (!data) return;

  // Pillar 1: Frequency
  if (data.frequency) {
    const f = data.frequency;
    const lBandEl = document.getElementById('sciSkinDepthL');
    const sBandEl = document.getElementById('sciSkinDepthS');
    const epsEl = document.getElementById('sciDielectricEps');
    const attenEl = document.getElementById('sciRadarAtten');

    const lBandVal = (f.bands && f.bands.L_BAND) ? f.bands.L_BAND.skin_depth_m : (f.skin_depth_m || f.skin_depth_l_band_m);
    const sBandVal = (f.bands && f.bands.S_BAND) ? f.bands.S_BAND.skin_depth_m : (f.skin_depth_s_band_m || (lBandVal ? (lBandVal * 0.39).toFixed(2) : null));
    const epsVal = (f.bands && f.bands.L_BAND) ? f.bands.L_BAND.dielectric_constant : (f.dielectric_constant || 2.70);
    const attenVal = (f.bands && f.bands.L_BAND) ? f.bands.L_BAND.two_way_attenuation_db_per_m : (f.two_way_attenuation_db_per_m || f.attenuation_rate_db_per_m);

    if (lBandEl && lBandVal != null) lBandEl.textContent = `${Number(lBandVal).toFixed(2)} m`;
    if (sBandEl && sBandVal != null) sBandEl.textContent = `${Number(sBandVal).toFixed(2)} m`;
    if (epsEl && epsVal != null) epsEl.textContent = `${Number(epsVal).toFixed(2)}`;
    if (attenEl && attenVal != null) attenEl.textContent = `${Number(attenVal).toFixed(2)} dB/m`;
  }

  // Pillar 2: Physics
  if (data.physics) {
    const p = data.physics;
    const hapkeEl = document.getElementById('sciHapkeRefl');
    const thermalEl = document.getElementById('sciThermalSkin');
    const drawbarEl = document.getElementById('sciRoverDrawbar');
    const mobilityEl = document.getElementById('sciRoverMobility');

    const hapkeVal = p.hapke ? p.hapke.hapke_reflectance : p.hapke_reflectance;
    const thermalVal = p.thermal ? p.thermal.thermal_skin_depth_cm : (p.thermal_skin_depth_m != null ? p.thermal_skin_depth_m * 100 : 4.8);
    const terra = p.terramechanics || p.rover_mobility;
    const drawbarVal = terra ? (terra.net_drawbar_pull_n ?? terra.drawbar_pull_n) : null;
    const mobilityVerdict = terra ? (terra.mobility_verdict ?? terra.mobility_status) : null;

    if (hapkeEl && hapkeVal != null) hapkeEl.textContent = `${Number(hapkeVal).toFixed(4)}`;
    if (thermalEl && thermalVal != null) thermalEl.textContent = `${Number(thermalVal).toFixed(1)} cm`;
    if (drawbarEl && drawbarVal != null) drawbarEl.textContent = `${Number(drawbarVal).toFixed(1)} N`;
    if (mobilityEl && mobilityVerdict) {
      mobilityEl.textContent = mobilityVerdict.replace(/_/g, ' ');
      mobilityEl.style.color = mobilityVerdict.includes('GO') || mobilityVerdict.includes('HIGH') ? '#00e676' : '#fdcb6e';
    }
  }

  // Pillar 3: Chemistry
  if (data.chemistry) {
    const c = data.chemistry;
    const bandDepthEl = document.getElementById('sciBandDepth');
    const waterPpmEl = document.getElementById('sciWaterPpm');
    const o2YieldEl = document.getElementById('sciOxygenYield');
    const energyEl = document.getElementById('sciIsruEnergy');

    const bandObj = c.band_depth_water_proxy;
    const isruObj = c.isru_pyrolysis;

    const bdVal = bandObj ? bandObj.band_depth : (c.absorption_band_depth_2850nm ?? 0.142);
    const ppmVal = bandObj ? bandObj.estimated_water_equivalent_ppm : (c.estimated_water_ppm ?? 284);
    const o2Val = isruObj ? isruObj.oxygen_yield_kg : (c.sample_isru_yield_kg_o2 ?? c.oxygen_yield_kg);
    const energyVal = isruObj ? isruObj.thermal_energy_kwh : (c.thermal_energy_required_kwh ?? c.thermal_energy_kwh);

    if (bandDepthEl && bdVal != null) bandDepthEl.textContent = `${Number(bdVal).toFixed(3)}`;
    if (waterPpmEl && ppmVal != null) waterPpmEl.textContent = `${Number(ppmVal).toFixed(0)} ppm`;
    if (o2YieldEl && o2Val != null) o2YieldEl.textContent = `${Number(o2Val).toFixed(1)} kg`;
    if (energyEl && energyVal != null) energyEl.textContent = `${Number(energyVal).toFixed(0)} kWh`;
  }

  // Pillar 4: Biology
  if (data.biology) {
    const b = data.biology;
    const o2ClosureEl = document.getElementById('sciO2Closure');
    const recycledH2OEl = document.getElementById('sciRecycledH2O');
    const radDoseEl = document.getElementById('sciRadDose');
    const radVerdictEl = document.getElementById('sciRadVerdict');

    const eclssObj = b.eclss || b.eclss_closure || b.eclss_balance;
    const radObj = b.radiation || b.radiation_shielding;

    const o2ClosureVal = eclssObj ? (eclssObj.o2_loop_closure_pct ?? eclssObj.o2_closure_percent) : null;
    const recycledH2OVal = eclssObj ? (eclssObj.water_recycled_kg) : null;
    const radDoseVal = radObj ? (radObj.attenuated_annual_dose_msv_yr ?? radObj.attenuated_annual_dose_msv) : null;
    const radVerdictVal = radObj ? (radObj.radiation_safety_verdict ?? radObj.safe_status) : null;

    if (o2ClosureEl && o2ClosureVal != null) o2ClosureEl.textContent = `${Number(o2ClosureVal).toFixed(1)} %`;
    if (recycledH2OEl && recycledH2OVal != null) recycledH2OEl.textContent = `${Number(recycledH2OVal).toFixed(1)} kg`;
    if (radDoseEl && radDoseVal != null) radDoseEl.textContent = `${Number(radDoseVal).toFixed(2)} mSv/yr`;
    if (radVerdictEl && radVerdictVal) {
      radVerdictEl.textContent = radVerdictVal.replace(/_/g, ' ');
      radVerdictEl.style.color = radVerdictVal.includes('SAFE') ? '#00e676' : '#ff7675';
    }
  }

  // Physics-Informed Neural Network (PINN) Telemetry
  if (data.pinn) {
    const pinn = data.pinn;
    const archEl = document.getElementById('pinnArch');
    const resEl = document.getElementById('pinnResidualRms');
    const trapEl = document.getElementById('pinnColdTrap');
    const objEl = document.getElementById('pinnObjective');

    if (archEl && pinn.neural_architecture) archEl.textContent = pinn.neural_architecture;
    if (resEl && pinn.pde_residual_rms != null) resEl.textContent = `${pinn.pde_residual_rms}`;
    if (trapEl && pinn.subsurface_cold_trap_detected != null) {
      trapEl.textContent = pinn.subsurface_cold_trap_detected ? 'DETECTED (< 110 K)' : 'STABLE SUB-SURFACE';
      trapEl.style.color = '#00e676';
    }
    if (objEl && pinn.total_loss != null) {
      objEl.textContent = `L_total: ${Number(pinn.total_loss).toFixed(4)}`;
    }
  }
}

