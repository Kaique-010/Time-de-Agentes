# Agentes Agno FULL

## Pré-requisitos

- Python 3.12+
- Variável de ambiente: OPENAI_API_KEY

## Instalar (como lib)

```bash
python -m venv venv
.\venv\Scripts\python.exe -m pip install -U pip
.\venv\Scripts\python.exe -m pip install -e .
```

## Rodar HTTP (FastAPI)

```bash
.\venv\Scripts\python.exe -m uvicorn agentes_agno.integrations.fastapi_adapter:app --reload --host 0.0.0.0 --port 8000
```

- UI: http://localhost:8000/

## Rodar MCP (stdio)

Para integrar em clientes MCP via stdio (padrão):

```bash
.\venv\Scripts\python.exe -m agentes_agno.mcp.server
```

Ele fica aguardando um cliente MCP conectar via stdio (é normal parecer que “não aconteceu nada”).

## Rodar MCP (SSE / HTTP)

```powershell
$env:MCP_TRANSPORT="sse"
$env:FASTMCP_HOST="0.0.0.0"
$env:FASTMCP_PORT="8001"
.\venv\Scripts\python.exe -m agentes_agno.mcp.server
```

- SSE: http://localhost:8001/sse
- Messages: http://localhost:8001/messages/

## Rodar Docker

Crie um `.env` com `OPENAI_API_KEY=...` (ou exporte no shell) e rode:

```bash
docker compose up --build
```

- API: http://localhost:8000/
- MCP SSE: http://localhost:8001/sse

## Uso lib

```python
from agentes_agno import gerar_backend
resultado = gerar_backend("gere uma API DRF para o model Foo com exemplos e urls")
print(resultado)
```

- Uso local / desenvolvimento do gerador (mais simples): HTTP (FastAPI)
  Você já tem o index.html integrado e SSE pra acompanhar logs. É o melhor fluxo pra iterar rápido e ver o ZIP saindo.
  Ex.: python -m uvicorn agentes_agno.integrations.fastapi_adapter:app --reload
- Integrar com clientes MCP (Claude Desktop etc.): MCP via stdio
  É o “padrão ouro” pra integração MCP porque não expõe porta HTTP e costuma ser o caminho mais compatível.
  Ex.: python -m agentes_agno.mcp.server
- Rodar MCP como serviço na rede / container: MCP via SSE
  Bom quando você quer subir num servidor/Docker e conectar remotamente via HTTP.
  Ex.: MCP_TRANSPORT=sse FASTMCP_PORT=8001 python -m agentes_agno.mcp.server
- Ambiente consistente / deploy rápido local: Docker Compose
  Recomendo quando você quer padronizar execução (API + MCP) e não depender do ambiente Python da máquina.
  Ex.: docker compose up --build
  Resumo direto:

- Quer usar o UI e gerar código : FastAPI HTTP.
- Quer conectar num cliente MCP : MCP stdio.
- Quer MCP como serviço : MCP SSE.
- Quer rodar tudo padronizado : Docker Compose.
