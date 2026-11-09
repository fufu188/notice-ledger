"""Runtime claim index built from the OFFLINE-ONLY asset data/claims.json.

Why this exists (P-008 / D2): BM25 over paragraph chunks misses numeric facts.
Q13「国赛二等奖比例」used to retrieve only the generic "获奖资格核心要求" chunk,
while the 20% / 25% sentences were dropped by the one-chunk-per-doc dedupe.
The atomic claims asset already contains those exact spans, so we use it as a
second, structured recall path instead of trying to fix BM25 with more tuning.

Design constraints:
- zero third-party dependencies (stdlib json + existing tokenizer);
- the asset is committed, so runtime needs no LLM, no network, no key;
- every returned hit keeps the ORIGINAL Doc, so citation/authority stay honest;
- can be disabled (`use_claims=False`) for ablation.
"""
import json
from pathlib import Path

from .models import Chunk, Hit
from .retriever import tokenize

ROOT = Path(__file__).resolve().parent.parent
CLAIMS_PATH = ROOT / "data" / "claims.json"

# 数值型询问词 → 对应的断言类型，用于给结构化召回加权
TYPE_HINTS = (
    (("比例", "获奖率", "百分之", "名额", "占比", "几等奖"), {"award"}),
    (("多少页", "几页", "页数", "分钟", "多长", "时长", "几个", "多大", "多少"), {"requirement", "rule"}),
    (("截止", "期限", "什么时候", "哪一天", "日期"), {"deadline", "link"}),
    (("链接", "地址", "网址", "入口", "在哪"), {"link"}),
)


def _terms(text):
    return set(tokenize(text or ""))


class ClaimIndex:
    def __init__(self, docs, path=CLAIMS_PATH):
        self.docs = {d.doc_id: d for d in docs}
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.claims = []
        for item in raw.get("claims", []):
            if not item.get("evidence_verified", False):
                continue  # 只信任逐字回查过原文的断言
            doc = self.docs.get(item["doc_id"])
            if doc is None:
                continue
            self.claims.append({
                "id": item["claim_id"],
                "doc": doc,
                "text": item["evidence_span"],
                "value": item.get("value", ""),
                "claim_type": item.get("claim_type", ""),
                "terms": _terms(item.get("text", "") + " " + item.get("value", "")),
            })

    def preferred_types(self, question):
        out = set()
        for words, types in TYPE_HINTS:
            if any(w in question for w in words):
                out |= types
        return out

    def search(self, question, top_k=3):
        q = _terms(question)
        if not q:
            return []
        preferred = self.preferred_types(question)
        scored = []
        for claim in self.claims:
            inter = len(q & claim["terms"])
            if inter == 0 and claim["value"] not in question:
                continue
            coverage = inter / max(1, len(q))
            score = coverage * 2.0 + 0.15 * inter
            if claim["claim_type"] in preferred:
                score += 0.6
            if claim["value"] and claim["value"] in question:
                score += 0.3
            scored.append((score, claim))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:top_k]

    def to_hits(self, scored):
        return [
            Hit(
                chunk=Chunk(chunk_id=claim["id"], doc=claim["doc"], text=claim["text"]),
                score=round(score, 6),
            )
            for score, claim in scored
        ]


_INDEX_CACHE = {}


def load_claim_index(docs=None, path=CLAIMS_PATH):
    """Load (and cache) the claim index. docs=None → load from data/docs itself."""
    key = str(path)
    if key in _INDEX_CACHE:
        return _INDEX_CACHE[key]
    try:
        if docs is None:
            from .loader import load_docs
            docs = load_docs(ROOT / "data" / "docs")
        index = ClaimIndex(docs, path=path)
    except (OSError, ValueError, KeyError):
        index = None  # 资产缺失时静默降级到纯 BM25，不让系统崩
    _INDEX_CACHE[key] = index
    return index
