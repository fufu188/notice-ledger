"""Start the local UI reliably: start the server, WAIT until it answers, then open the browser.

Why this exists (two real failures on 2026-11-10):
1. The old .bat opened the browser *before* Python bound port 8000, so the first
   paint was always ERR_CONNECTION_REFUSED.
2. .bat files on this machine must be pure ASCII + CRLF (see user MEMORY.md),
   so all real logic lives here in Python and the .bat is only a 5-line launcher.

Usage:
    python tools/launch_ui.py                     # start + wait + open browser + stay
    python tools/launch_ui.py --check-only         # dry run, no server, no browser
    python tools/launch_ui.py --no-browser --self-test-seconds 4   # full start/stop test
    python tools/launch_ui.py --port 8011         # use another port
"""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8000
LOG = ROOT / "start-ui.log"
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass  # logging must never break the launcher


def interpreter() -> Path:
    """Prefer the project venv; fall back to the interpreter running this script."""
    venv = ROOT / ".venv" / "Scripts" / "python.exe"
    return venv if venv.exists() else Path(sys.executable)


def port_open(port: int, timeout: float = 0.3) -> bool:
    with socket.socket() as sock:
        sock.settimeout(timeout)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def get_json(url: str, timeout: float = 3.0):
    with NO_PROXY.open(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def probe(port: int) -> dict:
    """Return health + whether the modern /api/overview endpoint exists."""
    out = {"alive": False, "overview": False, "knowledge": {}}
    try:
        out["health"] = get_json(f"http://127.0.0.1:{port}/health", timeout=1.5)
        out["alive"] = True
    except Exception as exc:
        out["health_error"] = str(exc)
        return out
    try:
        ov = get_json(f"http://127.0.0.1:{port}/api/overview", timeout=5.0)
        out["overview"] = True
        out["knowledge"] = ov.get("knowledge", {})
    except Exception as exc:
        out["overview_error"] = str(exc)
    return out


def check_only(port: int) -> int:
    log("---- CHECK ONLY (no server started, no browser opened) ----")
    log(f"project : {ROOT}")
    log(f"python  : {interpreter()}")
    log(f"log file: {LOG}")
    ok = True
    if not (ROOT / "app" / "server.py").exists():
        log("[FAIL] app/server.py not found")
        ok = False
    if not interpreter().exists():
        log("[FAIL] python interpreter not found")
        ok = False
    if port_open(port):
        state = probe(port)
        log(f"port {port}: already listening, health={state.get('health')}")
        if not state["overview"]:
            log("[FAIL] an OLD server process owns the port (no /api/overview).")
            log("       Close that console window and run this launcher again.")
            ok = False
        else:
            log(f"[OK] running server is current, knowledge={state['knowledge']}")
    else:
        log(f"port {port}: free (launcher will start a server)")
    log("[OK] check-only passed" if ok else "[FAIL] check-only failed")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--self-test-seconds", type=float, default=0.0,
                    help="auto-stop the server after N seconds (for launcher verification)")
    args = ap.parse_args()
    port = args.port
    url = f"http://127.0.0.1:{port}/"

    if args.check_only:
        return check_only(port)

    log(f"---- LAUNCH port={port} ----")

    if port_open(port):
        state = probe(port)
        if not state["overview"]:
            log("[FAIL] port is owned by an OLD server process without /api/overview.")
            log("       Close the old console window (or end its python.exe), then run again.")
            log(f"       health={state.get('health')}")
            return 1
        log(f"[OK] a current server is already running: {url}")
        proc = None
    else:
        py = str(interpreter())
        log(f"starting: {py} -m app.server --port {port} (cwd={ROOT})")
        proc = subprocess.Popen(
            [py, "-m", "app.server", "--port", str(port)],
            cwd=str(ROOT),
        )
        deadline = time.monotonic() + args.timeout
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                log(f"[FAIL] server exited early with code {proc.returncode}")
                return 1
            if port_open(port):
                break
            time.sleep(0.25)
        else:
            log(f"[FAIL] server did not bind port {port} within {args.timeout}s")
            proc.terminate()
            return 1

    state = probe(port)
    if not state["overview"]:
        log("[FAIL] server answers /health but /api/overview is missing or broken: "
            + str(state.get("overview_error", "unknown")))
        if proc:
            proc.terminate()
        return 1

    k = state["knowledge"]
    log(f"[OK] server ready: {url}")
    log(f"[OK] self-check  docs={k.get('docs')}  chunks={k.get('chunks')}  claims={k.get('claims')}")
    log(f"[OK] log file   {LOG}")

    if not args.no_browser:
        webbrowser.open(url)
        log("[OK] browser opened")
    else:
        log("[OK] browser skipped (--no-browser)")

    if args.self_test_seconds > 0:
        log(f"[OK] self-test: keeping server for {args.self_test_seconds}s, then stopping")
        time.sleep(args.self_test_seconds)
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            log("[OK] self-test: server stopped, port should be free now")
        log("[OK] SELF-TEST PASSED")
        return 0

    if proc:
        log("Keep this window open while using the page. Ctrl+C here stops the server.")
        try:
            proc.wait()
        except KeyboardInterrupt:
            log("Ctrl+C received, stopping server")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        log("[OK] server stopped")
    else:
        log("This window did not start the server; close the server window to stop it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
