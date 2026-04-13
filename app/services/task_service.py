from __future__ import annotations

from pathlib import Path

from app.agents.planner_agent import PlannerAgent
from app.agents.router_agent import RouterAgent
from app.agents.validator_agent import ValidatorAgent
from app.core.contracts import TaskRequest, TaskResponse, ToolContext
from app.tools.github_tool import GithubTool
from app.tools.postgres_tool import PostgresTool
from app.tools.rag_tool import InMemoryVectorStore, RagTool


class TaskService:
    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.router = RouterAgent()
        self.validator = ValidatorAgent()
        self.github = GithubTool(repo_root=Path.cwd())
        self.postgres = PostgresTool()
        self.rag = RagTool(vector_store=InMemoryVectorStore(docs=[]))

    def execute(self, payload: TaskRequest) -> TaskResponse:
        intent = self.planner.classify_intent(payload.task)
        plan = self.planner.build_plan(intent)

        project_context = payload.project_context
        slug = str(project_context.get("slug", "default"))
        context = ToolContext(
            github={"hits": self.github.search("class ")[:5]},
            postgres=self.postgres.inspect_schema(slug),
            rag=self.rag.retrieve(payload.task),
        )

        delegated_agent = self.router.choose(intent, project_context)
        output = {
            "agent": delegated_agent,
            "task": payload.task,
            "implementation_notes": [
                "manter arquitetura horizontal",
                "usar multi-db com get_db_from_slug e .using(db)",
            ],
        }

        valid, errors = self.validator.validate(output)

        return TaskResponse(
            intent=intent,
            plan=plan,
            delegated_agent=delegated_agent,
            context=context,
            output=output,
            valid=valid,
            validation_errors=errors,
        )
