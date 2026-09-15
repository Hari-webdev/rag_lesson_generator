import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings
from src.core.schemas import LessonPlan
from src.core.state import GraphState
from src.memory.operations import fetch_system_learnings
from src.observability.logger import get_logger

logger = get_logger("planner_agent")

PLANNER_PROMPT = """You are a Senior Curriculum Designer specializing in technical education for Indian students.
Your target audience is an Indian 12th-grade graduate with foundational computer knowledge and English at an A2/B1 CEFR level.

Task:
Create a detailed, pedagogical Lesson Plan for the topic: "{topic}".

Past System Learnings to avoid previous evaluation pitfalls:
{memory_context}

Pedagogical Structure Requirements:
1. WHAT: High-level intuitive explanation in simple terms.
2. WHY: Why this concept exists, what real problem it solves.
3. HOW: Step-by-step breakdown. If explaining RAG, must explicitly outline Retrieval, Augmentation, and Generation.
4. EXAMPLE: A clear everyday analogy (e.g. an Indian school library, open-book examination, textbook reference card).
5. SUMMARY: 3-4 bullet-point recap.

Return your response strictly adhering to the LessonPlan schema.
"""


async def planner_node(state: GraphState) -> dict:
    """Generates the pedagogical lesson plan incorporating prior system memory."""
    topic = state.get("topic", "Introduction to RAG")
    memory_context = state.get("memory_context")
    if not memory_context:
        memory_context = await fetch_system_learnings(topic)

    logger.info(f"[Planner Agent] Planning lesson outline for topic: '{topic}'")

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.2,
    )
    structured_llm = llm.with_structured_output(LessonPlan)

    prompt = ChatPromptTemplate.from_template(PLANNER_PROMPT)
    chain = prompt | structured_llm

    try:
        plan: LessonPlan = await chain.ainvoke({
            "topic": topic,
            "memory_context": memory_context,
        })
        formatted_plan = (
            f"# Lesson Plan: {plan.topic}\n\n"
            f"**Audience**: {plan.target_audience}\n\n"
            f"### 1. What\n{plan.what}\n\n"
            f"### 2. Why\n{plan.why}\n\n"
            f"### 3. How\n{plan.how}\n\n"
            f"### 4. Relatable Example\n{plan.example}\n\n"
            f"### 5. Summary\n{plan.summary}\n"
        )
    except Exception as e:
        logger.warning(f"[Planner Agent] Structured output fallback: {e}")
        # Fallback to standard chat invocation if structured output fails
        raw_chain = prompt | llm
        response = await raw_chain.ainvoke({
            "topic": topic,
            "memory_context": memory_context,
        })
        formatted_plan = response.content

    return {
        "lesson_plan": formatted_plan,
        "memory_context": memory_context,
    }
