import logging

from app.config import settings
from app.core.pipeline.diagnosis.base import Diagnosis
from app.core.pipeline.diagnosis.heuristic_diagnoser import diagnose_heuristic
from app.core.pipeline.diagnosis.llm_diagnoser import LLMDiagnosisError, diagnose_llm
from app.core.pipeline.validation import RowValidationResult

logger = logging.getLogger(__name__)


async def diagnose(result: RowValidationResult, use_llm: bool | None = None) -> Diagnosis:
    """Tries the LLM mode first when configured, otherwise uses the heuristic.
    Any LLM failure degrades gracefully to the heuristic path instead of
    aborting the run.
    """
    should_try_llm = use_llm if use_llm is not None else bool(settings.groq_api_key)

    if should_try_llm:
        try:
            return await diagnose_llm(result)
        except LLMDiagnosisError as exc:
            logger.warning("LLM diagnosis failed, falling back to heuristic: %s", exc)

    return diagnose_heuristic(result)
