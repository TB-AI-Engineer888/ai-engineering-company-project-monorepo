"""Unit tests for HealthCore retrieval and answer generation.

Qdrant and the generation model are mocked. No network and no live database.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.pipelines import rag
from data.process.rag import SOURCE_SLUGS, chunk_markdown, load_corpus, point_id


class _Point:
    def __init__(self, score: float, payload: dict) -> None:
        self.score = score
        self.payload = payload


class _Result:
    def __init__(self, points: list[_Point]) -> None:
        self.points = points


class _Client:
    def __init__(self, points: list[_Point]) -> None:
        self.points = points
        self.limit = None

    def query_points(self, **kwargs):
        self.limit = kwargs.get("limit")
        return _Result(self.points)


def test_each_source_document_yields_at_least_three_chunks() -> None:
    counts: dict[str, int] = {}
    for chunk in load_corpus():
        counts[chunk["source_document"]] = counts.get(chunk["source_document"], 0) + 1
    assert set(counts) == set(SOURCE_SLUGS.values())
    assert all(count >= 3 for count in counts.values())


def test_chunk_ids_are_stable() -> None:
    first = point_id("appointment-policy", 1)
    second = point_id("appointment-policy", 1)
    other = point_id("appointment-policy", 2)
    assert first == second
    assert first != other


def test_list_items_are_not_split_mid_rule() -> None:
    markdown = """# Sample

Rules:
- Cancelling more than 24 hours in advance: no charge.
- Medicare or Medicaid patients: not charged a no-show fee.
"""
    chunks = chunk_markdown("appointment-policy", markdown)
    joined = "\n".join(chunk["text"] for chunk in chunks)
    assert "Cancelling more than 24 hours in advance: no charge." in joined
    assert "not charged a no-show fee" in joined


def test_retrieve_drops_hits_below_min_score(monkeypatch) -> None:
    client = _Client(
        [
            _Point(0.91, {"text": "kept", "source_document": "appointment-policy", "chunk_index": 0}),
            _Point(0.40, {"text": "dropped", "source_document": "appointment-policy", "chunk_index": 1}),
        ]
    )
    monkeypatch.setattr(rag, "embed", lambda _text: [0.1, 0.2])
    monkeypatch.setattr(rag, "qdrant_client", lambda: client)
    rows = rag.retrieve("cancellation fee", k=5, min_score=0.62)
    assert client.limit == 5
    assert [row["text"] for row in rows] == ["kept"]


def test_retrieve_can_return_fewer_than_k(monkeypatch) -> None:
    client = _Client(
        [
            _Point(0.2, {"text": "no", "chunk_index": 0}),
            _Point(0.1, {"text": "also no", "chunk_index": 1}),
        ]
    )
    monkeypatch.setattr(rag, "embed", lambda _text: [0.1])
    monkeypatch.setattr(rag, "qdrant_client", lambda: client)
    assert rag.retrieve("capital of France", k=5, min_score=0.62) == []


def test_query_returns_the_model_output_not_the_raw_chunk(monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(
        rag,
        "retrieve",
        lambda _question, **_kwargs: [
            {"text": "RAW CHUNK ONLY", "source_document": "appointment-policy", "section": "Fees", "chunk_index": 0}
        ],
    )
    monkeypatch.setattr(rag, "_chat", lambda _prompt: "Medicare patients are not charged a no-show fee.")
    answer = rag.query("Is there a no-show fee?")
    assert answer == "Medicare patients are not charged a no-show fee."
    assert answer != "RAW CHUNK ONLY"


def test_query_says_when_nothing_is_relevant(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(rag, "retrieve", lambda _question, **_kwargs: [])
    answer = rag.query("What is the capital of France?")
    assert "won't guess" in answer
    assert "Paris" not in answer
