"""Retrieval over business documents (knowledge/*.md, *.txt).

Two modes:
  keyword     - TF-IDF cosine similarity, no extra services needed (default)
  embeddings  - Ollama embedding model + cosine similarity; falls back to keyword on any error
"""
import math
import re
from collections import Counter
from pathlib import Path

import requests

from . import config

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were", "for", "on", "with",
    "as", "by", "at", "it", "this", "that", "be", "from", "what", "which", "who", "how", "why", "me",
    "show", "list", "give", "do", "does", "all", "any",
}


def _tokens(text: str) -> list:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if len(t) > 1 and t not in STOPWORDS]


def _split_long(text: str, limit: int = 900) -> list:
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for para in re.split(r"\n\s*\n", text):
        if current and len(current) + len(para) > limit:
            parts.append(current.strip())
            current = ""
        current += para + "\n\n"
    if current.strip():
        parts.append(current.strip())
    return parts


def load_chunks(directory) -> list:
    folder = Path(directory)
    if not folder.is_dir():
        return []
    chunks = []
    for path in sorted(list(folder.glob("*.md")) + list(folder.glob("*.txt"))):
        text = path.read_text(encoding="utf-8")
        for section in re.split(r"\n(?=#{1,3} )", text):
            section = section.strip()
            if len(section) >= 20:
                chunks.extend({"source": path.name, "text": part} for part in _split_long(section))
    return chunks


def _cosine_dense(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _ollama_embed(text: str) -> list:
    r = requests.post(
        f"{config.OLLAMA_URL}/api/embeddings",
        json={"model": config.EMBED_MODEL, "prompt": text},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["embedding"]


class Retriever:
    def __init__(self, chunks: list, mode: str = "keyword", embed=None):
        self.chunks = chunks
        self.mode = mode
        self._embed = embed or _ollama_embed
        self._vectors = None
        self._tf = [Counter(_tokens(c["text"])) for c in chunks]
        df = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(chunks)
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    def _keyword_scores(self, query: str) -> list:
        q = Counter(_tokens(query))
        qvec = {t: q[t] * self._idf.get(t, 0.0) for t in q}
        qnorm = math.sqrt(sum(v * v for v in qvec.values()))
        scores = []
        for tf in self._tf:
            dvec = {t: tf[t] * self._idf[t] for t in tf}
            dnorm = math.sqrt(sum(v * v for v in dvec.values()))
            dot = sum(v * dvec.get(t, 0.0) for t, v in qvec.items())
            scores.append(dot / (qnorm * dnorm) if qnorm and dnorm else 0.0)
        return scores

    def _embedding_scores(self, query: str) -> list:
        if self._vectors is None:
            self._vectors = [self._embed(c["text"]) for c in self.chunks]
        qv = self._embed(query)
        return [_cosine_dense(qv, v) for v in self._vectors]

    def search(self, query: str, k: int = 3, min_score: float = 0.05) -> list:
        if not self.chunks:
            return []
        scores = None
        if self.mode == "embeddings":
            try:
                scores = self._embedding_scores(query)
            except (requests.RequestException, KeyError, ValueError):
                scores = None  # Ollama/embedding model unavailable -> keyword fallback
        if scores is None:
            scores = self._keyword_scores(query)
        ranked = sorted(zip(scores, self.chunks), key=lambda x: -x[0])[:k]
        return [{**c, "score": round(s, 3)} for s, c in ranked if s >= min_score]


_retriever = None


def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(load_chunks(config.KNOWLEDGE_DIR), config.RAG_MODE)
    return _retriever


def reset() -> None:
    global _retriever
    _retriever = None


def search(query: str, k: int = 3) -> list:
    return get_retriever().search(query, k)


def format_context(chunks: list) -> str:
    if not chunks:
        return ""
    body = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
    return f"Business notes (use for definitions and rules only):\n{body}\n"
