"""Load markdown docs with a tiny front-matter parser. No third-party deps."""
from pathlib import Path

from .models import Doc

FIELDS = ("doc_id", "title", "source", "source_url", "published_at", "authority")


def parse_front_matter(text):
    meta, body = {}, text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip()
            body = parts[2].strip()
    return meta, body


def load_docs(root):
    root = Path(root)
    docs = []
    for path in sorted(root.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        missing = [f for f in FIELDS if f not in meta]
        if missing:
            raise ValueError(f"{path.name} missing front-matter fields: {missing}")
        docs.append(
            Doc(
                doc_id=meta["doc_id"],
                title=meta["title"],
                source=meta["source"],
                source_url=meta["source_url"],
                published_at=meta["published_at"],
                authority=int(meta["authority"]),
                body=body,
            )
        )
    return docs
