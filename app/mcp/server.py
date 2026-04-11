from __future__ import annotations

from app.core.contracts import TaskRequest
from app.orchestrator.engine import OrchestratorEngine


class MCPServerFacade:
    """Placeholder para integrar SDK MCP/FastMCP real."""

    def __init__(self) -> None:
        self.engine = OrchestratorEngine()

    def execute(self, task: str, project_context: dict | None = None) -> dict:
        payload = TaskRequest(task=task, project_context=project_context or {})
        return self.engine.execute_task(payload).model_dump()
