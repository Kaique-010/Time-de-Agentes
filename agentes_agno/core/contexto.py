from pathlib import Path

from agentes_agno.core.introspector_django import DjangoIntrospector


class MontadorContexto:

    def montar(self, tarefa: str):
        introspector = DjangoIntrospector()
        modelos = introspector.extrair_models()

        base_dir = Path(__file__).resolve().parents[2]
        mdfe_path = base_dir / "mdfe.py"
        reneg_path = base_dir / "renegociacao_service.py"
        exemplo_serializer_normalizado = mdfe_path.read_text(encoding="utf-8") if mdfe_path.exists() else None
        exemplo_service = reneg_path.read_text(encoding="utf-8") if reneg_path.exists() else None

        return {
            "tarefa": tarefa,
            "modelos_reais": modelos,
            "exemplo_serializer_normalizado": exemplo_serializer_normalizado,
            "exemplo_service": exemplo_service,
            "rag_fontes_preferenciais": [
                "modelos_reais",
                "models_py",
                "documentacao_texto",
                "contratos_documentacao",
                "README.md",
                "mdfe.py",
                "renegociacao_service.py",
            ],
            "documentacao_texto": None,
            "contratos_documentacao": None,
            "plano_sicredi_boletos": None,
        }
