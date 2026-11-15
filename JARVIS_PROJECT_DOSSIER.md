# JARVIS Forexcast Intelligence — Project Dossier

> **Version:** 1.0.0 · **Banaya gaya:** Shees ke liye · **Last updated:** 16 Nov 2026
> **Stack:** Chrome Extension (MV3) + Python FastAPI + Gemini AI + SQLite/SQLAlchemy + Cloudflare Tunnel + PWA

---

## 1. Ek Nazar Mein (Executive Summary)

JARVIS ek **personal AI forex assistant** hai jo do shakalon mein milta hai:

1. **Floating glassmorphism browser extension** — kisi bhi website ke upar tairta hua widget (Google, TradingView, kuch bhi). Mic dabao, bolo, jawab suno.
2. **PWA dashboard** — full-screen chat app (`http://127.0.0.1:8000`) jismein chat history sidebar, live market ticker aur economic calendar strip hai. Isay phone ki home screen par install kiya ja sakta hai.

Dono ek hi local FastAPI backend se baat karte hain, jo **EUR/USD market context (DXY, US10Y)** ko har AI prompt mein inject karta hai, aur har baat-cheet SQLite mein save karta hai.

**Ek line mein:** *"Browser ya phone se, awaaz ya typing se, apne market ke sawal poocho — JARVIS apne PC par chalta hai, data tumhara rehta hai, aur jawab awaaz mein deta hai."*

---

## 2. Yeh Project Kyun Banaya? (Why)

| # | Maqsad (Goal) | Kyun Zaroori Tha (Rationale) |
|---|---|---|
| 1 | **Trading analysis ke waqt assistant haath mein ho** | Chart dekhte waqt tab switch karke ChatGPT kholna flow tod deta hai. Floating widget usi page par rehta hai. |
| 2 | **Awaaz se baat** | Chart par nazar hoti hai, haath free nahi hote. "Hey JARVIS" bol kar poochna natural hai. |
| 3 | **Live market context AI ke dimaag mein ho** | Normal chatbot ko DXY ya US10Y ka pata nahi hota. Yahan har reply ke saath live prices prompt mein jaate hain. |
| 4 | **Memory ho** | Har baar context dohrana na pade. SQLite har session save karta hai aur AI ko pichhle 10 turns yaad rehte hain. |
| 5 | **100% local aur private** | Sab kuch apne PC par. Sirf AI call bahar jaati hai (Gemini). Chat history kabhi cloud par nahi jaati. |
| 6 | **Seekhne ka mission** | FastAPI + MV3 + STT/TTS + SQLAlchemy + tunnel — ek asli product ke through poora stack cover karna. |

**Persona choice:** JARVIS ek *dost* ki tarah baat karta hai, report ki tarah nahi. Roman Urdu, Hinglish ya English — jo user bole, usi mein jawab. ("Yaar, EURUSD abhi 1.0850 ke aas paas hai aur DXY thoda strong lag raha hai.")

---

## 3. Kya Kya Hua — Safar (Timeline / War Stories)

Yeh project ek seedhi line nahi, ek debugging journey raha hai. Har stage ne ek asli masla hal kiya:

### Phase 1 — Idea & Foundation
- FastAPI skeleton bana: `/chat`, `/health`, `/api/news` routes aur CORS middleware.
- `ai_service.py` mein Gemini wire kiya, `market_data.py` + `news_service.py` se context inject kiya.
- Chrome extension (MV3) ka basic floating widget likha.

### Phase 2 — "Server Connect Nahi Ho Raha" (The Crash Phase)
> **Symptom:** `run.bat` kholte hi band ho jaata tha. Extension mein "Connection Error".

Debugging ke baad do root causes nikle:
- **Cause A:** `google-genai` package install hi nahi tha. `main.py` import hote hi `ModuleNotFoundError: No module named 'google'` se crash-ho jaata tha → window turant band.
- **Cause B:** Windows **Application Control policy** SQLAlchemy ki compiled `.pyd` files block kar rahi thi (`DLL load failed while importing _immutabledict_cy`).

**Fix:** dependency install + `.pyd` files ko `.disabled` rename karke SQLAlchemy ko pure-Python mode mein chalana (yeh fixup ab `run.bat`, `run_hidden.bat` aur `start_jarvis_bg.vbs` — teenon mein automatically hota hai).

### Phase 3 — Startup Ko Bulletproof Banana
- `config/settings.py`: `GROQ_API_KEY` pehle server ko kill kar deta tha — ab sirf warn karta hai.
- `ai_service.py`: Gemini client import-time par nahi, **lazily** banta hai. Ghalat/missing key ab server nahi girata, sirf chat error deta hai.
- `run.bat` ko **self-healing** banaya: crash par 5 second baad khud restart.

### Phase 4 — False "Connection Error" (CORS + Private Network)
> **Symptom:** Server bilkul healthy tha, phir bhi extension "Connection Error" dikhata tha.

Asli wajah **Chrome ki Private Network Access preflight** thi: public website (jaise google.com) se `http://127.0.0.1:8000` call karne par browser `Access-Control-Request-Private-Network: true` bhejta hai, aur jab tak reply mein `Access-Control-Allow-Private-Network: true` na ho, request block ho jaati hai.

**Dohra fix:**
1. Backend: `allow_private_network=True` + `allow_origins=["*"]`.
2. Extension: requests ko content script se nahi, **background service worker** se bheja — uske paas extension ka apna origin aur host permissions hoti hain, is liye CORS/PNA rules lagte hi nahi.

### Phase 5 — AI Ke Jhatke (Gemini 503 / Hindi Reply)
- **Problem:** Gemini `503 UNAVAILABLE — model overloaded` return karta tha aur chat fail ho jaati thi.
  **Fix:** `ai_service.py` mein retry + **model fallback chain** (primary `gemini-2.5-flash`, phir lite fallbacks). SDK ka apna 90-second internal retry bhi band kiya taaki fallback jaldi chale.
- **Problem:** Roman Urdu sawal par Gemini **Devanagari (Hindi)** mein jawab deta tha.
  **Fix:** `SYSTEM_INSTRUCTION` + `_detect_language()` script sniff — ab jawab usi zabaan/script mein aata hai jo user ne likhi.

### Phase 6 — Voice Polish
- **Problem:** TTS "asterisk asterisk" padhta tha aur emojin ke naam bolta tha.
  **Fix:** `plainText()` / `toSpeakableText()` stripper — markdown, URLs, emoji sab hata deta hai.
- **Problem:** Mic JARVIS ki apni awaz transcribe kar leta tha.
  **Fix:** bolte waqt mic band, awaaz khatam hote hi (utterance `onend`) mic khud on — **hands-free loop**.
- **Problem:** Android Chrome final words ko **dubara append** kar raha tha ("hey hey Jarvis...").
  **Fix:** transcript har event par index 0 se poora dobara banaya jaata hai, `event.resultIndex` par bharosa nahi.

### Phase 7 — Kisi Bhi Network Se Access (Tunnel + PWA)
- **`tunnel.py`** banaya: Cloudflare quick tunnel (no account) → ngrok fallback. `https://xxxx.trycloudflare.com` jaisa free HTTPS URL deta hai.
- **Kyun HTTPS zaroori tha:** mobile browsers mic aur Web Speech API sirf **secure origin** par dete hain.
- **`static/`** mein PWA assets (manifest, service worker, icons) add kiye — "Add to Home Screen" ab kaam karta hai.

### Phase 8 — Silent Auto-Start + Watchdog
- `run_hidden.bat` — output `logs\` mein, koi CMD window nahi.
- `start_jarvis_bg.vbs` — **watchdog**: har 15 sec `/health` check, girne par khud restart + log rotation.
- `install_startup.bat` (alias `setup_autostart.bat`) — one-click Windows Startup shortcut + 200 OK verification.

### Phase 9 — Data Persistence
- `services/database.py` — SQLAlchemy models (`ChatSession`, `ChatMessage`) + SQLite (WAL mode).
- `/chat` ab session banata hai, pichhle 10 turns AI ko deta hai, aur har exchange save karta hai.

### Phase 10 — Skin & UX
- Backend ko `manifest.json`/`sw.js`/`favicon.ico` serve karwaya.
- Dashboard ko glassmorphism dark theme diya: session sidebar, market ticker, news strip, typing dots.

---

## 4. Architecture (Kaise Judaa Hai Sab Kuch)

```
                    ┌──────────────────────────────────────────────┐
                    │              USER (Shees)                    │
                    │   awaaz 🎙️  ya  typing ⌨️                    │
                    └───────────────┬──────────────────────────────┘
                                    │
        ┌───────────────────────────┴────────────────────────────┐
        │                                                        │
   ┌────▼─────────────────────┐                    ┌─────────────▼────────────┐
   │  EXTENSION (MV3)         │                    │  PWA DASHBOARD           │
   │  content.js + .css       │                    │  templates/index.html    │
   │  • floating widget       │                    │  • session sidebar       │
   │  • wake word "hey jarvis"│                    │  • market ticker         │
   │  • drag + dock           │                    │  • news strip            │
   │  • STT (SpeechRecog.)    │                    │  • STT/TTS + hands-free  │
   │  • TTS (SpeechSynth.)    │                    │  • service worker (PWA)  │
   └────┬─────────────────────┘                    └─────────────┬────────────┘
        │  chrome.runtime message                          fetch() (same origin)
        │  (CORS/PNA bypass)                                       │
   ┌────▼─────────────────────┐                                    │
   │ background.js            │                                    │
   │ • backend discovery      │                                    │
   │   (probe /health)        │                                    │
   │ • request proxy          │                                    │
   └────┬─────────────────────┘                                    │
        │                                                          │
        └──────────────────────┬───────────────────────────────────┘
                               │  HTTP  (local: 127.0.0.1:8000 · ya HTTPS tunnel)
                    ┌──────────▼──────────────────────────────────┐
                    │         FastAPI  (main.py)                  │
                    │  /  /chat  /health  /api/market             │
                    │  /api/news  /api/sessions[...]  /sw.js      │
                    │  CORS * + allow_private_network             │
                    │  TrustedHostMiddleware (tunnel domains)     │
                    └───────┬───────────────────┬─────────────────┘
                            │                   │
              ┌─────────────▼──────┐   ┌────────▼──────────────────┐
              │  services/         │   │  services/database.py     │
              │  ai_service.py     │   │  SQLite + SQLAlchemy      │
              │  • persona ruls    │   │  • ChatSession            │
              │  • retry/fallback  │   │  • ChatMessage            │
              │  market_data.py    │   └────────┬──────────────────┘
              │  news_service.py   │            │
              └─────────┬──────────┘            │
                        │                       │
                ┌───────▼────────┐      ┌───────▼────────┐
                │  Gemini API    │      │   jarvis.db    │
                │ (2.5-flash +   │      │  (WAL mode)    │
                │  fallbacks)    │      └────────────────┘
                └────────────────┘
```

### Layered Responsibilities

| Layer | Files | Zimmedari |
|---|---|---|
| **UI** | `extension/content.js`, `extension/content.css`, `templates/index.html` | Widget/dashboard, glassmorphism, markdown render, auto-scroll, mic/TTS |
| **Bridge** | `extension/background.js` | Backend discovery + request proxy (CORS/PNA bypass) |
| **API** | `main.py` | Routes, Pydantic models, CORS, host allow-list, PWA assets |
| **Domain** | `services/ai_service.py` | Persona, language rules, retry + model fallback |
| **Data** | `services/market_data.py`, `services/news_service.py` | Market/news context builders |
| **Storage** | `services/database.py` | Sessions + messages persistence |
| **Ops** | `run.bat`, `run_hidden.bat`, `start_jarvis_bg.vbs`, `install_startup.bat`, `tunnel.py` | Launch modes, watchdog, auto-start, public tunnel |
| **Legacy** | `bot/` | Telegram bot + APScheduler morning brief (web server isay use nahi karta) |

---

## 5. Ek Sawal Ka Poora Safar (End-to-End Request Flow)

```
1. User bole:            "Hey JARVIS, EURUSD ka outlook kya hai?"
2. Extension STT:        wake word match → recognition start → 2s silence → command finalize
3. Bridge:               background.js /health probe → backend URL resolve (cache)
4. POST /chat:           { message: "...", session_id: "abc123" }
5. main.py:              session_id verify/create
6. database.get_history: pichhle 10 turns nikalta hai  → memory
7. market_data:          EURUSD / DXY / US10Y snapshot → context string
8. ai_service:           SYSTEM_INSTRUCTION + history + market data + query → prompt
9. Gemini:               generate_content (retry x3, phir fallback models)
10. database.record_turn: user + assistant message save (jarvis.db)
11. Response:            { response, market_context, session_id, timestamp }
12. Widget:              markdown render + auto-scroll  →  TTS bolta hai
13. Hands-free:          utterance onend → mic dobara armed (loop chalta rehta hai)
```

---

## 6. Do Frontends — Farq Kya Hai

| Feature | Extension (`extension/`) | PWA Dashboard (`templates/index.html`) |
|---|---|---|
| Kahan dikhta hai | Kisi bhi website ke upar float | Apna poora page |
| Access | Chrome → Load unpacked | `http://127.0.0.1:8000` ya tunnel URL |
| Mobile | Nahi (desktop Chrome) | Haan — home screen par install |
| Chat history | Shared session (`/api/sessions`) | Full sidebar + search/delete |
| Market ticker | Halka | Live ticker (20s refresh) |
| News strip | Nahi | Haan (5 min refresh) |
| Voice | Wake word + drag + dock | Continuous + hands-free loop + notifications |
| CORS/PNA | Service worker proxy se bypass | Same-origin, problem hi nahi |
| Offline | Nahi | Haan (service worker shell cache) |

**Dono ek hi `session_id` key share karte hain**, is liye extension se shuru ki gayi baat dashboard mein continue ho sakti hai.

---

## 7. Char Deployment Modes (Launch Options)

| Command | Host | Kiske Liye | Notes |
|---|---|---|---|
| `run.bat` | `127.0.0.1:8000` | Sirf isi PC par (extension + browser) | Crash par auto-restart |
| `run.bat lan` | `0.0.0.0:8000` | Same Wi-Fi ke phones | `ALLOWED_HOSTS=*`, firewall allow karein |
| `run.bat remote` | `0.0.0.0` + tunnel | Duniya mein kahin se bhi | Cloudflare HTTPS URL print hota hai |
| `install_startup.bat` | Background | Rozana automatic | Silent watchdog + Windows Startup |

**Note:** `run.bat remote` mein backend minimized window mein, tunnel isi console mein chalta hai. Mic **sirf HTTPS** par chalta hai — is liye phone ke liye remote mode zaroori hai.

---

## 8. Jo Masail Hal Hue — Root Cause Table

| # | Symptom | Asli Wajah (Root Cause) | Hal |
|---|---|---|---|
| 1 | `run.bat` turant band | `google-genai` missing → import crash | Package install + requirements.txt |
| 2 | Server start par crash | SQLAlchemy `.pyd` App Control policy se blocked | `.pyd` → `.disabled` (pure-Python mode) |
| 3 | Extension "Connection Error" | Chrome Private Network Access preflight | `allow_private_network=True` + service worker proxy |
| 4 | Health 200 lekin request fail | Background port already in use | `/health` payload fingerprint check |
| 5 | Chat fail (503) | Gemini model overloaded | Retry + model fallback chain |
| 6 | Hindi/Devanagari jawab | Model language drift | `SYSTEM_INSTRUCTION` + script sniff |
| 7 | Chat 90s hang | SDK ka internal 5x retry | `HttpRetryOptions(attempts=1)` |
| 8 | TTS "asterisk asterisk" | Markdown symbols voice mein | `plainText()` stripper |
| 9 | Mic apni hi awaz sunta | TTS ke sath mic on | Bolte waqt mic off, `onend` par resume |
| 10 | Words dubara aa rahe (Android) | Chrome poora `event.results` dobara bhejta hai | Index 0 se transcript rebuild |
| 11 | Tunnel par 400 Bad Request | `TrustedHostMiddleware` random domain | Wildcard allow-list |
| 12 | `--forwarded-allow-ips *` crash | Click `*` ko glob expand kar deta hai | Env var `FORWARDED_ALLOW_IPS` se set |
| 13 | Server missing GROQ key par marta | Import-time `raise ValueError` | Sirf warning |
| 14 | Dashboard par "server offline" (galat) | Har error ko connection error samajhna | HTTP status + real `detail` dikhana |

---

## 9. Abhi Ki Haqeeqat (Honest Current State)

Yeh section jaan-boojh kar seedha hai — kyunki roadmap ke liye sach zaroori hai.

### ✅ Jo Kaam Kar Raha Hai
- Backend stable, silent auto-start + watchdog ke sath.
- AI chat with market context + 10-turn memory.
- SQLite persistence (sessions list, transcript load, delete).
- Extension: wake word, drag, dock, STT, TTS, backend auto-discovery.
- PWA dashboard: sidebar, ticker, news strip, phone install, offline shell.
- 4 launch modes + public HTTPS tunnel.

### ⚠️ Jo Abhi Placeholder Hai (Sabse Bada Gap)
- **Market data hardcoded hai.** `market_data.py` wapas fixed values deta hai (`EURUSD: 1.0850`, `DXY: 104.20`, `US10Y: 4.25`). Yeh asli live data **nahi** hai — comment khud kehta hai "Replace with actual APIs".
- **News/calendar bhi mock hai.** `news_service.py` mein NFP, ISM PMI, FOMC waghaira static list hai.
- **Natija:** AI ka analysis structurally sahi hai, lekin uske numbers asli market se nahi aa rahe. Yeh roadmap ka **Level 2** hai.

### ⚠️ Technical Debt
| Item | Tafseel |
|---|---|
| Koi authentication nahi | Koi bhi `127.0.0.1:8000` call kar sakta hai. Local theek, tunnel par khatarnak. |
| Single-user model | Sab sessions ek hi pool mein, koi user concept nahi. |
| API key plaintext | `GEMINI_API_KEY` `.env` mein — encryption/secret store nahi. |
| `bot/` + APScheduler dormant | Telegram bot aur morning brief likha hai lekin web server se wired nahi. |
| SQLAlchemy pure-Python | `.pyd` disabled — thoda slow. Policy hatne par wapas enable ho sakta hai. |
| Junk files | `extension/check_backtick.py`, `content_first46*.txt`, `_temp_write.py`, `_test_fallback2.py`, `_test_out2.txt`, `_temp_write.py`. Root mein bhi `_temp_write.py`, `_test_fallback2.py`, `_test_out2.txt`. |
| Koi tests nahi | Koi test file nahi — regression ka bharosa manual hai. |
| Session id client-generated | Dashboard `crypto.randomUUID()` se banata hai, server verify nahi karta (abuse possible). |

---

## 10. Future Roadmap — Kis Level Tak Le Ja Sakte Hain

Yeh ek **maturity ladder** hai. Har level apne aap mein usable product hai — upar jaana optional hai.

### 🟢 Level 1 — Clean & Solid (foundation)
**Goal:** Jo hai, woh production-grade ho.
- Junk/temp files hatana; `extension/` saaf karna; `.gitignore` + git history.
- `pytest` suite: `/chat`, `/health`, `/api/sessions` ke contract tests.
- `requirements.txt` pin versions; Python 3.11+ par lock.
- Logging `print` → proper `logging` (rotating file handler).
- Setup steps isi file ke Section 13 mein hain (koi alag README nahi chahiye).
- **Time to value:** sabse kam mehnat, sabse zyada faida.

### 🟡 Level 2 — Real Data (game changer)
**Goal:** Mock hatana — AI asli market par bole.
- EUR/USD, DXY, US10Y ke liye live feed: **Twelve Data / Alpha Vantage / Polygon / yfinance**.
- Economic calendar API: **Trading Economics / Finnhub / ForexFactory feed** (PKT timezone convert).
- Caching layer (e.g. 60s in-memory ya Redis) + rate-limit backoff.
- Data source fail ho to **graceful degradation**: "live data unavailable" bolo, fake number **kabhi** na do.
- `market_data.py` ko `providers/` pattern mein refactor (swap source, ek line change).
- **Yahan se project asli trading assistant ban jaata hai.**

### 🟡 Level 3 — Memory & Personalization
- Chat summary memory (long sessions ko condense karke prompt mein).
- **Vector memory:** embeddings + SQLite/ChromaDB — "pichhle hafte tune NFP par kya kaha tha?" jaise sawal.
- User profile: trading style, favourite pairs, risk appetite.
- Watchlist: user ke levels/pairs, jin par JARVIS nazar rakhe.

### 🟠 Level 4 — Proactive Intelligence (assistant se aage)
- **Alert engine:** "DXY 0.5% se zyada hile" → browser notification / phone push / Telegram.
- Pehle se banaya hua `bot/scheduler.py` wapas jodna → daily 11:00 PKT morning brief Telegram par.
- News event se 15 min pehle automated heads-up.
- Price levels par trigger: "EURUSD 1.0900 touch hua".
- Weekly performance digest.

### 🟠 Level 5 — Charts & Multi-Asset
- Widget ke andar mini candlestick chart (Lightweight Charts by TradingView — free).
- Gemini **vision** se chart screenshot analysis ("yeh setup batao").
- EUR/USD ke aage: GBP/USD, USD/JPY, Gold, indices, crypto.
- Correlation view (DXY vs EURUSD vs yields).

### 🔴 Level 6 — Voice-First Upgrade
- **Streaming STT/TTS** — pehla lafz bhi turant, poora jawab ka intezaar nahi.
- Offline/private: **Whisper.cpp** (STT) + **Piper** (TTS) — Gemini ke ilawa sab kuch local.
- Multi-language auto-switch: Urdu / Hindi / English / Roman Urdu bina setting.
- Voice profiles + barge-in (bolte waqt user rok de to ruk jaye).

### 🔴 Level 7 — Multi-User SaaS
- Auth: JWT / OAuth (Google login), sessions per user.
- Multi-tenant DB (Postgres + Alembic migrations), user-scoped API keys.
- Rate limiting + quota per user.
- Cloud deploy: EC2/Fly.io/Render + Docker + proper HTTPS domain (tunnel ke bajaye).
- Usage billing (Stripe) — free tier + pro tier.

### ⚫ Level 8 — Agentic Trading Copilot
- **Tool use / function calling:** JARVIS khud data fetch kare, levels calculate kare, backtest chalao.
- Trading journal: har trade entry/exit + AI post-mortem.
- Risk engine: position sizing, stop-loss suggestions, drawdown alerts.
- Backtesting hooks (pandas/backtrader) — strategy validate karne ke liye.
- **Broker read-only integration** (MT5 Python bridge / OANDA API) — kekar status dekh sake.
- ⚠️ **Execution/khatarnaak actions par hamesha explicit verbal confirmation** — user ka "SIRF MERE KEHNE PAR" protocol.

### ⚫ Level 9 — Autonomous Multi-Agent System
- MCP tools se JARVIS external systems se juda ho (calendar, sheets, email).
- Multiple agents: **Analyst** (news/price) + **Risk** (exposure) + **Coach** (journal/psychology) + **Orchestrator**.
- Continuous background loop: market dekhta rahe, sirf tab bole jab matter kare.
- Self-evaluation: apne past calls ka accuracy track kare ("pichhle 20 signals mein 14 sahi").
- Multi-model routing: sasta model routine kaam ke liye, strong model analysis ke liye (cost 60-80% kam).

### Recommended Path
```
Level 1 (clean)  →  Level 2 (real data)  →  Level 4 (proactive)  →  Level 6 (voice)  →  Level 8 (agentic)
        ▲                   ▲
        │                   └── Yeh do sabse zyada asar dalte hain
        └── Aaj hi shuru ho sakta hai, koi dependency nahi
```
Level 3, 5, 7 tab chuno jab Level 2 ka asli data chal raha ho — warna woh decoration hai.

---

## 11. Tech Stack

| Layer | Technology | Kyun Chuna |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async, auto-docs (`/docs`), Pydantic validation |
| AI | Google Gemini (`google-genai`) | Free tier, tez, multimodal (future vision) |
| AI resilience | Retry + fallback chain | Model overload par chat na ruke |
| DB | SQLite + SQLAlchemy 2.0 | Zero-setup, single file, ORM se Postgres migration aasan |
| Frontend 1 | Chrome MV3 + vanilla JS | No build step, kisi bhi page par inject |
| Frontend 2 | Single-file HTML/CSS/JS + PWA | Offline shell, phone install |
| Voice | Web Speech API (STT + TTS) | Browser-native, free, koi server nahi chahiye |
| Tunnel | Cloudflare Tunnel / ngrok | Free HTTPS, no account (Cloudflare) |
| Ops | Batch + VBScript | Windows-native, koi Python daemon nahi |
| Legacy | python-telegram-bot + APScheduler | Mobile alerts (future Level 4) |

---

## 12. File Map (Kya Kahaan Hai)

```
c:\jarvis-bot\
├── main.py                      # FastAPI app + saare routes
├── tunnel.py                    # Cloudflare/ngrok public HTTPS tunnel
├── requirements.txt
├── .env                         # GEMINI_API_KEY (plaintext — jaldi secret store par le jayein)
├── jarvis.db                    # SQLite (chat history) + -wal/-shm
│
├── config/
│   ├── __init__.py              # settings namespace
│   └── settings.py              # env vars, APP_TITLE, DATABASE_URL
│
├── services/
│   ├── ai_service.py            # Gemini + persona/language rules + retry/fallback
│   ├── database.py              # SQLAlchemy models + CRUD helpers
│   ├── market_data.py           # ⚠️ MOCK — EURUSD/DXY/US10Y
│   └── news_service.py          # ⚠️ MOCK — economic calendar
│
├── templates/
│   └── index.html               # PWA dashboard (sidebar + ticker + voice)
│
├── static/                      # PWA assets
│   ├── manifest.json  sw.js
│   └── icon.svg  icon-192.png  icon-512.png
│
├── extension/                   # Chrome MV3 widget
│   ├── manifest.json            # host_permissions: localhost + tunnel domains
│   ├── background.js            # service worker: discovery + request proxy
│   ├── content.js               # widget: wake word, drag, dock, STT/TTS
│   └── content.css              # glassmorphism styles
│
├── bot/                         # legacy Telegram layer (dormant)
│   ├── telegram_bot.py  network.py  scheduler.py
│
├── logs/                        # backend.log  launcher.log  tunnel.log
├── tools/cloudflared.exe        # auto-downloaded tunnel binary
│
└── Launchers:
    ├── run.bat                  # local / lan / remote
    ├── run_hidden.bat           # silent (logs only)
    ├── start_jarvis_bg.vbs      # watchdog
    ├── install_startup.bat      # one-click auto-start
    └── setup_autostart.bat      # alias
```

---

## 13. Commands Cheat-Sheet

### 🌱 First-Time Setup (scratch se — sirf ye ek file follow karein)

**Prerequisites:** Python 3.11+, Google Chrome, internet (Gemini call ke liye).

```bash
# 1) Virtual environment + dependencies
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt

# 2) .env file project root mein banayein (sirf ek line)
#    GEMINI_API_KEY=your_key_here
#    Key yahan se milegi: https://aistudio.google.com/apikey

# 3) Server chalayein aur verify karein
run.bat
#    → http://127.0.0.1:8000/health  par  {"status":"ok"}  aana chahiye

# 4) Extension load karein
#    chrome://extensions  →  Developer mode ON  →  Load unpacked  →  extension/ folder

# 5) (Optional) Phone par le jayein
run.bat remote              # terminal mein https://xxxx.trycloudflare.com milega
#    → wo URL phone browser mein kholein → "Add to Home Screen"

# 6) (Optional) Permanent silent auto-start
install_startup.bat         # ek baar chalayein, phir Windows ke sath khud chalu
```

**Note:** SQLAlchemy ki blocked `.pyd` files ka workaround (is machine ki Application Control policy) `run.bat` / `run_hidden.bat` / `start_jarvis_bg.vbs` khud handle karte hain — manually kuch nahi karna.

### 🔧 Rozana Ke Commands

```bash
# ── Normal use ──────────────────────────────────────────────
run.bat                     # local server (PC par extension ke liye)
run.bat lan                 # same Wi-Fi ke phone ke liye
run.bat remote              # kahin se bhi (HTTPS tunnel URL milega)

# ── Background / permanent ──────────────────────────────────
install_startup.bat         # ek baar chalayein → Windows ke sath auto-start
start_jarvis_bg.vbs         # background watchdog manually start karein

# ── Health checks ───────────────────────────────────────────
http://127.0.0.1:8000/health        # {"status":"ok"}
http://127.0.0.1:8000/docs          # interactive API docs
http://127.0.0.1:8000/              # PWA dashboard

# ── Extension load karna ────────────────────────────────────
chrome://extensions  →  Developer mode ON  →  Load unpacked  →  extension/ folder
(code change ke baad ⟳ Reload + page refresh zaroori hai)

# ── Logs ────────────────────────────────────────────────────
logs\backend.log    logs\launcher.log    logs\tunnel.log

# ── Manual / debugging ──────────────────────────────────────
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
venv\Scripts\python.exe tunnel.py            # tunnel only
venv\Scripts\python.exe -c "import main"     # import errors jaldi pakadne ke liye
```

**Note:** Watchdog chhupa hua process task manager mein `wscript.exe` ke naam se milta hai. Band karne ke liye usay end karein — ya `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.lnk` delete kar dein.

---

## 14. Design Principles (Jo Sab Kuch Chalata Hai)

1. **Server kabhi na mare.** Missing key, dead model, blocked DLL — koi bhi cheez poora server nahi girationi chahiye. Jin cheezon ki zaroorat nahi, unke liye warning; zaroori cheezon ke liye lazy init.
2. **User ko sach batao.** "Connection Error" sirf tab jab connection hi na ho. AI overloaded ho to "AI busy" — galat ilzaam nahi.
3. **Data jhoota na bolo.** AI ko sirf woh context do jo asli hai. Data missing ho to saaf bolo, number invent na karo.
4. **Jawab sunne ke liye likha jaye.** Persona aisi hai ke har jawab bol kar sunaya ja sake (no markdown, koi symbol nahi, 2–5 sentences).
5. **User ki zabaan bolo.** Roman Urdu sawal → Roman Urdu jawab, Devanagari nahi.
6. **Awaz user ki ho.** Mic bolte waqt band — apni hi awaz kabhi transcribe na ho.
7. **Windows-native ops.** Koi heavy daemon nahi — batch + VBScript, logs saaf, watchdog khud khada ho.
8. **Har fix ka root cause comment mein.** Code padhne wale ko "kyun" pata chale, sirf "kya" nahi.

---

## 15. Aage Ka Pehla Qadam (Aaj Ka Action Plan)

Agar aaj hi shuru karna hai, sabse zyada asar wala order yeh hai:

1. **Level 1 ki safai** — junk files hatao, git init, `requirements.txt` pin karo. (Ghar ki safai, 1 sitting.)
2. **Level 2 ka pehla feed** — `market_data.py` ko Twelve Data ya yfinance se jodo. Yeh **sabse bada single upgrade** hai: JARVIS us din se asli market par baat karega.
3. **Memory depth** — `get_history(limit=10)` ko summarization ke sath badhao taaki lambi baat-cheet bhoolay na.

Baaki sab (voice streaming, SaaS, agentic) tab jab yeh teeno tik jaayen.
