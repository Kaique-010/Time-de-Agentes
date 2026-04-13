import unittest

from app.agents.router_agent import RouterAgent
from app.core.contracts import Intent


class TestRouterAgent(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = RouterAgent()

    def test_choose_django_agent_for_create_module(self):
        chosen = self.agent.choose(Intent.CREATE_MODULE, {"framework": "django"})
        self.assertEqual(chosen, "django_engineer_agent")

    def test_choose_inspector_agent(self):
        chosen = self.agent.choose(Intent.INSPECT, {})
        self.assertEqual(chosen, "inspector_agent")


if __name__ == "__main__":
    unittest.main()
