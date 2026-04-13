from __future__ import annotations

from app.core.contracts import Intent, PlanStep


class PlannerAgent:
    def classify_intent(self, task: str) -> Intent:
        lowered = task.lower()
        if any(k in lowered for k in ("criar", "create", "novo módulo", "new module")):
            return Intent.CREATE_MODULE
        if any(k in lowered for k in ("patch", "refator", "corrigir", "fix")):
            return Intent.PATCH_EXISTING
        if any(k in lowered for k in ("inspec", "analisar", "search", "buscar")):
            return Intent.INSPECT
        return Intent.UNKNOWN

    def build_plan(self, intent: Intent) -> list[PlanStep]:
        common = [
            PlanStep(id="collect_context", description="Coletar contexto nas tools"),
            PlanStep(id="delegate", description="Delegar para agente especializado"),
            PlanStep(id="validate", description="Validar saída com regras de segurança"),
        ]
        if intent == Intent.CREATE_MODULE:
            return [PlanStep(id="design", description="Desenhar contratos e estrutura horizontal"), *common]
        if intent == Intent.PATCH_EXISTING:
            return [PlanStep(id="inspect", description="Inspecionar estado atual do código"), *common]
        return common
