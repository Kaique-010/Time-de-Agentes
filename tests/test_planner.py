import unittest

from app.agents.planner_agent import PlannerAgent
from app.core.contracts import Intent


class TestPlannerAgent(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = PlannerAgent()

    def test_classify_create_module(self):
        intent = self.agent.classify_intent("criar um módulo django de comissões")
        self.assertEqual(intent, Intent.CREATE_MODULE)

    def test_build_plan_has_validation_step(self):
        plan = self.agent.build_plan(Intent.PATCH_EXISTING)
        self.assertTrue(any(step.id == "validate" for step in plan))


if __name__ == "__main__":
    unittest.main()
