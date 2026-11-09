"""Paragraph-level chunking; source metadata stays attached to every chunk.

两根硬约束（都由真实缺陷倒逼出来，过程见 evidence/prompts/P-005.md）：

1. 小节标题不能单独成块。真实语料里「二、作品提交方式」这类标题与正文之间有空行，
   若切开，标题会变成只有 8 个字、零信息的 chunk —— 短文本在 BM25 里词频密度天然高，
   于是空壳标题挤掉真正含答案的段落（实测：official-01#4「二、作品提交方式」以 5.312
   分排在第二位，而含 kdocs 直链的 official-03 根本进不了 top8）。合并后标题连同正文
   一起被命中。
2. 合并后可能超长，所以合并完再按 MAX_CHARS 二次切分。
"""
import re

from .models import Chunk

MAX_CHARS = 320
# 短于此长度、且不以句末标点收尾的段落，视为小节标题而非正文
HEADING_MAX_CHARS = 40
SENTENCE_END = ("。", "！", "？", "；", "…", "”", ".")


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


def is_heading(text):
    stripped = text.strip()
    if not stripped or len(stripped) > HEADING_MAX_CHARS:
        return False
    return not stripped.endswith(SENTENCE_END)


def merge_headings(paragraphs):
    """把标题段落粘到它下面第一段正文上，避免产生零信息的空壳块。"""
    merged, pending = [], ""
    for para in paragraphs:
        if pending:
            para = pending + "\n" + para
            pending = ""
        if is_heading(para):
            pending = para
            continue
        merged.append(para)
    if pending:
        # 整篇都是标题、或末尾剩一个孤立标题：并入上一段，别丢
        if merged:
            merged[-1] = merged[-1] + "\n" + pending
        else:
            merged.append(pending)
    return merged


def chunk_docs(docs):
    chunks = []
    for doc in docs:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", doc.body) if p.strip()]
        pieces = []
        for para in merge_headings(paragraphs):
            pieces.extend(split_long(para) if len(para) > MAX_CHARS else [para])
        for index, piece in enumerate(pieces):
            chunks.append(Chunk(chunk_id=f"{doc.doc_id}#{index}", doc=doc, text=piece))
    return chunks
