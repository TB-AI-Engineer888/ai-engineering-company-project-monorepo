# HealthCore RAG design

This is the desk assistant for Priya Nair's patient coordinators. It answers from the four policy documents only. It does not store patient records.

## RAG process

1. `docs/company-knowledge-base/` holds the four source files: insurance coverage, appointment policy, referral process, and the new-patient checklist.
2. `setup()` in `data/process/rag.py` reads those files, splits them into chunks, and embeds each chunk with `embed()`.
3. The vectors go into the Qdrant collection `healthcore_knowledge` on cosine distance. Each point payload has `company`, `source_document`, `section`, `language`, `chunk_index`, and `text`.
4. A coordinator question hits `POST /knowledge/query`. The router calls `query()` and returns `{ "answer": "..." }` only.
5. `query()` in `data/pipelines/rag.py` calls `retrieve()`, which embeds the question with the same `embed()` function and keeps hits at or above `min_score`. It can return fewer than 5 chunks.
6. `generate_answer()` builds the coordinator prompt from those chunks and asks the generation model for the reply. `query()` is only `retrieve()` plus `generate_answer()`.
7. If nothing clears the threshold, the answer says the policy documents do not contain enough information. It does not guess.

```text
question -> embed -> Qdrant healthcore_knowledge
        -> drop scores under 0.62
        -> coordinator prompt
        -> generation model
        -> answer
```

Qdrant runs from `docker-compose.yml` on port 6333. `QDRANT_URL` overrides the address.

## Chunking strategy

The source files are short policies with hard line wraps. The splitter joins a wrapped line back onto the bullet or sentence it belongs to before it cuts anything.

Each bullet and each numbered step becomes its own chunk. The heading that introduced it is repeated on the chunk, so "50 USD" is never separated from "cancelling less than 24 hours in advance." A prose rule, such as the 11-day referral average or the Marcus Reid escalation, stays as one paragraph. A heading with no rule under it is not stored.

That fits this corpus because every fee, insurer, and deadline is already one bullet. A fixed character window would have split the Medicaid sentence across the Georgia exception. After `setup()`, the collection holds 30 chunks: 8 insurance, 7 appointment, 7 referral, and 8 new-patient.

Re-running `setup()` does not duplicate points. The point id is a UUID5 of `source_document` plus `chunk_index`, and existing points for that source document are deleted before the upsert.

## Embedding practices

`embed()` and the generation call use different model ids.

| Job | Model id | Default |
| --- | --- | --- |
| Embeddings | `LLM_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` |
| Generation | `LLM_MODEL` | `gpt-4o-mini` |

`embed()` refuses to run if those two ids are the same. The default embedding model is a local fastembed model, 384 dimensions, cosine similarity in Qdrant. The same function embeds chunks at index time and the question at query time. Text is whitespace-normalized before embedding. No other preprocessing is applied.

`min_score` is 0.62. On this model, the correct policy chunk for the eval questions scores about 0.78 to 0.87. An unrelated question such as the capital of France scores about 0.41 and is dropped, so the generator is not handed a policy that does not answer the question. The threshold was chosen by reading those scores, not by copying a generic 0.7 from a different embedding model.

`data/eval/test-queries.json` has 14 questions covering all four documents. Recall@3 against `retrieve()` with this threshold is 100%.

The generation model is called at `LLM_API_URL` (default `https://api.openai.com/v1/chat/completions`) when `LLM_API_KEY` is set. The prompt tells it to speak as a HealthCore front-desk coordinator for Priya Nair, to use only the excerpts, to separate the United States from the United Kingdom on coverage questions that name no country, to never charge a Medicare or Medicaid patient a no-show fee, and to send an unlisted insurer to the billing team. If `LLM_API_KEY` is empty, `generate_answer()` still writes that coordinator reply from the retrieved sentences only, and it copies fees and timeframes verbatim so they cannot drift.

The academy model picker can replace either default. Set `LLM_EMBEDDING_MODEL` and `LLM_MODEL` to the two different ids, and set `LLM_API_KEY` plus `LLM_API_URL` when the embeddings id is a remote API model rather than a `BAAI/` or `sentence-transformers/` model.
