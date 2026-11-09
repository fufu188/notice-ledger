"""OFFLINE EXPERIMENT RUNNER — benchmark v1 + generative baseline + ablations.

公平性约定：
- 抽取式系统与纯生成基线拿到**完全相同**的 top-k 检索片段（同一 retriever、同一 query）；
- 两者被要求做同一件事：回答问题 + 说明依据；
- 不给基线任何「遇到冲突要显式列出」「无依据要拒答」的提示——那些正是待测的设计；
- 判卷由 tools/score_eval.py 用确定性规则完成，LLM 只作被测对象，不作裁判。

产物固化落盘，运行答案时不需要 key、不需要联网。
"""
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.answer import compose  # noqa: E402
from app.cli import build  # noqa: E402
from app.llm import endpoint, resolve  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "data" / "benchmark-v1.json"
OUT = ROOT / "evidence" / "baseline" / "run-001.json"
ABL_OUT = ROOT / "evidence" / "ablation" / "table.json"

FULL = dict(authority_weight=0.15, recency_tau=540, expand=True,
            min_score=0.35, normalize_dates=True)
ABLATIONS = {
    "full": {},
    "no_authority": {"authority_weight": 0.0},
    "no_recency": {"recency_tau": 1e9},
    "no_expansion": {"expand": False},
    "no_abstain": {"min_score": 0.0},
    "no_date_norm": {"normalize_dates": False},
}

BASELINE_SYSTEM = (
    "你是问答助手。根据下面给出的资料片段回答用户问题，并说明依据来自哪条片段。"
    "直接作答，不要解释你的推理过程。"
)


def build_context(hits):
    blocks = []
    for i, h in enumerate(hits, 1):
        doc = h.chunk.doc
        blocks.append(
            f"[{i}] {doc.title} | 来源：{doc.source} | 发布：{doc.published_at}\n{h.chunk.text}"
        )
    return "\n\n".join(blocks)


def llm_answer(question, hits):
    key, base, model = resolve()
    if not key:
        raise RuntimeError("缺少 API key（LLM_API_KEY / DEEPSEEK_API_KEY）")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user", "content": f"资料片段：\n{build_context(hits)}\n\n问题：{question}"},
        ],
        "stream": False,
        "temperature": 0,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint(base), data=payload,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def extractive(question, hits, params):
    p = {**FULL, **params}
    result = compose(
        question, hits,
        min_score=p["min_score"],
        normalize_dates=p["normalize_dates"],
    )
    return {
        "answer": result.text,
        "citations": result.citations,
        "conflicts": result.conflicts,
        "refused": result.refused,
        "hits": [
            {"chunk_id": h.chunk.chunk_id, "doc_id": h.chunk.doc.doc_id, "score": h.score}
            for h in result.hits
        ],
    }


def run():
    bench = json.loads(BENCH.read_text(encoding="utf-8"))
    docs, retriever = build()
    cases = bench["cases"]
    systems = {}

    ext_hits = {}
    for c in cases:
        p = {**FULL}
        ext_hits[c["id"]] = retriever.search(
            c["question"], top_k=5,
            authority_weight=p["authority_weight"], recency_tau=p["recency_tau"],
            expand=p["expand"],
        )

    systems["extractive"] = {
        "params": FULL,
        "description": "规则裁决 + 抽取式回答 + 引用溯源 + 拒答边界",
        "answers": [
            {"case_id": c["id"], "question": c["question"],
             **extractive(c["question"], ext_hits[c["id"]], {})}
            for c in cases
        ],
    }

    gen_answers, gen_tokens, gen_errors = [], 0, []
    for c in cases:
        try:
            text, usage = llm_answer(c["question"], ext_hits[c["id"]])
            gen_tokens += usage.get("total_tokens", 0)
            gen_answers.append({
                "case_id": c["id"], "question": c["question"],
                "answer": text, "citations": [], "conflicts": [],
                "refused": False, "hits": [],
            })
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
            gen_errors.append(f"{c['id']}: {type(exc).__name__}: {str(exc)[:120]}")
            gen_answers.append({
                "case_id": c["id"], "question": c["question"],
                "answer": "", "citations": [], "conflicts": [],
                "refused": False, "hits": [], "error": str(exc)[:160],
            })
    key, base, model = resolve()
    systems["generative_baseline"] = {
        "params": {"model": model, "base_url": base, "temperature": 0, "top_k": 5},
        "description": "朴素 LLM + 与抽取式完全相同的检索片段；无冲突提示、无拒答指令",
        "tokens": gen_tokens,
        "errors": gen_errors,
        "answers": gen_answers,
    }

    abl = {}
    for name, override in ABLATIONS.items():
        p = {**FULL, **override}
        hits_cache = {}
        answers = []
        for c in cases:
            hits = retriever.search(
                c["question"], top_k=5,
                authority_weight=p["authority_weight"], recency_tau=p["recency_tau"],
                expand=p["expand"],
            )
            hits_cache[c["id"]] = hits
            answers.append({
                "case_id": c["id"], "question": c["question"],
                **extractive(c["question"], hits, override),
            })
        abl[name] = {"params": p, "answers": answers}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    ABL_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark": "data/benchmark-v1.json",
        "case_count": len(cases),
        "doc_count": len(docs),
        "key_source": "environment variable only; never stored",
        "systems": systems,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ABL_OUT.write_text(json.dumps({
        "built_at": payload["built_at"],
        "full_config": FULL,
        "ablations": abl,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"cases={len(cases)} systems={list(systems)} ablations={list(abl)}")
    print(f"baseline_tokens~={gen_tokens} errors={len(gen_errors)}")
    for e in gen_errors:
        print("  ", e)
    print("written:", OUT.relative_to(ROOT), "/", ABL_OUT.relative_to(ROOT))


if __name__ == "__main__":
    run()
