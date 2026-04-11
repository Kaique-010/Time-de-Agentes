from __future__ import annotations

from app.core.contracts import Intent


class RouterAgent:
    def choose(self, intent: Intent, project_context: dict) -> str:
        framework = str(project_context.get("framework", "")).lower()
        if framework == "django" and intent in {Intent.CREATE_MODULE, Intent.PATCH_EXISTING}:
            return "django_engineer_agent"
        if intent == Intent.INSPECT:
            return "inspector_agent"
        return "generalist_agent"
