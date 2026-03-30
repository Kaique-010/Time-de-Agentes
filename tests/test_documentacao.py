import unittest

from agentes_agno.core.documentacao import LeitorDocumentacao
from agentes_agno.core.executor import _validar_contratos_documentacao


class TestDocumentacao(unittest.TestCase):
    def test_limpa_html(self):
        leitor = LeitorDocumentacao()
        texto = leitor.extrair_texto({"documentacao_html": "<h1>API</h1><p>GET /v1/x</p>"})
        self.assertIn("API", texto)
        self.assertIn("GET /v1/x", texto)

    def test_valida_contratos(self):
        contratos = _validar_contratos_documentacao(
            [
                {"endpoint": "/itens", "metodo": "get", "entrada": {}, "saida": {}, "regras": []},
                {"endpoint": "", "metodo": "post"},
            ]
        )
        self.assertEqual(len(contratos), 1)
        self.assertEqual(contratos[0]["metodo"], "GET")


if __name__ == "__main__":
    unittest.main()
