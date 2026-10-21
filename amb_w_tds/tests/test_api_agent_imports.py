"""F-L2 smoke test: the rewritten amb_w_tds.api.agent imports cleanly and
exposes its expected public surface. Replaces the retired legacy test_agent.py
(which imported names that no longer exist). Plain unittest; no network, no DB writes."""

import unittest


class TestApiAgentImports(unittest.TestCase):
    def test_module_imports(self):
        import amb_w_tds.api.agent  # noqa: F401

    def test_public_surface(self):
        import amb_w_tds.api.agent as m

        for name in (
            "apply_activity_log",
            "hourly_sync_agents",
            "pre_stock_entry_agent_validation",
        ):
            self.assertTrue(hasattr(m, name), f"missing: {name}")
            self.assertTrue(callable(getattr(m, name)), f"not callable: {name}")


if __name__ == "__main__":
    unittest.main()
