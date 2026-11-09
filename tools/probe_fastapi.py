"""校验 FastAPI 版服务：新端点与 /ask 新增字段（不依赖常驻进程）。"""
import json
import threading
import time
import urllib.request

import uvicorn

from app.main import app

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url):
    with OPENER.open(url, timeout=20) as r:
        return r.status, json.loads(r.read().decode())


def main():
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8016, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    base = "http://127.0.0.1:8016"
    for _ in range(60):
        try:
            get(base + "/health")
            break
        except Exception:
            time.sleep(0.2)
    try:
        st, h = get(base + "/health")
        print("GET /health", st, h)
        st, o = get(base + "/api/overview")
        print("GET /api/overview", st, "| deadline", (o.get("deadline") or {}).get("iso"),
              "| metrics", len(o["metrics"].get("main", [])), "| timeline", len(o["timeline"]))
        body = json.dumps({"question": "省赛作品提交截止是哪一天？", "top_k": 5}).encode()
        req = urllib.request.Request(base + "/ask", data=body,
                                     headers={"Content-Type": "application/json"})
        with OPENER.open(req, timeout=20) as r:
            d = json.loads(r.read().decode())
        print("POST /ask", r.status, "| strength", d["evidence_strength"]["score"],
              "| sources", len(d["sources"]), "| ics", bool(d["ics"]))
    finally:
        server.should_exit = True


if __name__ == "__main__":
    main()
