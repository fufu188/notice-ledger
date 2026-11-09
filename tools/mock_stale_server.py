"""模拟「页面已更新、后端进程还是旧版」的服务，用于复验前端的接口失败态。

背景：本项目曾出现「面板显示不可用 / 渠道层级空白」，根因不是逻辑错误，而是
浏览器连着一个更早启动的服务进程——那个进程没有 /api/overview 端点，数据也是旧的。
前端现在把这类失败显式化（顶栏「数据不同步」+ 具体原因 + 重新请求），
本脚本就是用来复现该场景、确认提示到位的。

用法：
    python tools/mock_stale_server.py --port 8040
    # 然后访问 http://127.0.0.1:8040/#tab=timeline，应看到：
    #   顶栏琥珀色「数据不同步」、左栏与右栏的错误框（含 HTTP 404 与重启命令）、「重新请求」按钮
"""
import argparse
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.server import Handler  # noqa: E402


class StaleHandler(Handler):
    """/api/overview 一律 404，其余端点照常，模拟旧版后端。"""

    def do_GET(self):
        if self.path.split("?")[0] == "/api/overview":
            self._send(404, {"error": "not found", "hint": "old server process"})
            return
        super().do_GET()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8040)
    args = ap.parse_args()
    print(f"stale mock on http://127.0.0.1:{args.port}/  (/api/overview -> 404)")
    ThreadingHTTPServer(("127.0.0.1", args.port), StaleHandler).serve_forever()


if __name__ == "__main__":
    main()
