from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass


_WORD_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


@dataclass(slots=True)
class RagChunk:
    """Representa um trecho recuperável para compor o contexto do agente."""

    source: str
    content: str


class RagEngine:
    """Motor RAG simples baseado em similaridade léxica (TF-IDF leve)."""

    def __init__(self, chunks: list[RagChunk]):
        self._chunks = chunks
        self._idf = self._build_idf(chunks)

    def buscar(self, consulta: str, top_k: int = 4) -> list[RagChunk]:
        if not consulta or not self._chunks:
            return []

        q_terms = self._tokenize(consulta)
        if not q_terms:
            return []

        query_tf = Counter(q_terms)
        query_vec = self._tfidf(query_tf)

        scored: list[tuple[float, RagChunk]] = []
        for chunk in self._chunks:
            doc_tf = Counter(self._tokenize(chunk.content))
            doc_vec = self._tfidf(doc_tf)
            score = self._cosine(query_vec, doc_vec)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[: max(top_k, 0)]]

    def montar_contexto(self, consulta: str, top_k: int = 4) -> str:
        encontrados = self.buscar(consulta, top_k=top_k)
        if not encontrados:
            return ""

        blocos = []
        for idx, chunk in enumerate(encontrados, start=1):
            blocos.append(f"[RAG {idx}] Fonte: {chunk.source}\n{chunk.content.strip()}")
        return "\n\n".join(blocos)

    def _build_idf(self, chunks: list[RagChunk]) -> dict[str, float]:
        n_docs = max(len(chunks), 1)
        doc_freq: Counter[str] = Counter()

        for chunk in chunks:
            terms = set(self._tokenize(chunk.content))
            doc_freq.update(terms)

        return {term: math.log((1 + n_docs) / (1 + freq)) + 1.0 for term, freq in doc_freq.items()}

    def _tfidf(self, tf: Counter[str]) -> dict[str, float]:
        vec: dict[str, float] = {}
        for term, count in tf.items():
            idf = self._idf.get(term)
            if idf is None:
                continue
            vec[term] = (1 + math.log(count)) * idf
        return vec

    def _cosine(self, a: dict[str, float], b: dict[str, float]) -> float:
        if not a or not b:
            return 0.0

        common = set(a.keys()) & set(b.keys())
        dot = sum(a[t] * b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))

        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _tokenize(self, text: str) -> list[str]:
        return [t.lower() for t in _WORD_RE.findall(text or "")]
