"""Retrieve HealthCore policy chunks and answer as the front desk.

`query()` is the only function the API calls. A later agent can call
`retrieve()` and `generate_answer()` on their own.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.process.rag import (
    COLLECTION,
    MIN_SCORE,
    embed,
    generation_model_name,
    qdrant_client,
)

logger = logging.getLogger("healthcore.rag")

INSUFFICIENT = (
    "I don't have enough information in the HealthCore policy documents to answer that, "
    "so I won't guess."
)
VOICE = (
    "I'm a HealthCore front-desk coordinator on Priya Nair's patient experience team."
)

_COUNTRY_MARKERS = (
    "united states",
    "united kingdom",
    "u.s.",
    "u.k.",
    "texas",
    "florida",
    "georgia",
    "london",
    "manchester",
    "medicare",
    "medicaid",
    "nhs",
)
_INSURANCE_MARKERS = ("insurance", "coverage", "insurer", "plan", "accept", "medicaid", "medicare", "nhs")
_FEE_MARKERS = ("no-show", "noshow", "cancel", "cancellation", "fee", "charge")


def retrieve(query: str, *, k: int = 5, min_score: float = MIN_SCORE) -> list[dict]:
    """Top matches at or above `min_score`. The list can be shorter than k."""
    if k < 1:
        raise ValueError("k must be at least 1")
    vector = embed(query)
    results = qdrant_client().query_points(
        collection_name=COLLECTION,
        query=vector,
        limit=k,
        with_payload=True,
    )
    kept: list[dict] = []
    for point in results.points:
        score = float(point.score)
        logger.info("rag hit score=%.4f source=%s", score, (point.payload or {}).get("source_document"))
        if score < min_score or not point.payload:
            continue
        kept.append(dict(point.payload))
    return kept


def _mentions_country(question: str) -> bool:
    lowered = question.lower()
    if any(marker in lowered for marker in _COUNTRY_MARKERS):
        return True
    # "US" and "UK" as whole words. Avoid matching them inside other words.
    tokens = {token.strip(".,?;:!'\"") for token in lowered.split()}
    return "us" in tokens or "uk" in tokens


def _is_insurance_question(question: str) -> bool:
    lowered = question.lower()
    return any(marker in lowered for marker in _INSURANCE_MARKERS)


def _is_fee_question(question: str) -> bool:
    lowered = question.lower()
    return any(marker in lowered for marker in _FEE_MARKERS)


def _merge(primary: list[dict], extra: list[dict]) -> list[dict]:
    seen = {(row.get("source_document"), row.get("chunk_index")) for row in primary}
    merged = list(primary)
    for row in extra:
        key = (row.get("source_document"), row.get("chunk_index"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def _prompt(question: str, context: list[dict]) -> str:
    if not context:
        blocks = "(no matching policy text)"
    else:
        blocks = "\n\n".join(
            f"[{row.get('source_document')} / {row.get('section')}]\n{row.get('text', '')}"
            for row in context
        )
    return (
        f"{VOICE} Answer only from the policy excerpts below. "
        "Do not invent coverage, fees, or timeframes. "
        "If the excerpts do not contain the answer, say you do not have enough information and do not guess. "
        "If the question is about insurance and does not name a country, distinguish the United States from the United Kingdom. "
        "Never apply a no-show or late-cancellation fee to a Medicare or Medicaid patient. "
        "If an insurer is not listed in the excerpts, say it must be verified with the billing team and do not confirm it.\n\n"
        f"Policy excerpts:\n{blocks}\n\n"
        f"Question: {question}\n"
        "Answer:"
    )


def _chat(prompt: str) -> str:
    import httpx

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    api_url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1").rstrip("/")
    response = httpx.post(
        f"{api_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": generation_model_name(),
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You answer only from the policy excerpts in the user message. "
                        "You speak as a HealthCore front-desk coordinator for Priya Nair."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"]).strip()


def _grounded_answer(question: str, context: list[dict]) -> str:
    """Used when no generation API key is configured. Facts stay verbatim."""
    if not context:
        return f"{VOICE} {INSUFFICIENT}"
    excerpts = "\n".join(str(row.get("text", "")) for row in context)
    parts = [VOICE]
    if (
        _is_insurance_question(question)
        and not _mentions_country(question)
        and "United States" in excerpts
        and "United Kingdom" in excerpts
    ):
        parts.append(
            "HealthCore coverage is not the same in the United States and the United Kingdom. "
            "The rules below are only the ones found in the policy documents."
        )
    if _is_fee_question(question) and "not charged a no-show fee" in excerpts:
        parts.append("Medicare or Medicaid patients are not charged a no-show fee.")
    for row in context:
        text = str(row.get("text", "")).strip()
        if text:
            parts.append(text)
    joined = " ".join(part.lower() for part in parts)
    if _is_insurance_question(question) and "billing team" in joined:
        parts.append(
            "If the insurer is not in those excerpts, do not confirm coverage. "
            "Verify it with the billing team first."
        )
    parts.append("I will not add a coverage rule, fee, or timeframe that is not in those excerpts.")
    return "\n\n".join(parts)


def generate_answer(question: str, context: list[dict]) -> str:
    """Turn retrieved policy chunks into the coordinator's answer."""
    prompt = _prompt(question, context)
    if not os.environ.get("LLM_API_KEY", "").strip():
        if not context:
            return f"{VOICE} {INSUFFICIENT}"
        return _grounded_answer(question, context)
    try:
        answer = _chat(prompt)
    except Exception:
        logger.exception("generation model call failed")
        if not context:
            return f"{VOICE} {INSUFFICIENT}"
        return _grounded_answer(question, context)
    if not answer:
        return f"{VOICE} {INSUFFICIENT}"
    return answer


def query(question: str) -> str:
    """Retrieve, then generate. This is the only call the API makes."""
    context = retrieve(question)
    if _is_insurance_question(question) and not _mentions_country(question):
        context = _merge(
            context,
            retrieve("United States and United Kingdom accepted insurance coverage"),
        )
    if _is_fee_question(question):
        fee_rows = [
            row
            for row in retrieve("Medicare or Medicaid patients are not charged a no-show fee")
            if "not charged a no-show fee" in str(row.get("text", ""))
        ]
        context = _merge(context, fee_rows)
    return generate_answer(question, context)
