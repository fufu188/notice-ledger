"""Zero-dependency HTTP demo server (fallback when FastAPI deps are unavailable).

This is NOT a replacement for app/main.py (the Python/FastAPI deliverable).
It exists so the work is still demonstrable on a bare Python install, which is
also what makes the 10-minute reproduction guide honest.

    python -m app.server --selftest    # start, probe /health + /ask, shut down
    python -m app.server --port 8000   # serve on http://127.0.0.1:8000
"""
import argparse
import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .answer import compose
from .cli import DOCS, build

DOCUMENTS, RETRIEVER = build()
# Bypass any injected HTTP proxy for loopback requests.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, {
                "status": "ok",
                "server": "stdlib-fallback",
                "docs": len(DOCUMENTS),
                "chunks": len(RETRIEVER.chunks),
                "doc_dir": str(DOCS),
                "llm_configured": bool(
                    os.environ.get("LLM_API_KEY")
                    and os.environ.get("LLM_BASE_URL")
                    and os.environ.get("LLM_MODEL")
                ),
            })
        elif path == "/sources":
            self._send(200, [
                {
                    "doc_id": d.doc_id,
                    "title": d.title,
                    "source": d.source,
                    "source_url": d.source_url,
                    "published_at": d.published_at,
                    "authority": d.authority,
                }
                for d in DOCUMENTS
            ])
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/ask":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"error": "invalid json"})
            return
        question = str(data.get("question", "")).strip()
        if not question:
            self._send(400, {"error": "question is required"})
            return
        top_k = int(data.get("top_k", 5))
        hits = RETRIEVER.search(question, top_k=top_k)
        min_score = float(os.environ.get("MIN_RELEVANCE_SCORE", "0.35"))
        result = compose(question, hits, min_score=min_score, use_llm=bool(data.get("use_llm")))
        self._send(200, {
            "question": result.question,
            "answer": result.text,
            "citations": result.citations,
            "conflicts": result.conflicts,
            "refused": result.refused,
            "llm_degraded": result.degraded,
            "hits": [
                {"chunk_id": h.chunk.chunk_id, "title": h.chunk.doc.title, "score": h.score}
                for h in hits
            ],
        })


def selftest():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    try:
        with OPENER.open(base + "/health", timeout=5) as response:
            print("GET /health ->", json.loads(response.read().decode("utf-8")))
        with OPENER.open(base + "/sources", timeout=5) as response:
            print("GET /sources ->", len(json.loads(response.read().decode("utf-8"))), "docs")
        payload = json.dumps({"question": "选错组别会怎样"}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            base + "/ask", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with OPENER.open(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        print("POST /ask -> refused =", result["refused"],
              "| citations =", len(result["citations"]),
              "| hits =", len(result["hits"]))
        print("POST /ask answer ->", result["answer"][:120].replace("\n", " "))
    finally:
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description="零依赖 HTTP 演示服务（FastAPI 依赖不可用时的降级方案）")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--selftest", action="store_true", help="自启自测并退出，不需要常驻进程")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"serving on http://127.0.0.1:{args.port} (stdlib fallback; Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
