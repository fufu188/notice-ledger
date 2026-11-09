"""Zero-dependency CLI. Runs on a bare Python install."""
import argparse
import os
from pathlib import Path

from .answer import compose
from .chunker import chunk_docs
from .loader import load_docs
from .retriever import Retriever

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "docs"

# 评测集：全部指向真实官方语料（data/docs/official-*.md），只保留一条 demo 用于
# 「二手整理稿 vs 官方原文」的权威度对比。每题标注的是「必须被召回的文档」。
EVAL_SET = [
    ("省赛作品提交截止是哪一天？", "official-01"),
    ("省赛作品提交入口在哪里", "official-01"),
    ("选错组别会有什么后果？", "demo-04"),
    ("省赛一等奖的比例是多少？", "official-05"),
    ("技术文档不能超过多少页？", "official-06"),
    ("演示视频要多长时间？", "official-06"),
    ("国赛作品提交截止是什么时候？", "official-02"),
    ("作品介绍文档要写哪些内容？", "official-04"),
]


def build():
    docs = load_docs(DOCS)
    return docs, Retriever(chunk_docs(docs))


def run_eval(retriever, top_k):
    passed3 = passed5 = 0
    for question, expected in EVAL_SET:
        hits = retriever.search(question, top_k=max(top_k, 5))
        matched = [h.chunk.doc.doc_id for h in hits]
        ok3, ok5 = expected in matched[:3], expected in matched[:5]
        passed3 += int(ok3)
        passed5 += int(ok5)
        mark = "PASS" if ok3 else ("TOP5" if ok5 else "FAIL")
        print(f"[{mark}] {question} -> {matched[:5]}")
    n = len(EVAL_SET)
    print(f"recall@3 = {passed3}/{n} = {passed3 / n:.0%} | recall@5 = {passed5}/{n} = {passed5 / n:.0%}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="校务/赛事通知可信问答助手（离线可跑）")
    parser.add_argument("question", nargs="?", help="要问的问题")
    parser.add_argument("--sources", action="store_true", help="列出当前知识库文档")
    parser.add_argument("--eval", action="store_true", help="运行内置评测集，输出 recall@3")
    parser.add_argument("--llm", action="store_true", help="复杂任务时启用可选云端生成（需环境变量）")
    parser.add_argument("--top-k", type=int, default=int(os.environ.get("RETRIEVAL_TOP_K", "5")))
    args = parser.parse_args(argv)

    docs, retriever = build()
    if args.sources:
        for doc in docs:
            print(f"{doc.doc_id} | {doc.title} | {doc.source} | {doc.published_at}")
        return
    if args.eval:
        run_eval(retriever, args.top_k)
        return
    if not args.question:
        parser.print_help()
        return

    hits = retriever.search(args.question, top_k=args.top_k)
    min_score = float(os.environ.get("MIN_RELEVANCE_SCORE", "0.35"))
    result = compose(args.question, hits, min_score=min_score, use_llm=args.llm)
    print(f"问题：{result.question}")
    print(f"回答：\n{result.text}")
    print("\n来源：")
    for line in result.citations:
        print("  " + line)
    if result.conflicts:
        print(f"\n口径差异 {len(result.conflicts)} 条（已在回答中并列呈现，须核对原始通知）")
    print(f"\n拒答={result.refused} | LLM降级={result.degraded} | 命中 {len(result.hits)} 条")
    print("检索得分：" + ", ".join(f"{h.chunk.chunk_id}={h.score}" for h in hits))


if __name__ == "__main__":
    main()
