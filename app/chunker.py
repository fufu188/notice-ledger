"""Paragraph-level chunking; source metadata stays attached to every chunk."""
import re

from .models import Chunk

MAX_CHARS = 320


def split_long(text, limit=MAX_CHARS):
    sentences = re.split(r"(?<=[。！？；\n])", text)
    out, buf = [], ""
    for sentence in sentences:
        if not sentence.strip():
            continue
        if len(buf) + len(sentence) > limit and buf:
            out.append(buf.strip())
            buf = sentence
        else:
            buf += sentence
    if buf.strip():
        out.append(buf.strip())
    return out


def chunk_docs(docs):
    chunks = []
    for doc in docs:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", doc.body) if p.strip()]
        pieces = []
        for para in paragraphs:
            pieces.extend(split_long(para) if len(para) > MAX_CHARS else [para])
        for index, piece in enumerate(pieces):
            chunks.append(Chunk(chunk_id=f"{doc.doc_id}#{index}", doc=doc, text=piece))
    return chunks
