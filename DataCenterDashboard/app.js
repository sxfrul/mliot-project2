const ctx = document.getElementById('historyChart').getContext('2d');
let mqttClient = null;
let simInterval = null;
let packetsReceived = 0;
let startTime = Date.now();

let logEntries = [];

setInterval(() => {
  const elapsed = Date.now() - startTime;
  const hrs = String(Math.floor(elapsed / 3600000)).padStart(2, '0');
  const mins = String(Math.floor((elapsed % 3600000) / 60000)).padStart(2, '0');
  const secs = String(Math.floor((elapsed % 60000) / 1000)).padStart(2, '0');
  document.getElementById('system-uptime').textContent = `${hrs}:${mins}:${secs}`;
}, 1000);

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      { label: 'Temperature', data: [], borderColor: '#f43f5e', borderWidth: 2, tension: 0.2, fill: false, pointRadius: 1, pointHoverRadius: 4, yAxisID: 'y' },
      { label: 'Humidity', data: [], borderColor: '#38bdf8', borderWidth: 2, tension: 0.2, fill: false, pointRadius: 1, pointHoverRadius: 4, yAxisID: 'y1' }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    scales: {
      y: { type: 'linear', position: 'left', grid: { color: 'rgba(255, 255, 255, 0.02)' }, ticks: { color: '#f43f5e', font: { size: 10 } } },
      y1: { type: 'linear', position: 'right', grid: { display: false }, ticks: { color: '#38bdf8', font: { size: 10 } } },
      x: { grid: { display: false }, ticks: { color: 'rgba(255, 255, 255, 0.2)', font: { size: 9 } } }
    },
    plugins: { legend: { display: false } }
  }
});

document.getElementById('btn-fake').addEventListener('click', (e) => {
    if (simInterval) {
        clearInterval(simInterval);
        simInterval = null;
        e.target.textContent = "Start Simulation Stream";
        e.target.className = "w-full btn-gradient bg-indigo-600 hover:bg-indigo-500 text-white py-2.5 rounded text-xs font-semibold tracking-wider transition-colors";
    } else {
        e.target.textContent = "Halt Simulation Stream";
        e.target.className = "w-full btn-gradient bg-rose-600 hover:bg-rose-500 text-white py-2.5 rounded text-xs font-semibold tracking-wider transition-colors";
        simInterval = setInterval(() => {
            const temp = (25 + Math.random() * 10).toFixed(1);
            const hum = (40 + Math.random() * 20).toFixed(1);
            const smoke = Math.random() > 0.92 ? 1 : 0;
            const modes = ["air", "evaporative", "emergency", "humidity_warn", "security_alert"];
            const mode = modes[Math.floor(Math.random() * modes.length)];
            
            const fakePayload = {
              temperature: parseFloat(temp),
              humidity: parseFloat(hum),
              smoke_alert: smoke,
              cooling_mode: mode,
              confidence: parseFloat(Math.random().toFixed(3)),
              predicted_PUE: parseFloat((1.1 + Math.random() * 0.5).toFixed(3)),
              predicted_WUE: parseFloat((1.2 + Math.random() * 0.6).toFixed(3))
            };
            parseData(JSON.stringify(fakePayload));
        }, 2000);
    }
});

document.getElementById('btn-toggle').addEventListener('click', () => {
  if (mqttClient && mqttClient.isConnected()) {
    document.getElementById('feed-log').innerHTML = `<div class="text-rose-400 font-mono text-[10px]">> Terminating link connection protocol...</div>`;
    mqttClient.disconnect();
    return;
  }

  const cid = "client_" + Math.random().toString(16).substr(2, 6);
  document.getElementById('feed-log').innerHTML = `<div class="text-amber-400 font-mono text-[10px] animate-pulse">> Initializing handshake with edge broker...</div>`;
  
  mqttClient = new Paho.MQTT.Client("broker.hivemq.com", 8000, cid);
  
  mqttClient.onConnectionLost = () => {
    updateStatusUI("OFFLINE", "text-rose-400");
    updateToggleButton(false);
    document.getElementById('feed-log').innerHTML = `<div class="text-rose-500 font-mono text-[10px]">> Link Disrupted or Closed. Core offline.</div>`;
  };
  
  mqttClient.onMessageArrived = (msg) => {
    parseData(msg.payloadString);
  };

  mqttClient.connect({
    onSuccess: () => {
        updateStatusUI("ONLINE", "text-emerald-400");
        updateToggleButton(true);
        document.getElementById('feed-log').innerHTML = `<div class="text-emerald-400 font-mono text-[10px]">> Session verification established. Secure bridge running.</div>`;
        mqttClient.subscribe("MLIOT/datacenter");
    },
    onFailure: (err) => {
        updateToggleButton(false);
        document.getElementById('feed-log').innerHTML = `<div class="text-rose-400 font-mono text-[10px]">> Handshake Failed: ${err.errorMessage}</div>`;
    }
  });
});

function updateToggleButton(isConnected) {
  const btn = document.getElementById('btn-toggle');
  if (isConnected) {
    btn.querySelector('span').textContent = "DISCONNECT MQTT LINK";
    btn.className = "btn-cyber text-xs border border-rose-500/20 bg-rose-500/5 hover:bg-rose-500/10 text-rose-400 py-2.5 rounded font-semibold tracking-wider transition-colors";
  } else {
    btn.querySelector('span').textContent = "ESTABLISH MQTT LINK";
    btn.className = "btn-cyber text-xs border border-white/10 hover:bg-white/5 text-gray-300 py-2.5 rounded font-semibold tracking-wider transition-colors";
  }
}

function updateStatusUI(txt, colorClass) {
  const el = document.getElementById('conn-text');
  el.textContent = txt;
  el.className = `${colorClass} font-semibold uppercase`;
}

function parseData(str) {
  packetsReceived++;
  document.getElementById('packet-counter').textContent = packetsReceived;

  const logTimestamp = new Date().toLocaleTimeString();

  const log = document.getElementById('feed-log');
  const row = document.createElement('div');
  row.className = "border-l border-indigo-500/30 py-0.5 pl-2 text-gray-400 transition-all hover:bg-white/5";
  row.innerHTML = `<span class="text-indigo-400/50 font-semibold">[${logTimestamp}]</span> ${str}`;
  log.prepend(row);
  
  if (log.children.length > 30) log.removeChild(log.lastChild);

  try {
    const data = JSON.parse(str);
    
    const tempVal = parseFloat(data.temperature);
    const humVal = parseFloat(data.humidity);
    const smokeAlert = parseInt(data.smoke_alert);
    const coolingMode = data.cooling_mode;

    logEntries.push({
      timestamp: logTimestamp,
      message: str,
      temp: tempVal,
      hum: humVal,
      smoke: smokeAlert === 1 ? "SMOKE" : "CLEAR",
      fan: (coolingMode === 'air' || coolingMode === 'evaporative' || coolingMode === 'emergency') ? "ON" : "OFF",
      cool: (coolingMode === 'evaporative' || coolingMode === 'emergency') ? "ON" : "OFF"
    });

    document.getElementById('text-temp').textContent = tempVal.toFixed(1);
    document.getElementById('text-hum').textContent = humVal.toFixed(1);
    
    const tempBox = document.getElementById('card-temp-box');
    const tempMark = document.getElementById('mark-temp');
    if (tempVal > 30) {
      tempBox.className = 'dashboard-card border border-rose-500/30 bg-rose-950/10 p-6 rounded-lg flex-1 flex items-center justify-between relative overflow-hidden';
      tempMark.className = 'card-watermark watermark-alert-red';
    } else {
      tempBox.className = 'dashboard-card border border-white/5 p-6 rounded-lg flex-1 flex items-center justify-between relative overflow-hidden';
      tempMark.className = 'card-watermark';
    }
      
    const humBox = document.getElementById('card-hum-box');
    const humMark = document.getElementById('mark-hum');
    if (humVal < 42) {
      humBox.className = 'dashboard-card border border-sky-500/30 bg-sky-950/10 p-6 rounded-lg flex-1 flex items-center justify-between relative overflow-hidden';
      humMark.className = 'card-watermark watermark-alert-blue';
    } else {
      humBox.className = 'dashboard-card border border-white/5 p-6 rounded-lg flex-1 flex items-center justify-between relative overflow-hidden';
      humMark.className = 'card-watermark';
    }

    const smokeText = document.getElementById('text-smoke');
    const smokeBox = document.getElementById('card-smoke');
    const smokeMark = document.getElementById('mark-smoke');
    if (smokeAlert === 1) {
      smokeText.textContent = "CRITICAL ALERT";
      smokeText.className = "text-sm font-bold text-rose-400 tracking-wider z-10";
      smokeBox.className = "dashboard-card border border-rose-500/40 bg-rose-950/20 p-6 rounded-lg flex-1 flex items-center justify-between relative overflow-hidden";
      smokeMark.className = 'card-watermark watermark-alert-red';
    } else {
      smokeText.textContent = "SYSTEM SAFE";
      smokeText.className = "text-sm font-bold text-emerald-400 tracking-wider z-10";
      smokeBox.className = "dashboard-card border border-white/5 p-6 rounded-lg flex-1 flex items-center justify-between relative overflow-hidden";
      smokeMark.className = 'card-watermark watermark-safe-green';
    }

    const isFanOn = (coolingMode === 'air' || coolingMode === 'evaporative' || coolingMode === 'emergency');
    const isCoolOn = (coolingMode === 'evaporative' || coolingMode === 'emergency');

    updateActuatorElement('act-fan', 'badge-fan', isFanOn, 'border-emerald-500/20 bg-emerald-500/5', 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10');
    updateActuatorElement('act-cool', 'badge-cool', isCoolOn, 'border-indigo-500/20 bg-indigo-500/5', 'border-indigo-500/30 text-indigo-400 bg-indigo-500/10');

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    chart.data.labels.push(time);
    chart.data.datasets[0].data.push(tempVal);
    chart.data.datasets[1].data.push(humVal);
    if (chart.data.labels.length > 15) {
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
      chart.data.datasets[1].data.shift();
    }
    chart.update();

  } catch (e) {
    logEntries.push({
      timestamp: logTimestamp,
      message: str,
      temp: '',
      hum: '',
      smoke: 'ERROR',
      fan: 'OFF',
      cool: 'OFF'
    });
  }
}

function updateActuatorElement(boxId, badgeId, isActive, activeBoxClass, activeBadgeClass) {
  const box = document.getElementById(boxId);
  const badge = document.getElementById(badgeId);
  if (isActive) {
    badge.textContent = "ACTIVE RUN";
    badge.className = `actuator-badge text-[10px] px-3 py-1 font-semibold tracking-wide border ${activeBadgeClass}`;
    box.className = `dashboard-card border px-6 rounded-lg flex-1 flex items-center justify-between ${activeBoxClass}`;
  } else {
    badge.textContent = "STANDBY";
    badge.className = "actuator-badge badge-off text-[10px] px-3 py-1 font-medium tracking-wide";
    box.className = "dashboard-card border border-white/5 px-6 rounded-lg flex-1 flex items-center justify-between hover:bg-white/[0.01]";
  }
}

function renderModalTable() {
  if (logEntries.length === 0) {
    return `<div class="p-6 text-gray-500 italic font-mono text-xs">// Data register empty. No logs saved yet.</div>`;
  }
  let html = `<table class="w-full text-left font-mono text-[11px] border-collapse text-gray-300">
    <thead>
      <tr class="border-b border-white/10 bg-gray-900/60 sticky top-0 uppercase tracking-wider text-indigo-400">
        <th class="p-3 font-semibold">Timestamp</th>
        <th class="p-3 font-semibold">Raw Message</th>
        <th class="p-3 font-semibold text-right">Temp(°C)</th>
        <th class="p-3 font-semibold text-right">Hum(%)</th>
        <th class="p-3 font-semibold text-center">Smoke</th>
        <th class="p-3 font-semibold text-center">Fan</th>
        <th class="p-3 font-semibold text-center">CoolLED</th>
      </tr>
    </thead>
    <tbody>`;
  logEntries.forEach((e, idx) => {
    let bgRow = idx % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.01]';
    let smokeColor = e.smoke === 'SMOKE' ? 'text-rose-400 font-semibold' : 'text-gray-400';
    let fanColor = e.fan === 'ON' ? 'text-emerald-400 font-semibold' : 'text-gray-500';
    let coolColor = e.cool === 'ON' ? 'text-indigo-400 font-semibold' : 'text-gray-500';
    html += `<tr class="${bgRow} border-b border-white/[0.03] hover:bg-white/5 transition-colors">
      <td class="p-3 font-semibold text-gray-400">${e.timestamp}</td>
      <td class="p-3 text-gray-400 truncate max-w-xs">${e.message}</td>
      <td class="p-3 text-right text-rose-300 font-semibold">${e.temp !== '' ? Number(e.temp).toFixed(1) : ''}</td>
      <td class="p-3 text-right text-sky-300 font-semibold">${e.hum !== '' ? Number(e.hum).toFixed(1) : ''}</td>
      <td class="p-3 text-center ${smokeColor}">${e.smoke}</td>
      <td class="p-3 text-center ${fanColor}">${e.fan}</td>
      <td class="p-3 text-center ${coolColor}">${e.cool}</td>
    </tr>`;
  });
  html += `</tbody></table>`;
  return html;
}

const modal = document.getElementById('log-modal');

document.getElementById('btn-view-logs').addEventListener('click', () => {
  document.getElementById('modal-log-content').innerHTML = renderModalTable();
  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.classList.remove('opacity-0');
  }, 10);
});

function closeModal() {
  modal.classList.add('opacity-0');
  setTimeout(() => {
    modal.classList.add('hidden');
  }, 300);
}

document.getElementById('btn-close-modal').addEventListener('click', closeModal);
modal.addEventListener('click', (e) => {
  if (e.target === modal) closeModal();
});

document.getElementById('btn-clear-file').addEventListener('click', () => {
  logEntries = [];
  document.getElementById('modal-log-content').innerHTML = renderModalTable();
});

document.getElementById('btn-download-file').addEventListener('click', () => {
  let csvContent = "\ufeffTimestamp,Raw Message,Temperature(C),Humidity(%),Smoke Alert,Fan State,CoolLED State\n";
  
  logEntries.forEach(e => {
    let cleanMsg = e.message.replace(/"/g, '""');
    csvContent += `"${e.timestamp}","${cleanMsg}","${e.temp}","${e.hum}","${e.smoke}","${e.fan}","${e.cool}"\n`;
  });
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'log.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});