"""Lexical retrieval: Chinese char bigrams + BM25 + source-authority / recency priors.

Honest scope: this is a strong lexical baseline, NOT a semantic vector model.
Embedding / hybrid retrieval is a planned iteration (see README roadmap).
Zero third-party dependencies so the core runs on a bare Python install.
"""
import math
import re
from collections import Counter
from datetime import date

from .models import Hit

K1 = 1.5
B = 0.75
CJK = re.compile(r"[\u4e00-\u9fff]+")
LATIN = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text):
    tokens = []
    for seg in CJK.findall(text):
        if len(seg) == 1:
            tokens.append(seg)
        else:
            tokens.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    tokens.extend(t.lower() for t in LATIN.findall(text))
    return tokens


def _days_since(iso_text):
    try:
        year, month, day = (int(x) for x in iso_text.split("-"))
        return (date.today() - date(year, month, day)).days
    except (ValueError, TypeError):
        return 3650


class Retriever:
    def __init__(self, chunks):
        self.chunks = chunks
        self.tfs = []
        self.df = Counter()
        self.lengths = []
        for chunk in chunks:
            tokens = tokenize(chunk.text + " " + chunk.doc.title)
            tf = Counter(tokens)
            self.tfs.append(tf)
            self.lengths.append(len(tokens))
            for term in tf:
                self.df[term] += 1
        self.n = len(chunks)
        self.avg_len = sum(self.lengths) / max(1, self.n)

    def _idf(self, term):
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query, top_k=5, authority_weight=0.15, recency_tau=540):
        query_terms = set(tokenize(query))
        hits = []
        for index, tf in enumerate(self.tfs):
            dl = self.lengths[index] or 1
            score = 0.0
            for term in query_terms:
                freq = tf.get(term, 0)
                if not freq:
                    continue
                denom = freq + K1 * (1 - B + B * dl / (self.avg_len or 1))
                score += self._idf(term) * freq * (K1 + 1) / denom
            if score <= 0:
                continue
            doc = self.chunks[index].doc
            score *= 1 + authority_weight * (doc.authority - 1)
            age = max(0, _days_since(doc.published_at))
            score *= 0.7 + 0.3 * math.exp(-age / recency_tau)
            hits.append(Hit(chunk=self.chunks[index], score=round(score, 6)))
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:top_k]
