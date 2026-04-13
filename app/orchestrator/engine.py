from __future__ import annotations

from app.core.contracts import TaskRequest, TaskResponse
from app.services.task_service import TaskService


class OrchestratorEngine:
    def __init__(self, task_service: TaskService | None = None) -> None:
        self.task_service = task_service or TaskService()

    def execute_task(self, payload: TaskRequest) -> TaskResponse:
        return self.task_service.execute(payload)
