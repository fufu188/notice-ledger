"""FastAPI thin wrapper over the zero-dependency core. Requires requirements.txt."""
import os

from fastapi import FastAPI
from pydantic import BaseModel

from .answer import compose
from .cli import DOCS as DOC_DIR, build

app = FastAPI(title="校务/赛事通知可信问答助手", version="0.1.0")
DOCUMENTS, RETRIEVER = build()


class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    use_llm: bool = False


@app.get("/health")
def health():
    return {
        "status": "ok",
        "docs": len(DOCUMENTS),
        "chunks": len(RETRIEVER.chunks),
        "doc_dir": str(DOC_DIR),
        "llm_configured": bool(
            os.environ.get("LLM_API_KEY")
            and os.environ.get("LLM_BASE_URL")
            and os.environ.get("LLM_MODEL")
        ),
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
    }
