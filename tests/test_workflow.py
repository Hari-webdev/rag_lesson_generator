import pytest
from src.core.schemas import EvaluationRubric, FailedCheck
from src.graph.workflow import route_decision
from src.memory.database import init_db
from src.memory.operations import (
    fetch_system_learnings,
    record_evaluation_run,
    record_rejection_logs,
)


def test_rubric_validation_strictness():
    """Verify that overall_pass can only be True if all 6 dimensions pass."""
    rubric = EvaluationRubric(
        accuracy=True,
        beginner_friendly=True,
        example_based=True,
        jargon_handling=False,  # Fails
        core_concepts=True,
        teaching_flow=True,
        overall_pass=False,
        failed_checks=[
            FailedCheck(
                criterion="Jargon Handling",
                reason="Word 'Embedding' used without inline definition",
                suggestion="Add '(converting words to lists of numbers)'",
            )
        ],
    )
    assert rubric.overall_pass is False
    assert len(rubric.failed_checks) == 1
    assert rubric.failed_checks[0].criterion == "Jargon Handling"


def test_route_decision_success():
    """Tests that a passed rubric directs to success."""
    state = {
        "evaluation_results": {"overall_pass": True},
        "retry_count": 0,
    }
    decision = route_decision(state)
    assert decision == "success"


def test_route_decision_retry():
    """Tests that a failed rubric under max retries directs to reflector retry loop."""
    state = {
        "evaluation_results": {"overall_pass": False},
        "retry_count": 1,
    }
    decision = route_decision(state)
    assert decision == "retry"


def test_route_decision_exhausted():
    """Tests that reaching MAX_RETRIES (2) terminates with exhausted."""
    state = {
        "evaluation_results": {"overall_pass": False},
        "retry_count": 2,
    }
    decision = route_decision(state)
    assert decision == "exhausted"


@pytest.mark.asyncio
async def test_database_operations(tmp_path, monkeypatch):
    """Verifies SQLite memory operations."""
    test_db = str(tmp_path / "test_memory.db")
    monkeypatch.setattr("src.core.config.settings.DATABASE_URL", test_db)
    monkeypatch.setattr("src.memory.database.DB_FILE", tmp_path / "test_memory.db")

    await init_db()

    # Verify seed learning is retrieved
    learnings = await fetch_system_learnings("Introduction to RAG")
    assert "Vector" in learnings or "Embedding" in learnings

    # Test run logging
    await record_evaluation_run("run-test-1", "Test RAG", 1, "PASS")
    await record_rejection_logs(
        "run-test-1",
        [
            {
                "attempt": 1,
                "status": "FAIL",
                "failed_checks": [{"criterion": "Accuracy", "reason": "Minor error"}],
                "corrections": ["Fix explanation"],
            }
        ],
    )
