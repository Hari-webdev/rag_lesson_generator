import json
from typing import List, Dict, Any
from src.memory.database import get_db_connection
from src.core.state import RejectionLog


async def fetch_system_learnings(topic: str) -> str:
    """Queries system_learnings for keywords matching the given topic."""
    words = [w.lower().strip() for w in topic.split() if len(w) >= 3]
    if not words:
        words = [topic.lower().strip()]

    learnings_found: List[str] = []
    async with await get_db_connection() as db:
        for word in words:
            cursor = await db.execute(
                """
                SELECT recurring_failure, successful_fix 
                FROM system_learnings 
                WHERE LOWER(topic_keyword) LIKE ?
                LIMIT 3;
                """,
                (f"%{word}%",),
            )
            rows = await cursor.fetchall()
            for row in rows:
                learning_str = f"- Past Failure: {row['recurring_failure']} -> Fix: {row['successful_fix']}"
                if learning_str not in learnings_found:
                    learnings_found.append(learning_str)

    if not learnings_found:
        return "No prior failure logs recorded for this topic. Follow core rubric strictly."
    return "\n".join(learnings_found)


async def record_evaluation_run(
    run_id: str,
    topic: str,
    total_attempts: int,
    final_status: str,
) -> None:
    """Records the metadata of an evaluation run."""
    async with await get_db_connection() as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO eval_history (run_id, topic, total_attempts, final_status)
            VALUES (?, ?, ?, ?);
            """,
            (run_id, topic, total_attempts, final_status),
        )
        await db.commit()


async def record_rejection_logs(
    run_id: str,
    rejection_log: List[RejectionLog],
) -> None:
    """Inserts rejection details for diagnostic analytics."""
    if not rejection_log:
        return

    async with await get_db_connection() as db:
        for entry in rejection_log:
            attempt = entry.get("attempt", 1)
            corrections_str = json.dumps(entry.get("corrections", []))
            for failed in entry.get("failed_checks", []):
                criterion = failed.get("criterion", "Unknown")
                reason = failed.get("reason", "Unknown")
                await db.execute(
                    """
                    INSERT INTO rejection_logs (run_id, attempt, failed_criterion, failure_reason, corrections)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (run_id, attempt, criterion, reason, corrections_str),
                )
        await db.commit()


async def add_system_learning(
    topic_keyword: str,
    recurring_failure: str,
    successful_fix: str,
) -> None:
    """Adds a new extracted learning into long-term memory."""
    async with await get_db_connection() as db:
        await db.execute(
            """
            INSERT INTO system_learnings (topic_keyword, recurring_failure, successful_fix)
            VALUES (?, ?, ?);
            """,
            (topic_keyword.lower().strip(), recurring_failure, successful_fix),
        )
        await db.commit()
