import uuid
from langgraph.graph import StateGraph, START, END
from src.core.config import settings
from src.core.state import GraphState
from src.agents.planner import planner_node
from src.agents.generator import generator_node
from src.agents.evaluator import evaluator_node
from src.agents.reflector import reflector_node
from src.agents.regenerator import regenerator_node
from src.memory.operations import record_evaluation_run, record_rejection_logs
from src.observability.logger import get_logger

logger = get_logger("workflow")


async def success_output_node(state: GraphState) -> dict:
    """Handles terminal PASS state, logs success, and persists metrics."""
    run_id = str(uuid.uuid4())[:8]
    topic = state.get("topic", "")
    attempts = state.get("retry_count", 0) + 1
    rejection_log = state.get("rejection_log", [])

    logger.info(f"[Workflow Result] PASS achieved after {attempts} attempt(s) for '{topic}'")

    await record_evaluation_run(run_id, topic, attempts, "PASS")
    await record_rejection_logs(run_id, rejection_log)

    return {"final_status": "PASS"}


async def fail_output_node(state: GraphState) -> dict:
    """Handles terminal FAIL state when retries are exhausted, and persists logs."""
    run_id = str(uuid.uuid4())[:8]
    topic = state.get("topic", "")
    attempts = state.get("retry_count", 0) + 1
    rejection_log = state.get("rejection_log", [])

    logger.warning(
        f"[Workflow Result] REJECTION: Max retries ({settings.MAX_RETRIES}) reached without passing rubric for '{topic}'"
    )

    await record_evaluation_run(run_id, topic, attempts, "FAIL")
    await record_rejection_logs(run_id, rejection_log)

    return {"final_status": "FAIL"}


def route_decision(state: GraphState) -> str:
    """Conditional router based on evaluator rubric and retry count."""
    eval_results = state.get("evaluation_results", {})
    passed = eval_results.get("overall_pass", False)
    retry_count = state.get("retry_count", 0)

    if passed:
        return "success"

    if retry_count < settings.MAX_RETRIES:
        return "retry"
    else:
        return "exhausted"


def build_workflow():
    """Compiles the cyclic self-correcting LangGraph workflow."""
    workflow = StateGraph(GraphState)

    # Register Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("generator", generator_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("reflector", reflector_node)
    workflow.add_node("regenerator", regenerator_node)
    workflow.add_node("success_output", success_output_node)
    workflow.add_node("fail_output", fail_output_node)

    # Linear Edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "generator")
    workflow.add_edge("generator", "evaluator")

    # Conditional Routing from Evaluator
    workflow.add_conditional_edges(
        "evaluator",
        route_decision,
        {
            "success": "success_output",
            "retry": "reflector",
            "exhausted": "fail_output",
        },
    )

    # Cyclic Edge for Self-Correction Loop
    workflow.add_edge("reflector", "regenerator")
    workflow.add_edge("regenerator", "evaluator")

    # Terminations
    workflow.add_edge("success_output", END)
    workflow.add_edge("fail_output", END)

    return workflow.compile()


app = build_workflow()
