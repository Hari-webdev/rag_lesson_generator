import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings
from src.core.state import GraphState
from src.observability.logger import get_logger

logger = get_logger("reflector_agent")

REFLECTOR_PROMPT = """You are a Master Instructional Designer and Educational Reflection Specialist.
The evaluation agent has rejected the current lesson draft because it failed one or more strict rubric criteria.

Topic: {topic}

Failed Checks from Evaluator:
{failed_checks_json}

Current Lesson Draft:
\"\"\"
{lesson_content}
\"\"\"

Your Task:
Conduct a surgical diagnostic analysis of the failures:
1. For each failed check, identify the exact sentences, missing components, or jargon that triggered the rejection.
2. Formulate clear, concise, actionable instructions telling the Regenerator Agent EXACTLY what edits to make.
3. Explicitly tell the Regenerator to preserve all sections that passed and ONLY modify the problematic sections.

Provide your reflection advice clearly and concisely:
"""


async def reflector_node(state: GraphState) -> dict:
    """Analyzes failed checks and constructs precise reflection feedback for the regenerator."""
    topic = state.get("topic", "")
    failed_checks = state.get("failed_checks", [])
    lesson_content = state.get("lesson_content", "")

    logger.info(f"[Reflector Agent] Analyzing {len(failed_checks)} failed checks for: '{topic}'")

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )
    prompt = ChatPromptTemplate.from_template(REFLECTOR_PROMPT)
    chain = prompt | llm

    response = await chain.ainvoke({
        "topic": topic,
        "failed_checks_json": json.dumps(failed_checks, indent=2),
        "lesson_content": lesson_content,
    })

    return {
        "reflection_feedback": response.content,
    }
