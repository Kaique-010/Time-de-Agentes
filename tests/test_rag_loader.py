import unittest

from agentes_agno.core.rag.loader import RagLoader


class TestRagLoader(unittest.TestCase):
    def test_respeita_fontes_preferenciais(self):
        contexto = {
            "rag_fontes_preferenciais": ["documentacao_texto"],
            "documentacao_texto": "doc",
            "exemplo_service": "nao deve entrar",
            "modelos_reais": {"A": {}},
        }
        chunks = RagLoader().carregar_chunks(contexto, extras={"models_py": "class X: pass"})
        fontes = [c.source for c in chunks]
        self.assertIn("Documentação importada", fontes)
        self.assertNotIn("Exemplo de service", fontes)


if __name__ == "__main__":
    unittest.main()
