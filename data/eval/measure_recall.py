"""Measure Recall@3 for data/eval/test-queries.json.

    python data/eval/measure_recall.py

Requires Qdrant and a completed setup().
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data.pipelines.rag import retrieve

QUERIES = Path(__file__).with_name("test-queries.json")


def recall_at_3() -> tuple[float, list[str]]:
    rows = json.loads(QUERIES.read_text(encoding="utf-8"))
    misses: list[str] = []
    hits = 0
    for row in rows:
        found = retrieve(row["question"], k=3)
        top = found[:3]
        ok = any(
            item.get("source_document") == row["source_document"] and row["expect_text"] in item.get("text", "")
            for item in top
        )
        if ok:
            hits += 1
        else:
            misses.append(row["question"])
    return hits / len(rows), misses


if __name__ == "__main__":
    score, misses = recall_at_3()
    print(f"Recall@3 {score:.0%}")
    for question in misses:
        print(f"MISS {question}")
