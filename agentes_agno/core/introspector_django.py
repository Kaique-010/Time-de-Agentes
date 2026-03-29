import os
import django
from django.apps import apps

class DjangoIntrospector:

    def setup(self):
        settings_module = os.getenv("DJANGO_SETTINGS_MODULE")
        if not settings_module:
            return False
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)
        django.setup()
        return True

    def extrair_models(self):
        if not self.setup():
            return {}
        data = {}

        for model in apps.get_models():
            campos = []
            for f in model._meta.fields:
                campos.append({"nome": f.name, "tipo": f.get_internal_type()})

            data[model.__name__] = {
                "app": model._meta.app_label,
                "tabela": model._meta.db_table,
                "campos": campos
            }

        return data
