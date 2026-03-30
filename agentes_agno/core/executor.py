import ast
import json
import logging
import re
from time import perf_counter
from pathlib import Path

from agentes_agno.core.contexto import MontadorContexto
from agentes_agno.agentes.leitor_documentacao import agente_leitor_documentacao
from agentes_agno.core.documentacao import LeitorDocumentacao
from agentes_agno.core.gravador_arquivos import GravadorArquivos
from agentes_agno.core.rag.engine import RagEngine
from agentes_agno.core.rag.loader import RagLoader
from agentes_agno.time import time_dev


logger = logging.getLogger("agentes.executor")


def _trace(trilha: list[dict], etapa: str, msg: str, **meta):
    trilha.append({"etapa": etapa, "msg": msg, **meta})


def _validar_contratos_documentacao(contratos: object) -> list[dict]:
    if not isinstance(contratos, list):
        return []

    out: list[dict] = []
    for item in contratos:
        if not isinstance(item, dict):
            continue
        endpoint = item.get("endpoint")
        metodo = item.get("metodo")
        entrada = item.get("entrada")
        saida = item.get("saida")
        regras = item.get("regras")

        if not isinstance(endpoint, str) or not endpoint.strip():
            continue
        if not isinstance(metodo, str) or not metodo.strip():
            continue
        if entrada is None:
            entrada = {}
        if saida is None:
            saida = {}
        if regras is None:
            regras = []
        out.append(
            {
                "endpoint": endpoint.strip(),
                "metodo": metodo.strip().upper(),
                "entrada": entrada,
                "saida": saida,
                "regras": regras,
            }
        )
    return out


def _compilar_politicas_modelos(modelos_upload: dict | None) -> dict:
    politicas: dict[str, dict] = {}
    if not isinstance(modelos_upload, dict):
        return politicas

    for model_name, model_info in modelos_upload.items():
        campos = model_info.get("campos", []) if isinstance(model_info, dict) else []
        nomes = [c.get("nome", "").lower() for c in campos if isinstance(c, dict)]
        tipos = [c.get("tipo", "").lower() for c in campos if isinstance(c, dict)]

        has_status = any("status" in n or "situacao" in n for n in nomes)
        has_soft_delete = any(n in {"ativo", "inativo"} or "deleted_at" in n or "excluido" in n for n in nomes)
        has_text = any(t in {"textfield", "charfield"} for t in tipos)
        has_periodo = any(t in {"datefield", "datetimefield"} for t in tipos) or any("data" in n or "dt_" in n for n in nomes)

        politicas[model_name] = {
            "normalizar_campos": True,
            "acoes_obrigatorias": ["resumo", "buscar", "relatorio", "bulk"],
            "status_transition": has_status,
            "soft_delete": has_soft_delete,
            "busca_textual": has_text,
            "filtros_periodo": has_periodo,
        }
    return politicas


def _compilar_plano_sicredi_boletos(modelos_upload: dict | None, contratos: list[dict] | None) -> dict:
    if not isinstance(modelos_upload, dict):
        return {}

    nomes_modelos = {str(k).lower() for k in modelos_upload.keys()}
    alvo = {"boleto", "titulosreceber", "remessaretorno", "boletoscancelados", "carteira", "bordero"}
    if not (nomes_modelos & alvo):
        return {}

    contratos = contratos or []
    endpoints = []
    for c in contratos:
        if not isinstance(c, dict):
            continue
        endpoint = str(c.get("endpoint") or "").lower()
        metodo = str(c.get("metodo") or "").upper()
        if endpoint and ("boleto" in endpoint or "cobranca" in endpoint or "sicredi" in endpoint):
            endpoints.append({"endpoint": endpoint, "metodo": metodo})

    return {
        "provedor": "sicredi_api_online",
        "modelos_detectados": sorted(nomes_modelos & alvo),
        "acoes_recomendadas": [
            "emitir_boleto",
            "consultar_boleto",
            "cancelar_boleto",
            "baixar_boleto",
            "registrar_retorno",
        ],
        "endpoints_documentados": endpoints,
        "mapeamentos_minimos": {
            "Boleto.bole_noss": "nossoNumero",
            "Boleto.bole_linh_digi": "linhaDigitavel",
            "Titulosreceber.titu_url_bole": "urlBoleto",
            "Boletoscancelados.linh_digi": "linhaDigitavel",
        },
    }


def _gerar_contexto_documentacao(tarefa: str, extras: dict) -> dict:
    texto_doc = LeitorDocumentacao().extrair_texto(extras)
    if not texto_doc:
        return {"texto": "", "contratos": None}

    prompt = (
        "Analise a documentação abaixo e gere contratos de API úteis para implementação de backend. "
        "Responda somente JSON válido com chave 'contratos'.\n\n"
        f"Tarefa alvo:\n{tarefa}\n\n"
        f"Documentação:\n{texto_doc[:12000]}"
    )

    logger.info("Analisando documentação com agente dedicado | tamanho=%s", len(texto_doc))
    resposta_doc = agente_leitor_documentacao.run(prompt)
    raw_doc = getattr(resposta_doc, "content", resposta_doc)

    try:
        parsed = _extrair_json(raw_doc)
    except Exception:
        logger.exception("Falha ao interpretar JSON do leitor de documentação")
        parsed = {"contratos": None, "raw": str(raw_doc)}

    contratos = parsed.get("contratos") if isinstance(parsed, dict) else None
    return {"texto": texto_doc, "contratos": _validar_contratos_documentacao(contratos)}
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
    t0 = perf_counter()
    extras = extras or {}
    trilha: list[dict] = []
    _trace(trilha, "START", "Iniciando execução")
    logger.info("Iniciando execução do agente | tarefa=%s", (tarefa or "")[:180])

    if "models_py" in extras and "modelos_upload" not in extras and isinstance(extras.get("models_py"), str):
        extras = {**extras, "modelos_upload": _parse_models_py(extras["models_py"])}
        _trace(trilha, "MODELS", "models.py convertido para modelos_upload", total=len(extras.get("modelos_upload", {})))

    if _deve_aplicar_padrao_backend(tarefa, extras):
        tarefa = _aplicar_padrao_backend_na_tarefa(tarefa)
        _trace(trilha, "PROMPT", "Padrão backend aplicado à tarefa")

    contexto = MontadorContexto().montar(tarefa)

    contexto_documentacao = _gerar_contexto_documentacao(tarefa, extras)
    if contexto_documentacao["texto"]:
        contexto["documentacao_texto"] = contexto_documentacao["texto"]
        _trace(trilha, "DOC", "Documentação textual carregada", chars=len(contexto_documentacao["texto"]))
    if contexto_documentacao["contratos"] is not None:
        contexto["contratos_documentacao"] = contexto_documentacao["contratos"]
        _trace(trilha, "DOC", "Contratos extraídos da documentação", total=len(contexto_documentacao["contratos"]))

    politicas_modelos = _compilar_politicas_modelos(extras.get("modelos_upload"))
    if politicas_modelos:
        contexto["politicas_modelos"] = politicas_modelos
        _trace(trilha, "POLICY", "Políticas de modelo compiladas", total=len(politicas_modelos))

    plano_sicredi = _compilar_plano_sicredi_boletos(extras.get("modelos_upload"), contexto_documentacao.get("contratos"))
    if plano_sicredi:
        contexto["plano_sicredi_boletos"] = plano_sicredi
        _trace(trilha, "SICREDI", "Plano Sicredi para boletos detectado", modelos=plano_sicredi.get("modelos_detectados", []))

    chunks = RagLoader().carregar_chunks(contexto, extras)
    rag_engine = RagEngine(chunks)
    rag_contexto = rag_engine.montar_contexto(tarefa, top_k=4)
    _trace(trilha, "RAG", "RAG executado", chunks=len(chunks), has_contexto=bool(rag_contexto))
    tarefa_com_rag = tarefa
    if rag_contexto:
        tarefa_com_rag = f"{tarefa}\n\nContexto recuperado (RAG):\n{rag_contexto}"
    if plano_sicredi:
        tarefa_com_rag = (
            f"{tarefa_com_rag}\n\nPlano de implementação Sicredi (boletos):\n"
            f"{json.dumps(plano_sicredi, ensure_ascii=False)}"
        )

    logger.info(
        "Executando agente com RAG | chunks=%s | contexto_recuperado=%s",
        len(chunks),
        bool(rag_contexto),
    )
    resposta = time_dev.run(
        tarefa_com_rag,
        session_state={**contexto, **extras, "rag_contexto": rag_contexto, "documentacao": contexto_documentacao},
    )
    _trace(trilha, "LLM", "Execução do orquestrador concluída")

    raw = getattr(resposta, "content", resposta)

    try:
        resultado = _extrair_json(raw)
    except Exception:
        logger.exception("Falha ao converter resposta da LLM em JSON")
        _trace(trilha, "ERROR", "Falha ao converter resposta da LLM em JSON")
        return {"erro": "LLM inválida", "raw": raw}

    if isinstance(resultado, dict):
        resultado = _ensure_urls_file(resultado)
        resultado = _ensure_examples_file(resultado)

    arquivos = GravadorArquivos().salvar(resultado)
    logger.info("Execução finalizada | arquivos_gerados=%s", len(arquivos or []))
    _trace(trilha, "SAVE", "Arquivos gerados", total=len(arquivos or []))
    duracao_ms = round((perf_counter() - t0) * 1000, 2)
    _trace(trilha, "DONE", "Fluxo finalizado", duracao_ms=duracao_ms)

    return {
        "ok": True,
        "arquivos": arquivos,
        "resultado": resultado,
        "trace": trilha,
        "metricas": {"duracao_ms": duracao_ms, "chunks_rag": len(chunks), "arquivos_gerados": len(arquivos or [])},
    }
