from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass(slots=True)
class PostgresTool:
    """Inspector de schema e executor de query segura (somente leitura)."""

    resolve_db_from_slug: Callable[[str], str] | None = None

    def inspect_schema(self, slug: str) -> dict[str, object]:
        db_alias = self._db_alias(slug)
        return {
            "db_alias": db_alias,
            "tables": ["users", "orders", "audit_log"],
            "note": "mock schema; conecte driver real para produção",
        }

    def safe_query(self, slug: str, sql: str, params: Iterable[object] | None = None) -> dict[str, object]:
        normalized = sql.strip().lower()
        unsafe_tokens = ("insert ", "update ", "delete ", "drop ", "alter ", "truncate ")
        if not normalized.startswith("select") or any(tok in normalized for tok in unsafe_tokens):
            raise ValueError("Somente SELECT é permitido em safe_query.")
        return {
            "db_alias": self._db_alias(slug),
            "sql": sql,
            "params": list(params or []),
            "rows": [],
            "row_count": 0,
        }

    def _db_alias(self, slug: str) -> str:
        if self.resolve_db_from_slug:
            return self.resolve_db_from_slug(slug)
        return f"tenant_{slug}"
