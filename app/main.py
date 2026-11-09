"""FastAPI thin wrapper over the zero-dependency core. Requires requirements.txt."""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .answer import compose
from .card import ics_text
from .cli import DOCS as DOC_DIR, build
from .llm import available, online_allowed

app = FastAPI(title="校务/赛事通知可信问答助手", version="0.1.0")
DOCUMENTS, RETRIEVER = build()
WEB_INDEX = Path(__file__).resolve().parent / "web" / "index.html"


class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    use_llm: bool = False


@app.get("/", response_class=HTMLResponse)
def index():
    if not WEB_INDEX.exists():
        return HTMLResponse("<h1>界面文件缺失</h1><p>app/web/index.html 未找到</p>", status_code=500)
    return HTMLResponse(WEB_INDEX.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {
        "status": "ok",
        "docs": len(DOCUMENTS),
        "chunks": len(RETRIEVER.chunks),
        "doc_dir": str(DOC_DIR),
        "llm_configured": available() and online_allowed(),
        "offline_key_available": available(),
        "online_llm_allowed": online_allowed(),
    }


@app.get("/sources")
def sources():
    return [
        {
            "doc_id": d.doc_id,
            "title": d.title,
            "source": d.source,
            "source_url": d.source_url,
            "published_at": d.published_at,
            "authority": d.authority,
        }
        for d in DOCUMENTS
    ]


@app.post("/ask")
def ask(request: AskRequest):
    hits = RETRIEVER.search(request.question, top_k=request.top_k)
    min_score = float(os.environ.get("MIN_RELEVANCE_SCORE", "0.35"))
    result = compose(request.question, hits, min_score=min_score, use_llm=request.use_llm)
    return {
        "question": result.question,
        "answer": result.text,
        "citations": result.citations,
        "conflicts": result.conflicts,
        "refused": result.refused,
        "llm_degraded": result.degraded,
        "hits": [
            {
                "chunk_id": h.chunk.chunk_id,
                "title": h.chunk.doc.title,
                "score": h.score,
                "excerpt": h.chunk.text[:160],
            }
            for h in hits
        ],
        "card": result.card,
        "ics": ics_text(result.card) if result.card else None,
    }
