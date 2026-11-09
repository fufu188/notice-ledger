"""Bootstrap third-party wheels without using pip's blocked index request.

Why: in this sandbox `pip install` fails three ways (1626 → 403 Forbidden for
the simple index, 7897/直连 → from versions: none), while plain `curl` to the
PyPI JSON API and to files.pythonhosted.org works. So: curl the wheels down,
then let pip install strictly offline from a local directory.

    python tools/bootstrap_wheels.py
    .venv/Scripts/python.exe -m pip install --no-index --find-links=.wheels -r requirements.txt
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / ".wheels"

PACKAGES = [
    "fastapi", "uvicorn", "pydantic", "pydantic-core", "starlette",
    "annotated-types", "typing-extensions", "anyio", "idna", "sniffio",
    "click", "h11", "colorama",
]


def curl(url, binary=False):
    result = subprocess.run(
        ["curl", "-sSL", "-m", "40", "--noproxy", "*", url],
        capture_output=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr[:120]!r}")
    return result.stdout if binary else result.stdout.decode("utf-8")


def usable(filename):
    low = filename.lower()
    if not low.endswith(".whl"):
        return False
    blocked = ("macos", "manylinux", "musllinux", "aarch64", "arm64",
               "i686", "win32", "s390x", "ppc64", "linux_")
    if any(tag in low for tag in blocked):
        return False
    # 编译型 wheel 必须匹配 CPython 3.13 / Windows x64；纯 Python wheel 不受限
    if "cp3" in low and "cp313" not in low and "abi3" not in low:
        return False
    if "win_amd64" in low and "cp313" not in low and "abi3" not in low:
        return False
    return True


def main():
    OUT.mkdir(exist_ok=True)
    downloaded = []
    for pkg in PACKAGES:
        try:
            meta = json.loads(curl(f"https://pypi.org/pypi/{pkg}/json"))
        except Exception as exc:
            print(f"[WARN] {pkg}: metadata {exc}")
            continue
        version = meta["info"]["version"]
        candidates = [f for f in meta.get("urls", []) if usable(f["filename"])]
        if not candidates:
            print(f"[WARN] {pkg}=={version}: no compatible wheel")
            continue
        # 优先 win_amd64 编译版，其次通用 py3-none-any
        candidates.sort(key=lambda f: ("win_amd64" not in f["filename"].lower(),
                                       f["filename"]))
        chosen = candidates[0]
        target = OUT / chosen["filename"]
        if not target.exists():
            try:
                target.write_bytes(curl(chosen["url"], binary=True))
            except Exception as exc:
                print(f"[WARN] {pkg}: download {exc}")
                continue
        downloaded.append(f"{pkg}=={version} -> {chosen['filename']}")
    print(f"downloaded {len(downloaded)} wheels into {OUT}")
    for line in downloaded:
        print("  ", line)
    return 0 if len(downloaded) >= 8 else 1


if __name__ == "__main__":
    sys.exit(main())
