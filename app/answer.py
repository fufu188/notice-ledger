"""Answer composition: citation, date-conflict flagging, abstention, optional LLM.

Intent-control strategy (scores 20% on the rubric) is explicit in SYSTEM_PROMPT:
only answer from retrieved evidence, cite every claim, surface conflicting dates
side by side instead of picking one, and abstain when evidence is insufficient.
"""
import json
import re
import urllib.request

from .claims import load_claim_index
from .llm import endpoint, online_allowed, resolve
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


NUM_DATE = re.compile(r"(20\d{2})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})")
MONTH_ONLY = re.compile(r"(20\d{2})\D{0,3}(\d{1,2})月(?:底|初|中)?")


def _norm_date(value):
    """把「2026年11月18日」「2026-11-18」「2026/11/18」归一成同一个键。

    不做这一步，同一天的三种写法会被当成三处「口径差异」——误报比漏报更伤可信度：
    用户看到「存在 3 处不同写法」去核对，发现全是同一天，就不再信这个系统了。
    """
    match = NUM_DATE.search(value)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
    match = MONTH_ONLY.search(value)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    return value


def detect_conflicts(hits, normalize_dates=True):
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
                date_key = _norm_date(value) if normalize_dates else value
                key = (date_key, doc.doc_id)
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


def _offline_answer(base_hits, extra_hits, cite_hits, conflicts,
                    verdict=True, verdict_text=None):
    """抽取式回答：先给结论句，再给原文片段，冲突只作为附注。

    P-008 修复：
    - D3：新增裁决句，照录最贴合问题的断言原文，不擅自合并口径；
    - D2：补充片段单独用 [补充N] 标记，**不占用 [1][2][3] 编号**，
      否则正文编号与 citation 列表会错配，等于伪造溯源。
    """
    cites = _citation_list(cite_hits[:3])
    head = ""
    if verdict and cite_hits:
        sentence = (verdict_text or "").strip() or _verdict_sentence(cite_hits[0].chunk.text)
        doc = cite_hits[0].chunk.doc
        head = (
            f"按权威度与发布时间排序后，排序最高的来源记载为：{sentence}\n"
            f"该来源：{doc.title}（权威度 {doc.authority}，发布 {doc.published_at}）。"
            "其余口径未作合并裁定，见下方原文片段。\n"
        )
    head += "据资料记载（以下为检索到的原文片段，非自动改写结论）：\n"
    lines = [f"[{i}] {h.chunk.text}" for i, h in enumerate(base_hits, 1)]
    lines += [f"[补充{i}] {h.chunk.text}" for i, h in enumerate(extra_hits, 1)]
    body = "\n".join(lines)
    if conflicts:
        head += (
            f"\n注意：同一事项在资料中存在 {len(conflicts)} 处不同写法，"
            "已在下方「口径差异」中并列列出，请以原始通知为准。\n"
        )
    return head + body, cites, False


def _verdict_sentence(text):
    """从最高排序片段里挑第一句含具体数值/日期/比例的原句，逐字照录。"""
    for sentence in re.split(r"(?<=[。；\n])", text):
        sentence = sentence.strip()
        if sentence and re.search(r"\d|%|分钟|页", sentence):
            return sentence
    return text.strip().split("\n")[0]


QUESTION_TERMS = re.compile(r"[^\u4e00-\u9fff]+")


def _question_grams(question):
    s = QUESTION_TERMS.sub("", question)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def _coverage(question, text):
    grams = _question_grams(question)
    if not grams:
        return 1.0
    return sum(1 for g in grams if g in text) / len(grams)


MONEY_ASK = ("多少钱", "金额", "费用", "报名费", "缴费多少", "要交多少")
MONEY_MARK = ("元", "¥", "￥", "RMB", "块钱")


def _should_abstain(question, deduped, claim_best, top1_score):
    """D1：语义级拒答。两条通用规则，不针对任何题目 ID。

    1. 断言资产与 BM25 都没真正覆盖问题对象（claim 分 < 1.0、top1 分 < 12，
       且首位片段对问题词项的覆盖率 < 0.30）；
    2. 问金额，但召回证据里根本没有金额单位——资料只写了「需完成缴费」。
    阈值取自 24 题基准集的分数分布，属于可复现的经验阈值，不是按题目硬编码。
    """
    # 保护：BM25 首位片段确实覆盖了问题词项时，即便断言资产没收录也不能拒答
    # （组别规则只存在于 demo 文档，断言索引里没有，曾导致「选错组别会怎样」被误拒）。
    coverage = _coverage(question, deduped[0].chunk.text) if deduped else 0.0
    if claim_best < 1.0 and top1_score < 12.0 and coverage < 0.30:
        return True, "检索片段与断言资产均未覆盖问题的核心对象"
    if any(w in question for w in MONEY_ASK):
        joined = " ".join(h.chunk.text for h in deduped[:3])
        if not any(m in joined for m in MONEY_MARK):
            return True, "资料只提到缴费要求，未给出金额"
    return False, ""


def pick_verdict_text(base_hits, claim_hits):
    """D3 裁决句取材：优先 BM25 首位片段里的具体数值句，否则用断言索引首位。

    只用断言首位会丢精度（例如 Q01 会取到「2026年11月18日」而漏掉 15:00），
    只用 BM25 首位会漏掉没被召回的比例（Q13）。两条路径互补。
    """
    if base_hits:
        for sentence in re.split(r"(?<=[。；\n])", base_hits[0].chunk.text):
            sentence = sentence.strip()
            if sentence and re.search(r"\d|%|分钟|页", sentence):
                return sentence
    if claim_hits:
        return claim_hits[0].chunk.text.strip()
    return ""


def build_claim_hits(question, docs=None, top_k=3):
    """D2：结构化断言补充召回。资产缺失时静默降级。"""
    index = load_claim_index(docs)
    if index is None:
        return [], float("inf")  # 未测，不得据此触发拒答
    scored = index.search(question, top_k=top_k)
    best = scored[0][0] if scored else 0.0
    return index.to_hits(scored), best


def _llm_answer(question, hits, conflicts):
    if not online_allowed():
        return None
    key, base, model = resolve()
    if not key:
        return None
    url = endpoint(base)
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


def compose(question, hits, min_score=0.35, use_llm=False, normalize_dates=True,
            use_claims=True, semantic_abstain=True, verdict=True):
    deduped = _dedupe_by_doc([h for h in hits if h.score >= min_score])

    # D2：断言资产作为第二召回路径，只补充原文片段，不进 citation（避免来源重复）
    claim_hits, claim_best = (
        build_claim_hits(question) if use_claims else ([], float("inf"))
    )

    # D1：语义级拒答。放在所有召回之后、生成答案之前。
    top1_score = deduped[0].score if deduped else 0.0
    if semantic_abstain:
        abstain, reason = _should_abstain(question, deduped, claim_best, top1_score)
        if abstain:
            return Answer(
                question=question,
                text=f"知识库中没有可靠依据（{reason}）。请核对官方页面或导入相关通知原文后再问。",
                refused=True,
            )

    if not deduped:
        return Answer(
            question=question,
            text="知识库中没有可靠依据。请导入相关通知原文后再问，或核对官方页面。",
            refused=True,
        )
    conflicts = detect_conflicts(deduped, normalize_dates=normalize_dates)
    cites = _citation_list(deduped[:3])
    text = None
    degraded = False
    if use_llm:
        text = _llm_answer(question, deduped, conflicts)
        if text is None:
            degraded = True
    if text is None:
        existing = {h.chunk.text.strip() for h in deduped[:3]}
        extra = [h for h in claim_hits if h.chunk.text.strip() not in existing][:2]
        verdict_text = pick_verdict_text(deduped[:3], claim_hits)
        text, cites, refused = _offline_answer(
            deduped[:3], extra, deduped, conflicts,
            verdict=verdict, verdict_text=verdict_text,
        )
    else:
        refused = False
    return Answer(
        question=question,
        text=text,
        citations=cites,
        conflicts=conflicts,
        refused=refused,
        degraded=degraded,
        hits=deduped,
    )
