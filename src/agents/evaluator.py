from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings
from src.core.schemas import EvaluationRubric
from src.core.state import GraphState
from src.observability.logger import get_logger

logger = get_logger("evaluator_agent")

EVALUATOR_PROMPT = """You are a rigorous, zero-tolerance Chief Pedagogical Auditor and Content Judge.
Your mission is to evaluate the following educational lesson against a strict 6-dimension rubric.
NO PARTIAL CREDIT. If a dimension fails even once, mark that dimension as False and provide an explicit failure check.

Topic: {topic}

Candidate Lesson Text:
\"\"\"
{lesson_content}
\"\"\"

Rubric Dimensions:
1. accuracy: Is the content factually and conceptually accurate? (Pass/Fail)
2. beginner_friendly: Is the language at an A2/B1 CEFR level with simple phrasing suitable for a 12th-grade graduate? Fail if sentences are overly academic, convoluted, or dense.
3. example_based: Does the lesson feature a concrete, relatable real-world example (like an open-book exam, school library, or index card system)?
4. jargon_handling: Are all technical terms (specifically 'Vector', 'Embedding', 'LLM', 'Context Window', etc.) accompanied by an immediate inline explanation in parentheses or within the same sentence? If ANY jargon is introduced without explanation, this FAILS.
5. core_concepts: Does the lesson explicitly explain the three pillars of RAG: Retrieval, Augmentation, and Generation? If any is missing, this FAILS.
6. teaching_flow: Does the lesson follow the What -> Why -> How -> Example -> Summary structure?

Rules for overall_pass:
- overall_pass can ONLY be True if ALL six criteria (accuracy, beginner_friendly, example_based, jargon_handling, core_concepts, teaching_flow) are True.
- If ANY criterion is False, overall_pass MUST be False, and you MUST populate failed_checks with the exact criterion, the offending text/reason, and a concrete suggestion.

Output strictly using the structured EvaluationRubric schema.
"""


async def evaluator_node(state: GraphState) -> dict:
    """Evaluates the lesson against the 6-dimension rubric with structured output."""
    topic = state.get("topic", "Introduction to RAG")
    lesson_content = state.get("lesson_content", "")

    logger.info(f"[Evaluator Agent] Auditing lesson content for: '{topic}'")

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.0,
    )
    structured_evaluator = llm.with_structured_output(EvaluationRubric)

    prompt = ChatPromptTemplate.from_template(EVALUATOR_PROMPT)
    chain = prompt | structured_evaluator

    rubric_result: EvaluationRubric = await chain.ainvoke({
        "topic": topic,
        "lesson_content": lesson_content,
    })

    # Double-check invariant: overall_pass must be false if any check is false
    all_passed = (
        rubric_result.accuracy
        and rubric_result.beginner_friendly
        and rubric_result.example_based
        and rubric_result.jargon_handling
        and rubric_result.core_concepts
        and rubric_result.teaching_flow
    )
    rubric_result.overall_pass = all_passed and rubric_result.overall_pass

    failed_checks_dict = [fc.model_dump() for fc in rubric_result.failed_checks]

    logger.info(
        f"[Evaluator Agent] Audit completed. Passed: {rubric_result.overall_pass}. "
        f"Failed Checks Count: {len(failed_checks_dict)}"
    )

    return {
        "evaluation_results": rubric_result.model_dump(),
        "failed_checks": failed_checks_dict,
    }
