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

EVAL_SET = [
    ("省赛报名什么时候截止？", "demo-01"),
    ("作品提交截止是哪一天？", "demo-02"),
    ("国赛作品提交截止和省赛评审意见分别是什么时候？", "demo-03"),
    ("选错组别会有什么后果？", "demo-04"),
]


def build():
    docs = load_docs(DOCS)
    return docs, Retriever(chunk_docs(docs))


def run_eval(retriever, top_k):
    passed = 0
    for question, expected in EVAL_SET:
        hits = retriever.search(question, top_k=top_k)
        matched = [h.chunk.doc.doc_id for h in hits[:3]]
        ok = expected in matched
        passed += int(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {question} -> {matched[:3]}")
    print(f"recall@3 = {passed}/{len(EVAL_SET)} = {passed / len(EVAL_SET):.0%}")


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
