import json

from groq import AsyncGroq

from app.config import settings
from app.core.pipeline.diagnosis.base import Diagnosis, TransformID
from app.core.pipeline.validation import RowValidationResult

_SYSTEM_PROMPT = (
    "You are a data-repair diagnostic assistant for an order pipeline. "
    "Given a single invalid row and its validation error, identify the most likely "
    "root cause and choose EXACTLY ONE transform from this fixed list, or 'no_fix' "
    "if none applies safely:\n"
    "- coerce_amount: amount has currency symbols or formatting noise around a valid number\n"
    "- reformat_date: order_date is a real calendar date in a non-ISO format (e.g. DD/MM/YYYY)\n"
    "- fix_encoding: order_id or customer_id has a trailing non-ASCII/mojibake artifact\n"
    "- no_fix: missing/blank required fields, unresolvable foreign keys, or anything you "
    "cannot safely fix without guessing a value\n"
    "Never invent a value or a transform outside this list. "
    'Respond with ONLY a JSON object: {"hypothesis": str, "transform": str, "confidence": float 0-1, "reasoning": str}.'
)


class LLMDiagnosisError(Exception):
    pass


async def diagnose_llm(result: RowValidationResult, client: AsyncGroq | None = None) -> Diagnosis:
    if result.valid:
        raise ValueError("Cannot diagnose a row that already passed validation")
    if client is None and not settings.groq_api_key:
        raise LLMDiagnosisError("GROQ_API_KEY is not configured")

    # Send every current validation error, not just the first -- a row can fail
    # on more than one field at once, and the first-listed error isn't
    # necessarily the one worth fixing.
    user_prompt = (
        f"Row data: {result.raw_row}\n"
        f"Error type: {result.error_type}\n"
        f"Validation errors: {result.errors}"
    )

    try:
        groq_client = client or AsyncGroq(api_key=settings.groq_api_key)
        response = await groq_client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    except LLMDiagnosisError:
        raise
    except Exception as exc:
        raise LLMDiagnosisError(f"Groq API call failed: {exc}") from exc

    try:
        parsed = json.loads(content)
        transform_raw = parsed["transform"]
        confidence = float(parsed["confidence"])
        hypothesis = str(parsed["hypothesis"])
        reasoning = str(parsed["reasoning"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LLMDiagnosisError(f"Unparseable LLM output: {content!r}") from exc

    if not 0 <= confidence <= 1:
        raise LLMDiagnosisError(f"Confidence out of range: {confidence}")

    if transform_raw == "no_fix":
        transform = None
    else:
        try:
            transform = TransformID(transform_raw)
        except ValueError as exc:
            raise LLMDiagnosisError(f"Unknown transform proposed by LLM: {transform_raw!r}") from exc

    return Diagnosis(
        hypothesis=hypothesis,
        transform=transform,
        confidence=confidence,
        reasoning=reasoning,
        source="llm",
    )
