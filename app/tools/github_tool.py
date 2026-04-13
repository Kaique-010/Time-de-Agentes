from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class GithubTool:
    """Ferramenta local para leitura, busca e preparação de patch estilo GitHub."""

    repo_root: Path

    def read(self, file_path: str) -> str:
        full_path = self.repo_root / file_path
        return full_path.read_text(encoding="utf-8")

    def search(self, pattern: str) -> list[str]:
        matches: list[str] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if pattern.lower() in content.lower():
                matches.append(str(path.relative_to(self.repo_root)))
        return matches

    def build_patch(self, file_path: str, before: str, after: str) -> dict[str, str]:
        if before == after:
            return {"file": file_path, "patch": "", "changed": "false"}
        return {
            "file": file_path,
            "patch": f"--- a/{file_path}\n+++ b/{file_path}\n",
            "changed": "true",
        }
