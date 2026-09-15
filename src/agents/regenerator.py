from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings
from src.core.state import GraphState, RejectionLog
from src.observability.logger import get_logger

logger = get_logger("regenerator_agent")

REGENERATOR_PROMPT = """You are a Targeted Content Revision Specialist.
Your goal is to apply surgical fixes to a rejected lesson draft based on the Reflector's feedback.

CURRENT DRAFT:
\"\"\"
{lesson_content}
\"\"\"

SURGICAL FEEDBACK FROM REFLECTOR:
\"\"\"
{reflection_feedback}
\"\"\"

REVISION INSTRUCTIONS:
1. ONLY modify the parts flagged by the Reflector.
2. DO NOT rewrite sections that already met the standards.
3. If jargon was flagged (e.g. Vector, Embedding, LLM), insert immediate inline definitions in parentheses right where the word appears.
4. Ensure the What, Why, How (Retrieval, Augmentation, Generation), Example, and Summary flow remains clean and cohesive.
5. Maintain A2/B1 English level suitable for a 12th-grade Indian graduate.

Output the complete, corrected lesson markdown:
"""


async def regenerator_node(state: GraphState) -> dict:
    """Corrects the lesson content according to reflection feedback and increments retry counter."""
    current_attempt = state.get("retry_count", 0) + 1
    failed_checks = state.get("failed_checks", [])
    reflection_feedback = state.get("reflection_feedback", "")
    lesson_content = state.get("lesson_content", "")
    rejection_log = list(state.get("rejection_log", []))

    logger.info(f"[Regenerator Agent] Executing retry #{current_attempt}")

    # Build RejectionLog entry
    corrections = [fc.get("suggestion", "") for fc in failed_checks if fc.get("suggestion")]
    rejection_entry: RejectionLog = {
        "attempt": current_attempt,
        "status": "FAIL",
        "failed_checks": failed_checks,
        "corrections": corrections,
    }
    rejection_log.append(rejection_entry)

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )
    prompt = ChatPromptTemplate.from_template(REGENERATOR_PROMPT)
    chain = prompt | llm

    response = await chain.ainvoke({
        "lesson_content": lesson_content,
        "reflection_feedback": reflection_feedback,
    })

    return {
        "lesson_content": response.content,
        "retry_count": current_attempt,
        "rejection_log": rejection_log,
    }
