from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

_SERVICES_DIR = Path(__file__).resolve().parents[1]
_ROOT = _SERVICES_DIR.parent
for _path in (str(_ROOT), str(_SERVICES_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from data.pipelines.rag import query as answer_question

knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)


@knowledge_router.post("/query")
def knowledge_query(body: KnowledgeQuery) -> dict[str, str]:
    try:
        answer = answer_question(body.question.strip())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="The knowledge base is unavailable.") from exc
    return {"answer": answer}
