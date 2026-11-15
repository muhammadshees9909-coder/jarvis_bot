// ===========================================================================
// JARVIS — floating glassmorphism widget
//   • draggable bubble (mouse + touch) with saved position
//   • wake-word activation ("Hey JARVIS") and silence-based auto-send
// ===========================================================================

// ---------------------------------------------------------------------------
// Backend discovery
// ---------------------------------------------------------------------------
// The base URL used to be hardcoded to one port, so running the server anywhere
// else (or through the tunnel) produced a false "Connection Error" even though
// the FastAPI backend was up. It is now resolved at runtime — see
// `jarvisRequest()` — and requests go through the extension service worker,
// whose origin is exempt from the page's CORS / Private-Network-Access rules.
const DEFAULT_BACKEND = 'http://127.0.0.1:8000';
let backendBase = DEFAULT_BACKEND;
let DASHBOARD_URL = backendBase + '/';
const BUBBLE_SIZE = 58;

const jarvisRoot = document.createElement('div');
jarvisRoot.id = 'jarvis-root';

jarvisRoot.innerHTML = `
  <div id="jarvis-bubble" role="button" tabindex="0" title="JARVIS — drag to move, click to open">
    <span class="jarvis-logo">J</span>
    <span class="jarvis-wake-dot" id="jarvis-wake-dot"></span>
  </div>

  <div id="jarvis-card" class="jarvis-hidden">
    <div class="jarvis-header">
      <span class="jarvis-brand"><span class="jarvis-brand-mark">J</span>JARVIS</span>
      <div class="jarvis-actions">
        <button id="jarvis-dashboard" class="jarvis-btn-icon" title="Open full dashboard">▦</button>
        <button id="jarvis-speak-toggle" class="jarvis-btn-icon" title="Toggle voice replies">🔇</button>
        <button id="jarvis-toggle-dock" class="jarvis-btn-icon" title="Toggle side panel">⇱</button>
        <button id="jarvis-close" class="jarvis-btn-icon" title="Minimize">✕</button>
      </div>
    </div>

    <div class="jarvis-status" id="jarvis-status">Tap 🎙️ to enable “Hey JARVIS”</div>

    <div class="jarvis-messages" id="jarvis-chat-box">
      <div class="jarvis-msg jarvis-msg-bot">
        Hello Shees! Main aapka JARVIS Trading Assistant hoon. 🎙️ dabayein aur “Hey JARVIS” bolein.
      </div>
    </div>

    <div class="jarvis-footer">
      <button id="jarvis-mic" class="jarvis-mic-btn" title="Toggle wake-word listening">🎙️</button>
      <input type="text" id="jarvis-input-field" class="jarvis-input" placeholder="Ask JARVIS..." />
      <button id="jarvis-send-trigger" class="jarvis-send-btn">Send</button>
    </div>
  </div>
`;

document.body.appendChild(jarvisRoot);

// Elements
const bubble = document.getElementById('jarvis-bubble');
const card = document.getElementById('jarvis-card');
const closeBtn = document.getElementById('jarvis-close');
const dockBtn = document.getElementById('jarvis-toggle-dock');
const dashboardBtn = document.getElementById('jarvis-dashboard');
const sendBtn = document.getElementById('jarvis-send-trigger');
const inputField = document.getElementById('jarvis-input-field');
const chatBox = document.getElementById('jarvis-chat-box');
const micBtn = document.getElementById('jarvis-mic');
const speakToggle = document.getElementById('jarvis-speak-toggle');
const statusEl = document.getElementById('jarvis-status');
const wakeDot = document.getElementById('jarvis-wake-dot');

// ---------------------------------------------------------------------------
// Session (shared with the full dashboard portal)
// ---------------------------------------------------------------------------
const SESSION_KEY = 'jarvis_session_id';
// The dashboard keeps its active conversation under this key. Reading it first
// means the widget and the full portal always attach to the same thread — and
// therefore the same rows in jarvis.db.
const DASHBOARD_SESSION_KEY = 'jarvis_dashboard_session';
let sessionId =
  localStorage.getItem(DASHBOARD_SESSION_KEY) || localStorage.getItem(SESSION_KEY) || null;
let historyLoaded = false;

// ---------------------------------------------------------------------------
// Voice settings
// ---------------------------------------------------------------------------
// Auto-speak is ON by default (only an explicit mute is remembered), so the
// widget behaves like a real voice assistant without any setup.
const SPEAK_KEY = 'jarvis_speak_enabled';
let speakEnabled = localStorage.getItem(SPEAK_KEY) !== '0';
speakToggle.textContent = speakEnabled ? '🔊' : '🔇';
speakToggle.title = speakEnabled
  ? 'Voice replies ON — click to mute'
  : 'Voice replies OFF — click to unmute';
speakToggle.classList.toggle('jarvis-btn-on', speakEnabled);

const WAKE_KEY = 'jarvis_wake_enabled';

// ===========================================================================
// 1. DRAGGABLE BUBBLE (mouse + touch)
// ===========================================================================
const POS_KEY = 'jarvis_bubble_pos';
let dragState = null;
let justDragged = false;

function clampPos(x, y) {
  const margin = 8;
  const maxX = window.innerWidth - BUBBLE_SIZE - margin;
  const maxY = window.innerHeight - BUBBLE_SIZE - margin;
  return {
    x: Math.min(Math.max(margin, x), Math.max(margin, maxX)),
    y: Math.min(Math.max(margin, y), Math.max(margin, maxY)),
  };
}

function applyPos(x, y) {
  const p = clampPos(x, y);
  jarvisRoot.style.left = p.x + 'px';
  jarvisRoot.style.top = p.y + 'px';
  jarvisRoot.style.right = 'auto';
  jarvisRoot.style.bottom = 'auto';
  return p;
}

function pointFromEvent(e) {
  if (e.touches && e.touches.length) return { x: e.touches[0].clientX, y: e.touches[0].clientY };
  if (e.changedTouches && e.changedTouches.length) {
    return { x: e.changedTouches[0].clientX, y: e.changedTouches[0].clientY };
  }
  return { x: e.clientX, y: e.clientY };
}

function onDragStart(e) {
  const p = pointFromEvent(e);
  const rect = jarvisRoot.getBoundingClientRect();
  dragState = {
    startX: p.x,
    startY: p.y,
    offsetX: p.x - rect.left,
    offsetY: p.y - rect.top,
    moved: false,
  };
  bubble.classList.add('jarvis-dragging');
  window.addEventListener('mousemove', onDragMove);
  window.addEventListener('mouseup', onDragEnd);
  window.addEventListener('touchmove', onDragMove, { passive: false });
  window.addEventListener('touchend', onDragEnd);
  e.preventDefault();
}

function onDragMove(e) {
  if (!dragState) return;
  const p = pointFromEvent(e);
  if (
    Math.abs(p.x - dragState.startX) > 3 ||
    Math.abs(p.y - dragState.startY) > 3
  ) {
    dragState.moved = true;
  }
  if (!dragState.moved) return;
  applyPos(p.x - dragState.offsetX, p.y - dragState.offsetY);
  if (e.cancelable) e.preventDefault();
}

function onDragEnd() {
  window.removeEventListener('mousemove', onDragMove);
  window.removeEventListener('mouseup', onDragEnd);
  window.removeEventListener('touchmove', onDragMove);
  window.removeEventListener('touchend', onDragEnd);
  bubble.classList.remove('jarvis-dragging');

  if (dragState && dragState.moved) {
    const rect = jarvisRoot.getBoundingClientRect();
    const p = applyPos(rect.left, rect.top);
    localStorage.setItem(POS_KEY, JSON.stringify(p));
    // The click event still fires after a drag — swallow it once.
    justDragged = true;
    setTimeout(() => {
      justDragged = false;
    }, 250);
  }
  dragState = null;
}

bubble.addEventListener('mousedown', onDragStart);
bubble.addEventListener('touchstart', onDragStart, { passive: false });

// Restore the saved position (default: bottom-right corner)
(function initBubblePosition() {
  let saved = null;
  try {
    saved = JSON.parse(localStorage.getItem(POS_KEY) || 'null');
  } catch (err) {
    saved = null;
  }
  if (saved && typeof saved.x === 'number' && typeof saved.y === 'number') {
    applyPos(saved.x, saved.y);
  } else {
    applyPos(window.innerWidth - BUBBLE_SIZE - 24, window.innerHeight - BUBBLE_SIZE - 24);
  }
})();

// Keep the bubble on-screen when the window is resized
window.addEventListener('resize', () => {
  const rect = jarvisRoot.getBoundingClientRect();
  const p = applyPos(rect.left, rect.top);
  localStorage.setItem(POS_KEY, JSON.stringify(p));
  if (!card.classList.contains('jarvis-hidden')) positionCard();
});

// Flip the card when the bubble sits too close to a screen edge
function positionCard() {
  const rect = jarvisRoot.getBoundingClientRect();
  card.classList.toggle('jarvis-card-below', rect.top < 560);
  card.classList.toggle('jarvis-card-left', rect.left < 420);
}

// ===========================================================================
// 2. WIDGET CONTROLS
// ===========================================================================
bubble.addEventListener('click', () => {
  if (justDragged) return;
  openCard();
});

bubble.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') openCard();
});

function openCard() {
  bubble.classList.add('jarvis-hidden');
  card.classList.remove('jarvis-hidden');
  positionCard();
  adoptDashboardSession();
  probeBackend();
  restoreHistory();
  // First open is a user gesture — a good moment to arm the wake word.
  if (!recognitionWanted && localStorage.getItem(WAKE_KEY) !== '0') {
    enableWakeWord();
  }
}

// Picks up a conversation the dashboard started after this page finished
// loading, so the widget never drifts onto a separate thread / separate rows.
function adoptDashboardSession() {
  const shared = localStorage.getItem(DASHBOARD_SESSION_KEY);
  if (shared && shared !== sessionId) {
    sessionId = shared;
    localStorage.setItem(SESSION_KEY, shared);
    historyLoaded = false;
  }
}

closeBtn.addEventListener('click', () => {
  stopSpeaking();
  card.classList.add('jarvis-hidden');
  bubble.classList.remove('jarvis-hidden');
});

dockBtn.addEventListener('click', () => {
  card.classList.toggle('jarvis-docked');
  positionCard();
});

dashboardBtn.addEventListener('click', () => {
  try {
    chrome.runtime.sendMessage({ type: 'OPEN_DASHBOARD', url: DASHBOARD_URL }, () => {
      if (chrome.runtime.lastError) window.open(DASHBOARD_URL, '_blank', 'noopener');
    });
  } catch (err) {
    window.open(DASHBOARD_URL, '_blank', 'noopener');
  }
});

speakToggle.addEventListener('click', () => {
  speakEnabled = !speakEnabled;
  localStorage.setItem(SPEAK_KEY, speakEnabled ? '1' : '0');
  speakToggle.textContent = speakEnabled ? '🔊' : '🔇';
  speakToggle.title = speakEnabled
    ? 'Voice replies ON — click to mute'
    : 'Voice replies OFF — click to unmute';
  speakToggle.classList.toggle('jarvis-btn-on', speakEnabled);
  setStatus(speakEnabled ? 'Voice replies ON' : 'Voice replies OFF', 'idle');
  setTimeout(() => {
    if (recognitionWanted && !commandMode) setStatus('Listening for “Hey JARVIS”…', 'idle');
  }, 1800);
  if (!speakEnabled) stopSpeaking();
});

// ===========================================================================
// 3. RENDERING HELPERS
// ===========================================================================
function formatText(text) {
  return String(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function toSpeakableText(text) {
  // Turns a reply into something a voice can read without stumbling: markdown,
  // links, URLs and emojis are stripped so the TTS never spells symbols (or
  // emoji names) out loud.
  return String(text)
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, ' ') // markdown images
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // markdown links -> label
    .replace(/(https?:\/\/|www\.)\S+/gi, ' ') // bare URLs
    .replace(/\*\*?([^*]+)\*\*?/g, '$1') // bold / italic
    .replace(/^\s*[-*+]\s+/gm, '') // bullet markers
    .replace(/^\s*#{1,6}\s*/gm, '') // heading markers
    .replace(/[*_~`#>|]+/g, ' ') // leftover markup symbols
    .replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, ' ') // emoji (surrogate pairs)
    .replace(/[\u2190-\u21FF\u2300-\u27BF\u2B00-\u2BFF]/g, ' ') // arrows + symbols
    .replace(/[\uFE0F\u200D\u20E3]/g, '') // emoji modifiers / joiners
    .replace(/\s+/g, ' ')
    .trim();
}

function appendMessage(text, role) {
  const msg = document.createElement('div');
  msg.className = 'jarvis-msg ' + (role === 'user' ? 'jarvis-msg-user' : 'jarvis-msg-bot');
  if (role === 'user') msg.innerText = text;
  else msg.innerHTML = formatText(text);
  chatBox.appendChild(msg);
  chatBox.scrollTop = chatBox.scrollHeight;
  return msg;
}

function setStatus(text, state) {
  statusEl.textContent = text;
  statusEl.className = 'jarvis-status' + (state ? ' jarvis-status-' + state : '');
}

// ===========================================================================
// 4. TEXT TO SPEECH
// ===========================================================================
function stopSpeaking() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  resumeRecognitionAfterSpeech();
}

let cachedVoice = null;

// A plain en-US voice spells Roman Urdu written in Latin letters ("theek hai
// yaar") out one letter at a time. South-Asian phonetic voices read it the way
// it actually sounds, so they are tried in this order:
//   ur-PK  ->  hi-IN  ->  en-IN / en-PK  ->  Google voices  ->  any English.
const VOICE_PREFERENCE = [/^ur[-_]/i, /^hi[-_]/i, /^en[-_](IN|PK)/i, /google/i, /^en[-_]/i];

function pickVoice() {
  if (cachedVoice || !('speechSynthesis' in window)) return cachedVoice;
  const voices = window.speechSynthesis.getVoices() || [];
  for (let p = 0; p < VOICE_PREFERENCE.length && !cachedVoice; p++) {
    for (let i = 0; i < voices.length; i++) {
      if (VOICE_PREFERENCE[p].test(voices[i].lang) || VOICE_PREFERENCE[p].test(voices[i].name)) {
        cachedVoice = voices[i];
        break;
      }
    }
  }
  if (!cachedVoice) cachedVoice = voices[0] || null;
  return cachedVoice;
}

function speak(text) {
  if (!speakEnabled || !('speechSynthesis' in window)) return;
  const clean = toSpeakableText(text);
  if (!clean) return;

  stopSpeaking();
  // Mute the mic while JARVIS talks so it never transcribes its own voice.
  pauseRecognitionForSpeech();

  const voice = pickVoice();
  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.lang = voice ? voice.lang : 'en-IN';
  utterance.rate = 1.02;
  utterance.pitch = 1.0;
  if (voice) utterance.voice = voice;
  // Either ending re-arms the mic, so the hands-free loop can never stall.
  utterance.onend = resumeRecognitionAfterSpeech;
  utterance.onerror = resumeRecognitionAfterSpeech;
  window.speechSynthesis.speak(utterance);
}

if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoice = null;
    pickVoice();
  };
}

// ===========================================================================
// 5. SPEECH RECOGNITION — wake word + silence auto-send
// ===========================================================================
const WAKE_PATTERN = /\b(?:hey|hi|hello|ok|okay|yo)\s+jarvis\b/i;
const SILENCE_MS = 2000;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;
let recognitionWanted = false; // user has the engine switched on
let recognitionRunning = false;
let commandMode = false; // false = waiting for "Hey JARVIS"
let commandBuffer = ''; // final transcript chunks of the current command
let interimText = ''; // not-yet-final tail
let silenceTimer = null;
let speechPause = false; // mic muted because TTS is speaking

function currentTranscript() {
  return (commandBuffer + ' ' + interimText).replace(/\s+/g, ' ').trim();
}

if (SpeechRecognition) {
  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || 'en-US';
  recognition.interimResults = true;
  recognition.continuous = true;

  recognition.onstart = () => {
    recognitionRunning = true;
    micBtn.classList.add('jarvis-on');
    wakeDot.classList.add('jarvis-on');
    if (!commandMode) setStatus('Listening for “Hey JARVIS”…', 'idle');
  };

  recognition.onresult = (event) => {
    interimText = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const chunk = event.results[i][0].transcript;
      if (event.results[i].isFinal) commandBuffer += chunk + ' ';
      else interimText += chunk;
    }

    const full = currentTranscript();
    if (!full) return;

    if (!commandMode) {
      const match = full.match(WAKE_PATTERN);
      if (!match) {
        setStatus('Listening for “Hey JARVIS”…', 'idle');
        return;
      }
      // Wake word heard — anything after it is already part of the command.
      commandMode = true;
      const after = full.slice(match.index + match[0].length).trim();
      commandBuffer = after ? after + ' ' : '';
      interimText = '';
      inputField.value = commandBuffer.trim();
      micBtn.classList.add('jarvis-capturing');
      setStatus('Listening…', 'active');
      armSilenceTimer();
      return;
    }

    inputField.value = full;
    setStatus('Listening…', 'active');
    armSilenceTimer();
  };

  recognition.onerror = (event) => {
    if (event.error === 'no-speech' || event.error === 'aborted') return;
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
      recognitionWanted = false;
      micBtn.classList.remove('jarvis-on', 'jarvis-capturing');
      wakeDot.classList.remove('jarvis-on');
      setStatus('Microphone blocked — allow mic access for this site', 'error');
      return;
    }
    setStatus('Voice error: ' + event.error, 'error');
  };

  recognition.onend = () => {
    recognitionRunning = false;
    micBtn.classList.remove('jarvis-on', 'jarvis-capturing');

    // Chrome ends the session after every pause; restart while it is wanted.
    if (recognitionWanted && !speechPause) {
      setTimeout(() => {
        if (recognitionWanted && !speechPause && !recognitionRunning) {
          try {
            recognition.start();
          } catch (err) {
            /* already starting */
          }
        }
      }, 250);
      return;
    }
    wakeDot.classList.remove('jarvis-on');
    if (!recognitionWanted) setStatus('Voice off — tap 🎙️ to enable', 'idle');
  };
} else {
  micBtn.title = 'Voice input is not supported in this browser';
  micBtn.style.opacity = '0.4';
  setStatus('Voice input unsupported in this browser', 'error');
}

// ---- silence detection ----------------------------------------------------
function armSilenceTimer() {
  clearTimeout(silenceTimer);
  silenceTimer = setTimeout(finalizeCommand, SILENCE_MS);
}

function finalizeCommand() {
  clearTimeout(silenceTimer);
  silenceTimer = null;

  const text = currentTranscript();
  resetCommandState();

  if (text) sendMessage(text);
  else setStatus('Listening for “Hey JARVIS”…', 'idle');
}

function resetCommandState() {
  commandMode = false;
  commandBuffer = '';
  interimText = '';
  inputField.value = '';
  micBtn.classList.remove('jarvis-capturing');
  if (recognitionWanted) setStatus('Listening for “Hey JARVIS”…', 'idle');
}

// ---- mic lifecycle --------------------------------------------------------
function enableWakeWord() {
  if (!recognition) return;
  recognitionWanted = true;
  localStorage.setItem(WAKE_KEY, '1');
  micBtn.classList.add('jarvis-on');
  setStatus('Listening for “Hey JARVIS”…', 'idle');
  if (!recognitionRunning) {
    try {
      recognition.start();
    } catch (err) {
      /* already running */
    }
  }
}

function disableWakeWord() {
  recognitionWanted = false;
  localStorage.setItem(WAKE_KEY, '0');
  clearTimeout(silenceTimer);
  silenceTimer = null;
  commandMode = false;
  commandBuffer = '';
  interimText = '';
  micBtn.classList.remove('jarvis-on', 'jarvis-capturing');
  wakeDot.classList.remove('jarvis-on');
  if (recognition) {
    try {
      recognition.stop();
    } catch (err) {
      /* not running */
    }
  }
  setStatus('Voice off — tap 🎙️ to enable', 'idle');
}

micBtn.addEventListener('click', () => {
  if (!recognition) return;
  if (recognitionWanted) disableWakeWord();
  else enableWakeWord();
});

// Mute the mic while TTS plays so JARVIS never hears itself
function pauseRecognitionForSpeech() {
  if (!recognition || !recognitionRunning) return;
  speechPause = true;
  try {
    recognition.abort();
  } catch (err) {
    speechPause = false;
  }
}

function resumeRecognitionAfterSpeech() {
  if (!speechPause) return;
  speechPause = false;
  if (recognitionWanted && recognition && !recognitionRunning) {
    try {
      recognition.start();
    } catch (err) {
      /* already starting */
    }
  }
}

// ===========================================================================
// 6. BACKEND CONNECTION
// ===========================================================================
function extensionAlive() {
  try {
    return typeof chrome !== 'undefined' && !!chrome.runtime && !!chrome.runtime.id;
  } catch (err) {
    return false;
  }
}

function askExtension(message) {
  return new Promise((resolve) => {
    if (!extensionAlive()) {
      resolve(null);
      return;
    }
    try {
      chrome.runtime.sendMessage(message, (response) => {
        if (chrome.runtime.lastError) resolve(null);
        else resolve(response || null);
      });
    } catch (err) {
      resolve(null);
    }
  });
}

function setBackendBase(base) {
  const clean = String(base || '').replace(/\/+$/, '');
  if (!clean || clean === backendBase) return;
  backendBase = clean;
  DASHBOARD_URL = clean + '/';
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch (err) {
    return null;
  }
}

// One request against the backend. The service worker is tried first because it
// is not subject to the page's CORS / Private-Network-Access rules; a plain
// fetch is the fallback for when the extension context is unavailable (e.g. the
// extension was just reloaded).
async function jarvisRequest(path, options) {
  const opts = options || {};
  const proxied = await askExtension({
    type: 'JARVIS_FETCH',
    path: path,
    pageOrigin: window.location.origin,
    options: opts,
  });

  if (proxied && proxied.ok) {
    setBackendBase(proxied.backend);
    return {
      ok: proxied.status >= 200 && proxied.status < 300,
      status: proxied.status,
      text: proxied.body || '',
    };
  }

  const res = await fetch(backendBase + path, opts);
  return { ok: res.ok, status: res.status, text: await res.text() };
}

// ---------------------------------------------------------------------------
// Active tab context — attached to every /chat request so JARVIS knows which
// website or trading portal the user is looking at ("Main kis platform par
// hoon?"). Primary source is the page this widget runs in (it is the visible
// tab); the service worker's chrome.tabs lookup is the fallback for pages that
// cannot report their own URL.
// ---------------------------------------------------------------------------
function localPageContext() {
  try {
    const url = window.location.href || '';
    if (!/^https?:|^file:/i.test(url)) return null;
    return { url: url, title: (document.title || '').slice(0, 300) };
  } catch (err) {
    return null;
  }
}

async function collectPageContext() {
  const local = localPageContext();
  if (local && local.title) return local;

  const info = await askExtension({ type: 'JARVIS_ACTIVE_TAB' });
  if (info && info.url) return { url: info.url, title: info.title || '' };
  return local;
}

// Confirms the backend is really running and, on success, briefly shows which
// host the widget settled on so a wrong URL is obvious instead of silent.
async function probeBackend() {
  let ok = false;
  try {
    const r = await jarvisRequest('/health');
    const info = r.ok ? parseJson(r.text) : null;
    ok = !!(info && (info.service === 'JARVIS' || info.status === 'ok'));
  } catch (err) {
    ok = false;
  }

  if (ok) {
    setStatus('Connected — ' + backendBase.replace(/^https?:\/\//, ''), 'active');
    setTimeout(() => {
      if (recognitionWanted && !commandMode) setStatus('Listening for “Hey JARVIS”…', 'idle');
    }, 2500);
  } else {
    setStatus('Backend offline — JARVIS server start karein', 'error');
  }
  return ok;
}

// ===========================================================================
// 7. HISTORY + CHAT
// ===========================================================================
async function restoreHistory() {
  if (historyLoaded || !sessionId) return;
  historyLoaded = true;
  try {
    const r = await jarvisRequest('/api/sessions/' + encodeURIComponent(sessionId) + '/messages');
    if (!r.ok) return;
    const data = parseJson(r.text);
    if (!data || !data.messages || !data.messages.length) return;
    chatBox.innerHTML = '';
    data.messages.forEach((m) => appendMessage(m.content, m.role));
  } catch (err) {
    // Server unreachable right now — retry the next time the card is opened.
    historyLoaded = false;
  }
}

async function sendMessage(textOverride) {
  const text = (textOverride !== undefined ? textOverride : inputField.value).trim();
  if (!text) return;

  // Leaving command mode keeps the wake-word listener alive for the next turn.
  resetCommandState();
  stopSpeaking();
  appendMessage(text, 'user');
  inputField.value = '';

  const botMsg = appendMessage('Thinking...', 'bot');

  try {
    // Tell JARVIS which tab this question came from (url + title) so it can
    // answer "Main kis platform par hoon?" / "screen par kya khula hai?".
    const pageContext = await collectPageContext();
    const payload = { message: text, session_id: sessionId };
    if (pageContext && pageContext.url) payload.page_context = pageContext;

    const r = await jarvisRequest('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!r.ok) {
      // The server answered, so this is NOT a connection problem: surface the
      // real reason (for example a busy AI model) instead of blaming FastAPI.
      const errBody = parseJson(r.text) || {};
      let detail = errBody.detail || errBody.error || '';
      // FastAPI validation errors send an array here; only show plain text.
      if (typeof detail !== 'string') detail = '';
      botMsg.innerText = detail
        ? '⚠️ ' + detail
        : '⚠️ Server error (' + r.status + '). Dobara try karein.';
      chatBox.scrollTop = chatBox.scrollHeight;
      return;
    }

    const data = parseJson(r.text) || {};

    if (data.session_id && data.session_id !== sessionId) {
      sessionId = data.session_id;
      localStorage.setItem(SESSION_KEY, sessionId);
    }
    // Share the session with the full dashboard so both stay on the same chat.
    if (sessionId) localStorage.setItem(DASHBOARD_SESSION_KEY, sessionId);

    const rawReply = data.response || data.reply || 'No response';
    botMsg.innerHTML = formatText(rawReply);
    chatBox.scrollTop = chatBox.scrollHeight;
    speak(rawReply);
  } catch (err) {
    // Reached only when the backend cannot be contacted at all.
    botMsg.innerText =
      '🔥 Backend tak nahi pohnch saka. JARVIS server (' + backendBase + ') aur tunnel check karein.';
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}

sendBtn.addEventListener('click', () => sendMessage());
inputField.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') sendMessage();
});
