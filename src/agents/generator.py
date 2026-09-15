from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from src.core.config import settings
from src.core.state import GraphState
from src.observability.logger import get_logger

logger = get_logger("generator_agent")

GENERATOR_PROMPT = """You are an expert AI Educator teaching Indian high school graduates (12th-grade level, CEFR A2/B1 English).

Lesson Outline:
{lesson_plan}

Past Pitfalls & Learnings to remember:
{memory_context}

STRICT TEACHING RULES:
1. Simplicity: Use short, conversational sentences. Avoid complex vocabulary or dense academic prose.
2. Structure: You MUST explicitly include these 5 sections with exact headers:
   ## 1. What is {topic}?
   ## 2. Why Do We Need It?
   ## 3. How Does It Work?
   ## 4. Everyday Example
   ## 5. Summary & Key Takeaways
3. Core Concepts: In the "How Does It Work?" section, you MUST clearly explain all three parts:
   - **Retrieval** (finding relevant facts from documents)
   - **Augmentation** (adding the retrieved facts into the prompt/question)
   - **Generation** (having the AI create an accurate answer using the provided facts)
4. Jargon Handling: Whenever you introduce technical words like **Vector**, **Embedding**, or **LLM (Large Language Model)**, you MUST provide an immediate, inline explanation in parentheses or within the same sentence. For example:
   "An **Embedding** (a way to turn words into lists of numbers so a computer understands their meaning)..."
5. Grounded Example: Provide an engaging real-world analogy (e.g. an open-book exam or a school librarian finding reference books for you).

Write the full lesson in clean Markdown format:
"""


async def generator_node(state: GraphState) -> dict:
    """Drafts the complete lesson content following pedagogical guidelines."""
    topic = state.get("topic", "Introduction to RAG")
    lesson_plan = state.get("lesson_plan", "")
    memory_context = state.get("memory_context", "")

    logger.info(f"[Generator Agent] Generating lesson content for: '{topic}'")

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.3,
    )
    prompt = ChatPromptTemplate.from_template(GENERATOR_PROMPT)
    chain = prompt | llm

    response = await chain.ainvoke({
        "topic": topic,
        "lesson_plan": lesson_plan,
        "memory_context": memory_context,
    })

    return {
        "lesson_content": response.content,
    }
