import asyncio
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import uvicorn

from src.core.schemas import GenerationRequest, GenerationResponse
from src.core.state import GraphState
from src.memory.database import init_db, get_db_connection
from src.memory.operations import fetch_system_learnings
from src.observability.logger import setup_observability, get_logger
from src.graph.workflow import app as workflow_app

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for DB initialization and observability setup."""
    setup_observability(app=app)
    await init_db()
    logger.info("Application initialized. Database ready.")
    yield
    logger.info("Application shutdown.")


# FastAPI Application
api = FastAPI(
    title="RAG Lesson Generator API",
    description="Production-ready cyclic LangGraph content generation with strict pedagogical evaluation.",
    version="1.0.0",
    lifespan=lifespan,
)



@api.get("/learnings")
async def get_learnings():
    """Returns past recurring failures and successful fixes stored in memory."""
    async with await get_db_connection() as db:
        cursor = await db.execute(
            "SELECT id, topic_keyword, recurring_failure, successful_fix, created_at FROM system_learnings ORDER BY id DESC LIMIT 50;"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


@api.post("/generate", response_model=GenerationResponse)
async def generate_lesson(request: GenerationRequest):
    """Executes the cyclic LangGraph workflow to produce a certified lesson."""
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty.")

    initial_state: GraphState = {
        "topic": topic,
        "lesson_plan": "",
        "lesson_content": "",
        "evaluation_results": {},
        "failed_checks": [],
        "reflection_feedback": "",
        "retry_count": 0,
        "rejection_log": [],
        "memory_context": "",
        "final_status": "PENDING",
    }

    try:
        final_state = await workflow_app.ainvoke(initial_state)
        return GenerationResponse(
            topic=topic,
            status=final_state.get("final_status", "UNKNOWN"),
            attempts=final_state.get("retry_count", 0) + 1,
            lesson_content=final_state.get("lesson_content", ""),
            rejection_log=final_state.get("rejection_log", []),
            reflection_feedback=final_state.get("reflection_feedback"),
        )
    except Exception as e:
        logger.error(f"Error during lesson generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def run_cli(topic: str = "Introduction to RAG (Retrieval-Augmented Generation)"):
    """Runs the workflow directly in terminal mode."""
    setup_observability()
    await init_db()

    print(f"\n==========================================")
    print(f"🚀 Starting RAG Lesson Generator")
    print(f"Topic: {topic}")
    print(f"==========================================\n")

    initial_state: GraphState = {
        "topic": topic,
        "lesson_plan": "",
        "lesson_content": "",
        "evaluation_results": {},
        "failed_checks": [],
        "reflection_feedback": "",
        "retry_count": 0,
        "rejection_log": [],
        "memory_context": "",
        "final_status": "PENDING",
    }

    result = await workflow_app.ainvoke(initial_state)

    print(f"\n[Status]: {result.get('final_status')}")
    print(f"[Total Retries]: {result.get('retry_count')}")
    print("\n--- Final Content ---\n")
    print(result.get("lesson_content"))
    print("\n--- Rejection Log History ---")
    print(result.get("rejection_log"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        uvicorn.run("src.main:api", host="0.0.0.0", port=8000, reload=True)
    else:
        topic_arg = "Introduction to RAG (Retrieval-Augmented Generation)"
        if len(sys.argv) > 1:
            topic_arg = " ".join(sys.argv[1:])
        asyncio.run(run_cli(topic_arg))
