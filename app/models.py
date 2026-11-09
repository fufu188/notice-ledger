"""Core data structures. Standard library only."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class Doc:
    doc_id: str
    title: str
    source: str
    source_url: str
    published_at: str
    authority: int
    body: str


@dataclass
class Chunk:
    chunk_id: str
    doc: Doc
    text: str


@dataclass
class Hit:
    chunk: Chunk
    score: float


@dataclass
class Answer:
    question: str
    text: str
    citations: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    refused: bool = False
    degraded: bool = False
    hits: List[Hit] = field(default_factory=list)
    card: object = None
