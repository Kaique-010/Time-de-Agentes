import os
from pathlib import Path

class GravadorArquivos:

    def __init__(self):
        repo_root = Path(__file__).resolve().parents[2]
        output_dir = os.getenv("AGENTES_AGNO_OUTPUT_DIR")
        base = Path(output_dir) if output_dir else repo_root
        if not base.is_absolute():
            base = (repo_root / base).resolve()
        self.base = base

    def salvar(self, resultado: dict):
        salvos = []

        for arq in resultado.get("arquivos", []):
            path = self.base / arq["caminho"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(arq["conteudo"], encoding="utf-8")
            salvos.append(str(path))

        return salvos
