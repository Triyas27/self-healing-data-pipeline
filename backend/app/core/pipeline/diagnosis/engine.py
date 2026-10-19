import logging

from app.config import settings
from app.core.pipeline.diagnosis.base import Diagnosis
from app.core.pipeline.diagnosis.heuristic_diagnoser import diagnose_heuristic
from app.core.pipeline.diagnosis.llm_diagnoser import LLMDiagnosisError, diagnose_llm
from app.core.pipeline.validation import RowValidationResult

logger = logging.getLogger(__name__)

# These error types have exactly one possible diagnosis with no ambiguity for
# an LLM to weigh in on (see heuristic_diagnoser.py) -- sending them to the
# LLM would just spend tokens to re-derive the same no_fix answer every time.
_DETERMINISTIC_ERROR_TYPES = {"duplicate_order_id", "invalid_foreign_key"}


async def diagnose(result: RowValidationResult, use_llm: bool | None = None) -> Diagnosis:
    """Tries the LLM mode first when configured, otherwise uses the heuristic.
    Any LLM failure degrades gracefully to the heuristic path instead of
    aborting the run. Error types the heuristic already resolves
    unambiguously skip the LLM outright, regardless of use_llm.
    """
    should_try_llm = use_llm if use_llm is not None else bool(settings.groq_api_key)
    should_try_llm = should_try_llm and result.error_type not in _DETERMINISTIC_ERROR_TYPES

    if should_try_llm:
        try:
            return await diagnose_llm(result)
        except LLMDiagnosisError as exc:
            logger.warning("LLM diagnosis failed, falling back to heuristic: %s", exc)

    return diagnose_heuristic(result)
