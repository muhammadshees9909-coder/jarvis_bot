"""Expose the local JARVIS server through a secure public HTTPS tunnel.

Usage:
    python tunnel.py            # supervised Cloudflare Tunnel, ngrok fallback
    python tunnel.py --ngrok    # force ngrok

Why HTTPS matters: mobile browsers only grant microphone access and the Web
Speech API on a *secure* origin. A Cloudflare quick tunnel needs no account and
prints a free ``https://<random>.trycloudflare.com`` URL that works from any
network (mobile data included), which is exactly what the phone needs.

Resilience (why cloudflared is supervised)
------------------------------------------
logs/tunnel.log used to fill up with two kinds of failure:

  1. ``ERR Register tunnel error from server side error="Unauthorized: Tunnel
     not found"`` — the Cloudflare edge has forgotten the quick tunnel, but
     cloudflared keeps re-registering the *same* dead tunnel forever. It never
     exits and never recovers, so the VBS watchdog saw "a tunnel.py process is
     running" and left it alone. Only a brand new cloudflared process (which
     gets a brand new URL) escapes that state.
  2. ``dial tcp 127.0.0.1:8000: connectex: ... the target machine actively
     refused it`` — the tunnel was fine, the FastAPI origin was not answering.

So this script no longer trusts cloudflared to fix itself. Before every attempt
it verifies the backend (and restarts it if needed), and while cloudflared runs
it only watches things we can see *locally*: the cloudflared process itself and
the local ``/health`` origin. The tunnel's own public URL is deliberately never
probed - a slow ISP DNS lookup or a timed-out outbound request from this machine
must never be mistaken for a dead tunnel and tear down a perfectly good one.
Whenever the tunnel really drops or wedges it kills the process and rebuilds it
with exponential backoff. Stale python/cloudflared processes are cleared first
so duplicates cannot pile up.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import random
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import List, NamedTuple, Optional

BASE_DIR = Path(__file__).resolve().parent
TOOLS_DIR = BASE_DIR / "tools"

LOCAL_URL = os.getenv("JARVIS_LOCAL_URL", "http://127.0.0.1:8000").rstrip("/")
LOCAL_PORT = int(LOCAL_URL.rsplit(":", 1)[-1])

CLOUDFLARED_DOWNLOAD = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-windows-amd64.exe"
)
CLOUDFLARED_RE = re.compile(r"https://[a-z0-9][a-z0-9-]*\.trycloudflare\.com")
NGROK_API = "http://127.0.0.1:4040/api/tunnels"

# ---------------------------------------------------------------------------
# Tuning knobs (all overridable from the environment)
# ---------------------------------------------------------------------------
# Restart policy: 5s -> 10s -> 20s -> ... capped, plus a little jitter so a
# network outage does not turn into a synchronised retry storm.
BACKOFF_BASE_SECONDS = float(os.getenv("JARVIS_TUNNEL_BACKOFF_BASE", "5"))
BACKOFF_MAX_SECONDS = float(os.getenv("JARVIS_TUNNEL_BACKOFF_MAX", "120"))
# A run that stayed healthy at least this long is considered "good" and clears
# the backoff, so a rare blip never escalates to minute-long waits.
BACKOFF_RESET_AFTER = float(os.getenv("JARVIS_TUNNEL_RESET_AFTER", "300"))
# Give up on a run that never prints a public URL at all.
URL_WAIT_SECONDS = float(os.getenv("JARVIS_TUNNEL_URL_WAIT", "75"))
# How often the local origin (/health) is checked while a tunnel is up. The
# tunnel's OWN public URL is deliberately never probed: a DNS delay or an
# outbound timeout on that request (very common on this ISP) must never be read
# as "the tunnel is dead".
BACKEND_CHECK_INTERVAL = float(os.getenv("JARVIS_TUNNEL_BACKEND_CHECK", "30"))
# "Unauthorized: Tunnel not found" seen this often on a registered tunnel means
# the edge dropped it and a rebuild is the only cure.
REGISTER_ERROR_LIMIT = int(os.getenv("JARVIS_TUNNEL_REGISTER_ERRORS", "5"))
# Backend preflight: quick grace period, then start it and wait this long.
BACKEND_GRACE_SECONDS = float(os.getenv("JARVIS_BACKEND_GRACE", "25"))
BACKEND_START_SECONDS = float(os.getenv("JARVIS_BACKEND_START_TIMEOUT", "90"))

# Windows: never flash a console window for the helpers we spawn.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
_DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0) if os.name == "nt" else 0
_DEVNULL = subprocess.DEVNULL


def _banner(url: str) -> None:
    line = "=" * 64
    print("\n" + line)
    print("  JARVIS PUBLIC URL  (phone / kisi bhi network se kholein)")
    print("  " + url)
    print(line + "\n", flush=True)


# ---------------------------------------------------------------------------
# Stale process cleanup (item 3: no duplicate tunnels)
# ---------------------------------------------------------------------------
def _powershell() -> Optional[str]:
    return shutil.which("powershell") or shutil.which("pwsh")


def _kill_command_lines(pattern: str) -> List[int]:
    """Kill every process whose command line contains ``pattern``.

    Uses PowerShell's CIM view because that is the only reliable way to match on
    a command line on Windows (taskkill /IM can only match an image name). Our
    own process and our parent are excluded: the venv shim launches a second
    python with the same command line, so killing it would take the launcher
    script down with us.

    Every failure is non-fatal — cleanup is best effort, never a reason to abort.
    """
    exe = _powershell()
    if not exe:
        return []

    # NOTE: the script text itself contains `pattern`, so the PowerShell process
    # running this query would also match it — hence `-ne $PID`.
    query = (
        "Get-CimInstance Win32_Process | "
        "Where-Object {{ $_.CommandLine -like '*{pattern}*' "
        "-and $_.ProcessId -ne {own} -and $_.ProcessId -ne {parent} "
        "-and $_.ProcessId -ne $PID }} | "
        "ForEach-Object {{ $_.ProcessId }}"
    ).format(pattern=pattern, own=os.getpid(), parent=os.getppid())

    try:
        result = subprocess.run(
            [exe, "-NoProfile", "-NonInteractive", "-Command", query],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
            creationflags=_NO_WINDOW,
        )
    except Exception as exc:  # noqa: BLE001 - cleanup is best effort
        print(f"[WARN] Stale process query fail hua ({pattern}): {exc}", flush=True)
        return []

    pids = [int(token) for token in result.stdout.split() if token.isdigit()]
    killed: List[int] = []
    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=_DEVNULL,
                stderr=_DEVNULL,
                timeout=15,
                creationflags=_NO_WINDOW,
            )
            killed.append(pid)
        except Exception:  # noqa: BLE001 - the process may already be gone
            pass
    return killed


def _stop_stale_tunnels() -> None:
    """Remove leftover cloudflared / tunnel.py processes before a (re)start.

    A wedged cloudflared keeps its edge registration and a half-dead tunnel.py
    keeps its own retry state; leaving either behind is how duplicate tunnels
    (and "Tunnel not found" churn) build up.
    """
    # "tunnel --url" is the quick-tunnel signature, so a named cloudflared
    # tunnel / service on this machine is left alone.
    stale_cloudflared = _kill_command_lines("tunnel --url")
    # Match the full script path, never the bare name: a shell that merely has
    # "tunnel.py" on its own command line (the launcher that started us, or an
    # open terminal) would otherwise be killed as if it were a stale runner.
    stale_runners = _kill_command_lines(str(BASE_DIR / "tunnel.py"))
    if stale_cloudflared or stale_runners:
        print(
            "[CLEANUP] purane processes hata diye — cloudflared: "
            f"{stale_cloudflared or 'none'}, tunnel.py: {stale_runners or 'none'}",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Backend preflight (item 2: never proxy to a dead origin)
# ---------------------------------------------------------------------------
def _server_is_up(timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(LOCAL_URL + "/health", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001 - offline is a normal state here
        return False


def _wait_for_server(timeout: float, interval: float = 1.0) -> bool:
    """Poll /health until it answers 200, or the deadline passes."""
    deadline = time.time() + timeout
    while True:
        if _server_is_up():
            return True
        if time.time() >= deadline:
            return False
        time.sleep(interval)


def _port_is_open(host: str = "127.0.0.1", timeout: float = 1.5) -> bool:
    """True when *something* listens on the backend port (healthy or not)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, LOCAL_PORT))
            return True
        except OSError:
            return False


def _start_backend() -> bool:
    """Start the FastAPI backend hidden, exactly like the launcher does."""
    bat = BASE_DIR / "run_hidden.bat"
    if not bat.exists():
        print("[ERROR] run_hidden.bat nahi mila — backend start nahi ho saka.", flush=True)
        return False
    try:
        subprocess.Popen(
            ["cmd", "/c", "call", str(bat), "backend"],
            cwd=str(BASE_DIR),
            stdin=_DEVNULL,
            stdout=_DEVNULL,
            stderr=_DEVNULL,
            close_fds=True,
            creationflags=_NO_WINDOW | _DETACHED,
        )
    except Exception as exc:  # noqa: BLE001 - report and let the caller decide
        print(f"[ERROR] Backend start nahi ho saka: {exc}", flush=True)
        return False
    return True


def _ensure_backend() -> bool:
    """Verify ``/health`` before the tunnel points at it, restarting if needed.

    Order matters: a port that is open but not answering /health means a wedged
    uvicorn holding the socket, which has to be cleared before a fresh instance
    can bind. The VBS watchdog may race us here, but a second uvicorn simply
    fails to bind and exits, so the outcome stays one healthy server.
    """
    print(f"Backend preflight: {LOCAL_URL}/health ...", flush=True)
    if _wait_for_server(BACKEND_GRACE_SECONDS):
        print("Backend OK — tunnel start kar raha hoon.\n", flush=True)
        return True

    if _port_is_open():
        print(
            f"[WARN] Port {LOCAL_PORT} khula hai magar /health dead hai — "
            "stale backend hata raha hoon ...",
            flush=True,
        )
        _kill_command_lines("uvicorn main:app")
        time.sleep(2)

    print("[WARN] Backend jawab nahi de raha — ise khud start kar raha hoon ...", flush=True)
    if not _start_backend():
        return False

    if _wait_for_server(BACKEND_START_SECONDS):
        print("Backend start ho gaya.\n", flush=True)
        return True

    print(
        f"[ERROR] {BACKEND_START_SECONDS:.0f}s me backend up nahi hua — tunnel "
        "phir bhi try kar raha hoon (agle retry par dobara check hoga).\n",
        flush=True,
    )
    return False


# ---------------------------------------------------------------------------
# Cloudflare Tunnel
# ---------------------------------------------------------------------------
def _find_cloudflared() -> Optional[str]:
    found = shutil.which("cloudflared")
    if found:
        return found
    local = TOOLS_DIR / ("cloudflared.exe" if sys.platform == "win32" else "cloudflared")
    if local.exists():
        return str(local)
    return None


def _download_cloudflared() -> Optional[str]:
    if sys.platform != "win32":
        return None  # PATH lookup only on other platforms
    TOOLS_DIR.mkdir(exist_ok=True)
    dest = TOOLS_DIR / "cloudflared.exe"
    print("cloudflared nahi mila — download kar raha hoon ...")
    try:
        urllib.request.urlretrieve(CLOUDFLARED_DOWNLOAD, dest)
    except Exception as exc:  # noqa: BLE001 - fall back to ngrok / instructions
        print(f"[WARN] cloudflared download fail hua: {exc}")
        return None
    print("cloudflared download ho gaya.\n")
    return str(dest)


def _cloudflared_argv(exe: str) -> List[str]:
    """Command line for a quick tunnel.

    ``--protocol http2`` / ``--edge-ip-version 4`` are deliberate: the old logs
    are full of QUIC-over-UDP failures ("wsasendto: ... unreachable host",
    "failed to dial to edge with quic"), which is exactly what this network
    blocks, so the tunnel is pinned to the TCP path over IPv4.
    """
    return [
        exe,
        "tunnel",
        "--url", LOCAL_URL,
        "--no-autoupdate",
        "--protocol", os.getenv("JARVIS_TUNNEL_PROTOCOL", "http2"),
        "--edge-ip-version", os.getenv("JARVIS_TUNNEL_IP_VERSION", "4"),
    ]


class CloudflaredRun(NamedTuple):
    """How one cloudflared process ended."""

    reason: str
    public_url: Optional[str]
    healthy_seconds: float
    tail: List[str]


def _pipe_reader(stream, sink: "queue.Queue[Optional[str]]") -> None:
    """Drain cloudflared's stdout on a thread so the main loop stays responsive."""
    try:
        for line in stream:
            sink.put(line.rstrip())
    except Exception:  # noqa: BLE001 - the pipe dies with the process
        pass
    finally:
        sink.put(None)  # sentinel: nothing more will arrive


def _terminate(proc: subprocess.Popen) -> None:
    """Kill cloudflared and anything it spawned (it can leave helpers behind)."""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=6)
        except Exception:  # noqa: BLE001 - escalate to a hard kill
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
    try:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=_DEVNULL,
            stderr=_DEVNULL,
            timeout=15,
            creationflags=_NO_WINDOW,
        )
    except Exception:  # noqa: BLE001 - already gone is the normal case
        pass


def _run_cloudflared_once(exe: str) -> CloudflaredRun:
    """Run one cloudflared process until it dies, wedges or goes unregistered.

    Liveness is judged only from signals observable *locally*:
      * the cloudflared process itself exits / closes its output stream
      * no public URL within URL_WAIT_SECONDS      -> registration never worked
      * N registration errors on a live tunnel     -> the edge dropped it

    The tunnel's own public URL is never probed from here on purpose. An
    external HTTP request to ``https://<random>.trycloudflare.com`` frequently
    times out because of local ISP DNS delays, and treating that as a tunnel
    failure would restart a perfectly healthy tunnel (and change its URL) for no
    reason. As long as cloudflared is running, the tunnel is left alone.
    """
    argv = _cloudflared_argv(exe)
    print("Cloudflare Tunnel start ho raha hai: " + " ".join(argv[1:]) + "\n", flush=True)
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=_NO_WINDOW,
    )

    lines: "queue.Queue[Optional[str]]" = queue.Queue()
    threading.Thread(target=_pipe_reader, args=(proc.stdout, lines), daemon=True).start()

    started = time.time()
    public_url: Optional[str] = None
    healthy_since: Optional[float] = None
    register_errors = 0
    next_backend_check = 0.0
    reason = "unknown"
    tail: List[str] = []

    try:
        while True:
            if proc.poll() is not None and lines.empty():
                reason = f"cloudflared exit code {proc.returncode}"
                break

            try:
                line = lines.get(timeout=0.5)
            except queue.Empty:
                line = ""

            if line is None:
                reason = "cloudflared output stream closed"
                break

            if line:
                tail.append(line)
                del tail[:-40]
                if public_url is None:
                    match = CLOUDFLARED_RE.search(line)
                    if match:
                        public_url = match.group(0)
                        healthy_since = time.time()
                        next_backend_check = time.time() + BACKEND_CHECK_INTERVAL
                        _banner(public_url)
                    elif "ERR" in line:
                        print(line, flush=True)
                else:
                    lowered = line.lower()
                    if "unauthorized" in lowered or "register tunnel error" in lowered:
                        register_errors += 1
                        print(line, flush=True)
                        if register_errors >= REGISTER_ERROR_LIMIT:
                            reason = (
                                f"edge ne tunnel drop kar diya "
                                f"({register_errors}x 'Unauthorized: Tunnel not found')"
                            )
                            break
                    elif "err" in lowered or "error=" in lowered:
                        print(line, flush=True)

            now = time.time()
            if public_url is None:
                if now - started > URL_WAIT_SECONDS:
                    reason = f"{URL_WAIT_SECONDS:.0f}s me koi public URL nahi mila"
                    break
                continue

            # Local origin liveness only. If the backend stops answering the
            # tunnel is useless, but cloudflared is deliberately left running so
            # the public URL stays exactly the same - we simply bring the origin
            # back. No external request is ever made from this loop.
            if now >= next_backend_check:
                next_backend_check = now + BACKEND_CHECK_INTERVAL
                if not _server_is_up():
                    print(
                        "[BACKEND] local /health jawab nahi de raha — backend "
                        "restart kar raha hoon (tunnel aur URL wahi rahenge) ...",
                        flush=True,
                    )
                    _ensure_backend()
    except KeyboardInterrupt:
        reason = "interrupted"
    finally:
        _terminate(proc)

    healthy = max(0.0, time.time() - healthy_since) if healthy_since else 0.0
    return CloudflaredRun(reason, public_url, healthy, tail[-10:])


def _supervise_cloudflared(exe: str) -> int:
    """Keep exactly one healthy quick tunnel alive, rebuilding it forever."""
    failures = 0
    while True:
        # Item 2 + 3: clean slate, then a backend that actually answers.
        _stop_stale_tunnels()
        _ensure_backend()

        run = _run_cloudflared_once(exe)

        if run.reason == "interrupted":
            print("\nTunnel band kar raha hoon ...", flush=True)
            return 0

        if run.public_url:
            print(
                f"[TUNNEL] {run.public_url} band ho gaya — {run.reason} "
                f"({run.healthy_seconds:.0f}s chala).",
                flush=True,
            )
        else:
            print(f"[TUNNEL] Cloudflare ne koi URL nahi diya — {run.reason}.", flush=True)

        if not run.public_url and run.tail:
            print("        Last cloudflared output:", flush=True)
            for line in run.tail:
                print("          " + line, flush=True)

        # A tunnel that worked for a long time means "rare blip", not "broken
        # network": start the backoff from scratch.
        if run.healthy_seconds >= BACKOFF_RESET_AFTER:
            failures = 0

        failures += 1
        delay = min(BACKOFF_BASE_SECONDS * (2 ** (failures - 1)), BACKOFF_MAX_SECONDS)
        delay += random.uniform(0, 1.5)
        print(f"[RETRY] {delay:.0f}s baad naya tunnel banaya jayega (attempt {failures}).\n", flush=True)
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            print("\nTunnel band kar raha hoon ...", flush=True)
            return 0


# ---------------------------------------------------------------------------
# ngrok fallback
# ---------------------------------------------------------------------------
def _ngrok_https_url() -> Optional[str]:
    try:
        with urllib.request.urlopen(NGROK_API, timeout=2) as resp:
            data = json.load(resp)
    except Exception:  # noqa: BLE001 - API not ready yet
        return None
    for tunnel in data.get("tunnels", []):
        url = tunnel.get("public_url", "")
        if url.startswith("https://"):
            return url
    return None


def _run_ngrok() -> int:
    exe = shutil.which("ngrok")
    if not exe:
        return 1
    print("ngrok start ho raha hai ...\n")
    proc = subprocess.Popen(
        [exe, "http", str(LOCAL_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_NO_WINDOW,
    )
    url = None
    try:
        for _ in range(40):
            if proc.poll() is not None:
                break
            time.sleep(0.5)
            url = _ngrok_https_url()
            if url:
                _banner(url)
                break
        if not url:
            print(
                "[ERROR] ngrok public URL nahi mila.\n"
                "        Pehle auth token set karein: "
                "ngrok config add-authtoken <YOUR_TOKEN>"
            )
            return 1
        proc.wait()
        return 0
    except KeyboardInterrupt:
        print("\nTunnel band kar raha hoon ...")
        return 0
    finally:
        if proc.poll() is None:
            proc.terminate()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    # Print progress immediately even when stdout is not a real console (some
    # launchers capture the stream, which would otherwise block-buffer output).
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(
        description="Expose the local JARVIS server over a secure HTTPS tunnel."
    )
    parser.add_argument(
        "--ngrok", action="store_true", help="force ngrok instead of Cloudflare"
    )
    args = parser.parse_args()

    print("=" * 64)
    print("  JARVIS Remote Access — secure HTTPS tunnel (supervised)")
    print(f"  Local server : {LOCAL_URL}")
    print("=" * 64, flush=True)

    # Item 3: no stale python/cloudflared left over from an earlier run.
    _stop_stale_tunnels()

    # Item 2: the origin must answer before anything is exposed.
    _ensure_backend()

    if not args.ngrok:
        exe = _find_cloudflared() or _download_cloudflared()
        if exe:
            return _supervise_cloudflared(exe)
        print("cloudflared available nahi hai — ngrok par switch kar raha hoon ...\n")

    if shutil.which("ngrok"):
        return _run_ngrok()

    print(
        "\n[ERROR] Na cloudflared mila na ngrok. Koi ek install karein:\n"
        "\n  Cloudflare (free, no account needed):\n"
        "     winget install --id Cloudflare.cloudflared\n"
        "\n  ngrok:\n"
        "     winget install --id ngrok.ngrok\n"
        "     ngrok config add-authtoken <YOUR_TOKEN>\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
