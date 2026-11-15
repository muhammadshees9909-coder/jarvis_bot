/**
 * background.js — Service worker for the JARVIS Glass Assistant
 *
 * Manifest V3 background service worker. Currently responsible for:
 *   - Logging installation / startup events to the service-worker console
 *   - Providing a minimal lifecycle hook so Chrome keeps the worker alive
 *     and ready to route messages (future: popup commands, badge updates,
 *     action-click router, tab management).
 *
 * No host-facing permissions are required here; it only logs.
 */

"use strict";

// ---------------------------------------------------------------------------
// Event: service worker is installed / updated
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener((details) => {
  const reason = details.reason;
  const previousVersion = details.previousVersion || "first install";

  console.log("[JARVIS Background]", `Installed version ${previousVersion} -> ${chrome.runtime.getManifest().version}`, `reason: ${reason}`);

  // Welcome / onboarding note
  if (reason === "install") {
    console.log("[JARVIS Background]", "JARVIS Glass Assistant installed. Popup this window from chrome://extensions to get started.");
  } else if (reason === "update") {
    console.log("[JARVIS Background]", `Updated from ${previousVersion} to current version.`);
  } else if (reason === "chrome_update") {
    console.log("[JARVIS Background]", "Chrome updated — JARVIS extension reloaded.");
  }
});

// ---------------------------------------------------------------------------
// Event: service worker is launched (startup)
// ---------------------------------------------------------------------------
chrome.runtime.onStartup.addListener(() => {
  console.log("[JARVIS Background]", `Startup — version ${chrome.runtime.getManifest().version}`);
});

// ---------------------------------------------------------------------------
// Backend discovery + request proxy
// ---------------------------------------------------------------------------
// A content script speaks with the *page's* origin, so when the widget called
// http://127.0.0.1:8000 from a public website Chrome applied CORS and Private
// Network Access rules and blocked it — which surfaced as a false "Connection
// Error" while the FastAPI server was perfectly healthy. The service worker has
// the extension's own origin plus host permissions, so requests are made here.
const DEFAULT_BACKENDS = ["http://127.0.0.1:8000", "http://localhost:8000"];
const BACKEND_KEY = "jarvis_backend_url";
const PROBE_TIMEOUT_MS = 2500;
const REQUEST_TIMEOUT_MS = 90000;

let cachedBackend = null;

function normalise(url) {
  return String(url || "").trim().replace(/\/+$/, "");
}

// Only a page origin that could plausibly be JARVIS itself is probed, so the
// widget never fires requests at unrelated websites.
function isJarvisPageOrigin(origin) {
  if (!origin || !/^https?:\/\//i.test(origin)) return false;
  let host;
  try {
    host = new URL(origin).hostname.toLowerCase();
  } catch (err) {
    return false;
  }
  if (host === "127.0.0.1" || host === "localhost" || host === "[::1]") return true;
  if (/^(10|192\.168)\./.test(host)) return true;
  if (/^172\.(1[6-9]|2\d|3[01])\./.test(host)) return true;
  return /\.(trycloudflare\.com|ngrok-free\.app|ngrok-free\.dev|ngrok\.app|ngrok\.io|loca\.lt)$/.test(host);
}

async function backendCandidates(pageOrigin) {
  const list = [];

  // 1. an explicit override saved in extension storage (e.g. today's tunnel):
  //    chrome.storage.local.set({ jarvis_backend_url: "https://xxx.trycloudflare.com" })
  try {
    const stored = await chrome.storage.local.get(BACKEND_KEY);
    const saved = normalise(stored && stored[BACKEND_KEY]);
    if (saved) list.push(saved);
  } catch (err) {
    // Storage unavailable - carry on with the defaults below.
  }

  // 2. the page's own origin, when this tab is already the JARVIS dashboard.
  //    Covers both http://127.0.0.1:8000 and the Cloudflare tunnel URL.
  const origin = normalise(pageOrigin);
  if (origin && isJarvisPageOrigin(origin) && !list.includes(origin)) list.push(origin);

  // 3. the defaults the launcher and run.bat use.
  for (const base of DEFAULT_BACKENDS) {
    if (!list.includes(base)) list.push(base);
  }
  return list;
}

// A 200 alone is not enough: another app could own the port. The payload is
// checked for the JARVIS fingerprint before the URL is trusted.
async function probeBackend(base) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const res = await fetch(base + "/health", { signal: controller.signal, cache: "no-store" });
    if (!res.ok) return false;
    const info = await res.json();
    return !!(info && (info.service === "JARVIS" || info.status === "ok"));
  } catch (err) {
    return false;
  } finally {
    clearTimeout(timer);
  }
}

async function resolveBackend(pageOrigin, force) {
  if (!force && cachedBackend) return cachedBackend;
  for (const base of await backendCandidates(pageOrigin)) {
    if (await probeBackend(base)) {
      cachedBackend = base;
      return base;
    }
  }
  cachedBackend = null;
  return null;
}

// Performs the request and hands the raw body back, so the widget can render
// success and error payloads exactly like the dashboard does.
async function proxyRequest(path, options, pageOrigin) {
  const opts = options || {};
  let base = await resolveBackend(pageOrigin, false);
  let lastError = "JARVIS backend not reachable";

  for (let attempt = 0; attempt < 2 && base; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const res = await fetch(base + path, {
        method: opts.method || "GET",
        headers: opts.headers || undefined,
        body: opts.body || undefined,
        cache: "no-store",
        signal: controller.signal,
      });
      return { ok: true, backend: base, status: res.status, body: await res.text() };
    } catch (err) {
      // The server may be restarting, or the widget may be pointing at a stale
      // tunnel: drop the cached URL and probe everything again before failing.
      lastError = String(err);
      cachedBackend = null;
      base = await resolveBackend(pageOrigin, true);
    } finally {
      clearTimeout(timer);
    }
  }

  return { ok: false, backend: base, error: lastError };
}

// ---------------------------------------------------------------------------
// Active tab lookup (fallback for the widget's page context)
// ---------------------------------------------------------------------------
// The content script normally reads window.location/document.title itself, but
// it asks here when the page cannot report its own URL (e.g. an about:srcdoc
// frame). Note Chrome only fills in url/title for tabs this extension is
// allowed to see: the JARVIS dashboard and tunnel hosts (see host_permissions),
// or any tab once an "activeTab"/"tabs" grant applies.
function activeTabInfo() {
  return new Promise((resolve) => {
    try {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        const tab = (tabs && tabs[0]) || null;
        if (chrome.runtime.lastError || !tab || typeof tab.url !== "string") {
          resolve(null);
          return;
        }
        resolve({ url: tab.url, title: tab.title || "" });
      });
    } catch (err) {
      resolve(null);
    }
  });
}

// ---------------------------------------------------------------------------
// Event: message router (content script -> service worker)
// ---------------------------------------------------------------------------
// Opening the dashboard from the service worker avoids the page-level popup
// blockers and CSP rules that can silently kill a content-script window.open().
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== "string") return false;

  if (message.type === "OPEN_DASHBOARD") {
    chrome.tabs.create({ url: message.url || "http://127.0.0.1:8000/" });
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === "JARVIS_ACTIVE_TAB") {
    activeTabInfo()
      .then((info) => sendResponse(info))
      .catch(() => sendResponse(null));
    return true;
  }

  if (message.type === "JARVIS_FETCH") {
    proxyRequest(message.path, message.options, message.pageOrigin)
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true; // keep the channel open until the async reply is ready
  }

  if (message.type === "JARVIS_BACKEND") {
    resolveBackend(message.pageOrigin, !!message.force)
      .then((backend) => sendResponse({ backend: backend }))
      .catch(() => sendResponse({ backend: null }));
    return true;
  }

  return false;
});

// ---------------------------------------------------------------------------
// Event: tab updated / activated — optional hook for future features
// ---------------------------------------------------------------------------
chrome.tabs.onActivated.addListener((activeInfo) => {
  // Placeholder for future "switch to tab" logic if needed.
  // Currently we keep the worker alive only.
});

// ---------------------------------------------------------------------------
// Event: tab created — useful for future "open popup on install" flows
// ---------------------------------------------------------------------------
chrome.tabs.onCreated.addListener((tab) => {
  // Currently unused, but registered for future popup-on-install flows.
});

// ---------------------------------------------------------------------------
// Expose a tiny debug helper for the console
// ---------------------------------------------------------------------------
chrome.runtime.onConnect.addListener((port) => {
  console.log("[JARVIS Background]", "Message port connected from a content script or extension page.");
});
