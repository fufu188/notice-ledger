"""一次性探针：同进程起服务、跑问题集、打印结构化结果后退出。
用于验证新端点与前端所需字段（不依赖常驻后台进程）。"""
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from app.server import Handler

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

QUESTIONS = [
    "省赛作品提交截止是哪一天？",
    "作品提交截止到底是 11 月 18 日还是 12 月 27 日？",
    "省赛和国赛的作品提交截止分别是哪一天？",
    "省赛作品提交入口在哪里？",
    "官方通知和交接整理稿的说法不一致时，应该以哪个为准？",
    "选错组别会有什么后果？",
    "技术文档不能超过多少页？",
    "今天天气适合放风筝吗",
]


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    try:
        with OPENER.open(base + "/api/overview", timeout=8) as r:
            o = json.loads(r.read().decode())
        print("overview:", o["knowledge"], "| deadline:", (o.get("deadline") or {}).get("iso"),
              "| channels:", len(o["channels"]), "| timeline:", len(o["timeline"]))
        for q in QUESTIONS:
            body = json.dumps({"question": q, "top_k": 5}, ensure_ascii=False).encode()
            req = urllib.request.Request(base + "/ask", data=body,
                                         headers={"Content-Type": "application/json"})
            with OPENER.open(req, timeout=15) as r:
                d = json.loads(r.read().decode())
            st = d.get("evidence_strength") or {}
            print(f"\nQ {q}")
            print(f"  refused={d['refused']} strength={st.get('score')}/{st.get('level')} "
                  f"conflicts={len(d['conflicts'])} sources={len(d['sources'])} "
                  f"hits={len(d['hits'])} card={bool(d['card'])} ics={bool(d['ics'])}")
            print("  head:", d["answer"][:70].replace("\n", " "))
            if d["conflicts"]:
                print("  c1:", d["conflicts"][0][:120])
            if d["sources"]:
                s = d["sources"][0]
                print("  s1:", s["title"][:28], "| auth", s["authority"], "| score", s["score"],
                      "| excerpt", len(s["excerpt"]))
        with OPENER.open(base + "/", timeout=8) as r:
            html = r.read().decode()
        print("\nGET / ->", r.status, len(html), "bytes | hero:", "让每一条通知" in html,
              "| cmdk:", "cmdkList" in html, "| eval:", "消融" in html)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
