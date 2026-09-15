import logging
import sys
from typing import Any
from src.core.config import settings

# Setup standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("rag_lesson_generator")


def setup_observability(app: Any = None) -> None:

    """Configures Pydantic Logfire (system metrics, pydantic, openai, fastapi) and LangSmith."""
    # 1. Setup Logfire
    try:
        import logfire
        import os
        if settings.LOGFIRE_TOKEN:
            logfire.configure(token=settings.LOGFIRE_TOKEN)
        else:
            # Falls back to CLI auth / local config (~/.logfire/settings.toml)
            logfire.configure()

        # Instrument Pydantic validation
        logfire.instrument_pydantic()

        # Instrument system metrics (CPU, RAM, etc.)
        try:
            logfire.instrument_system_metrics()
            logger.info("Logfire system metrics instrumented.")
        except Exception as sm_err:
            logger.debug(f"System metrics instrumentation skipped: {sm_err}")

        # Instrument OpenAI LLM calls (token counts, latency, costs)
        try:
            logfire.instrument_openai()
            logger.info("Logfire OpenAI instrumentation enabled.")
        except Exception as oai_err:
            logger.debug(f"OpenAI instrumentation skipped: {oai_err}")

        # Instrument FastAPI if provided
        if app is not None:
            try:
                logfire.instrument_fastapi(app)
                logger.info("Logfire FastAPI instrumentation enabled.")
            except Exception as fa_err:
                logger.debug(f"FastAPI instrumentation skipped: {fa_err}")

        logger.info("Pydantic Logfire configured successfully.")
    except Exception as e:
        logger.warning(f"Logfire configuration note: {e}")


    # 2. Setup LangChain / LangSmith tracing
    langsmith_key = settings.LANGSMITH_API_KEY or settings.LANGCHAIN_API_KEY or os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY")
    tracing_enabled = settings.LANGCHAIN_TRACING_V2 or os.environ.get("LANGCHAIN_TRACING_V2") == "true" or os.environ.get("LANGSMITH_TRACING") == "true"
    project_name = settings.LANGSMITH_PROJECT or settings.LANGCHAIN_PROJECT or os.environ.get("LANGSMITH_PROJECT") or os.environ.get("LANGCHAIN_PROJECT") or "rag_lesson_generator"

    if tracing_enabled and langsmith_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = langsmith_key
        os.environ["LANGSMITH_API_KEY"] = langsmith_key
        os.environ["LANGCHAIN_PROJECT"] = project_name
        os.environ["LANGSMITH_PROJECT"] = project_name
        logger.info(f"LangSmith tracing enabled for project: '{project_name}'")
    else:
        logger.info("LangSmith tracing is disabled or API key is not configured.")


def get_logger(name: str = "rag_lesson_generator") -> logging.Logger:
    return logging.getLogger(name)
