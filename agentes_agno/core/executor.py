import json
import re
import ast
from pathlib import Path
from agentes_agno.core.contexto import MontadorContexto
from agentes_agno.time import time_dev
from agentes_agno.core.gravador_arquivos import GravadorArquivos

def _extrair_json(raw: object):
    if isinstance(raw, (dict, list)):
        return raw
    if raw is None:
        raise ValueError("raw vazio")

    text = str(raw).strip()
    if not text:
        raise ValueError("raw vazio")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fence:
        candidate = fence.group(1).strip()
        return json.loads(candidate)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1]
        return json.loads(candidate)

    return json.loads(text)

def _parse_models_py(models_py: str):
    try:
        tree = ast.parse(models_py)
    except Exception:
        return {}

    models: dict[str, dict] = {}

    def _base_is_model(base: ast.expr) -> bool:
        if isinstance(base, ast.Attribute) and base.attr == "Model":
            return True
        if isinstance(base, ast.Name) and base.id == "Model":
            return True
        return False

    def _field_type(value: ast.AST) -> str | None:
        if not isinstance(value, ast.Call):
            return None
        fn = value.func
        if isinstance(fn, ast.Attribute):
            if isinstance(fn.value, ast.Name) and fn.value.id == "models":
                return fn.attr
            return fn.attr
        if isinstance(fn, ast.Name):
            return fn.id
        return None

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_base_is_model(b) for b in node.bases):
            continue

        fields = []
        meta = {}
        for stmt in node.body:
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                name = stmt.targets[0].id
                ftype = _field_type(stmt.value)
                if ftype:
                    fields.append({"nome": name, "tipo": ftype})
            if isinstance(stmt, ast.ClassDef) and stmt.name == "Meta":
                for meta_stmt in stmt.body:
                    if isinstance(meta_stmt, ast.Assign) and len(meta_stmt.targets) == 1 and isinstance(meta_stmt.targets[0], ast.Name):
                        k = meta_stmt.targets[0].id
                        if isinstance(meta_stmt.value, ast.Constant) and isinstance(meta_stmt.value.value, (str, int, float, bool)):
                            meta[k] = meta_stmt.value.value
        models[node.name] = {"campos": fields, "meta": meta}

    return models

def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

def _pluralize(s: str) -> str:
    if not s:
        return s
    if s.endswith("s"):
        return s
    return f"{s}s"

def _deve_aplicar_padrao_backend(tarefa: str, extras: dict) -> bool:
    if isinstance(extras.get("models_py"), str) and extras.get("models_py"):
        return True
    if isinstance(extras.get("modelos_upload"), dict) and extras.get("modelos_upload"):
        return True
    if "models.py" in (tarefa or "").lower():
        return True
    return False

def _aplicar_padrao_backend_na_tarefa(tarefa: str) -> str:
    prefixo = "\n".join(
        [
            "Você é um gerador de backend Django Rest Framework.",
            "Você deve responder SOMENTE em JSON válido com a chave 'arquivos' (lista de {caminho, conteudo}).",
            "Não inclua markdown nem texto extra.",
            "Obrigatório gerar: services, serializers, views/viewsets, urls (urls.py + router) e 1 arquivo de exemplos (requests.http ou examples.py).",
            "Padrão de rota: todos os endpoints devem ser acessíveis sob /api/{slug}/..., onde slug vem na URL (compatível com LicencaMiddleware).",
            "Multi-db: sempre use core.utils.get_licenca_db_config(request) e aplique .using(db) em queries.",
            "No examples/requests.http: usar base http://localhost:8000/api/{slug}/ e incluir headers X-Empresa e X-Filial quando fizer sentido.",
            "",
            "Tarefa:",
        ]
    )
    return f"{prefixo}\n{tarefa}"

def _ensure_urls_file(resultado: dict) -> dict:
    arquivos = resultado.get("arquivos")
    if not isinstance(arquivos, list):
        return resultado

    if any(isinstance(a, dict) and str(a.get("caminho", "")).endswith("urls.py") for a in arquivos):
        return resultado

    view_candidates = [
        a for a in arquivos
        if isinstance(a, dict)
        and isinstance(a.get("caminho"), str)
        and isinstance(a.get("conteudo"), str)
        and ("view" in a["caminho"].lower() or "viewset" in a["caminho"].lower())
    ]

    if view_candidates:
        base_dir = Path(view_candidates[0]["caminho"]).parent
    elif arquivos and isinstance(arquivos[0], dict) and isinstance(arquivos[0].get("caminho"), str):
        base_dir = Path(arquivos[0]["caminho"]).parent
    else:
        return resultado

    viewsets: list[tuple[Path, list[str]]] = []
    for a in arquivos:
        if not isinstance(a, dict):
            continue
        caminho = a.get("caminho")
        conteudo = a.get("conteudo")
        if not isinstance(caminho, str) or not isinstance(conteudo, str):
            continue
        p = Path(caminho)
        if p.parent != base_dir:
            continue
        classes = re.findall(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*ViewSet)\b", conteudo)
        if classes:
            viewsets.append((p, sorted(set(classes))))

    if not viewsets:
        return resultado

    import_lines = []
    for p, classes in viewsets:
        mod = p.stem
        import_lines.append(f"from .{mod} import {', '.join(classes)}")

    registrations = []
    for _, classes in viewsets:
        for cls in classes:
            base = cls.removesuffix("ViewSet")
            prefix = _pluralize(_camel_to_snake(base))
            basename = _camel_to_snake(base)
            registrations.append(f"router.register(r'{prefix}', {cls}, basename='{basename}')")

    urls_py = "\n".join(
        [
            "from rest_framework.routers import DefaultRouter",
            *import_lines,
            "",
            "router = DefaultRouter()",
            *registrations,
            "",
            "urlpatterns = router.urls",
            "",
        ]
    )

    arquivos.append({"caminho": str(base_dir / "urls.py").replace("\\", "/"), "conteudo": urls_py})
    return resultado

def _ensure_examples_file(resultado: dict) -> dict:
    arquivos = resultado.get("arquivos")
    if not isinstance(arquivos, list):
        return resultado

    if any(isinstance(a, dict) and str(a.get("caminho", "")).endswith(("requests.http", "examples.py")) for a in arquivos):
        return resultado

    urls = next((a for a in arquivos if isinstance(a, dict) and str(a.get("caminho", "")).endswith("urls.py")), None)
    base_dir = Path(urls["caminho"]).parent if isinstance(urls, dict) and isinstance(urls.get("caminho"), str) else Path(".")

    first_prefix = None
    if isinstance(urls, dict) and isinstance(urls.get("conteudo"), str):
        m = re.search(r"router\.register\(r'([^']+)'", urls["conteudo"])
        if m:
            first_prefix = m.group(1)

    prefix = first_prefix or "recurso"
    action_names: list[str] = []
    for a in arquivos:
        if not isinstance(a, dict):
            continue
        conteudo = a.get("conteudo")
        caminho = a.get("caminho")
        if not isinstance(conteudo, str) or not isinstance(caminho, str):
            continue
        if "view" not in caminho.lower() and "viewset" not in caminho.lower():
            continue
        for m in re.finditer(r"@action\b[\s\S]*?\ndef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", conteudo):
            name = m.group(1)
            if name not in action_names:
                action_names.append(name)
        if action_names:
            break

    action_line = None
    if action_names:
        action_line = f"GET {{{{base}}}}/api/{{slug}}/{prefix}/{action_names[0]}/"
    else:
        action_line = f"GET {{{{base}}}}/api/{{slug}}/{prefix}/resumo/"

    requests_http = "\n".join(
        [
            "@base = http://localhost:8000",
            "@slug = seu-slug",
            "@empresa = 1",
            "@filial = 1",
            "",
            "### Listar",
            f"GET {{{{base}}}}/api/{{slug}}/{prefix}/?ordering=-id",
            f"X-Empresa: {{{{empresa}}}}",
            f"X-Filial: {{{{filial}}}}",
            "",
            "### Criar (ajuste o JSON conforme o model)",
            f"POST {{{{base}}}}/api/{{slug}}/{prefix}/",
            "Content-Type: application/json",
            f"X-Empresa: {{{{empresa}}}}",
            f"X-Filial: {{{{filial}}}}",
            "",
            "{}",
            "",
            "### Ação customizada",
            action_line,
            f"X-Empresa: {{{{empresa}}}}",
            f"X-Filial: {{{{filial}}}}",
            "",
        ]
    )

    arquivos.append({"caminho": str(base_dir / "requests.http").replace("\\", "/"), "conteudo": requests_http})
    return resultado

def executar_tarefa(tarefa: str, extras: dict | None = None):
    extras = extras or {}
    if "models_py" in extras and "modelos_upload" not in extras and isinstance(extras.get("models_py"), str):
        extras = {**extras, "modelos_upload": _parse_models_py(extras["models_py"])}

    if _deve_aplicar_padrao_backend(tarefa, extras):
        tarefa = _aplicar_padrao_backend_na_tarefa(tarefa)

    contexto = MontadorContexto().montar(tarefa)

    resposta = time_dev.run(
        tarefa,
        session_state={**contexto, **extras}
    )

    raw = getattr(resposta, "content", resposta)

    try:
        resultado = _extrair_json(raw)
    except Exception:
        return {"erro": "LLM inválida", "raw": raw}

    if isinstance(resultado, dict):
        resultado = _ensure_urls_file(resultado)
        resultado = _ensure_examples_file(resultado)

    arquivos = GravadorArquivos().salvar(resultado)

    return {
        "ok": True,
        "arquivos": arquivos,
        "resultado": resultado
    }
