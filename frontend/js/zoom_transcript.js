// ── Zoom Bot Console — zoom_transcript.js ──

// ── State ──
let eventSource    = null;   // SSE connection
let isLive         = false;
let pendingLines   = [];     // lines buffered for current 60-sec segment
let segmentIndex   = 0;
let segmentTimer   = null;   // setInterval for 60-sec flush
let countdownTimer = null;   // setInterval for countdown UI
let countdownSec   = 60;
let totalLines     = 0;
const SEGMENT_SEC  = 60;

// ── Helpers ──
function ts() {
  return new Date().toTimeString().slice(0, 8);
}

function getConfig() {
  return {
    apiBase:  (document.getElementById('apiBase').value || 'http://127.0.0.1:8000').replace(/\/$/, ''),
    meetingId: document.getElementById('meetingId').value.trim().replace(/\s+/g, ''),
    password:  document.getElementById('meetingPassword').value.trim(),
    botName:   document.getElementById('botName').value.trim() || 'Transcript Bot',
    duration:  parseInt(document.getElementById('duration').value) || 3600,
  };
}

function setStatus(state, label) {
  const dot  = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  dot.className  = `status-indicator ${state}`;
  text.textContent = label.toUpperCase();
  text.style.color = state === 'active' ? 'var(--green)'
                   : state === 'busy'   ? 'var(--orange)'
                   : state === 'error'  ? 'var(--red)'
                   : 'var(--text-dim)';
}

function log(msg, type = 'info') {
  const container = document.getElementById('logContainer');
  const entry = document.createElement('div');
  entry.className = `log-entry log-${type}`;
  entry.innerHTML = `<span class="log-time">${ts()}</span><span class="log-msg">${escapeHtml(msg)}</span>`;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function updateTranscriptMeta() {
  document.getElementById('transcriptMeta').textContent =
    `${segmentIndex} segment${segmentIndex !== 1 ? 's' : ''} · ${totalLines} line${totalLines !== 1 ? 's' : ''}`;
}

// ── API helpers ──
async function apiPost(path, body) {
  const { apiBase } = getConfig();
  const res = await fetch(`${apiBase}${path}`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify(body),
  });
  return res.json();
}

// ── Button: Join As Me ──
async function joinAsMe() {
  const cfg = getConfig();
  if (!cfg.meetingId) { log('Meeting ID is required.', 'warn'); return; }

  const btn = document.getElementById('btnJoinMe');
  btn.disabled = true;
  setStatus('busy', 'Joining…');
  log(`Launching Zoom desktop app for meeting ${cfg.meetingId}…`);

  try {
    const payload = { meeting_id: cfg.meetingId };
    if (cfg.password) payload.password = cfg.password;

    const data = await apiPost('/zoom/me/join-meeting', payload);

    if (data.status) {
      setStatus('active', 'In Meeting');
      log(`✓ ${data.message}`, 'success');
    } else {
      setStatus('error', 'Failed');
      log(`✗ ${data.message}`, 'error');
    }
  } catch (err) {
    setStatus('error', 'Error');
    log(`Network error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
  }
}

// ── Button: Join As Bot ──
async function joinAsBot() {
  const cfg = getConfig();
  if (!cfg.meetingId) { log('Meeting ID is required.', 'warn'); return; }

  const btn = document.getElementById('btnJoinBot');
  btn.disabled = true;
  setStatus('busy', 'Bot Joining…');
  log(`Bot "${cfg.botName}" joining meeting ${cfg.meetingId}…`);

  try {
    const payload = { meeting_id: cfg.meetingId, bot_name: cfg.botName };
    if (cfg.password) payload.password = cfg.password;

    const data = await apiPost('/zoom/bot/join-meeting', payload);

    if (data.status) {
      setStatus('active', 'Bot Active');
      log(`✓ ${data.message}`, 'success');
    } else {
      setStatus('error', 'Failed');
      log(`✗ ${data.message}`, 'error');
    }
  } catch (err) {
    setStatus('error', 'Error');
    log(`Network error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
  }
}

// ── Button: Live Transcript (toggle) ──
function toggleLiveTranscript() {
  if (isLive) {
    stopLiveTranscript();
  } else {
    startLiveTranscript();
  }
}

function startLiveTranscript() {
  const cfg = getConfig();
  if (!cfg.meetingId) { log('Meeting ID is required.', 'warn'); return; }

  // Build SSE URL
  let url = `${cfg.apiBase}/zoom/bot/transcript/live?meeting_id=${encodeURIComponent(cfg.meetingId)}`
    + `&bot_name=${encodeURIComponent(cfg.botName)}`
    + `&duration_seconds=${cfg.duration}`;
  if (cfg.password) url += `&password=${encodeURIComponent(cfg.password)}`;

  log(`Opening SSE stream → ${url}`);
  setStatus('busy', 'Connecting…');

  eventSource = new EventSource(url);
  isLive = true;

  // Update UI
  const btn = document.getElementById('btnLive');
  btn.classList.add('running');
  document.getElementById('liveBtnTitle').textContent = 'STOP TRANSCRIPT';
  document.getElementById('liveBadge').classList.add('visible');
  document.getElementById('liveTicker').classList.remove('hidden');
  document.getElementById('segmentBar').classList.remove('hidden');

  // Hide empty state
  document.getElementById('emptyState').style.display = 'none';

  // Start 60-sec segment loop
  pendingLines = [];
  countdownSec = SEGMENT_SEC;
  updateCountdown();

  segmentTimer = setInterval(() => {
    flushSegment();
  }, SEGMENT_SEC * 1000);

  countdownTimer = setInterval(() => {
    countdownSec = Math.max(0, countdownSec - 1);
    if (countdownSec === 0) countdownSec = SEGMENT_SEC;
    updateCountdown();
  }, 1000);

  // SSE handlers
  eventSource.addEventListener('status', (e) => {
    const d = JSON.parse(e.data);
    log(`[STATUS] ${d.message}`, 'info');
    setStatus('active', 'Streaming');
    document.getElementById('tickerText').textContent = d.message;
  });

  eventSource.addEventListener('caption', (e) => {
    const d = JSON.parse(e.data);
    handleCaption(d.timestamp, d.text);
  });

  eventSource.addEventListener('error', (e) => {
    try {
      const d = JSON.parse(e.data);
      log(`[ERROR] ${d.message}`, 'error');
    } catch (_) {
      log('Stream disconnected or error.', 'warn');
    }
    setStatus('error', 'Stream Error');
  });

  eventSource.onerror = () => {
    if (isLive) {
      log('SSE connection lost.', 'error');
      setStatus('error', 'Disconnected');
    }
  };
}

function stopLiveTranscript() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  isLive = false;

  clearInterval(segmentTimer);
  clearInterval(countdownTimer);
  segmentTimer = null;
  countdownTimer = null;

  // Flush any remaining lines
  if (pendingLines.length > 0) {
    flushSegment();
  }

  // Update UI
  const btn = document.getElementById('btnLive');
  btn.classList.remove('running');
  document.getElementById('liveBtnTitle').textContent = 'LIVE TRANSCRIPT';
  document.getElementById('liveBadge').classList.remove('visible');
  document.getElementById('liveTicker').classList.add('hidden');
  document.getElementById('segmentBar').classList.add('hidden');

  setStatus('idle', 'IDLE');
  log('Live transcript session stopped.', 'warn');
}

// ── Handle incoming caption line ──
function handleCaption(timestamp, text) {
  // Update live ticker
  const ticker = document.getElementById('tickerText');
  ticker.style.opacity = '0';
  setTimeout(() => {
    ticker.textContent = text;
    ticker.style.opacity = '1';
  }, 150);

  // Buffer for segment
  pendingLines.push({ timestamp, text });
  totalLines++;
  updateTranscriptMeta();
}

// ── Flush buffered lines into a segment card ──
function flushSegment() {
  if (pendingLines.length === 0) {
    log(`Segment #${segmentIndex + 1}: no new captions in last ${SEGMENT_SEC}s.`, 'info');
    return;
  }

  segmentIndex++;
  const lines  = [...pendingLines];
  pendingLines = [];

  const container = document.getElementById('segmentsContainer');

  const card = document.createElement('div');
  card.className   = 'segment-card';
  card.id          = `seg-${segmentIndex}`;

  const now = new Date();
  const rangeEnd   = now.toTimeString().slice(0, 8);
  const rangeStart = new Date(now - SEGMENT_SEC * 1000).toTimeString().slice(0, 8);

  card.innerHTML = `
    <div class="segment-card-header">
      <span class="seg-num">SEGMENT ${String(segmentIndex).padStart(3, '0')}</span>
      <span class="seg-time">${rangeStart} → ${rangeEnd}</span>
      <span class="seg-count">${lines.length} line${lines.length !== 1 ? 's' : ''}</span>
    </div>
    <div class="segment-card-body">
      ${lines.map(l => `
        <div class="caption-line">
          <span class="caption-ts">${l.timestamp}</span>
          <span class="caption-text">${escapeHtml(l.text)}</span>
        </div>
      `).join('')}
    </div>
  `;

  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
  updateTranscriptMeta();
  log(`Segment #${segmentIndex} saved — ${lines.length} caption line${lines.length !== 1 ? 's' : ''}.`, 'success');
}

// ── Countdown UI ──
function updateCountdown() {
  document.getElementById('segmentCountdown').textContent = countdownSec;
  const pct = ((SEGMENT_SEC - countdownSec) / SEGMENT_SEC) * 100;
  document.getElementById('segmentFill').style.width = `${100 - pct}%`;
}

// ── Clear / Export ──
function clearTranscript() {
  document.getElementById('segmentsContainer').innerHTML =
    `<div class="empty-state" id="emptyState"><span class="empty-icon">◌</span><span>No transcript yet. Start a live session above.</span></div>`;
  segmentIndex = 0;
  totalLines   = 0;
  pendingLines = [];
  updateTranscriptMeta();
  log('Transcript cleared.', 'warn');
}

function exportTranscript() {
  const cards = document.querySelectorAll('.segment-card');
  if (!cards.length) { log('Nothing to export.', 'warn'); return; }

  let out = `ZOOM BOT TRANSCRIPT EXPORT\nGenerated: ${new Date().toLocaleString()}\n\n`;

  cards.forEach(card => {
    const header = card.querySelector('.seg-num')?.textContent || '';
    const time   = card.querySelector('.seg-time')?.textContent || '';
    out += `── ${header}  (${time}) ──\n`;
    card.querySelectorAll('.caption-line').forEach(line => {
      const t = line.querySelector('.caption-ts')?.textContent || '';
      const x = line.querySelector('.caption-text')?.textContent || '';
      out += `  [${t}] ${x}\n`;
    });
    out += '\n';
  });

  const blob = new Blob([out], { type: 'text/plain' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `zoom_transcript_${Date.now()}.txt`;
  a.click();
  URL.revokeObjectURL(a.href);
  log(`Exported ${cards.length} segment(s) to .txt file.`, 'success');
}

function clearLog() {
  document.getElementById('logContainer').innerHTML = '';
  log('Log cleared.', 'info');
}

// ── Button: Get Full Transcript (POST /zoom/bot/transcript) ──
async function getFullTranscript() {
  const cfg = getConfig();
  if (!cfg.meetingId) { log('Meeting ID is required.', 'warn'); return; }

  const btn = document.getElementById('btnFull');
  btn.disabled = true;
  btn.classList.add('running');
  document.getElementById('fullBtnTitle').textContent = 'RECORDING…';
  document.getElementById('fullBadge').classList.add('visible');
  document.getElementById('emptyState') && (document.getElementById('emptyState').style.display = 'none');

  setStatus('busy', 'Recording…');
  log(`Bot joining meeting ${cfg.meetingId} — will collect transcript for ${cfg.duration}s then return…`, 'info');
  log(`⚠ This blocks until the session ends (${cfg.duration}s). Use Live Transcript for real-time.`, 'warn');

  try {
    const payload = {
      meeting_id:       cfg.meetingId,
      bot_name:         cfg.botName,
      duration_seconds: cfg.duration,
    };
    if (cfg.password) payload.password = cfg.password;

    const res  = await fetch(`${cfg.apiBase}/zoom/bot/transcript`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
    });
    const data = await res.json();

    if (data.status && data.data?.transcript?.length) {
      const lines = data.data.transcript;  // [{timestamp, text}, ...]
      renderFullTranscriptSegments(lines);
      setStatus('idle', 'IDLE');
      log(`✓ Full transcript received — ${lines.length} lines.`, 'success');
    } else if (data.status && data.data?.transcript?.length === 0) {
      setStatus('idle', 'IDLE');
      log('Session ended but no transcript lines were captured. Ensure host enabled captions.', 'warn');
    } else {
      setStatus('error', 'Failed');
      log(`✗ ${data.message}`, 'error');
    }
  } catch (err) {
    setStatus('error', 'Error');
    log(`Network error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.classList.remove('running');
    document.getElementById('fullBtnTitle').textContent = 'GET TRANSCRIPT';
    document.getElementById('fullBadge').classList.remove('visible');
  }
}

// Render full transcript lines into 60-second segments
function renderFullTranscriptSegments(lines) {
  if (!lines.length) return;

  const container = document.getElementById('segmentsContainer');

  // Group lines into buckets of SEGMENT_SEC seconds by timestamp
  const buckets = [];
  let bucket    = [];
  let bucketStart = lines[0]?.timestamp || '00:00:00';

  lines.forEach((line, i) => {
    bucket.push(line);
    // Every SEGMENT_SEC lines (approximate) or last line → flush bucket
    if (bucket.length >= SEGMENT_SEC || i === lines.length - 1) {
      buckets.push({ start: bucketStart, end: line.timestamp, lines: [...bucket] });
      bucket      = [];
      bucketStart = lines[i + 1]?.timestamp || line.timestamp;
    }
  });

  buckets.forEach(b => {
    segmentIndex++;
    totalLines += b.lines.length;

    const card = document.createElement('div');
    card.className = 'segment-card';
    card.id        = `seg-${segmentIndex}`;
    card.innerHTML = `
      <div class="segment-card-header">
        <span class="seg-num">SEGMENT ${String(segmentIndex).padStart(3, '0')}</span>
        <span class="seg-time">${b.start} → ${b.end}</span>
        <span class="seg-count">${b.lines.length} line${b.lines.length !== 1 ? 's' : ''}</span>
      </div>
      <div class="segment-card-body">
        ${b.lines.map(l => `
          <div class="caption-line">
            <span class="caption-ts">${l.timestamp}</span>
            <span class="caption-text">${escapeHtml(l.text)}</span>
          </div>
        `).join('')}
      </div>
    `;
    container.appendChild(card);
  });

  container.scrollTop = container.scrollHeight;
  updateTranscriptMeta();
  log(`Rendered ${buckets.length} segment(s) from full transcript.`, 'success');
}