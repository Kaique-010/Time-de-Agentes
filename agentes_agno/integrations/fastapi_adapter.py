import json
from io import BytesIO
import os
from pathlib import Path
import tempfile
from urllib.parse import quote
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse

from agentes_agno import gerar_backend

app = FastAPI()

_BASE_DIR = Path(__file__).resolve().parents[2]
_INDEX_HTML = _BASE_DIR / "index.html"
_ARTIFACT_DIR = Path(os.getenv("AGENTES_AGNO_ARTIFACT_DIR") or (Path(tempfile.gettempdir()) / "agentes_agno_artifacts"))
_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
_UPLOADS: dict[str, dict] = {}
_RESULTS: dict[str, dict] = {}


@app.get("/")
def home():
    if _INDEX_HTML.exists():
        return FileResponse(_INDEX_HTML)
    return Response(status_code=404)


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1")

    modelo = f"{Path(file.filename or 'models').stem}-{uuid4().hex[:8]}"
    _UPLOADS[modelo] = {"filename": file.filename, "content": content}

    return {
        "ok": True,
        "modelo": modelo,
        "artefatos": [
            {"arquivo": file.filename, "bytes": len(content_bytes)},
        ],
    }


@app.post("/api/upload-doc")
async def upload_doc(file: UploadFile = File(...)):
    content_bytes = await file.read()
    filename = file.filename or "documentacao"
    ext = Path(filename).suffix.lower()
    modelo = f"{Path(filename).stem}-{uuid4().hex[:8]}"

    payload: dict = {"filename": filename}
    if ext in {".html", ".htm"}:
        try:
            payload["documentacao_html"] = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            payload["documentacao_html"] = content_bytes.decode("latin-1")
    elif ext == ".pdf":
        import base64

        payload["documentacao_pdf_base64"] = base64.b64encode(content_bytes).decode("ascii")
    else:
        try:
            payload["documentacao_texto"] = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            payload["documentacao_texto"] = content_bytes.decode("latin-1")

    _UPLOADS[modelo] = payload
    return {"ok": True, "modelo_doc": modelo, "arquivo": filename}


@app.get("/api/stream")
def stream(
    modelo: str = Query(..., min_length=1),
    modelo_doc: str | None = Query(default=None),
    inicio: str | None = Query(default=None),
    fim: str | None = Query(default=None),
):
    info = _UPLOADS.get(modelo)

    def sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

    def build_zip_bytes(result_obj: dict) -> bytes:
        inner = result_obj.get("resultado") if isinstance(result_obj, dict) else None
        arquivos = []
        if isinstance(inner, dict):
            arquivos = inner.get("arquivos") or []

        buf = BytesIO()
        with ZipFile(buf, "w", compression=ZIP_DEFLATED) as zf:
            if arquivos:
                for arq in arquivos:
                    caminho = arq.get("caminho") or "artefato.txt"
                    conteudo = arq.get("conteudo") or ""
                    zf.writestr(caminho, conteudo)
            else:
                zf.writestr("resultado.json", json.dumps(result_obj, ensure_ascii=False, indent=2))
        return buf.getvalue()

    def gen():
        yield sse({"stage": "START", "msg": "Stream iniciado"})
        if not info:
            yield sse({"stage": "FINAL", "final": True, "msg": "Modelo não encontrado", "ok": False})
            return

        yield sse({"stage": "CONTEXT", "msg": "Montando tarefa e contexto", "modelo": modelo, "inicio": inicio, "fim": fim})

        tarefa = (
            "A partir do arquivo models.py abaixo, gere uma camada completa de API.\n"
            "Obrigatório gerar: services, serializers, views/viewsets, urls (urls.py + router) e 1 arquivo de exemplos (requests.http ou examples.py).\n"
            "Responda SOMENTE em JSON válido com a chave 'arquivos' (lista de {caminho, conteudo}). Sem texto extra. Sem markdown.\n\n"
            "Regras obrigatórias:\n"
            "- Multi-db: sempre use core.utils.get_licenca_db_config(request) para escolher o banco e aplique .using(db) nas queries.\n"
            "- Middleware: considere que LicencaMiddleware injeta request.slug, request.empresa e request.filial.\n\n"
            "Inteligência:\n"
            "- Não fazer só CRUD básico.\n"
            "- Serializers: normalizar nomes de campos legados com aliases amigáveis via source='campo_legado' (não expor titu_* na API pública).\n"
            "- Exemplo de alias esperado: titu_empr->empresa, titu_fili->filial, titu_clie->cliente, titu_titu->titulo, titu_venc->vencimento, titu_valo->valor.\n"
            "- Services: incluir métodos além de list/create/update, com regras de negócio derivadas dos campos (ex.: filtrar por período/status, busca por texto, resumo/agregação, relatório, bulk ops).\n"
            "- Services: ser proativo com validações e regras (saneamento de filtros, ordenação segura, tratamento de nulos, transações atômicas e métricas úteis).\n"
            "- Views/ViewSets: expor ações customizadas (@action) que chamem o service (ex.: /resumo, /relatorio, /buscar, /bulk).\n"
            "- Exemplos: incluir payload de criação realista e exemplos de filtros/querystring e chamada de ação customizada.\n"
            "- Se existir campo tipo status/situacao, criar transição de status segura. Se existir flags de exclusão (ativo/excluido/deleted_at), considerar soft delete.\n\n"
            f"{info['content']}"
        )
        extras = {"models_py": info["content"], "inicio": inicio, "fim": fim, "modelo_upload": modelo}
        if modelo_doc:
            doc = _UPLOADS.get(modelo_doc)
            if doc:
                for k in ("documentacao_texto", "documentacao_html", "documentacao_pdf_base64"):
                    if k in doc:
                        extras[k] = doc[k]
                yield sse({"stage": "DOC", "msg": "Documentação anexada ao fluxo", "modelo_doc": modelo_doc, "arquivo": doc.get("filename")})
            else:
                yield sse({"stage": "DOC", "msg": "Modelo de documentação não encontrado", "modelo_doc": modelo_doc})

        try:
            yield sse({"stage": "EXEC", "msg": "Executando agente..."})
            resultado = gerar_backend(tarefa, extras=extras)
        except Exception as e:
            resultado = {"ok": False, "erro": str(e)}

        for ev in (resultado.get("trace") or []):
            yield sse({"stage": ev.get("etapa", "TRACE"), "msg": ev.get("msg", ""), "meta": ev})

        _RESULTS[modelo] = resultado

        zip_path = _ARTIFACT_DIR / f"{modelo}.zip"
        zip_path.write_bytes(build_zip_bytes(resultado))

        yield sse(
            {
                "stage": "FINAL",
                "final": True,
                "msg": "Concluído",
                "resultado": resultado,
                "download_url": f"/api/download-zip?modelo={quote(modelo)}",
            }
        )

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/download-zip")
def download_zip(modelo: str = Query(..., min_length=1)):
    resultado = _RESULTS.get(modelo)
    if not resultado:
        zip_path = _ARTIFACT_DIR / f"{modelo}.zip"
        if zip_path.exists():
            return FileResponse(zip_path, media_type="application/zip", filename=f"{modelo}.zip")
        return Response(status_code=404)

    inner = resultado.get("resultado") if isinstance(resultado, dict) else None
    arquivos = []
    if isinstance(inner, dict):
        arquivos = inner.get("arquivos") or []

    buf = BytesIO()
    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as zf:
        if arquivos:
            for arq in arquivos:
                caminho = arq.get("caminho") or "artefato.txt"
                conteudo = arq.get("conteudo") or ""
                zf.writestr(caminho, conteudo)
        else:
            zf.writestr("resultado.json", json.dumps(resultado, ensure_ascii=False, indent=2))

    buf.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{modelo}.zip"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)


@app.head("/api/download-zip")
def download_zip_head(modelo: str = Query(..., min_length=1)):
    zip_path = _ARTIFACT_DIR / f"{modelo}.zip"
    if modelo in _RESULTS or zip_path.exists():
        return Response(
            status_code=200,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{modelo}.zip"'},
        )
    return Response(status_code=404)


@app.post("/api/executar")
def executar(payload: dict):
    return gerar_backend(payload.get("tarefa"))


@app.get("/api/executar")
def executar_get(tarefa: str = Query(..., min_length=1)):
    return gerar_backend(tarefa)
