// frontend\js\mcp_bot.js

const API = "http://127.0.0.1:8000";

/* ── State ─────────────────────────────────────────────── */
const history = [];       // [{role, content}]
let pending   = null;     // action waiting for confirmation
let busy      = false;

/* ── DOM ───────────────────────────────────────────────── */
const feed    = document.getElementById("feed");
const inp     = document.getElementById("inp");
const sendBtn = document.getElementById("send-btn");
const welcome = document.getElementById("welcome");

/* ── Helpers ───────────────────────────────────────────── */
const esc  = s => s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
const fmt  = s => esc(s).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/\n/g,"<br>");
const scroll = () => { feed.scrollTop = feed.scrollHeight; };

function setSend() {
  const on = inp.value.trim().length > 0 && !busy;
  sendBtn.classList.toggle("on", on);
}

function hideWelcome() {
  if (welcome) welcome.style.display = "none";
}

/* ── Render user bubble ────────────────────────────────── */
function addUser(text) {
  hideWelcome();
  feed.insertAdjacentHTML("beforeend", `
    <div class="row user">
      <div class="av">👤</div>
      <div class="bub">${esc(text)}</div>
    </div>`);
  scroll();
}

/* ── Render bot text bubble ────────────────────────────── */
function addBot(text) {
  feed.insertAdjacentHTML("beforeend", `
    <div class="row bot">
      <div class="av">⚡</div>
      <div class="bub">${fmt(text)}</div>
    </div>`);
  scroll();
}

/* ── Render typing indicator ───────────────────────────── */
function showTyping() {
  busy = true; setSend();
  feed.insertAdjacentHTML("beforeend", `
    <div class="row bot" id="typing">
      <div class="av">⚡</div>
      <div class="dots"><span></span><span></span><span></span></div>
    </div>`);
  scroll();
}
function hideTyping() {
  busy = false; setSend();
  document.getElementById("typing")?.remove();
}

/* ── Render confirmation card ──────────────────────────── */
const TOOL_LABELS = {
  send_email:          "✉️  send_email",
  join_zoom_as_me:     "🎥  join_zoom_as_me",
  join_zoom_as_bot:    "🤖  join_zoom_as_bot",
  get_zoom_transcript: "📝  get_zoom_transcript",
};

function addConfirm(action, summary) {
  const label  = TOOL_LABELS[action.tool_name] || action.tool_name;
  const rows   = Object.entries(action.tool_args)
    .map(([k,v]) => `<tr><td>${k.replace(/_/g," ")}</td><td>${esc(String(v))}</td></tr>`)
    .join("");

  const id = "cc-" + Date.now();
  feed.insertAdjacentHTML("beforeend", `
    <div class="row bot" id="${id}">
      <div class="av">⚡</div>
      <div class="confirm-card">
        <div class="cc-badge">Action Required</div>
        <div class="cc-title">${esc(label)}</div>
        <div class="cc-summary">${fmt(summary)}</div>
        <table class="cc-params"><tbody>${rows}</tbody></table>
        <div class="cc-actions">
          <button class="btn btn-ok" data-id="${id}">✓ Confirm</button>
          <button class="btn btn-no" data-id="${id}">✕ Cancel</button>
        </div>
      </div>
    </div>`);
  scroll();

  // Wire buttons
  document.querySelector(`.btn-ok[data-id="${id}"]`).onclick = () => confirm(id, action);
  document.querySelector(`.btn-no[data-id="${id}"]`).onclick = () => cancel(id);
}

/* ── Render action result ──────────────────────────────── */
function addResult(msg) {
  const err = msg.startsWith("❌") || msg.toLowerCase().includes("failed");
  feed.insertAdjacentHTML("beforeend", `
    <div class="result-row">
      <div class="av" style="background:var(--s3);border:1px solid var(--border2)">⚡</div>
      <div class="result-card ${err?"err":""}">${fmt(msg)}</div>
    </div>`);
  scroll();
}

/* ── Confirm handler ───────────────────────────────────── */
async function confirm(cardId, action) {
  const card = document.getElementById(cardId);
  card.querySelectorAll(".btn").forEach(b => b.disabled = true);
  pending = null;

  showTyping();
  try {
    const res  = await post({ message:"confirmed", action_confirmed:true, pending_action:action });
    hideTyping();
    history.push({ role:"assistant", content:res.message });
    addResult(res.message);
  } catch(e) {
    hideTyping();
    addResult("❌ " + e.message);
  }
}

/* ── Cancel handler ────────────────────────────────────── */
function cancel(cardId) {
  pending = null;
  const card = document.getElementById(cardId);
  const actions = card.querySelector(".cc-actions");
  if (actions) actions.innerHTML = `<span class="cancelled">✕ Action cancelled</span>`;
  scroll();
}

/* ── POST helper ───────────────────────────────────────── */
async function post(body) {
  const res = await fetch(`${API}/mcp/chat`, {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json();
}

/* ── Send message ──────────────────────────────────────── */
async function send() {
  const text = inp.value.trim();
  if (!text || busy) return;

  inp.value = "";
  inp.style.height = "auto";
  setSend();

  addUser(text);
  history.push({ role:"user", content:text });
  showTyping();

  try {
    // Send history WITHOUT the turn we just added (backend adds it internally)
    const data = await post({
      message: text,
      history: history.slice(0, -1),
    });
    hideTyping();

    switch(data.type) {

      case "text":
        history.push({ role:"assistant", content:data.message });
        addBot(data.message);
        break;

      case "confirmation":
        pending = data.action;
        history.push({ role:"assistant", content:data.message });
        addConfirm(data.action, data.message);
        break;

      case "action_result":
        history.push({ role:"assistant", content:data.message });
        addResult(data.message);
        break;

      case "error":
      default:
        addBot("⚠️ " + (data.message || "Unexpected error."));
    }

  } catch(e) {
    hideTyping();
    addBot("❌ Could not reach the server. Is it running on port 8000?");
  }
}

/* ── Example chips ─────────────────────────────────────── */
function useChip(text) {
  inp.value = text;
  inp.style.height = "auto";
  inp.style.height = Math.min(inp.scrollHeight, 130) + "px";
  setSend();
  inp.focus();
}

/* ── Events ────────────────────────────────────────────── */
sendBtn.addEventListener("click", send);

inp.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});

inp.addEventListener("input", () => {
  inp.style.height = "auto";
  inp.style.height = Math.min(inp.scrollHeight, 130) + "px";
  setSend();
});

setSend();