from fastapi import FastAPI

from app.core.contracts import TaskRequest, TaskResponse
from app.orchestrator.engine import OrchestratorEngine

app = FastAPI(title="MCP Dev Agent")
engine = OrchestratorEngine()


@app.post("/tasks/execute", response_model=TaskResponse)
def execute_task(payload: TaskRequest) -> TaskResponse:
    return engine.execute_task(payload)
