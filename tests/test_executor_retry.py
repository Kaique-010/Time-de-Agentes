import unittest

from agentes_agno.core.executor import _erro_relacionado_a_tokens, _texto_limitado


class TestExecutorRetry(unittest.TestCase):
    def test_texto_limitado_trunca(self):
        original = "abcde" * 100
        limitado = _texto_limitado(original, 50)
        self.assertTrue(len(limitado) > 50)
        self.assertIn("contexto truncado", limitado)

    def test_erro_relacionado_a_tokens(self):
        self.assertTrue(_erro_relacionado_a_tokens("Request too large on tokens per min (TPM)"))
        self.assertTrue(_erro_relacionado_a_tokens("rate limit exceeded"))
        self.assertFalse(_erro_relacionado_a_tokens("json decode error"))


if __name__ == "__main__":
    unittest.main()
