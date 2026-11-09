"""OFFLINE BUILD TOOL — not part of the runtime answer path.

Run once during construction to turn notice documents into atomic claims.
The LLM proposes; deterministic code verifies. Every claim must carry an
`evidence_span` copied verbatim from the source, and this script checks that
span actually occurs in the document. Claims whose span is missing are KEPT
but flagged, so the artifact honestly shows where the model hallucinated.

This is the "offline asset factory" from CONFIRM.md D2a. Its output
(data/claims.json) is committed; the runtime stays zero-dependency.
"""
import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.llm import endpoint, resolve  # noqa: E402
from app.loader import load_docs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "data" / "docs"
OUT = ROOT / "data" / "claims.json"
LOG = ROOT / "evidence" / "claims-build.md"

SYSTEM = (
    "你是赛事通知结构化标注器。把通知拆成最小、可独立判定的事实断言。"
    "只输出 JSON 数组，不要任何解释文字、不要 Markdown 代码块。"
    "每个元素字段：text（一句话断言）、claim_type（deadline/requirement/rule/award/link/scope 之一）、"
    "value（该断言的关键值，如日期、页数、比例、链接）、"
    "evidence_span（必须逐字复制原文中的一段连续文字，不得改写、不得概括、不得编造）。"
    "一条断言只讲一件事；原文没写的不要推断；同一事实在原文出现多次只抽一次。"
    "禁止把文档标题、发布时间、来源名称、来源链接这类元数据抽成断言——只抽通知正文里的事实。"
)


def strip_fence(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start, end = text.find("["), text.rfind("]")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def call_llm(doc):
    key, base, model = resolve()
    if not key:
        raise RuntimeError("未找到 API key（LLM_API_KEY / DEEPSEEK_API_KEY）")
    prompt = (
        f"文档标题：{doc.title}\n"
        f"发布时间：{doc.published_at}\n"
        f"来源：{doc.source}\n"
        f"来源链接：{doc.source_url}\n\n"
        f"通知原文：\n{doc.body}"
    )
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
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
    content = data["choices"][0]["message"]["content"]
    return json.loads(strip_fence(content)), data.get("usage", {})


def normalize(text):
    return re.sub(r"\s+", "", text or "")


def main():
    docs = [d for d in load_docs(DOCS) if d.doc_id.startswith("official-")]
    key, base, model = resolve()
    claims, failures, usage_total = [], [], 0
    for doc in docs:
        try:
            raw, usage = call_llm(doc)
            usage_total += usage.get("total_tokens", 0)
        except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError, TimeoutError) as exc:
            failures.append(f"{doc.doc_id}: 调用/解析失败 {type(exc).__name__}: {str(exc)[:120]}")
            continue
        body_norm = normalize(doc.body)
        meta_norm = normalize(doc.source_url + " " + doc.title + " " + doc.source)
        for i, item in enumerate(raw, 1):
            if not isinstance(item, dict):
                continue
            span = str(item.get("evidence_span", "")).strip()
            span_norm = normalize(span)
            verified = bool(span) and span_norm in body_norm
            # v1 的归因错误：span 落在 frontmatter 元数据里曾被记成「模型编造」。
            # 实际那是把元数据抽成了断言，属于提示词约束缺失，不是幻觉。这里单独归类并排除。
            if not verified and span_norm and span_norm in meta_norm:
                failures.append(f"{doc.doc_id}-C{i:02d}: 元数据断言（非通知正文事实），已排除")
                continue
            if not verified and not span_norm:
                failures.append(f"{doc.doc_id}-C{i:02d}: 缺少 evidence_span，已排除")
                continue
            claims.append({
                "claim_id": f"{doc.doc_id}-C{i:02d}",
                "doc_id": doc.doc_id,
                "text": str(item.get("text", "")).strip(),
                "claim_type": str(item.get("claim_type", "scope")).strip(),
                "value": str(item.get("value", "")).strip(),
                "evidence_span": span,
                "evidence_verified": verified,
                "effective_from": doc.published_at,
                "authority": doc.authority,
                "source_url": doc.source_url,
                "produced_by": model,
            })
            if not verified:
                failures.append(f"{doc.doc_id}-C{i:02d}: evidence_span 未在原文找到（疑似改写/编造）")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "base_url": base,
        "scope": "offline-build-only; runtime does not depend on this file",
        "doc_count": len(docs),
        "claim_count": len(claims),
        "verified_count": sum(1 for c in claims if c["evidence_verified"]),
        "claims": claims,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    verified = sum(1 for c in claims if c["evidence_verified"])
    rate = f"{verified}/{len(claims)}" if claims else "0/0"
    lines = [
        "# 离线断言资产构建记录",
        "",
        f"- 构建时间：{datetime.now().isoformat(timespec='seconds')}",
        f"- 模型：`{model}`；端点：`{base}`（按官方文档，未照记忆填写）",
        "- 凭据来源：进程环境变量，**未写入任何文件、未进入仓库**",
        f"- 文档数：{len(docs)}；抽取断言：{len(claims)}；原文校验通过：{rate}",
        f"- 本次消耗：约 {usage_total} tokens",
        "- 用途边界：仅构建期运行；`data/claims.json` 固化落盘，运行时零依赖",
        "",
        "## 校验规则",
        "",
        "`evidence_span` 去空白后必须是通知原文的连续子串，否则标记 `evidence_verified=false`。"
        "未通过的条目**保留而非删除**，用于展示 LLM 会改写或编造，以及本系统如何用程序拦住它。",
        "",
        "## 未通过项",
        "",
    ]
    lines += [f"- {f}" for f in failures] if failures else ["- 无"]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"docs={len(docs)} claims={len(claims)} verified={rate} tokens~={usage_total}")
    print(f"failures={len(failures)}")
    print(f"written: {OUT.relative_to(ROOT)} / {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
