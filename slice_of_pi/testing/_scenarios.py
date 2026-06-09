"""
Scenario Runner

Runs end-to-end test scenarios against the agentic framework.
Scenarios define a sequence of actions and assertions that
verify the framework's behavior holistically.

A scenario is a named sequence of steps. Each step is an
action (create_agent, chat, schedule, assert_status) with
params and expected outcomes. The runner executes steps in
order, stopping at the first failure.
"""

from __future__ import annotations

from ..shared import Scenario, ScenarioResult


class ScenarioRunner:
    """Runs end-to-end scenarios against the agent framework.

    Scenarios are declarative — they describe what to do and
    what to expect. The runner executes them imperatively,
    collecting results.

    Usage:
        scenario = Scenario(
            name="agent chat works",
            steps=[
                ScenarioStep("create_agent", {"template": "echo"}),
                ScenarioStep("chat", {"message": "hello"}),
                ScenarioStep("assert_status", {"status": "running"}),
            ],
        )
        result = await runner.run(scenario)
        assert result.passed
    """

    async def run(self, scenario: Scenario) -> ScenarioResult:
        """Execute a scenario and return pass/fail with details.

        Steps are executed in order. If a step fails, remaining
        steps are skipped and cleanup steps are run.

        Args:
            scenario: The scenario to execute.

        Returns:
            ScenarioResult with pass/fail, step counts, and failures.
        """
        raise NotImplementedError
