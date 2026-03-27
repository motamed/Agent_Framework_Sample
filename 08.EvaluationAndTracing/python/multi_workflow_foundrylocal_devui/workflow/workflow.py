"""Workflow wiring for FoundryLocal planning + research agents.

Structure mirrors the pattern used in the GitHub Models multi-step
workflow (`multi_workflow_ghmodel_devui/workflow/workflow.py`). We
compose two agent executors with a transformation executor between them
to map JSON model outputs into the next agent's user message.
"""

from agent_framework import (
	AgentExecutor,
	AgentExecutorRequest,
	AgentExecutorResponse,
	Message,
	Role,
	WorkflowContext,
	executor,
)

from agent_framework.orchestrations import ConcurrentBuilder
from plan_agent import plan_agent
from researcher_agent import researcher_agent




planner_executor = AgentExecutor(plan_agent, id="plan_agent")  # type: ignore

research_executor = AgentExecutor(researcher_agent, id="researcher_agent")  # type: ignore


# Assemble workflow: planner -> transform -> researcher -> output
workflow = (
	ConcurrentBuilder(participants=[research_executor, planner_executor]).build()
)

    