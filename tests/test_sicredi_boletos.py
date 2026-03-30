import unittest

from agentes_agno.core.documentacao import LeitorDocumentacao
from agentes_agno.core.executor import (
    _compilar_plano_sicredi_boletos,
    _parse_models_py,
    _validar_contratos_documentacao,
)


MODELS_SICREDI = '''
from django.db import models

class Titulosreceber(models.Model):
    titu_titu = models.CharField(max_length=13)
    titu_venc = models.DateField(blank=True, null=True)
    titu_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    titu_noss_nume = models.CharField(max_length=30, blank=True, null=True)
    titu_linh_digi = models.CharField(max_length=255, blank=True, null=True)
    titu_url_bole = models.CharField(max_length=255, blank=True, null=True)

class Boleto(models.Model):
    bole_titu = models.CharField(max_length=13)
    bole_venc = models.DateField(blank=True, null=True)
    bole_valo = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    bole_noss = models.CharField(max_length=30, blank=True, null=True)
    bole_linh_digi = models.CharField(max_length=255, blank=True, null=True)

class Boletoscancelados(models.Model):
    linh_digi = models.CharField(max_length=255)
    canc_data = models.DateField(blank=True, null=True)
'''

DOC_HTML_SICREDI = '''
<h1>Sicredi Cobrança API</h1>
<p>POST /sicredi/cobranca/boletos</p>
<p>GET /sicredi/cobranca/boletos/{nossoNumero}</p>
<p>POST /sicredi/cobranca/boletos/{nossoNumero}/baixa</p>
'''


class TestSicrediBoletos(unittest.TestCase):
    def test_leitura_doc_e_plano_sicredi(self):
        texto_doc = LeitorDocumentacao().extrair_texto({"documentacao_html": DOC_HTML_SICREDI})
        self.assertIn("Sicredi Cobrança API", texto_doc)

        contratos = _validar_contratos_documentacao(
            [
                {"endpoint": "/sicredi/cobranca/boletos", "metodo": "post", "entrada": {}, "saida": {}, "regras": []},
                {"endpoint": "/sicredi/cobranca/boletos/{nossoNumero}", "metodo": "get", "entrada": {}, "saida": {}, "regras": []},
                {"endpoint": "/sicredi/cobranca/boletos/{nossoNumero}/baixa", "metodo": "post", "entrada": {}, "saida": {}, "regras": []},
            ]
        )

        modelos_upload = _parse_models_py(MODELS_SICREDI)
        plano = _compilar_plano_sicredi_boletos(modelos_upload, contratos)

        self.assertEqual(plano.get("provedor"), "sicredi_api_online")
        self.assertIn("boleto", plano.get("modelos_detectados", []))
        self.assertTrue(any("/sicredi/cobranca/boletos" in e.get("endpoint", "") for e in plano.get("endpoints_documentados", [])))
        self.assertIn("emitir_boleto", plano.get("acoes_recomendadas", []))


if __name__ == "__main__":
    unittest.main()
