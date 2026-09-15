from typing import TypedDict, List, Dict, Any


class RejectionLog(TypedDict):
    attempt: int
    status: str
    failed_checks: List[Dict[str, str]]
    corrections: List[str]


class GraphState(TypedDict):
    topic: str                        # Input topic, e.g., "Introduction to RAG"
    lesson_plan: str                  # Planner's structured outline
    lesson_content: str               # Drafted lesson markdown
    evaluation_results: Dict[str, Any]# Pydantic EvaluationRubric dump
    failed_checks: List[Dict[str, str]] # Failing dimensions & reasons
    reflection_feedback: str          # Actionable diagnosis from Reflector
    retry_count: int                  # Retries executed (Max 2)
    rejection_log: List[RejectionLog] # Historical failure log for this execution
    memory_context: str               # Prior system learnings retrieved from SQLite
    final_status: str                 # "PASS" or "FAIL"
