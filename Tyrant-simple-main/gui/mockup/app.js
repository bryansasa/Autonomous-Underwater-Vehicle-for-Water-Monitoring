'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const sensors = [
    { key: 'ec', name: 'Konduktivitas', unit: 'µS/cm', base: 1250, amplitude: 18, digits: 0, on: true },
    { key: 'ph', name: 'pH', unit: 'pH', base: 7.14, amplitude: .035, digits: 2, on: true },
    { key: 'temp', name: 'Suhu', unit: '°C', base: 27.3, amplitude: .16, digits: 1, on: true },
    { key: 'do', name: 'Oksigen terlarut', unit: 'mg/L', base: 6.82, amplitude: .09, digits: 2, on: true }
  ];
  const state = {
    mode: 'IDLE', scenario: 'normal', depth: 1.2, target: null, roll: 4, pitch: -3, yaw: 42,
    running: false, stepIndex: -1, snapshot: [], phaseStart: 0, samples: [], recorder: null,
    sessions: [], log: [], keys: new Set(), activeLimit: 60, stoppedLatch: false, tick: 0, lastTelemetry: performance.now(), yawReference: false, yawOffset: 0, stepSamples: 0, incompleteSamples: [], depthHistory: [], depthStable: false, powerRequest: 1000, chartPaused: false
  };
  // Struktur data yang dikirimkan backend:
  const telemetry = {
    depth: 1.25,          // Kedalaman aktual (meter)
    target_depth: 1.50,   // Kedalaman target LMPC (meter)
    roll: 2.1,            // Derajat tilt kiri/kanan
    pitch: -1.4,          // Derajat hidung naik/turun
    yaw: 45.0,            // Sudut hadap kompas (0-360 derajat)
    ph: 7.42,             // Sensor pH Atlas Scientific EZO
    do: 6.25,             // Sensor DO mg/L
    temp: 27.3,           // Sensor suhu air (°C)
    cond: 318.5,          // Konduktivitas EC (µS/cm)
    battery_v: 24.6,      // Tegangan LiPo 6S
    soc_kalman: 92.0,     // State of Charge % estimasi filter Kalman
    current_a: 3.12,      // Arus discharge thruster (Ampere)
    sensor_batt_v: 12.1,  // Tegangan rel sensor INA226
    sensor_current_a: 0.34, // Arus rel sensor (Ampere)
    pwm1: 1550,           // PWM Thruster 1 (1100 - 1900 µs)
    pwm2: 1550,           // PWM Thruster 2
    pwm3: 1450,           // PWM Thruster 3
    pwm4: 1450,           // PWM Thruster 4
    pwm5: 1600,           // PWM Thruster 5 (Vertikal)
    pwm6: 1600,           // PWM Thruster 6 (Vertikal)
    tbm_temp: 3.0,        // Interval sampling EA-DSRA Suhu (detik)
    tbm_do: 2.0,          // Interval sampling EA-DSRA DO (detik)
    tbm_ph: 5.0,          // Interval sampling EA-DSRA pH (detik)
    tbm_cond: 4.0,        // Interval sampling EA-DSRA EC (detik)
    mode: "MANUAL",       // Mode wahana saat ini
    is_armed: true        // Status thruster armed/disarmed
  };

  sensors.forEach(sensor => sensor.lastSample = performance.now());
  let plan = [
    { type: 'DIVE', value: 1, sampling: true },
    { type: 'SURGE', value: 10, sampling: false },
    { type: 'SWAY', value: 5, sampling: false },
    { type: 'HEADING', value: 90, sampling: false },
    { type: 'DIVE', value: 3, sampling: true }
  ];
  plan.forEach((step, index) => Object.assign(step, { id: `step_${index + 1}`, effort: step.type === 'WAIT' ? 0 : 35, timeout: ['SURGE', 'SWAY', 'WAIT'].includes(step.type) ? step.value + 10 : 45, tolerance: step.type === 'HEADING' ? 5 : .2 }));
  let nextStepId = 6;
  const titles = { operasi: 'Pandangan kendaraan', misi: 'Kendali & rencana perjalanan', grafik: 'Data & hasil pengukuran', diagnostik: 'Kesehatan sistem & parameter' };
  const norm = value => ((value % 360) + 360) % 360;
  const missionYaw = () => norm(state.yaw - (state.yawReference ? state.yawOffset : 0));
  const rawTargetYaw = value => norm(value + (state.yawReference ? state.yawOffset : 0));
  const time = () => new Date().toLocaleTimeString('id-ID', { hour12: false });
  const valid = () => ['normal', 'payload_hb_lost'].includes(state.scenario);
  const valueOf = (sensor, tick = state.tick) => sensor.base + sensor.amplitude * Math.sin(tick / 6 + sensors.indexOf(sensor));
  function note(message) {
    $('notice').textContent = message; $('log-latest').textContent = message;
    state.log.unshift({ time: time(), message }); state.log = state.log.slice(0, 6);
    $('log').replaceChildren(...state.log.map(item => {
      const row = document.createElement('div'); row.className = 'log-row';
      const stamp = document.createElement('time'); stamp.textContent = item.time;
      const text = document.createElement('span'); text.textContent = item.message;
      row.append(stamp, text); return row;
    }));
  }
  function setMode(mode) {
    state.keys.clear(); state.mode = mode; $('mode').value = mode; $('mode-badge').textContent = mode;
    $('apply-limit').disabled = mode !== 'IDLE'; $('zero-depth').disabled = mode !== 'IDLE';
    $('start-mission').disabled = state.running || mode !== 'AUTO' || !valid();
    updateManual(); updateOperationalSummary();
  }
  function selectTab(id) {
    Object.keys(titles).forEach(name => {
      $(name).hidden = name !== id; $('tab-' + name).setAttribute('aria-selected', String(name === id));
    });
    $('window-label').textContent = id.toUpperCase(); $('page-title').textContent = titles[id];
    if (id === 'grafik') drawCharts();
  }
  document.querySelectorAll('[data-tab]').forEach(button => button.addEventListener('click', () => selectTab(button.dataset.tab)));
  $('mode').addEventListener('change', event => {
    const requested = event.target.value;
    if (state.running) finishMission('STOPPED', 'Mode diganti saat misi aktif');
    setMode(requested); note('Mode contoh berubah menjadi ' + state.mode + '.');
  });
  $('stop').addEventListener('click', () => {
    if (state.running) finishMission('STOPPED', 'Stop operator');
    state.stoppedLatch = true; setMode('SAFE'); note('Stop simulasi: input netral, mode SAFE. Tidak ada perintah ke hardware.');
  });
  $('sensor-cards').innerHTML = sensors.map(s => `<div class="sensor-card"><div class="sensor-name">${s.name}</div><div class="sensor-number"><span id="sensor-${s.key}">—</span><small>${s.unit}</small></div><div id="valid-${s.key}" class="sensor-valid">VALID · SIM</div><span id="age-${s.key}" class="sensor-age">0.0 s</span><label class="sensor-toggle" aria-label="Daya ${s.name}"><input type="checkbox" data-power="${s.key}" checked></label></div>`).join('');
  document.querySelectorAll('[data-power]').forEach(input => input.addEventListener('change', () => {
    const sensor = sensors.find(s => s.key === input.dataset.power);
    const requested = input.checked, requestId = ++state.powerRequest;
    input.checked = sensor.on;
    if (state.running) { note('Daya sensor dikelola misi aktif. Hentikan misi untuk kontrol manual.'); return; }
    sensor.pending = requestId; input.disabled = true; renderTelemetry();
    note(`Request ${requestId}: daya ${sensor.name} ${requested ? 'ON' : 'OFF'} menunggu ACK contoh.`);
    setTimeout(() => {
      if (sensor.pending !== requestId) return;
      sensor.pending = null; input.disabled = false;
      if (state.scenario === 'disconnected') note(`Request ${requestId}: tidak ada ACK karena link putus. Status GPIO baru belum dapat dikonfirmasi.`);
      else if (requested && state.scenario === 'payload_hb_lost') note(`ACK SIM ${requestId}: accepted=false · SYSTEM_NOT_READY (5). ON membutuhkan heartbeat host ESP sehat; OFF tetap diizinkan.`);
      else { sensor.on = requested; if (!requested) sensor.lastSample = null; note(`ACK SIM ${requestId}: accepted=true, actual_enabled=${requested}. Status GPIO perintah, bukan pengukuran listrik.`); }
      input.checked = sensor.on; renderTelemetry();
    }, 350);
  }));
  function setSensorPower(on) {
    sensors.forEach(s => { s.pending = null; s.on = on && state.scenario === 'payload_hb_lost' ? s.on : on; document.querySelector(`[data-power="${s.key}"]`).checked = s.on; });
    renderTelemetry();
  }

  // Inisialisasi Three.js Viewport (Interaktif & Dinamis)
  (function initSubmersible3D() {
    try {
      if (typeof THREE === 'undefined') return;

      const container = document.getElementById('submersible-3d-canvas');
      if (!container) return;

      const width = container.clientWidth || 300;
      const height = container.clientHeight || 135;

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 1000);
      camera.position.set(95, 65, -135);
      camera.lookAt(0, 0, 0);

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(window.devicePixelRatio);
      container.innerHTML = '';
      container.appendChild(renderer.domElement);

      // Pencahayaan
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.65);
      scene.add(ambientLight);

      const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.2);
      dirLight1.position.set(100, 150, -100);
      scene.add(dirLight1);

      const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
      dirLight2.position.set(-100, 100, 100);
      scene.add(dirLight2);

      let subMesh = null;
      let targetRoll = 0, targetPitch = 0, targetYaw = 0;
      let manualRotX = 0, manualRotY = 0; // Rotasi dari mouse drag

      if (typeof THREE.STLLoader !== 'undefined') {
        const loader = new THREE.STLLoader();
        loader.load('assets/finaltes2.stl', function (geometry) {
          geometry.center();
          geometry.computeVertexNormals();

          geometry.computeBoundingBox();
          const box = geometry.boundingBox;
          const maxDim = Math.max(box.max.x - box.min.x, box.max.y - box.min.y, box.max.z - box.min.z) || 1;
          const fitScale = 62.0 / maxDim;

          const material = new THREE.MeshStandardMaterial({
            color: 0x0284c7,
            metalness: 0.35,
            roughness: 0.35
          });
          subMesh = new THREE.Mesh(geometry, material);
          subMesh.scale.set(fitScale, fitScale, fitScale);
          scene.add(subMesh);

          const robot2D = document.getElementById('robot');
          if (robot2D) robot2D.style.display = 'none';
        });
      }

      // 1. FITUR MOUSE DRAG: Klik dan geser untuk putar 3D bebas
      let isDragging = false, prevMouseX = 0, prevMouseY = 0;
      container.style.cursor = 'grab';

      container.addEventListener('mousedown', e => {
        isDragging = true;
        container.style.cursor = 'grabbing';
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      });

      window.addEventListener('mouseup', () => {
        isDragging = false;
        if (container) container.style.cursor = 'grab';
      });

      window.addEventListener('mousemove', e => {
        if (!isDragging) return;
        const deltaX = e.clientX - prevMouseX;
        const deltaY = e.clientY - prevMouseY;
        manualRotY += deltaX * 0.012;
        manualRotX += deltaY * 0.012;
        prevMouseX = e.clientX;
        prevMouseY = e.clientY;
      });

      // 2. ANIMASI RENDER LOOP: Ayunan air alami + rotasi telemetri
      function animate() {
        requestAnimationFrame(animate);

        if (subMesh) {
          // Efek ombak/gelombang air halus (Subsea Buoyancy Sway)
          const time = performance.now() * 0.0018;
          const waveRoll = Math.sin(time) * 0.035;       // ~2° ayunan kiri-kanan
          const wavePitch = Math.cos(time * 0.8) * 0.02; // ~1.2° ayunan hidung

          // Kombinasikan orientasi telemetri + gelombang air + drag mouse
          subMesh.rotation.x = -targetPitch + wavePitch + manualRotX;
          subMesh.rotation.y = -targetYaw + manualRotY;
          subMesh.rotation.z = targetRoll + waveRoll;
        }

        renderer.render(scene, camera);
      }
      animate();

      // Update dari data telemetri
      window.updateVehicle3DOrientation = function (rollDeg, pitchDeg, yawDeg) {
        targetRoll = (rollDeg * Math.PI) / 180;
        targetPitch = (pitchDeg * Math.PI) / 180;
        targetYaw = (yawDeg * Math.PI) / 180;
      };
    } catch (err) {
      console.warn('Three.js info:', err);
    }
  })();


  function renderTelemetry() {
    const ok = valid(); const linked = state.scenario !== 'disconnected';
    sensors.forEach(s => {
      $('sensor-' + s.key).textContent = ok && s.on && s.lastSample !== null ? valueOf(s).toFixed(s.digits) : '—';
      const control = document.querySelector(`[data-power="${s.key}"]`); control.disabled = state.running || !!s.pending;
      $('valid-' + s.key).textContent = s.pending ? 'MENUNGGU ACK · SIM' : !linked ? 'STALE · LINK PUTUS' : !s.on ? 'DAYA OFF' : s.lastSample === null ? 'INITIALIZING · SIM' : ok ? 'VALID · SIM' : 'TIDAK VALID';
      $('valid-' + s.key).style.color = ok && s.on ? 'var(--green)' : 'var(--amber)';
      $('age-' + s.key).textContent = !s.on ? 'OFF' : s.lastSample === null ? 'Belum ada sampel' : (ok ? 'Data ' : 'Terakhir ') + ((performance.now() - s.lastSample) / 1000).toFixed(1) + ' s';
    });
    $('sensor-current').textContent = ok ? (sensors.filter(s => s.on).length * .08).toFixed(2) + ' A' : '— A';
    $('depth-value').textContent = ok ? state.depth.toFixed(2) : '—';
    $('depth-target').textContent = state.target === null ? 'Target —' : 'Target ' + state.target.toFixed(2) + ' m · sim';
    $('depth-marker').style.top = Math.min(98, Math.max(0, state.depth * 10)) + '%'; $('depth-marker').hidden = !ok;
    ['roll', 'pitch', 'yaw'].forEach(key => $(key + '-value').textContent = ok ? state[key].toFixed(1) + '°' : '—');
    $('heading-value').textContent = ok ? norm(Math.round(missionYaw())) + '°' : '—';
    $('compass-title').textContent = state.yawReference ? 'Yaw misi' : 'Kompas asli';
    $('hud-heading-label').textContent = state.yawReference ? 'YAW MISI · SIM' : 'HEADING ASLI · SIM';
    $('heading-basis').textContent = state.yawReference ? 'YAW MISI · SIM' : 'HEADING ASLI · SIM';
    $('heading-raw').textContent = state.yawReference ? 'Asli ' + (ok ? state.yaw.toFixed(1) + '°' : '—') : '';
    $('yaw-reference-summary').textContent = state.yawReference ? `Nol misi = heading asli ${state.yawOffset.toFixed(1)}° · yaw misi ${missionYaw().toFixed(1)}°` : 'Default: heading asli magnetometer';
    $('target-heading-label').textContent = state.yawReference ? 'Yaw misi relatif (°)' : 'Heading asli (°)';
    $('attitude-horizon').setAttribute('transform', `translate(0 ${state.pitch * 1.3}) rotate(${-state.roll} 100 65)`);
    $('attitude-status').textContent = ok ? `ROLL ${state.roll.toFixed(1)}° · PITCH ${state.pitch.toFixed(1)}° · SIM` : 'ATTITUDE TIDAK VALID';
    document.querySelector('.attitude-overlay svg').style.opacity = ok ? '1' : '.2';
    $('compass-needle').style.transform = `rotate(${missionYaw()}deg)`; $('compass-needle').hidden = !ok;
    $('robot').style.transform = `rotateX(${55 + state.pitch}deg) rotateY(${state.roll}deg) rotateZ(${state.yaw}deg)`;
    // Update orientasi 3D STL secara realtime
    if (window.updateVehicle3DOrientation) {
      window.updateVehicle3DOrientation(state.roll, state.pitch, state.yaw);
    }
    $('robot').style.opacity = ok ? '1' : '.25';
    document.querySelectorAll('.instruments .quality-tag').forEach(tag => { tag.textContent = ok ? 'VALID · SIM' : linked ? 'TIDAK VALID' : 'STALE'; tag.classList.toggle('invalid', !ok); });
    $('connection').textContent = linked ? '● Link simulasi' : '○ Link putus · sim';
    $('connection').className = linked ? 'connected' : 'warning';
    document.querySelectorAll('.link-state').forEach((tag, index) => { tag.textContent = index === 2 && state.scenario === 'payload_hb_lost' ? 'Agent SIM · HB timeout' : linked ? 'Simulasi' : 'Terputus · sim'; tag.style.color = linked ? 'var(--green)' : 'var(--amber)'; });
    $('heartbeat-value').textContent = state.scenario === 'payload_hb_lost' ? 'Teensy 63 ms · ESP timeout · sim' : linked ? '63 ms · contoh' : 'Tidak tersedia';
    document.querySelectorAll('[data-power-value]').forEach(element => element.textContent = ok ? element.dataset.powerValue : '—');
    $('power-valid').textContent = ok ? 'INA226 · SIM' : linked ? 'TIDAK VALID' : 'STALE · LINK PUTUS';
    $('power-valid').classList.toggle('invalid', !ok);
    $('power-thruster').textContent = ok ? '79.4 W · sim' : '—';
    $('power-sensors').textContent = ok ? (12.1 * sensors.filter(sensor => sensor.on).length * .08).toFixed(1) + ' W · sim' : '—';
    updateOperationalSummary();
  }
  function updateOperationalSummary() {
    const ok = valid(), linked = state.scenario !== 'disconnected';
    $('ready-light').parentElement.parentElement.classList.toggle('blocked', !ok || state.scenario === 'payload_hb_lost');
    $('ready-title').textContent = state.scenario === 'payload_hb_lost' ? 'Heartbeat ESP timeout' : ok ? 'Siap simulasi' : linked ? 'AUTO diblokir' : 'Link terputus';
    $('ready-reason').textContent = state.scenario === 'payload_hb_lost' ? 'ESP menolak ON; OFF tetap diperbolehkan · telemetry dapat tetap tersedia' : ok ? 'Depth, attitude dan heartbeat valid pada preview' : linked ? 'Depth & attitude tidak valid · kontrol netral' : 'Telemetry stale · input netral · tidak ada resume otomatis';
    const age = ((performance.now() - state.lastTelemetry) / 1000).toFixed(1);
    $('telemetry-age').textContent = (ok ? 'Data ' : 'Terakhir ') + age + ' s · SIM';
    $('hud-depth').innerHTML = (ok ? state.depth.toFixed(2) : '—') + ' <small>m</small>';
    $('hud-heading').innerHTML = (ok ? String(norm(Math.round(missionYaw()))).padStart(3, '0') : '—') + ' <small>°</small>';
    $('hud-record').textContent = state.recorder ? '● REC' : 'OFF';
    $('hud-record').style.color = state.recorder ? 'var(--red)' : '';
    $('camera-mode').textContent = state.mode;
    $('camera-rec').textContent = state.recorder ? '● REC' : 'REC OFF';
    $('camera-rec').style.color = state.recorder ? 'var(--red)' : 'var(--muted)';
    $('camera-link').textContent = linked ? 'LINK SIM' : 'LINK PUTUS';
    $('camera-link').style.color = linked ? 'var(--green)' : 'var(--amber)';
    const step = state.running ? state.snapshot[state.stepIndex] : null;
    const status = $('mission-state').textContent.replace(' · SIM', '');
    $('peek-status').textContent = state.running ? 'ACTIVE · SIM' : status;
    $('peek-step').textContent = step ? `${state.stepIndex + 1}/${state.snapshot.length} · ${step.type}` : status === 'IDLE' ? 'Belum ada misi' : 'Misi ' + status.toLowerCase();
    $('peek-target').textContent = step ? ['DIVE', 'SURFACE'].includes(step.type) ? `Target ${step.value.toFixed(2)} m · contoh` : step.type === 'HEADING' ? `Heading ${step.displayValue ?? step.value}° ${state.yawReference ? "relatif" : "asli"} · contoh` : `Durasi rencana ${step.value} s · preview dipercepat` : 'Susun rencana di Kontrol & Misi';
    $('peek-error').textContent = 'Selisih depth ' + (ok && state.target !== null ? (state.depth - state.target).toFixed(2) + ' m' : '—');
    $('peek-samples').textContent = 'Contoh ' + state.samples.reduce((total, row) => total + row.count * 4, 0);
    const fraction = state.running ? Math.min(1, (performance.now() - state.phaseStart) / 3000) : 0;
    const progress = state.running ? (state.stepIndex + fraction) / state.snapshot.length : status === 'COMPLETE' ? 1 : 0;
    $('peek-progress').style.width = Math.max(0, progress * 100) + '%';
    document.querySelectorAll('#yaw-reference-enabled,#yaw-offset,#yaw-zero-current').forEach(input => input.disabled = state.running);
  }
  $('open-planner').addEventListener('click', () => { selectTab('misi'); $('tab-misi').focus(); window.scrollTo({ top: 0, behavior: 'instant' }); });
  const cameraDialog = $('camera-dialog'), cameraPanel = $('camera-panel');
  let cameraAnchor = null, previousOverflow = '';
  function closeCamera() { if (cameraDialog.open) cameraDialog.close(); }
  $('fullscreen').addEventListener('click', () => {
    cameraAnchor = document.createComment('camera-origin'); cameraPanel.before(cameraAnchor);
    cameraDialog.append(cameraPanel); $('fullscreen').hidden = true;
    $('camera-stop').hidden = false; $('camera-close').hidden = false;
    previousOverflow = document.body.style.overflow; document.body.style.overflow = 'hidden';
    cameraDialog.showModal(); $('camera-close').focus();
  });

  // --- LIVE CAMERA & UNDERWATER SIMULATION ENGINE ---
  const camVideo = $('camera-video');
  const camStream = $('camera-stream');
  const camCanvas = $('camera-underwater-canvas');
  const camCaption = $('camera-caption');
  const toggleCamBtn = $('toggle-camera-btn');
  const camStatus = $('camera-video-status');
  let localMediaStream = null;

  async function toggleCamera() {
    if (!localMediaStream) {
      try {
        localMediaStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        if (camVideo) {
          camVideo.srcObject = localMediaStream;
          camVideo.style.display = 'block';
        }
        if (camCanvas) camCanvas.style.display = 'none';
        if (camCaption) camCaption.style.display = 'none';
        if (toggleCamBtn) {
          toggleCamBtn.innerHTML = '<span>⏹️ Matikan Kamera</span>';
          toggleCamBtn.style.color = 'var(--red)';
          toggleCamBtn.style.borderColor = '#794851';
        }
        if (camStatus) camStatus.textContent = '● LIVE · WEBCAM REAL';
        $('camera-link').textContent = 'LIVE CAM';
        $('camera-link').style.color = 'var(--green)';
        note('Kamera webcam lokal/USB aktif.');
      } catch (err) {
        console.warn('Gagal membuka webcam:', err);
        note('Izin webcam ditolak atau kamera tidak terdeteksi.');
      }
    } else {
      localMediaStream.getTracks().forEach(track => track.stop());
      localMediaStream = null;
      if (camVideo) {
        camVideo.srcObject = null;
        camVideo.style.display = 'none';
      }
      if (camCanvas) camCanvas.style.display = 'block';
      if (camCaption) camCaption.style.display = 'block';
      if (toggleCamBtn) {
        toggleCamBtn.innerHTML = '<span>📹 Buka Kamera</span>';
        toggleCamBtn.style.color = 'var(--cyan)';
        toggleCamBtn.style.borderColor = '#3e6569';
      }
      if (camStatus) camStatus.textContent = 'FEED: SIMULASI AIR';
      $('camera-link').textContent = 'SIM';
      $('camera-link').style.color = 'var(--amber)';
      note('Kamera dimatikan · kembali ke simulasi air.');
    }
  }
  if (toggleCamBtn) toggleCamBtn.addEventListener('click', toggleCamera);

  function initUnderwaterSimulation() {
    if (!camCanvas) return;
    const ctx = camCanvas.getContext('2d');
    let w = (camCanvas.width = camCanvas.parentElement ? camCanvas.parentElement.clientWidth : 640);
    let h = (camCanvas.height = camCanvas.parentElement ? camCanvas.parentElement.clientHeight : 360);
    window.addEventListener('resize', () => {
      if (camCanvas.parentElement) {
        w = camCanvas.width = camCanvas.parentElement.clientWidth;
        h = camCanvas.height = camCanvas.parentElement.clientHeight;
      }
    });

    const bubbles = Array.from({ length: 30 }, () => ({
      x: Math.random() * (w || 640),
      y: Math.random() * (h || 360),
      radius: Math.random() * 3 + 1,
      speed: Math.random() * 0.7 + 0.3,
      wobble: Math.random() * Math.PI * 2,
      wobbleSpeed: Math.random() * 0.03 + 0.01,
      alpha: Math.random() * 0.4 + 0.2
    }));

    let t = 0;
    function drawUnderwater() {
      if (localMediaStream) {
        requestAnimationFrame(drawUnderwater);
        return;
      }
      t += 0.02;
      ctx.clearRect(0, 0, w, h);

      // Deep aquatic gradient
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, '#0f323a');
      grad.addColorStop(0.5, '#092128');
      grad.addColorStop(1, '#051217');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);

      // Gentle caustics / sun rays
      ctx.save();
      ctx.globalCompositeOperation = 'screen';
      for (let i = 0; i < 4; i++) {
        const rayX = (w * (i + 1)) / 5 + Math.sin(t + i) * 20;
        const rayGrad = ctx.createLinearGradient(rayX, 0, rayX + (i % 2 === 0 ? 30 : -30), h);
        rayGrad.addColorStop(0, 'rgba(120, 221, 212, 0.12)');
        rayGrad.addColorStop(0.7, 'rgba(120, 221, 212, 0.02)');
        rayGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = rayGrad;
        ctx.beginPath();
        ctx.moveTo(rayX - 35, 0);
        ctx.lineTo(rayX + 35, 0);
        ctx.lineTo(rayX + 110, h);
        ctx.lineTo(rayX - 40, h);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();

      // Floating bubbles
      ctx.save();
      bubbles.forEach(b => {
        b.y -= b.speed;
        b.wobble += b.wobbleSpeed;
        b.x += Math.sin(b.wobble) * 0.3;
        if (b.y < -10) {
          b.y = h + 10;
          b.x = Math.random() * w;
        }
        ctx.beginPath();
        ctx.arc(b.x, b.y, b.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180, 235, 230, ${b.alpha})`;
        ctx.fill();
        ctx.strokeStyle = `rgba(255, 255, 255, ${b.alpha * 1.5})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      });
      ctx.restore();

      requestAnimationFrame(drawUnderwater);
    }
    requestAnimationFrame(drawUnderwater);
  }
  initUnderwaterSimulation();
  $('reference-help-button').addEventListener('click', () => {
    const open = $('reference-help').hidden; $('reference-help').hidden = !open;
    $('reference-help-button').setAttribute('aria-expanded', String(open));
  });
  function updateYawReference() {
    if (state.running) return;
    if ($('yaw-reference-enabled').checked && !$('yaw-offset').checkValidity()) { $('yaw-reference-enabled').checked = state.yawReference; note('Nol yaw harus dalam rentang 0–359.999°.'); return; }
    state.yawReference = $('yaw-reference-enabled').checked; if ($('yaw-offset').checkValidity()) state.yawOffset = Number($('yaw-offset').value);
    renderSteps(); renderTelemetry(); note(state.yawReference ? 'Referensi yaw misi aktif. Heading asli tetap disimpan.' : 'Referensi yaw OFF: kembali ke heading asli.');
  }
  $('yaw-reference-enabled').addEventListener('change', updateYawReference);
  $('yaw-offset').addEventListener('change', updateYawReference);
  $('yaw-zero-current').addEventListener('click', () => {
    if (state.running || !valid()) { note('Referensi membutuhkan heading valid dan tidak ada misi aktif.'); return; }
    $('yaw-offset').value = state.yaw.toFixed(1); $('yaw-reference-enabled').checked = true; updateYawReference();
  });
  const instruments = document.querySelector('.instruments');

  function setNavigationView() {
    document.querySelector('.camera-placeholder').append(instruments);
    cameraPanel.classList.add('integrated-navigation');
  }
  $('camera-close').addEventListener('click', closeCamera);
  $('camera-stop').addEventListener('click', () => $('stop').click());
  cameraDialog.addEventListener('cancel', event => { event.preventDefault(); closeCamera(); });
  cameraDialog.addEventListener('close', () => {
    cameraAnchor.replaceWith(cameraPanel); cameraAnchor = null;
    $('fullscreen').hidden = false; $('camera-stop').hidden = true; $('camera-close').hidden = true;
    document.body.style.overflow = previousOverflow; $('fullscreen').focus();
  });
  $('scenario').addEventListener('change', event => {
    state.scenario = event.target.value; state.keys.clear();
    if (!valid()) {
      if (state.running) finishMission('FAILED', 'Telemetry tidak valid / terputus');
      setMode('SAFE');
    } else setMode('IDLE');
    note('Skenario preview: ' + event.target.selectedOptions[0].textContent + '. Tidak ada resume otomatis.');
    renderTelemetry(); drawCharts(); updateManual();
  });
  ['roll', 'pitch', 'yaw'].forEach(key => $(key + '-input').addEventListener('input', event => { state[key] = Number(event.target.value); renderTelemetry(); }));
  $('input-scale').addEventListener('input', event => { $('input-scale-value').textContent = event.target.value + '%'; updateManual(); });
  $('input-source').addEventListener('change', () => {
    state.keys.clear();
    const controller = $('input-source').value === 'controller';
    $('input-help').textContent = controller ? 'Pemeriksaan axes saja. Mapping/deadman browser belum dikualifikasi.' : 'W/S maju · A/D geser · Q/E yaw · R/F vertikal';
    note('Sumber input diganti. Input lama dinetralkan.'); updateManual();
  });
  function updateManual() {
    const enabled = state.mode === 'MANUAL' && valid() && !state.stoppedLatch && state.keys.has('Space') && $('input-source').value === 'keyboard';
    const k = state.keys; const scale = Number($('input-scale').value) / 100;
    const axis = (positive, negative) => enabled ? ((k.has(positive) ? 1 : 0) - (k.has(negative) ? 1 : 0)) * scale : 0;
    $('manual-axes').textContent = `Surge ${axis('KeyW', 'KeyS').toFixed(2)} · Sway ${axis('KeyD', 'KeyA').toFixed(2)} · Heave ${axis('KeyF', 'KeyR').toFixed(2)} · Yaw ${axis('KeyE', 'KeyQ').toFixed(2)}`;
    $('manual-status').textContent = enabled ? 'Deadman aktif · input simulasi' : $('input-source').value === 'controller' ? 'Controller: pemeriksaan input saja' : 'Netral · MANUAL + Space untuk preview';
  }
  document.addEventListener('keydown', event => {
    if (event.code === 'Escape') { if (cameraDialog.open) { event.preventDefault(); closeCamera(); } else $('stop').click(); return; }
    if (event.target.closest('input,select,textarea,button,a,svg')) return;
    if (!['Space', 'KeyW', 'KeyS', 'KeyA', 'KeyD', 'KeyQ', 'KeyE', 'KeyR', 'KeyF'].includes(event.code)) return;
    if (state.mode !== 'MANUAL' || $('input-source').value !== 'keyboard') return;
    event.preventDefault(); state.keys.add(event.code); updateManual();
  });
  document.addEventListener('keyup', event => { state.keys.delete(event.code); if (event.code === 'Space') state.stoppedLatch = false; updateManual(); });
  window.addEventListener('blur', () => { state.keys.clear(); updateManual(); });
  document.addEventListener('focusin', event => { if (event.target.closest('input,select,textarea,button,a,svg')) { state.keys.clear(); updateManual(); } });
  document.addEventListener('visibilitychange', () => { if (document.hidden) { state.keys.clear(); updateManual(); } });
  function targetAllowed() {
    if (!valid() || !['MANUAL', 'AUTO'].includes(state.mode) || state.running) { note('Target contoh membutuhkan MANUAL/AUTO, telemetry valid, dan tidak ada misi aktif.'); return false; }
    return true;
  }
  $('apply-target').addEventListener('click', () => {
    if (!targetAllowed()) return;
    const depth = Number($('target-depth').value), heading = Number($('target-heading').value);
    if (!$('target-depth').checkValidity() || !$('target-heading').checkValidity()) { note('Target di luar rentang: depth 0–10 m, heading 0–359°.'); return; }
    state.target = depth; state.depth = depth; state.yaw = rawTargetYaw(heading); $('yaw-input').value = state.yaw;
    renderTelemetry(); note('Target diterapkan langsung pada data contoh. Bukan respons controller riil.');
  });
  $('surface').addEventListener('click', () => { if (!targetAllowed()) return; state.depth = 0; state.target = 0; renderTelemetry(); note('Simulasi naik ke permukaan: target 0 m.'); });
  $('zero-depth').addEventListener('click', () => { if (state.mode !== 'IDLE' || !valid()) { note('Kalibrasi nol contoh membutuhkan IDLE dan depth valid.'); return; } state.depth = 0; state.target = null; renderTelemetry(); note('Referensi permukaan contoh dinolkan; bukan perintah gerak.'); });
  function renderSteps() {
    $('steps').innerHTML = plan.map((step, index) => {
      const depthType = ['DIVE', 'SURFACE'].includes(step.type);
      const label = depthType ? 'm' : step.type === 'HEADING' ? (state.yawReference ? '° relatif' : '° asli') : 's';
      const max = depthType ? 10 : step.type === 'HEADING' ? 359 : 600;
      const toleranceUnit = step.type === 'HEADING' ? '°' : 'm';
      const disabled = state.running ? 'disabled' : '';
      return `<tr class="${state.running && index === state.stepIndex ? 'active-step' : state.running && index < state.stepIndex ? 'complete-step' : ''}"><td class="step-name">${String(index + 1).padStart(2, '0')}</td><td><select data-step="${index}" data-property="type" aria-label="Jenis langkah ${index + 1}" ${disabled}>${['WAIT', 'SURGE', 'SWAY', 'DIVE', 'HEADING', 'SURFACE'].map(type => `<option ${step.type === type ? 'selected' : ''}>${type}</option>`).join('')}</select></td><td><input aria-label="Target langkah ${index + 1}" data-step="${index}" data-property="value" type="number" min="0" max="${max}" step="${depthType ? '.1' : '1'}" value="${step.value}" ${disabled}> <span class="subtle">${label}</span></td><td><input type="number" aria-label="Effort langkah ${index + 1}" data-step="${index}" data-property="effort" min="-100" max="100" step="1" value="${step.effort}" ${state.running || step.type === 'WAIT' ? 'disabled' : ''}></td><td><input type="number" aria-label="Timeout langkah ${index + 1}" data-step="${index}" data-property="timeout" min="0.1" max="3600" step="any" value="${step.timeout}" ${disabled}></td><td>${depthType || step.type === 'HEADING' ? `<input type="number" aria-label="Toleransi langkah ${index + 1}" data-step="${index}" data-property="tolerance" min="0.001" max="${step.type === 'HEADING' ? 179.999 : 10}" step="any" value="${step.tolerance}" ${disabled}><small>${toleranceUnit}</small>` : '—'}</td><td><label><input aria-label="Sampling langkah ${index + 1}" data-step="${index}" data-property="sampling" type="checkbox" ${step.sampling ? 'checked' : ''} ${state.running ? 'disabled' : ''}> Sampel</label></td><td><select data-step="${index}" data-property="sampleTiming" aria-label="Waktu sampel langkah ${index + 1}" ${!step.sampling || state.running ? 'disabled' : ''}><option value="during" ${step.sampleTiming !== 'after' ? 'selected' : ''}>Selama langkah</option><option value="after" ${step.sampleTiming === 'after' ? 'selected' : ''}>Setelah selesai</option></select></td><td><div class="step-actions"><button aria-label="Naikkan langkah ${index + 1}" data-up="${index}" ${state.running || index === 0 ? 'disabled' : ''}>↑</button><button aria-label="Turunkan langkah ${index + 1}" data-down="${index}" ${state.running || index === plan.length - 1 ? 'disabled' : ''}>↓</button><button aria-label="Hapus langkah ${index + 1}" data-delete="${index}" ${state.running ? 'disabled' : ''}>×</button></div></td></tr>`;
    }).join('');
    $('add-step').disabled = state.running || plan.length >= 100;
    document.querySelectorAll('.plan-settings input,.plan-settings select').forEach(input => input.disabled = state.running);
  }
  $('steps').addEventListener('change', event => {
    const index = Number(event.target.dataset.step), property = event.target.dataset.property;
    if (state.running || !property) return;
    const step = plan[index];
    step[property] = property === 'sampling' ? event.target.checked : ['value', 'effort', 'timeout', 'tolerance'].includes(property) ? Number(event.target.value) : event.target.value;
    if (property === 'sampling') document.querySelector(`[data-step="${index}"][data-property="sampleTiming"]`).disabled = !step.sampling;
    if (property === 'type') { step.effort = step.type === 'WAIT' ? 0 : 35; step.timeout = 45; step.tolerance = step.type === 'HEADING' ? 5 : .2; step.value = ['DIVE', 'SURFACE'].includes(step.type) ? 1 : step.type === 'HEADING' ? 90 : 5; renderSteps(); }
  });
  $('steps').addEventListener('click', event => {
    if (state.running) return;
    const remove = event.target.closest('[data-delete]'), up = event.target.closest('[data-up]'), down = event.target.closest('[data-down]');
    if (!remove && !up && !down) return;
    if (remove) plan.splice(Number(remove.dataset.delete), 1);
    if (up) { const index = Number(up.dataset.up);[plan[index - 1], plan[index]] = [plan[index], plan[index - 1]]; }
    if (down) { const index = Number(down.dataset.down);[plan[index], plan[index + 1]] = [plan[index + 1], plan[index]]; }
    renderSteps();
  });
  $('add-step').addEventListener('click', () => { if (!state.running && plan.length < 100) { plan.push({ id: `step_${nextStepId++}`, type: 'WAIT', value: 5, sampling: false, effort: 0, timeout: 15, tolerance: .2 }); renderSteps(); } });
  function startRecord(origin) {
    if (state.recorder) return;
    state.recorder = { id: 'SIM-' + new Date().toISOString().replace(/[-:]/g, '').slice(0, 15), origin, started: time(), rows: [] };
    $('rec-badge').textContent = '● REC · SIM'; $('rec-badge').className = 'active';
    $('record').textContent = 'Hentikan rekaman contoh'; note('Rekaman ' + origin + ' dimulai dalam memori preview.');
  }
  function stopRecord(result = 'STOPPED') {
    if (!state.recorder) return;
    state.recorder.result = result; state.sessions.unshift(state.recorder); state.recorder = null;
    state.sessions = state.sessions.slice(0, 10);
    $('rec-badge').textContent = 'REC OFF'; $('rec-badge').className = ''; $('record').textContent = 'Mulai rekaman contoh';
    $('sessions').innerHTML = state.sessions.map((session, index) => `<div class="session"><div>${session.id}<small>${session.rows.length} baris · ${session.result} · ${session.origin}</small></div><button data-export="${index}">CSV simulasi ↓</button></div>`).join('');
  }
  $('record').addEventListener('click', () => {
    if (state.running) { note('Rekaman dimiliki misi aktif; hentikan misi untuk menutupnya.'); return; }
    if (state.recorder) { stopRecord(); note('Rekaman contoh ditutup.'); } else startRecord('manual');
  });
  $('sessions').addEventListener('click', event => {
    const button = event.target.closest('[data-export]'); if (!button) return;
    const session = state.sessions[Number(button.dataset.export)];
    const lines = ['source,timestamp_utc,depth_m,ec_us_cm,ph,temperature_c,do_mg_l,depth_valid,ec_valid,ph_valid,temperature_valid,do_valid,heading_raw_deg,yaw_mission_deg,yaw_reference_enabled,yaw_offset_deg,depth_stable,heading_valid,step_id,sampling_timing,phase', ...session.rows.map(row => row.join(','))];
    const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = session.id + '-simulated.csv'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    note('CSV simulasi diunduh. Tidak berisi pengukuran sensor riil.');
  });
  $('start-mission').addEventListener('click', () => {
    if (state.mode !== 'AUTO' || !valid() || state.running) { note('Mulai misi contoh membutuhkan AUTO dan telemetry valid.'); return; }
    if (state.recorder) { note('Tutup rekaman manual terlebih dahulu.'); return; }
    if (!plan.length || ![...document.querySelectorAll('.plan-settings input,#steps input[type=number]')].every(input => input.checkValidity())) { note('Periksa rentang nilai dan minimal satu langkah misi.'); return; }
    const invalidStep = plan.find(step => step.type !== 'WAIT' && (!Number.isFinite(step.effort) || step.effort === 0 || Math.abs(step.effort) > 100) || ['WAIT', 'SURGE', 'SWAY'].includes(step.type) && step.timeout <= step.value);
    if (invalidStep) { note(`${invalidStep.id}: effort harus nonzero ±100%; timeout harus lebih besar dari durasi.`); return; }
    state.snapshot = plan.map(step => ({ ...step, displayValue: step.value, value: step.type === 'HEADING' ? rawTargetYaw(step.value) : step.value })); state.policy = $('sampling-policy').value;
    state.sampleCount = Number($('sample-count').value); state.incompleteSamples = []; state.running = true; state.stepIndex = -1; state.samples = [];
    $('sample-rows').innerHTML = '<tr><td colspan="6" class="empty">Menunggu titik sampling contoh</td></tr>';
    startRecord('mission'); $('mission-state').textContent = 'ACTIVE · SIM'; setMode('AUTO'); nextStep();
  });
  function nextStep() {
    state.stepIndex++;
    if (state.stepIndex >= state.snapshot.length) { finishMission(state.incompleteSamples.length ? 'FAILED' : 'COMPLETE', state.incompleteSamples.length ? 'Kuota contoh belum terpenuhi pada langkah ' + state.incompleteSamples.join(', ') : 'Semua langkah simulasi selesai'); return; }
    const step = state.snapshot[state.stepIndex]; state.phaseStart = performance.now(); state.startDepth = state.depth; state.stepSamples = 0;
    if (['DIVE', 'SURFACE'].includes(step.type)) state.target = step.value;
    setSensorPower(state.policy === 'throughout' || step.sampling);
    $('mission-progress').textContent = `${state.stepIndex + 1}/${state.snapshot.length} · ${step.type} · dipercepat`;
    renderSteps(); note('Langkah simulasi ' + (state.stepIndex + 1) + ': ' + step.type + '.');
  }
  function finishMission(result, reason) {
    state.running = false; $('mission-state').textContent = result + ' · SIM'; $('mission-progress').textContent = reason;
    setSensorPower(false); stopRecord(result); setMode('SAFE'); renderSteps(); note('Misi simulasi ' + result + ': ' + reason + '. Sensor dimatikan.');
  }
  $('thruster-limit').addEventListener('input', event => $('limit-draft').textContent = event.target.value + '%');
  $('apply-limit').addEventListener('click', () => {
    if (state.mode !== 'IDLE' || !valid()) { note('Apply contoh hanya ketika IDLE dan link valid.'); return; }
    state.activeLimit = Number($('thruster-limit').value); $('limit-active').textContent = 'Aktif: ' + state.activeLimit + '% · contoh';
    note('Batas output contoh diperbarui. Firmware tidak diubah; tidak ada ACK hardware.');
  });
  const chartHistory = sensors.map(sensor => Array.from({ length: 60 }, (_, index) => ({
    time: Date.now() - (59 - index) * 1000, sequence: index + 1,
    value: index >= 24 && index <= 29 ? null : valueOf(sensor, index - 59),
    depth: 1.2, depthValid: true, stable: false, valid: !(index >= 24 && index <= 29)
  })));
  let chartSequence = 60, chartSelection = {}, frozenCharts = null;
  $('charts').innerHTML = sensors.map(sensor => `<article class="chart-box"><header><div><h3>${sensor.name}</h3><span class="chart-unit">${sensor.unit} · SIM</span></div><strong id="chart-value-${sensor.key}"></strong></header><svg id="chart-${sensor.key}" class="chart" role="img" tabindex="0" aria-label="Grafik ${sensor.name} simulasi; sentuh atau arahkan kursor untuk memilih titik, tombol panah untuk detail"></svg><div id="chart-detail-${sensor.key}" class="chart-detail" aria-live="polite">Pilih titik untuk membaca waktu, nilai dan depth contoh</div></article>`).join('');
  $('chart-window').addEventListener('change', () => { chartSelection = {}; drawCharts(); });
  $('chart-pause').addEventListener('click', () => {
    state.chartPaused = !state.chartPaused;
    frozenCharts = state.chartPaused ? chartHistory.map(points => points.map(point => ({ ...point }))) : null;
    $('chart-pause').textContent = state.chartPaused ? 'Lanjutkan live' : 'Bekukan tampilan';
    $('chart-pause').setAttribute('aria-pressed', String(state.chartPaused)); drawCharts();
  });
  function captureChartPoint() {
    chartSequence++;
    sensors.forEach((sensor, index) => {
      const available = valid() && sensor.on && sensor.lastSample !== null;
      chartHistory[index].push({
        time: Date.now(), sequence: chartSequence,
        value: available ? valueOf(sensor) : null, valid: available,
        depth: valid() ? state.depth : null, depthValid: valid(), stable: state.depthStable
      });
      chartHistory[index].splice(0, Math.max(0, chartHistory[index].length - 900));
    });
  }
  function drawCharts() {
    if ($('grafik').hidden) return;
    sensors.forEach((sensor, index) => {
      const svg = $('chart-' + sensor.key), width = Math.max(240, svg.clientWidth), height = 250;
      const source = state.chartPaused ? frozenCharts[index] : chartHistory[index];
      const end = source.at(-1).time, seconds = Number($('chart-window').value), start = end - seconds * 1000;
      const points = source.filter(point => point.time >= start);
      const values = points.filter(point => point.valid && point.value !== null).map(point => point.value);
      const low = values.length ? Math.min(...values) : sensor.base - sensor.amplitude;
      const high = values.length ? Math.max(...values) : sensor.base + sensor.amplitude;
      const padding = Math.max((high - low) * .2, sensor.amplitude * .3);
      const min = low - padding, max = high + padding;
      const left = 61, right = width - 16, top = 20, bottom = 195;
      const x = time => left + (time - start) / (end - start) * (right - left);
      const y = value => bottom - (value - min) / (max - min) * (bottom - top);
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
      let marks = `<title>${sensor.name}, pembacaan sintetis</title><defs><clipPath id="clip-${sensor.key}"><rect x="${left - 3}" y="${top - 4}" width="${right - left + 6}" height="${bottom - top + 8}"/></clipPath></defs>`;
      for (let tick = 0; tick < 5; tick++) {
        const value = min + (max - min) * tick / 4, py = y(value);
        marks += `<path class="grid" d="M${left} ${py}H${right}"/><text x="${left - 9}" y="${py + 4}" text-anchor="end">${value.toFixed(sensor.digits)}</text>`;
      }
      const ticks = width < 350 ? 2 : 4;
      for (let tick = 0; tick <= ticks; tick++) {
        const px = left + (right - left) * tick / ticks, ago = seconds - seconds * tick / ticks;
        marks += `<path class="grid minor" d="M${px} ${top}V${bottom}"/><text x="${px}" y="${bottom + 24}" text-anchor="${tick === 0 ? 'start' : tick === ticks ? 'end' : 'middle'}">${ago === 0 ? 'Kini' : ago >= 60 ? (ago / 60).toFixed(ago % 60 ? 1 : 0) + 'm' : '−' + Math.round(ago) + 's'}</text>`;
      }
      let path = '', pen = false;
      points.forEach(point => { if (!point.valid) { pen = false; return; } path += `${pen ? 'L' : 'M'}${x(point.time).toFixed(1)},${y(point.value).toFixed(1)} `; pen = true; });
      marks += `<g clip-path="url(#clip-${sensor.key})"><path class="series" d="${path}"/>`;
      const stride = Math.max(1, Math.ceil(points.length / 100));
      points.forEach((point, i) => { if (point.valid && (i % stride === 0 || i === points.length - 1)) marks += `<circle class="sample-dot" cx="${x(point.time)}" cy="${y(point.value)}" r="3.2"/>`; });
      const selected = chartSelection[sensor.key];
      const point = selected !== undefined ? points.find(point => point.sequence === selected) : null;
      if (point) { marks += `<path class="selection-guide" d="M${x(point.time)} ${top}V${bottom}"/>`; if (point.valid) marks += `<circle class="selected-dot" cx="${x(point.time)}" cy="${y(point.value)}" r="5.2"/>`; }
      marks += '</g>';
      marks += `<text x="${right}" y="246" text-anchor="end">Waktu penerimaan contoh</text><rect x="${left}" y="${top}" width="${right - left}" height="${bottom - top}" fill="transparent" class="chart-hit"/>`;
      svg.innerHTML = marks;
      const latest = points.at(-1);
      $('chart-value-' + sensor.key).textContent = latest.valid ? latest.value.toFixed(sensor.digits) : '—';
      if (point) {
        $('chart-detail-' + sensor.key).textContent = `${new Date(point.time).toLocaleTimeString('id-ID')} · #${point.sequence} · ${point.valid ? point.value.toFixed(sensor.digits) + ' ' + sensor.unit : 'Tidak valid / OFF'} · depth ${point.depthValid ? point.depth.toFixed(2) + ' m' : 'tidak valid'} · ${point.stable ? 'stabil' : 'belum stabil'} · SIM`;
      } else if (selected !== undefined) $('chart-detail-' + sensor.key).textContent = 'Titik terpilih sudah keluar dari rentang. Pilih titik baru.';
      function selectAt(event) {
        const bounds = svg.getBoundingClientRect(), px = (event.clientX - bounds.left) * width / bounds.width;
        if (px < left || px > right) return;
        const time = start + (px - left) / (right - left) * (end - start);
        const nearest = points.reduce((best, point) => Math.abs(point.time - time) < Math.abs(best.time - time) ? point : best, points[0]);
        chartSelection[sensor.key] = nearest.sequence; drawCharts();
      }
      svg.onpointermove = event => { if (event.pointerType === 'mouse' && !state.chartPaused) selectAt(event); };
      svg.onclick = selectAt;
      svg.onkeydown = event => { if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return; event.preventDefault(); const current = points.findIndex(point => point.sequence === chartSelection[sensor.key]); const next = Math.max(0, Math.min(points.length - 1, (current < 0 ? points.length - 1 : current) + (event.key === 'ArrowRight' ? 1 : -1))); chartSelection[sensor.key] = points[next].sequence; drawCharts(); };
    });
  }
  new ResizeObserver(drawCharts).observe($('charts'));
  function updateDepthStability() {
    const now = performance.now();
    if (!valid()) { state.depthHistory = []; state.depthStable = false; return; }
    state.depthHistory.push({ time: now, depth: state.depth });
    state.depthHistory = state.depthHistory.filter(point => now - point.time <= 60000);
    const period = Number($('stable-time').value) * 1000;
    const cutoff = now - period;
    const before = state.depthHistory.filter(point => point.time <= cutoff).at(-1);
    const window = state.depthHistory.filter(point => point.time >= cutoff);
    if (before) window.unshift(before);
    state.depthStable = !!before && window.length >= 2 && Math.max(...window.map(point => point.depth)) - Math.min(...window.map(point => point.depth)) <= .05;
  }
  setInterval(() => {
    const wasRunning = state.running;
    state.tick++; $('clock').textContent = new Date().toLocaleString('id-ID');
    if (valid()) { state.lastTelemetry = performance.now(); sensors.forEach(sensor => { if (sensor.on) sensor.lastSample = state.lastTelemetry; }); }
    if (state.running) {
      const step = state.snapshot[state.stepIndex]; const fraction = Math.min(1, (performance.now() - state.phaseStart) / 3000);
      if (['DIVE', 'SURFACE'].includes(step.type)) state.depth = state.startDepth + (step.value - state.startDepth) * fraction;
      if (step.type === 'HEADING') { state.yaw = step.value; $('yaw-input').value = step.value; }
      updateDepthStability();
      if (step.sampling && state.stepSamples < state.sampleCount && (step.sampleTiming !== 'after' || fraction >= 1) && sensors.every(sensor => sensor.on)) {
        state.samples.push({ depth: state.depth, values: sensors.map(sensor => valueOf(sensor).toFixed(sensor.digits)), count: 1, stable: state.depthStable, type: step.type, timing: step.sampleTiming ?? 'during' });
        state.stepSamples++;
        $('sample-rows').innerHTML = state.samples.map(row => `<tr><td>${row.depth.toFixed(2)} m<small> · ${row.type}</small></td>${row.values.map(value => `<td>${value}</td>`).join('')}<td class="${row.stable ? '' : 'warning'}">${row.stable ? 'Stabil · contoh' : 'BELUM STABIL · contoh'}</td></tr>`).join('');
      }
      if (fraction >= 1) {
        if (step.sampling && !sensors.every(sensor => sensor.on)) finishMission('FAILED', 'Sensor contoh OFF saat sampling');
        else if (!step.sampling || state.stepSamples >= state.sampleCount || step.sampleTiming !== 'after') {
          if (step.sampling && state.stepSamples < state.sampleCount) { state.incompleteSamples.push(state.stepIndex + 1); note('Sampling selama langkah selesai; kuota contoh belum terpenuhi, tidak memperpanjang gerakan.'); }
          nextStep();
        }
      }
    }
    if (!wasRunning) updateDepthStability();
    if (state.recorder && state.recorder.rows.length < 600) {
      const flags = sensors.map(s => valid() && s.on);
      state.recorder.rows.push(['SIMULATED', new Date().toISOString(), valid() ? state.depth.toFixed(3) : '', ...sensors.map((s, i) => flags[i] ? valueOf(s).toFixed(s.digits) : ''), valid(), ...flags, valid() ? state.yaw.toFixed(2) : '', valid() ? missionYaw().toFixed(2) : '', state.yawReference, state.yawReference ? state.yawOffset : 0, state.depthStable, valid(), state.running ? state.snapshot[state.stepIndex].id : '', state.running && state.snapshot[state.stepIndex].sampling ? state.snapshot[state.stepIndex].sampleTiming ?? 'during' : 'off', state.running ? performance.now() - state.phaseStart < 3000 ? 'MOTION' : 'AFTER_MOTION' : 'MANUAL_RECORD']);
    }
    if (state.recorder && state.recorder.rows.length >= 600) {
      if (state.running) finishMission('STOPPED', 'Batas 600 baris preview');
      else { stopRecord('LIMIT'); note('Rekaman contoh ditutup pada batas 600 baris.'); }
    }
    try {
      const gamepads = navigator.getGamepads ? [...navigator.getGamepads()].filter(Boolean) : [];
      $('gamepad-state').textContent = gamepads.length ? gamepads[0].id + ' · axes: ' + gamepads[0].axes.map(axis => axis.toFixed(2)).join(' / ') + ' · pemeriksaan saja' : 'Controller belum terdeteksi · tekan tombol controller untuk pemeriksaan';
    } catch { $('gamepad-state').textContent = 'Gamepad API tidak tersedia pada origin ini.'; }
    // --- FUNGSI DETEKSI TELEMETRI LIVE ROS 2 JETSON ---
    fetchLiveTelemetry();
    if (state.tick % 2 === 0) captureChartPoint();
    renderTelemetry(); drawCharts();
  }, 500);

  let isLiveConnected = false;
  async function fetchLiveTelemetry() {
    try {
      const res = await fetch('http://127.0.0.1:8090/api/state', { cache: 'no-store' });
      if (!res.ok) throw new Error('Gateway offline');
      const data = await res.json();

      // Jika berhasil, beralih ke Mode LIVE
      if (!isLiveConnected) {
        isLiveConnected = true;
        const badge = document.querySelector('.badge.sim');
        if (badge) {
          badge.textContent = '● LIVE · ROS 2';
          badge.style.backgroundColor = '#1e3a2f';
          badge.style.color = '#a3d8b7';
        }
      }

      // 1. Data Navigasi & Sikap Asli dari Teensy 4.1
      if (data.streams && data.streams.navigation && data.streams.navigation.data) {
        const nav = data.streams.navigation.data;
        if (nav.depth !== null && nav.depth !== undefined) state.depth = nav.depth;
        if (nav.roll !== null && nav.roll !== undefined) state.roll = nav.roll;
        if (nav.pitch !== null && nav.pitch !== undefined) state.pitch = nav.pitch;
        if (nav.yaw !== null && nav.yaw !== undefined) state.yaw = nav.yaw;
      }

      // 2. Data Kualitas Air Asli dari ESP32-S3 (Atlas EZO)
      if (data.streams && data.streams.water_quality && data.streams.water_quality.data) {
        const wq = data.streams.water_quality.data;
        const sPh = sensors.find(s => s.key === 'ph');
        const sDo = sensors.find(s => s.key === 'do');
        const sEc = sensors.find(s => s.key === 'ec');
        const sTemp = sensors.find(s => s.key === 'temp');

        if (sPh && wq.ph !== null && wq.ph !== undefined) sPh.base = wq.ph;
        if (sDo && wq.dissolved_oxygen !== null && wq.dissolved_oxygen !== undefined) sDo.base = wq.dissolved_oxygen;
        if (sEc && wq.conductivity !== null && wq.conductivity !== undefined) sEc.base = wq.conductivity;
        if (sTemp && wq.temperature !== null && wq.temperature !== undefined) sTemp.base = wq.temperature;
      }

      // 3. Data Daya Baterai & INA226
      if (data.streams && data.streams.power_thruster && data.streams.power_thruster.data) {
        const pwr = data.streams.power_thruster.data;
        const pwrEl = document.querySelector('[data-power-value="24.8 V"]');
        if (pwrEl && pwr.voltage !== null && pwr.voltage !== undefined) pwrEl.textContent = pwr.voltage.toFixed(1) + ' V';
      }

    } catch (e) {
      // Jika gateway tidak menyala, tetap berjalan mulus di mode Simulasi
      if (isLiveConnected) {
        isLiveConnected = false;
        const badge = document.querySelector('.badge.sim');
        if (badge) {
          badge.textContent = 'SIMULASI · OFFLINE';
          badge.style.backgroundColor = '#2b281e';
          badge.style.color = 'var(--amber)';
        }
      }
    }
  }
  $('clock').textContent = new Date().toLocaleString('id-ID');
  setNavigationView(); setMode('IDLE'); renderSteps(); renderTelemetry(); fetchLiveTelemetry(); note('Console siap · memeriksa koneksi telemetri gateway.');
})();
