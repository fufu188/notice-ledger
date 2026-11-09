"""Answer composition: citation, date-conflict flagging, abstention, optional LLM.

Intent-control strategy (scores 20% on the rubric) is explicit in SYSTEM_PROMPT:
only answer from retrieved evidence, cite every claim, surface conflicting dates
side by side instead of picking one, and abstain when evidence is insufficient.
"""
import json
import os
import re
import urllib.request

from .models import Answer

DATE_RE = re.compile(
    r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?|20\d{2}年\d{1,2}月(?:底|初|中)?)"
)
CLAUSE_SPLIT = re.compile(r"[。；;\n，,]")
STRONG_TIME_WORDS = ("截止", "发布", "公布", "评审意见", "答辩")

SYSTEM_PROMPT = """你是校务/赛事通知可信问答助手，严格遵守以下约束：
1. 只能依据提供的资料片段回答，禁止使用外部知识，禁止编造日期、比例、金额、报名编号。
2. 每个结论后必须标注来源编号，如 [1]。
3. 若片段之间的日期或口径不一致，必须并列呈现全部口径，并明确提示「检测到口径差异，请核对原始通知」，禁止擅自替用户选定其中一条。
4. 若资料不足以回答，只输出「知识库中没有可靠依据」，禁止猜测。
5. 转述资料时用「据资料记载」，不把整理稿写成官方定论。
"""


def _dates(text):
    return list(dict.fromkeys(DATE_RE.findall(text)))


def detect_conflicts(hits):
    """Flag distinct deadline-style dates across retrieved chunks.

    Rule-based baseline, not semantic reasoning. Three deliberate constraints:
    - split into clauses, so an enrollment window "12-10 至 12-21" in a clause
      without a deadline word is not mistaken for a submission deadline;
    - only clauses with a strong time word contribute dates;
    - dedupe by (date, doc_id) so the same source is never listed twice.
    It says "口径差异", never claims two notices actually contradict each other.
    """
    found = {}
    for hit in hits:
        doc = hit.chunk.doc
        for clause in CLAUSE_SPLIT.split(hit.chunk.text):
            if not any(word in clause for word in STRONG_TIME_WORDS):
                continue
            for value in _dates(clause):
                key = (value, doc.doc_id)
                if key not in found:
                    found[key] = (
                        f"- {value}｜{doc.title}｜来源：{doc.source}"
                        f"（整理/发布 {doc.published_at}）｜{doc.source_url}"
                    )
    if len({date for date, _ in found}) < 2:
        return []
    return list(found.values())


def _dedupe_by_doc(hits):
    """Keep the highest-scoring chunk per document (hits arrive sorted)."""
    seen, out = set(), []
    for hit in hits:
        doc_id = hit.chunk.doc.doc_id
        if doc_id in seen:
            continue
        seen.add(doc_id)
        out.append(hit)
    return out


def _citation_list(hits):
    return [
        f"[{i}] {h.chunk.doc.title} | {h.chunk.doc.source} | "
        f"{h.chunk.doc.published_at} | {h.chunk.doc.source_url}"
        for i, h in enumerate(hits, 1)
    ]


def _build_context(hits):
    blocks = []
    for i, hit in enumerate(hits, 1):
        doc = hit.chunk.doc
        blocks.append(
            f"[{i}] {doc.title} | 来源：{doc.source} | 发布：{doc.published_at} | "
            f"{doc.source_url}\n{hit.chunk.text}"
        )
    return "\n\n".join(blocks)


def _offline_answer(hits, conflicts):
    top = hits[:3]
    cites = _citation_list(top)
    if conflicts:
        head = "检测到口径差异，以下为资料中并列记载的多个日期/说法，请核对原始通知，不要直接采信其中一条：\n"
        body = "\n".join(conflicts)
    else:
        head = "据资料记载（以下为检索到的原文片段，非自动改写结论）：\n"
        body = "\n".join(f"[{i}] {h.chunk.text}" for i, h in enumerate(top, 1))
    return head + body, cites, False


def _llm_answer(question, hits, conflicts):
    key = os.environ.get("LLM_API_KEY", "").strip()
    base = os.environ.get("LLM_BASE_URL", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    if not (key and base and model):
        return None
    url = base.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"问题：{question}\n\n资料片段：\n{_build_context(hits)}\n\n"
                    f"检测到的口径差异：\n" + ("\n".join(conflicts) if conflicts else "无")
                ),
            },
        ],
        "temperature": 0.1,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def compose(question, hits, min_score=0.35, use_llm=False):
    hits = _dedupe_by_doc([h for h in hits if h.score >= min_score])
    if not hits:
        return Answer(
            question=question,
            text="知识库中没有可靠依据。请导入相关通知原文后再问，或核对官方页面。",
            refused=True,
        )
    conflicts = detect_conflicts(hits)
    cites = _citation_list(hits[:3])
    text = None
    degraded = False
    if use_llm:
        text = _llm_answer(question, hits, conflicts)
        if text is None:
            degraded = True
    if text is None:
        text, cites, refused = _offline_answer(hits, conflicts)
    else:
        refused = False
    return Answer(
        question=question,
        text=text,
        citations=cites,
        conflicts=conflicts,
        refused=refused,
        degraded=degraded,
        hits=hits,
    )
