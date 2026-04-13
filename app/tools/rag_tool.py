from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class VectorStore(Protocol):
    def query(self, text: str, top_k: int = 4) -> list[dict]: ...


@dataclass(slots=True)
class InMemoryVectorStore:
    docs: list[dict]

    def query(self, text: str, top_k: int = 4) -> list[dict]:
        text_low = text.lower()
        scored = []
        for doc in self.docs:
            content = str(doc.get("content", "")).lower()
            score = 1 if text_low in content else 0
            scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored[:top_k]]


@dataclass(slots=True)
class RagTool:
    vector_store: VectorStore

    def retrieve(self, prompt: str, top_k: int = 4) -> dict[str, object]:
        matches = self.vector_store.query(prompt, top_k=top_k)
        return {"matches": matches, "count": len(matches)}
