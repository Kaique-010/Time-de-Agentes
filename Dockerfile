FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY agentes_agno /app/agentes_agno
COPY index.html /app/index.html

RUN python -m pip install -U pip setuptools wheel && python -m pip install -e . --no-build-isolation

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "uvicorn", "agentes_agno.integrations.fastapi_adapter:app", "--host", "0.0.0.0", "--port", "8000"]
