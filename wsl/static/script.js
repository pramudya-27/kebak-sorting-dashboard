// Configuration
const WS_URL = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + (window.location.host || 'localhost:8000') + '/ws/detections';
const API_URL = (window.location.protocol === 'https:' ? 'https://' : 'http://') + (window.location.host || 'localhost:8000') + '/api/v1';

// Global State
let ws = null;
let latestDetection = null;
let detectionCount = 0;
let detectionHistory = [];
const MAX_HISTORY = 50;

// Canvases
const camera0Canvas = document.getElementById('camera0Canvas');
const camera1Canvas = document.getElementById('camera1Canvas');
const ctx0 = camera0Canvas.getContext('2d');
const ctx1 = camera1Canvas.getContext('2d');

let radarAngle = 0;

// -------------------------------------------------------------
// 1. SORTING SUMMARY LOGIC
// -------------------------------------------------------------
let statsJantan = 0;
let statsBetina = 0;
let statsSehat = 0;
let statsTidakSehat = 0;

let inspectionSession = {
    active: false,
    startTime: 0,
    lastFrameTime: 0,
    
    jantanConfSum: 0,
    betinaConfSum: 0,
    sehatConfSum: 0,
    sakitConfSum: 0,
    
    jantanCount: 0,
    betinaCount: 0,
    sehatCount: 0,
    sakitCount: 0,

    jantanIntegral: 0,
    betinaIntegral: 0,
    sehatIntegral: 0,
    sakitIntegral: 0,

    concluded: false
};

function showCurrentStatus(text, type = 'info', timeString = null) {
    const banner = document.getElementById('currentResultBanner');
    const textEl = document.getElementById('currentResultText');
    if (!banner || !textEl) return;
    
    textEl.innerHTML = text;
    
    if (type === 'success') {
        banner.style.background = 'rgba(34, 197, 94, 0.15)';
        banner.style.borderColor = '#22c55e';
        textEl.style.color = '#22c55e';
    } else if (type === 'warning') {
        banner.style.background = 'rgba(234, 179, 8, 0.15)';
        banner.style.borderColor = '#eab308';
        textEl.style.color = '#eab308';
    } else {
        banner.style.background = 'rgba(14, 165, 233, 0.15)';
        banner.style.borderColor = '#0ea5e9';
        textEl.style.color = '#0ea5e9';
    }

    if (timeString) {
        const concTimeEl = document.getElementById('conclusionTime');
        if (concTimeEl) concTimeEl.textContent = timeString;
    }
}

function concludeSession() {
    if (inspectionSession.concluded) return;
    inspectionSession.concluded = true;
    
    const timeTaken = ((performance.now() - inspectionSession.startTime) / 1000).toFixed(2);
    
    // Average Calculation
    const avgJantan = inspectionSession.jantanCount > 0 ? (inspectionSession.jantanConfSum / inspectionSession.jantanCount * 100).toFixed(1) : 0;
    const avgBetina = inspectionSession.betinaCount > 0 ? (inspectionSession.betinaConfSum / inspectionSession.betinaCount * 100).toFixed(1) : 0;
    const avgSehat = inspectionSession.sehatCount > 0 ? (inspectionSession.sehatConfSum / inspectionSession.sehatCount * 100).toFixed(1) : 0;
    const avgSakit = inspectionSession.sakitCount > 0 ? (inspectionSession.sakitConfSum / inspectionSession.sakitCount * 100).toFixed(1) : 0;

    // Jangan pernah UNKNOWN, selalu pilih yang dominan (jika 0, default Jantan & Sehat)
    let finalSex = (inspectionSession.jantanIntegral >= inspectionSession.betinaIntegral) ? "JANTAN" : "BETINA";
    let finalHealth = (inspectionSession.sehatIntegral >= inspectionSession.sakitIntegral) ? "SEHAT" : "TIDAK SEHAT";
    
    if (false) { // obsolete block to maintain indentation/structure
        // nothing
    } else {
        if (finalSex === "JANTAN") statsJantan++;
        if (finalSex === "BETINA") statsBetina++;
        if (finalHealth === "SEHAT") statsSehat++;
        if (finalHealth === "TIDAK SEHAT") statsTidakSehat++;
        
        document.getElementById('countJantan').textContent = statsJantan;
        document.getElementById('countBetina').textContent = statsBetina;
        document.getElementById('countSehat').textContent = statsSehat;
        document.getElementById('countTidakSehat').textContent = statsTidakSehat;
        
        let chosenSexAvg = finalSex === "JANTAN" ? avgJantan : avgBetina;
        let chosenSexInt = finalSex === "JANTAN" ? inspectionSession.jantanIntegral : inspectionSession.betinaIntegral;
        let chosenHealthAvg = finalHealth === "SEHAT" ? avgSehat : avgSakit;
        let chosenHealthInt = finalHealth === "SEHAT" ? inspectionSession.sehatIntegral : inspectionSession.sakitIntegral;

        const verdictHTML = `KEPITING ${finalSex} <span style="font-size:1.2rem;">(Avg Conf: ${chosenSexAvg}% | Integral: ${chosenSexInt.toFixed(2)})</span><br><span style="font-size:1.2rem; color:#f8fafc;">Status: ${finalHealth} (Avg Conf: ${chosenHealthAvg}% | Integral: ${chosenHealthInt.toFixed(2)}) | Disimpulkan dalam ${timeTaken} detik</span>`;
        showCurrentStatus(verdictHTML, 'success', `${timeTaken}s`);
    }
}

function updateConclusion(detection) {
    const camera0Dets = detection.camera0?.detections || [];
    const camera1Dets = detection.camera1?.detections || [];
    const detections = detection.fused_detections || [...camera0Dets, ...camera1Dets];

    let foundCore = false;
    let maxJantanConf = 0, maxBetinaConf = 0, maxSakitConf = 0, maxSehatConf = 0;

    if (detections.length > 0) {
        detections.forEach(det => {
            const cls = (det.class_name || det.class || '').toLowerCase();
            const conf = det.confidence || 0;
            
            if (cls.includes('jantan')) { maxJantanConf = Math.max(maxJantanConf, conf); foundCore = true; }
            else if (cls.includes('betina')) { maxBetinaConf = Math.max(maxBetinaConf, conf); foundCore = true; }
            
            if (cls.includes('patah') || cls.includes('cacat') || cls.includes('hilang') || 
                cls.includes('unhealthy') || cls.includes('sakit') || cls.includes('dead')) {
                maxSakitConf = Math.max(maxSakitConf, conf); foundCore = true;
            } else if (cls.includes('healthy') || cls.includes('sehat')) {
                maxSehatConf = Math.max(maxSehatConf, conf); foundCore = true;
            } else if (cls.includes('crab') || cls.includes('kepiting')) {
                foundCore = true;
            }
        });
    }

    let currentTime = performance.now();

    if (foundCore) {
        if (!inspectionSession.active) {
            inspectionSession.active = true;
            inspectionSession.jantanConfSum = 0;
            inspectionSession.betinaConfSum = 0;
            inspectionSession.sehatConfSum = 0;
            inspectionSession.sakitConfSum = 0;
            inspectionSession.jantanCount = 0;
            inspectionSession.betinaCount = 0;
            inspectionSession.sehatCount = 0;
            inspectionSession.sakitCount = 0;
            inspectionSession.jantanIntegral = 0;
            inspectionSession.betinaIntegral = 0;
            inspectionSession.sehatIntegral = 0;
            inspectionSession.sakitIntegral = 0;
            
            inspectionSession.concluded = false;
            inspectionSession.startTime = currentTime;
            inspectionSession.lastFrameTime = currentTime;
            showCurrentStatus("INSPECTING CRAB...", 'info', '0.00s');
        }
        
        let dt = (currentTime - inspectionSession.lastFrameTime) / 1000;
        if (dt > 1.0) dt = 0.033; // Cap dt for first frame or massive lag
        inspectionSession.lastFrameTime = currentTime;
        
        if (!inspectionSession.concluded) {
            if (maxJantanConf > 0) { inspectionSession.jantanConfSum += maxJantanConf; inspectionSession.jantanCount++; }
            if (maxBetinaConf > 0) { inspectionSession.betinaConfSum += maxBetinaConf; inspectionSession.betinaCount++; }
            if (maxSakitConf > 0) { inspectionSession.sakitConfSum += maxSakitConf; inspectionSession.sakitCount++; }
            if (maxSehatConf > 0) { inspectionSession.sehatConfSum += maxSehatConf; inspectionSession.sehatCount++; }

            inspectionSession.jantanIntegral += maxJantanConf * dt;
            inspectionSession.betinaIntegral += maxBetinaConf * dt;
            inspectionSession.sakitIntegral += maxSakitConf * dt;
            inspectionSession.sehatIntegral += maxSehatConf * dt;
            
            // Naikkan threshold agar tidak langsung menyimpulkan
            let sexIntegralReady = (inspectionSession.jantanIntegral > 1.5 || inspectionSession.betinaIntegral > 1.5);
            let healthIntegralReady = (inspectionSession.sehatIntegral > 1.5 || inspectionSession.sakitIntegral > 1.5);
            
            let runningTime = ((currentTime - inspectionSession.startTime) / 1000).toFixed(2);
            // Tetap update UI timer
            showCurrentStatus("MENGANALISA KEPITING...", 'info', `${runningTime}s`);

            if (sexIntegralReady && healthIntegralReady) {
                // Begitu terdeteksi semua dengan mass integral cukup, simpulkan
                concludeSession();
            }
        }
    } else {
        if (inspectionSession.active) {
            // Waktu sejak terakhir kali melihat kepiting
            let timeWithoutDetection = currentTime - inspectionSession.lastFrameTime;
            
            // Jika kepiting tidak terlihat selama lebih dari 500 ms, anggap sudah diangkat
            if (timeWithoutDetection >= 500) {
                // Sesi benar-benar ditutup, kepiting berikutnya akan jadi sesi baru
                // Paksa concludeSession() jika diangkat sebelum selesai untuk menjumlahkan datanya
                if (!inspectionSession.concluded) {
                    concludeSession();
                }
                inspectionSession.active = false;
                showCurrentStatus("WAITING FOR CRAB...", 'info', '0.00s');
            }
        }
    }
}

// -------------------------------------------------------------
// 2. WEBSOCKET & BACKEND CONNECTION
// -------------------------------------------------------------
function connectWebSocket() {
    console.log('Connecting to Ocean Vision WebSocket at', WS_URL);
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);

        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send('ping');
            }
        }, 20000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type !== 'keepalive') {
                handleDetection(data);
            }
        } catch (err) {
            console.error('Error parsing WebSocket message:', err);
        }
    };

    ws.onerror = (err) => {
        console.warn('WebSocket connection error:', err);
        updateConnectionStatus(false);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
        setTimeout(connectWebSocket, 4000);
    };
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    if (connected) {
        statusEl.textContent = 'CONNECTED';
        statusEl.classList.remove('disconnected');
    } else {
        statusEl.textContent = 'OFFLINE';
        statusEl.classList.add('disconnected');
    }
}

// -------------------------------------------------------------
// 3. DETECTION HANDLING & UI UPDATES
// -------------------------------------------------------------
function handleDetection(detection) {
    // ---------------------------------------------------------
    // FILTER: If no core crab detected (Jantan/Betina/Healthy), 
    // ignore isolated part detections to prevent false positives.
    // ---------------------------------------------------------
    let hasCoreCrab = false;
    const coreClasses = ['jantan', 'betina', 'healthy', 'unhealthy', 'crab', 'kepiting'];
    
    const camera0Dets = detection.camera0?.detections || [];
    const camera1Dets = detection.camera1?.detections || [];
    const allDets = detection.fused_detections || [...camera0Dets, ...camera1Dets];
    
    for (let det of allDets) {
        const cls = (det.class_name || det.class || '').toLowerCase();
        if (coreClasses.some(core => cls.includes(core))) {
            hasCoreCrab = true;
            break;
        }
    }

    if (!hasCoreCrab) {
        if (detection.fused_detections) detection.fused_detections = [];
        if (detection.camera0?.detections) detection.camera0.detections = [];
        if (detection.camera1?.detections) detection.camera1.detections = [];
    }

    latestDetection = detection;
    detectionCount++;

    detectionHistory.push(detection);
    if (detectionHistory.length > MAX_HISTORY) detectionHistory.shift();

    updateDetectionList(detection);
    updateStatistics();
    drawDetections(detection);

    // Update Conclusion Widget
    updateConclusion(detection);
}

function updateDetectionList(detection) {
    const listEl = document.getElementById('detectionList');
    const camera0Dets = detection.camera0?.detections || [];
    const camera1Dets = detection.camera1?.detections || [];
    const detections = detection.fused_detections || [...camera0Dets, ...camera1Dets];

    if (detections.length === 0) {
        listEl.innerHTML = `
            <div class="no-data">
                <i class="fas fa-water"></i>
                <span>Clear waters: No marine targets detected</span>
            </div>
        `;
        return;
    }

    listEl.innerHTML = '';
    detections.slice(0, 10).forEach(det => {
        const item = document.createElement('div');
        item.className = 'detection-item';

        const models = det.models || [det.model || 'YOLOv8'];
        const modelBadges = models.map(m => `<span class="model-badge"><i class="fas fa-brain"></i> ${m}</span>`).join(' ');

        item.innerHTML = `
            <div class="detection-header">
                <span class="class-name"><i class="fas fa-crab"></i> ${det.class_name || det.class || 'Marine Target'}</span>
                <span class="confidence-badge">${(det.confidence * 100).toFixed(1)}%</span>
            </div>
            <div class="detection-meta">
                ${modelBadges}
                ${det.num_models ? `<span><i class="fas fa-layer-group"></i> ${det.num_models} models fused</span>` : ''}
            </div>
        `;
        listEl.appendChild(item);
    });
}

function updateStatistics() {
    document.getElementById('totalDetections').textContent = detectionCount;

    if (latestDetection) {
        const fps = latestDetection.inference_time ? (1 / latestDetection.inference_time).toFixed(1) : '30.0';
        document.getElementById('currentFPS').textContent = fps;

        const camera0Dets = latestDetection.camera0?.detections || [];
        const camera1Dets = latestDetection.camera1?.detections || [];
        const detections = latestDetection.fused_detections || [...camera0Dets, ...camera1Dets];

        if (detections.length > 0) {
            const avgConf = detections.reduce((sum, d) => sum + d.confidence, 0) / detections.length;
            document.getElementById('avgConfidence').textContent = (avgConf * 100).toFixed(1) + '%';
        }
    }

    // Fetch live API statistics from server
    fetch(`${API_URL}/stats`)
        .then(res => res.json())
        .then(data => {
            if (data.system) {
                updateModelStats(data.system);
            }
        })
        .catch(() => {
            // Silently fail if API endpoint isn't responsive
        });
}

function updateModelStats(stats) {
    const modelStatsEl = document.getElementById('modelStats');
    if (!stats.models || stats.models.length === 0) {
        // Show default active model indicators if no dynamic models returned yet
        modelStatsEl.innerHTML = `
            <div class="model-stat-card">
                <div class="model-stat-title"><span>Gender Detector (YOLOv8)</span> <span>2.4 ms</span></div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: 85%;"></div></div>
            </div>
            <div class="model-stat-card">
                <div class="model-stat-title"><span>Completeness Seg (YOLOv8-Seg)</span> <span>4.1 ms</span></div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: 70%;"></div></div>
            </div>
            <div class="model-stat-card">
                <div class="model-stat-title"><span>Health Detector (YOLO11)</span> <span>3.8 ms</span></div>
                <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: 92%;"></div></div>
            </div>
        `;
        return;
    }

    modelStatsEl.innerHTML = '';
    stats.models.forEach(m => {
        const infTime = m.avg_inference_time_ms ? m.avg_inference_time_ms.toFixed(1) : '3.2';
        const percentage = Math.min(100, Math.max(20, 100 - parseFloat(infTime) * 5));
        const item = document.createElement('div');
        item.className = 'model-stat-card';
        item.innerHTML = `
            <div class="model-stat-title">
                <span><i class="fas fa-microchip"></i> ${m.model_name || m.name}</span>
                <span>${infTime} ms | ${m.total_detections || 0} Dets</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${percentage}%;"></div>
            </div>
        `;
        modelStatsEl.appendChild(item);
    });
}

function formatUptime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    return h > 0 ? `${h}h ${m}m` : (m > 0 ? `${m}m ${s}s` : `${s}s`);
}

// -------------------------------------------------------------
// 4. CANVAS DRAWING
// -------------------------------------------------------------
function resizeCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const w = Math.floor(canvas.clientWidth * dpr);
    const h = Math.floor(canvas.clientHeight * dpr);
    if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
    }
}

function drawOfflineRadar(canvas, ctx, titleText) {
    resizeCanvas(canvas);
    const w = canvas.width;
    const h = canvas.height;
    const cx = w / 2;
    const cy = h / 2;
    
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, w, h);

    // Simple grid lines
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx, 0); ctx.lineTo(cx, h);
    ctx.moveTo(0, cy); ctx.lineTo(w, cy);
    ctx.stroke();

    // Concentric circles
    const radius = Math.min(w, h) * 0.4;
    for (let r = 0.25; r <= 1; r += 0.25) {
        ctx.beginPath();
        ctx.arc(cx, cy, radius * r, 0, Math.PI * 2);
        ctx.stroke();
    }

    // Scanning line
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(radarAngle);
    ctx.strokeStyle = 'rgba(14, 165, 233, 0.5)';
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.lineTo(radius, 0);
    ctx.stroke();
    ctx.restore();

    // Center Text Overlay
    ctx.font = `${Math.max(14, Math.round(16 * (window.devicePixelRatio || 1)))}px 'Plus Jakarta Sans', sans-serif`;
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.textAlign = 'center';
    ctx.fillText(titleText || 'WAITING FOR SIGNAL...', cx, cy + radius + 30);
}

function drawBoxes(ctx, detections, scaleX, scaleY) {
    const dpr = window.devicePixelRatio || 1;
    const fontSize = Math.max(12, Math.round(14 * dpr));
    ctx.font = `600 ${fontSize}px 'Plus Jakarta Sans', sans-serif`;
    ctx.textBaseline = 'top';
    ctx.textAlign = 'left';

    detections.forEach(det => {
        const [x1, y1, x2, y2] = det.bbox;
        const rx = x1 * scaleX;
        const ry = y1 * scaleY;
        const rw = (x2 - x1) * scaleX;
        const rh = (y2 - y1) * scaleY;

        const clsLower = (det.class_name || det.class || '').toLowerCase();
        
        ctx.strokeStyle = '#0ea5e9';
        ctx.lineWidth = Math.max(2, Math.round(3 * dpr));

        if (det.mask_polygons && det.mask_polygons.length > 0) {
            // Draw polygons if available
            
            const isJantan = clsLower.includes('jantan');
            const isBetina = clsLower.includes('betina');
            
            if (isJantan) {
                ctx.strokeStyle = '#38bdf8';
                ctx.fillStyle = 'rgba(56, 189, 248, 0.25)';
            } else if (isBetina) {
                ctx.strokeStyle = '#ec4899';
                ctx.fillStyle = 'rgba(236, 72, 153, 0.25)';
            } else {
                ctx.strokeStyle = '#0ea5e9';
                ctx.fillStyle = 'rgba(14, 165, 233, 0.2)';
            }

            ctx.beginPath();
            det.mask_polygons.forEach(poly => {
                if (poly.length > 0) {
                    ctx.moveTo(poly[0][0] * scaleX, poly[0][1] * scaleY);
                    for (let i = 1; i < poly.length; i++) {
                        ctx.lineTo(poly[i][0] * scaleX, poly[i][1] * scaleY);
                    }
                    ctx.closePath();
                }
            });
            ctx.stroke();
            ctx.fill();
        } else if (clsLower.includes('jantan') || clsLower.includes('betina')) {
            // Draw custom lines for Jantan / Betina to avoid full bounding box
            const isJantan = clsLower.includes('jantan');
            ctx.strokeStyle = isJantan ? '#38bdf8' : '#ec4899'; // Blue for Jantan, Pink for Betina
            
            ctx.beginPath();
            if (isJantan) {
                // Jantan: V shape (pointed abdomen)
                ctx.moveTo(rx, ry);
                ctx.lineTo(rx + rw / 2, ry + rh);
                ctx.lineTo(rx + rw, ry);
            } else {
                // Betina: U shape (rounded abdomen)
                ctx.moveTo(rx, ry);
                ctx.bezierCurveTo(rx, ry + rh * 1.2, rx + rw, ry + rh * 1.2, rx + rw, ry);
            }
            ctx.stroke();
            
            // Optional: light fill
            ctx.fillStyle = isJantan ? 'rgba(56, 189, 248, 0.15)' : 'rgba(236, 72, 153, 0.15)';
            ctx.fill();
        } else {
            // Solid Bounding Box for other classes
            ctx.strokeRect(rx, ry, rw, rh);
        }

        // Label Badge Background
        const label = `${det.class_name || det.class} ${(det.confidence * 100).toFixed(0)}%`;
        const pad = 6 * dpr;
        const tWidth = ctx.measureText(label).width;
        const tHeight = fontSize;
        const bgY = Math.max(ry - tHeight - pad * 2, 0);

        ctx.fillStyle = '#0ea5e9';
        ctx.fillRect(rx, bgY, tWidth + pad * 2, tHeight + pad);
        
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, rx + pad, bgY + pad / 2);
    });
}

function drawDetections(detection) {
    const camera0Dets = detection.camera0?.detections || detection.fused_detections || [];
    const camera1Dets = detection.camera1?.detections || [];

    resizeCanvas(camera0Canvas);
    resizeCanvas(camera1Canvas);

    const frameW = detection.frame_width || 640;
    const frameH = detection.frame_height || 480;
    const scaleX = camera0Canvas.width / frameW;
    const scaleY = camera0Canvas.height / frameH;

    // Draw Camera 0
    if (detection.frame_base64 || (detection.camera_frames && detection.camera_frames[0])) {
        const b64 = detection.frame_base64 || detection.camera_frames[0];
        const img = new Image();
        img.onload = () => {
            ctx0.drawImage(img, 0, 0, camera0Canvas.width, camera0Canvas.height);
            if (camera0Dets.length > 0) drawBoxes(ctx0, camera0Dets, scaleX, scaleY);
        };
        img.src = b64.startsWith('data:') ? b64 : 'data:image/jpeg;base64,' + b64;
    } else {
        drawOfflineRadar(camera0Canvas, ctx0, 'CAMERA BAWAH // STANDBY');
        if (camera0Dets.length > 0) drawBoxes(ctx0, camera0Dets, scaleX, scaleY);
    }

    // Draw Camera 1
    if (detection.camera_frames && detection.camera_frames[1]) {
        const b64 = detection.camera_frames[1];
        const img = new Image();
        img.onload = () => {
            ctx1.drawImage(img, 0, 0, camera1Canvas.width, camera1Canvas.height);
            if (camera1Dets.length > 0) drawBoxes(ctx1, camera1Dets, scaleX, scaleY);
        };
        img.src = b64.startsWith('data:') ? b64 : 'data:image/jpeg;base64,' + b64;
    } else {
        drawOfflineRadar(camera1Canvas, ctx1, 'CAMERA ATAS // STANDBY');
        if (camera1Dets.length > 0) drawBoxes(ctx1, camera1Dets, scaleX, scaleY);
    }
}


// -------------------------------------------------------------
// 5. INITIALIZATION
// -------------------------------------------------------------
function init() {

    // Radar animation loop for canvases when offline
    setInterval(() => {
        radarAngle += 0.03;
        if (!latestDetection) {
            drawOfflineRadar(camera0Canvas, ctx0, 'CAMERA BAWAH // STANDBY');
            drawOfflineRadar(camera1Canvas, ctx1, 'CAMERA ATAS // STANDBY');
        }
    }, 50);

    // Randomize depth meter slightly
    setInterval(() => {
        const depth = Math.floor(480 + Math.random() * 6);
        document.getElementById('depthMeter').textContent = `${depth} M`;
    }, 3000);
                
    // Connect WS
    connectWebSocket();

    // Periodic stats fetch
    setInterval(updateStatistics, 5000);

    // Initial model stats rendering
    updateModelStats({});
}

window.addEventListener('load', init);
