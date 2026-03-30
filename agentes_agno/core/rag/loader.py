from __future__ import annotations

import json
from pathlib import Path

from agentes_agno.core.rag.engine import RagChunk


class RagLoader:
    """Carrega documentos relevantes do projeto para alimentar o RAG."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).resolve().parents[3]

    def carregar_chunks(self, contexto: dict, extras: dict | None = None) -> list[RagChunk]:
        extras = extras or {}
        chunks: list[RagChunk] = []
        fontes_preferenciais = contexto.get("rag_fontes_preferenciais") or []
        fontes_set = set(fontes_preferenciais) if isinstance(fontes_preferenciais, list) else set()

        exemplos = {
            "exemplo_serializer_normalizado": "Exemplo de serializer normalizado",
            "exemplo_service": "Exemplo de service",
            "documentacao_texto": "Documentação importada",
        }
        for chave, nome in exemplos.items():
            if fontes_set and chave not in fontes_set:
                continue
            valor = contexto.get(chave)
            if isinstance(valor, str) and valor.strip():
                chunks.append(RagChunk(source=nome, content=valor))

        modelos_reais = contexto.get("modelos_reais")
        if modelos_reais and (not fontes_set or "modelos_reais" in fontes_set):
            chunks.append(RagChunk(source="Modelos Django reais", content=str(modelos_reais)))

        contratos = contexto.get("contratos_documentacao")
        if contratos and (not fontes_set or "contratos_documentacao" in fontes_set):
            chunks.append(RagChunk(source="Contratos da documentação", content=json.dumps(contratos, ensure_ascii=False)))

        models_py = extras.get("models_py")
        if isinstance(models_py, str) and models_py.strip() and (not fontes_set or "models_py" in fontes_set):
            chunks.append(RagChunk(source="models.py upload", content=models_py))

        for rel in ("README.md", "renegociacao_service.py", "mdfe.py"):
            if fontes_set and rel not in fontes_set:
                continue
            path = self.base_dir / rel
            if path.exists():
                try:
                    chunks.append(RagChunk(source=rel, content=path.read_text(encoding="utf-8")))
                except UnicodeDecodeError:
                    chunks.append(RagChunk(source=rel, content=path.read_text(encoding="latin-1")))

        return chunks
