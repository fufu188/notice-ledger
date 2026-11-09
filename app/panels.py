"""UI 面板数据聚合（/api/overview）。

设计约束（与项目其余部分一致）：
- 只读已提交的本地资产，不联网、不调用 LLM；
- 任何字段抽不到就返回 null，由前端隐藏对应模块，绝不编造；
- FastAPI 与标准库降级服务共用本模块，保证两套服务对外行为一致。
"""
import json
from datetime import datetime
from pathlib import Path

from .card import build_card, parse_deadline

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load(name, default):
    path = DATA / name
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return default


def _deadline(retriever):
    """从真实检索链路上抽截止时间：与用户提问走同一条 build_card 规则。"""
    if retriever is None:
        return None
    try:
        hits = retriever.search("省赛作品提交截止是哪一天？", top_k=5)
        if not hits:
            return None
        card = build_card("省赛作品提交截止是哪一天？", hits)
    except Exception:
        return None
    raw = card["fields"]["截止时间"]
    due = parse_deadline(raw)
    if due is None:
        return None
    return {
        "raw": raw,
        "iso": due.isoformat(timespec="minutes"),
        "source": "official-04",
        "note": "取自官方 WPS 提交表单字段说明，规则抽取，未做语义改写",
    }


def overview(documents, retriever=None):
    channels = _load("channels.json", {})
    coverage = _load("coverage.json", {})
    metrics = _load("metrics.json", {})
    claims = _load("claims.json", {})

    doc_meta = channels.get("docs", {})
    timeline = []
    for doc in documents:
        meta = doc_meta.get(doc.doc_id, {})
        timeline.append({
            "doc_id": doc.doc_id,
            "title": doc.title,
            "published_at": doc.published_at or None,
            "authority": doc.authority,
            "channel": meta.get("channel"),
            "channel_label": meta.get("label"),
            "source_url": doc.source_url,
        })
    timeline.sort(key=lambda d: (d["published_at"] or "", -d["authority"]), reverse=True)

    return {
        "knowledge": {
            "docs": len(documents),
            "chunks": len(retriever.chunks) if retriever is not None else None,
            "claims": claims.get("claim_count"),
            "verified": claims.get("verified_count"),
            "claims_built_at": claims.get("built_at"),
        },
        "channels": channels.get("levels", []),
        "channel_cases": channels.get("cross_channel_cases", []),
        "coverage_cases": coverage.get("cases", []),
        "timeline": timeline,
        "deadline": _deadline(retriever),
        "metrics": metrics,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
