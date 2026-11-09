"""Iteratively fetch missing transitive wheels and install fully offline.

pip resolves dependencies from the local wheel directory; whenever it reports a
missing distribution, this script downloads that wheel via curl (direct PyPI
JSON API, which is reachable) and retries, until install succeeds or stalls.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".wheels"
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def curl(url, timeout=120):
    return subprocess.run(
        ["curl", "-sSL", "-m", str(timeout), "--noproxy", "*", url],
        capture_output=True, timeout=timeout + 20,
    ).stdout


def usable(filename):
    low = filename.lower()
    if not low.endswith(".whl"):
        return False
    if any(t in low for t in ("macos", "manylinux", "musllinux", "aarch64",
                              "arm64", "i686", "win32", "s390x", "ppc64", "linux_")):
        return False
    if "cp3" in low and "cp313" not in low and "abi3" not in low:
        return False
    if "win_amd64" in low and "cp313" not in low and "abi3" not in low:
        return False
    return True


def fetch(pkg):
    try:
        meta = json.loads(curl(f"https://pypi.org/pypi/{pkg}/json", 180).decode("utf-8"))
    except Exception as exc:
        print(f"  [WARN] {pkg}: metadata {exc}")
        return False
    candidates = [f for f in meta.get("urls", []) if usable(f["filename"])]
    if not candidates:
        print(f"  [WARN] {pkg}: no compatible wheel")
        return False
    candidates.sort(key=lambda f: ("win_amd64" not in f["filename"].lower(), f["filename"]))
    chosen = candidates[0]
    target = OUT / chosen["filename"]
    if not target.exists():
        target.write_bytes(curl(chosen["url"], 180))
    print(f"  + {pkg} -> {chosen['filename']}")
    return True


def main():
    OUT.mkdir(exist_ok=True)
    seen = set()
    for round_no in range(1, 9):
        proc = subprocess.run(
            [str(PY), "-m", "pip", "install", "--no-index",
             "--find-links=.wheels", "-r", "requirements.txt",
             "--disable-pip-version-check"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        out = proc.stdout + proc.stderr
        if proc.returncode == 0:
            print(f"round {round_no}: install OK")
            print(out.strip().splitlines()[-3:])
            return 0
        names = re.findall(r"No matching distribution found for ([A-Za-z0-9_.-]+)", out)
        names += re.findall(r"Could not find a version that satisfies the requirement ([A-Za-z0-9_.-]+)", out)
        fresh = [n for n in dict.fromkeys(names) if n.lower() not in seen]
        if not fresh:
            print(f"round {round_no}: stalled, no new missing package")
            print(out[-800:])
            return 1
        print(f"round {round_no}: missing {fresh}")
        for name in fresh:
            seen.add(name.lower())
            fetch(name)
    print("gave up after 8 rounds")
    return 1


if __name__ == "__main__":
    sys.exit(main())
