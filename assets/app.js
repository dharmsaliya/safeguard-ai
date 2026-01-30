const socket = io();
let alarmActive = false;
let sirenInterval, countdownInterval;
let countdownVal = 10;
let qrGenerated = false;

const AudioContext = window.AudioContext || window.webkitAudioContext;
const audioCtx = new AudioContext();

// --- LOGGER FUNCTION ---
function addLog(msg, type = "normal") {
  const container = document.getElementById("log-container");
  const entry = document.createElement("div");
  entry.className = "log-entry";

  const time = new Date().toLocaleTimeString();
  let colorClass = "";
  if (type === "alert") colorClass = "log-alert";
  if (type === "info") colorClass = "log-info";

  entry.innerHTML = `<span class="log-time">[${time}]</span> <span class="${colorClass}">${msg}</span>`;
  container.prepend(entry); // Add to top
}

// Init Log
addLog("System Boot Sequence Initiated...", "info");
addLog("Sensors Online: Accel, Gyro, Temp", "info");

function playSiren() {
  if (!alarmActive) return;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.type = 'square';
  osc.frequency.setValueAtTime(800, audioCtx.currentTime);
  osc.frequency.linearRampToValueAtTime(600, audioCtx.currentTime + 0.4);
  gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
  gain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.4);
  osc.start();
  osc.stop(audioCtx.currentTime + 0.4);
}

function generateQR(impact, posture, temp) {
  const qrDiv = document.getElementById("qrcode");
  qrDiv.innerHTML = "";
  const safePosture = posture.replace(/[^\w\s]/gi, '');
  const reportText = `MEDICAL ALERT\nID: PT-8842\nBLOOD: O+\n-- VITALS --\nTEMP: ${temp}C\nIMPACT: ${impact}G\nPOS: ${safePosture}\nTIME: ${new Date().toLocaleTimeString()}`;
  new QRCode(qrDiv, { text: reportText, width: 180, height: 180, colorDark: "#000000", colorLight: "#ffffff", correctLevel: QRCode.CorrectLevel.M });
}

function triggerAlarm(impact, posture, temp) {
  if (alarmActive) return;
  alarmActive = true;
  qrGenerated = false;

  addLog(`CRITICAL: Fall Detected! Impact: ${impact}G`, "alert"); // LOG EVENT

  document.getElementById('alarm-overlay').style.display = "flex";
  document.getElementById('main-ui').style.filter = "blur(8px)";
  document.getElementById('timer-section').style.display = "flex";
  document.getElementById('qr-section').style.display = "none";

  document.getElementById('d-impact').innerText = impact + " G";
  document.getElementById('d-posture').innerText = posture;
  document.getElementById('d-temp').innerText = temp + " °C";

  countdownVal = 10;
  document.getElementById('countdown').innerText = countdownVal;

  countdownInterval = setInterval(() => {
    countdownVal--;
    document.getElementById('countdown').innerText = countdownVal;

    // 3. TIMEOUT REACHED -> SHOW QR & CALL 911
    if (countdownVal <= 0) {
      clearInterval(countdownInterval);
      clearInterval(sirenInterval);

      document.getElementById('timer-section').style.display = "none";
      document.getElementById('qr-section').style.display = "flex";
      addLog("Emergency Alert Broadcast Sent (QR Generated)", "alert");

      // --- NEW: TRIGGER TWILIO CALL ---
      addLog("Initiating Uplink to Emergency Dispatch...", "alert");
      fetch('/emergency_call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ impact: impact, temp: temp })
      }).then(res => res.json()).then(data => {
        if (data.status === 'success') {
          addLog("VOICE CALL CONNECTED", "info");
        } else {
          addLog("CALL FAILED: " + data.msg, "alert");
        }
      });
      // --------------------------------

      if (!qrGenerated) {
        qrGenerated = true;
        setTimeout(() => { generateQR(impact, posture, temp); }, 100);
      }
    }
  }, 1000);

  if (audioCtx.state === 'suspended') audioCtx.resume();
  sirenInterval = setInterval(playSiren, 600);
}

function cancelAlarm() {
  alarmActive = false;
  qrGenerated = false;
  clearInterval(sirenInterval);
  clearInterval(countdownInterval);
  document.getElementById('alarm-overlay').style.display = "none";
  document.getElementById('main-ui').style.filter = "none";
  addLog("Alarm Cancelled by User (False Positive Marked)", "info"); // LOG EVENT
}

function startCalibration() {
  fetch('/calibrate', { method: 'POST' });
  document.getElementById('btn-calibrate').innerText = "Calibrating...";
  document.getElementById('calib-msg').style.display = "block";
  addLog("Calibration Routine Started...", "info"); // LOG EVENT
}

// --- NEW HELPER: Save Incident ---
function saveToHistory(impact, posture, temp) {
  const newRecord = {
    date: new Date().toLocaleString(),
    type: "FALL DETECTED",
    impact: impact,
    posture: posture,
    temp: temp
  };

  // Get existing history or empty array
  const history = JSON.parse(localStorage.getItem('safeguard_history')) || [];

  // Add new record to the TOP of the list
  history.unshift(newRecord);

  // Save back to storage
  localStorage.setItem('safeguard_history', JSON.stringify(history));
}

function triggerAlarm(impact, posture, temp) {
  if (alarmActive) return;
  alarmActive = true;
  qrGenerated = false;

  addLog(`CRITICAL: Fall Detected! Impact: ${impact}G`, "alert");

  // === SAVE TO HISTORY HERE ===
  saveToHistory(impact, posture, temp);
  // ============================

  document.getElementById('alarm-overlay').style.display = "flex";
  document.getElementById('main-ui').style.filter = "blur(8px)";
  document.getElementById('timer-section').style.display = "flex";
  document.getElementById('qr-section').style.display = "none";

  document.getElementById('d-impact').innerText = impact + " G";
  document.getElementById('d-posture').innerText = posture;
  document.getElementById('d-temp').innerText = temp + " °C";

  // ... [Rest of triggerAlarm logic stays the same] ...

  countdownVal = 10;
  document.getElementById('countdown').innerText = countdownVal;

  countdownInterval = setInterval(() => {
    countdownVal--;
    document.getElementById('countdown').innerText = countdownVal;

    if (countdownVal <= 0) {
      clearInterval(countdownInterval);
      clearInterval(sirenInterval);
      document.getElementById('timer-section').style.display = "none";
      document.getElementById('qr-section').style.display = "flex";
      addLog("Emergency Alert Broadcast Sent (QR Generated)", "alert");

      if (!qrGenerated) {
        qrGenerated = true;
        setTimeout(() => { generateQR(impact, posture, temp); }, 100);
      }
    }
  }, 1000);

  if (audioCtx.state === 'suspended') audioCtx.resume();
  sirenInterval = setInterval(playSiren, 600);
}

socket.on('movement', (data) => {
  document.getElementById('main-status').innerText = data.status;
  if (data.threshold) document.getElementById('sensitivity-val').innerText = (data.threshold * 100) + "%";

  if (data.status.includes("FALL") && !alarmActive) {
    const imp = data.impact || 4.2;
    const pos = data.posture || "Face Down";
    const temp = data.temp || 36.5;
    triggerAlarm(imp, pos, temp);
  }
});

socket.on('calibration_done', (data) => {
  document.getElementById('user-profile').innerText = data.profile;
  document.getElementById('sensitivity-val').innerText = (data.threshold * 100) + "%";
  document.getElementById('btn-calibrate').innerText = "Recalibrate";
  document.getElementById('calib-msg').style.display = "none";
  addLog(`Calibration Complete. Profile: ${data.profile}`, "info"); // LOG EVENT
});

const ctx = document.getElementById('sensorChart').getContext('2d');
const chart = new Chart(ctx, {
  type: 'line',
  data: { labels: Array(30).fill(''), datasets: [{ label: 'Vertical Force', data: Array(30).fill(0), borderColor: '#00d2be', borderWidth: 2, pointRadius: 0, tension: 0.3 }] },
  options: { animation: false, scales: { y: { min: -2, max: 2, display: false }, x: { display: false } }, plugins: { legend: { display: false } } }
});
socket.on('sample', (data) => {
  chart.data.datasets[0].data.shift();
  chart.data.datasets[0].data.push(data.z);
  chart.update();
});