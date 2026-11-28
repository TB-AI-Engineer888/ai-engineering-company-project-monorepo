"""Chunk HealthCore policy documents and index them in Qdrant.

From the monorepo root, with the API virtualenv:

    python data/process/rag.py

`setup()` is safe to run again. Each chunk has a deterministic id, and any
older points for the same source document are removed before the new upsert.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, Filter, FieldCondition, MatchValue, PointStruct, VectorParams

CORPUS_DIR = _ROOT / "docs" / "company-knowledge-base"
COLLECTION = "healthcore_knowledge"
COMPANY = "healthcore"
LANGUAGE = "en"
# Cosine on BAAI/bge-small-en-v1.5. Relevant policy chunks land near 0.70 and
# above. 0.62 drops off-topic questions and still keeps the correct chunk in
# the top 3 for the eval set. See docs/rag/rag-design.md.
MIN_SCORE = 0.62
LOCAL_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_MODEL = "downtown-miami/openrouter/perplexity/pplx-embed-v1-0.6b"
GENERATION_MODEL = "downtown-miami/openrouter/deepseek/deepseek-v4-flash"
API_URL = "https://llm.4geeks.ai/v1"
POINT_NAMESPACE = uuid.UUID("8c1b6a4e-5d27-4f0a-9b3c-1e7a2d6f90ab")

SOURCE_SLUGS = {
    "healthcore-insurance-coverage.en.md": "insurance-coverage",
    "healthcore-appointment-policy.en.md": "appointment-policy",
    "healthcore-referral-process.en.md": "referral-process",
    "healthcore-new-patient-checklist.en.md": "new-patient-checklist",
}

_embedder = None


def embedding_model_name() -> str:
    return os.environ.get("LLM_EMBEDDING_MODEL", EMBEDDING_MODEL).strip() or EMBEDDING_MODEL


def generation_model_name() -> str:
    return os.environ.get("LLM_MODEL", GENERATION_MODEL).strip() or GENERATION_MODEL


def qdrant_client() -> QdrantClient:
    url = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333").strip()
    return QdrantClient(url=url, timeout=30, check_compatibility=False)


def _is_list_item(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("- "):
        return True
    digits = stripped.split(".", 1)[0]
    return digits.isdigit() and "." in stripped


def _section_from_prose(text: str, title: str) -> str:
    head, separator, _rest = text.partition(":")
    if separator and 0 < len(head) <= 80 and "\n" not in head:
        return head.strip()
    return title


def _paragraphs(markdown: str) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for raw_line in markdown.splitlines():
        if not raw_line.strip():
            if current:
                groups.append(current)
                current = []
            continue
        current.append(raw_line.strip())
    if current:
        groups.append(current)
    return groups


def chunk_markdown(source_document: str, markdown: str) -> list[dict]:
    """Split one policy file into self-contained chunks.

    Wrapped lines are joined first, so a fee or a coverage rule stays whole.
    Each bullet or numbered step becomes its own chunk under its heading.
    A prose paragraph stays whole.
    """
    title = source_document
    pieces: list[tuple[str, str]] = []

    for lines in _paragraphs(markdown):
        if lines[0].startswith("#"):
            title = lines[0].lstrip("#").strip()
            continue
        section = title
        items: list[str] = []
        prose: list[str] = []
        for line in lines:
            if line.endswith(":") and not _is_list_item(line):
                if prose:
                    prose.append(line)
                    section = _section_from_prose(" ".join(prose), title)
                    continue
                if len(line.split()) > 8:
                    pieces.append((_section_from_prose(line, title), line))
                    section = _section_from_prose(line, title)
                    continue
                section = line.rstrip(":")
                continue
            if _is_list_item(line):
                if prose and not items:
                    pieces.append((_section_from_prose(" ".join(prose), title), " ".join(prose)))
                    prose = []
                items.append(line)
                continue
            if items:
                items[-1] = f"{items[-1]} {line}"
            else:
                prose.append(line)
        if prose and not items:
            text = " ".join(prose)
            pieces.append((_section_from_prose(text, title), text))
        for item in items:
            pieces.append((section, f"{section}:\n{item}"))

    chunks: list[dict] = []
    for index, (section, text) in enumerate(pieces):
        cleaned = text.strip()
        if not cleaned or (cleaned.endswith(":") and "\n" not in cleaned):
            continue
        chunks.append(
            {
                "company": COMPANY,
                "source_document": source_document,
                "section": section,
                "language": LANGUAGE,
                "chunk_index": 0,
                "text": cleaned,
            }
        )
    for index, chunk in enumerate(chunks):
        chunk["chunk_index"] = index
    return chunks


def load_corpus(corpus_dir: Path | None = None) -> list[dict]:
    folder = corpus_dir or CORPUS_DIR
    chunks: list[dict] = []
    for filename, slug in SOURCE_SLUGS.items():
        path = folder / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        document_chunks = chunk_markdown(slug, path.read_text(encoding="utf-8"))
        if len(document_chunks) < 3:
            raise RuntimeError(f"{slug} produced {len(document_chunks)} chunks; at least 3 are required")
        chunks.extend(document_chunks)
    return chunks


def point_id(source_document: str, chunk_index: int) -> str:
    return str(uuid.uuid5(POINT_NAMESPACE, f"{source_document}:{chunk_index}"))


def _local_embedder(model_name: str):
    global _embedder
    if _embedder is None or getattr(_embedder, "model_name", None) != model_name:
        from fastembed import TextEmbedding

        _embedder = TextEmbedding(model_name)
        _embedder.model_name = model_name
    return _embedder


def _embed_http(text: str, model_name: str) -> list[float]:
    import httpx

    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise ValueError("LLM_API_KEY is required for the remote embeddings model")
    api_url = os.environ.get("LLM_API_URL", API_URL).rstrip("/")
    response = httpx.post(
        f"{api_url}/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model_name, "input": text},
        timeout=60,
    )
    response.raise_for_status()
    return list(response.json()["data"][0]["embedding"])


def embed(text: str) -> list[float]:
    """Vector for one string. Index time and query time both call this."""
    cleaned = " ".join(text.split())
    if not cleaned:
        raise ValueError("embed() requires text")
    model_name = embedding_model_name()
    if model_name == generation_model_name():
        raise ValueError("embed() must use a different model from the generation model")
    local_name = model_name
    if not model_name.startswith(("BAAI/", "sentence-transformers/", "jinaai/", "nomic-ai/", "Qdrant/")):
        if not os.environ.get("LLM_API_KEY", "").strip():
            local_name = LOCAL_EMBEDDING_MODEL
        else:
            return _embed_http(cleaned, model_name)
    vector = next(iter(_local_embedder(local_name).embed([cleaned])))
    return [float(value) for value in vector]


def setup(corpus_dir: Path | None = None, client: QdrantClient | None = None) -> int:
    """Index every source document. Returns the number of chunks stored."""
    chunks = load_corpus(corpus_dir)
    sample = embed(chunks[0]["text"])
    qdrant = client or qdrant_client()
    existing = {item.name: item for item in qdrant.get_collections().collections}
    if COLLECTION in existing:
        info = qdrant.get_collection(COLLECTION)
        size = info.config.params.vectors.size
        if size != len(sample):
            qdrant.delete_collection(COLLECTION)
            existing.pop(COLLECTION, None)
    if COLLECTION not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=len(sample), distance=Distance.COSINE),
        )

    by_source: dict[str, list[dict]] = {}
    for chunk in chunks:
        by_source.setdefault(chunk["source_document"], []).append(chunk)

    for source, source_chunks in by_source.items():
        qdrant.delete(
            collection_name=COLLECTION,
            points_selector=Filter(
                must=[FieldCondition(key="source_document", match=MatchValue(value=source))]
            ),
        )
        points = [
            PointStruct(
                id=point_id(chunk["source_document"], chunk["chunk_index"]),
                vector=embed(chunk["text"]),
                payload=chunk,
            )
            for chunk in source_chunks
        ]
        qdrant.upsert(collection_name=COLLECTION, points=points)
    return len(chunks)


if __name__ == "__main__":
    stored = setup()
    print(f"Indexed {stored} chunks into {COLLECTION}")
