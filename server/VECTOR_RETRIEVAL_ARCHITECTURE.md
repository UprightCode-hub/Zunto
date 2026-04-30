# Zunto Production Vector Retrieval Layer

## Current State

- `homepage_reco_catalog` uses marketplace `Product` rows, structured SQL filters, and `Product.embedding_vector` JSON as the source for semantic product matching.
- Support RAG uses lane-separated FAQ data under `assistant/data/rag_index/<lane>/` and `updated_faq.json` as the canonical source.
- These systems are intentionally separate. Product retrieval must not query FAQ chunks, and support RAG must not query product vectors.

## Vector Store Comparison

| Backend | Fit For Zunto Now | Strengths | Risks |
| --- | --- | --- | --- |
| pgvector | Best first production backend | Runs inside the existing Postgres system of record, supports HNSW/IVFFlat, works with Django/Psycopg, avoids another service, and keeps SQL filters close to vector search. | Requires Postgres extension and careful recall tuning when filters are selective. |
| Qdrant | Strong next step at high scale | Purpose-built vector DB, HNSW, payload indexes, filtering, collections, and named vectors. | Adds a separate database/service, sync pipeline, backup, auth, and network latency. |
| Weaviate | Strong for built-in hybrid RAG | Built-in hybrid vector plus BM25, schema objects, managed cloud path. | More infrastructure and data-model ownership than Zunto needs for first production recommender vector search. |
| Milvus | Strong for very large vector workloads | Large-scale index options, sharding, multiple ANN index types, and high-throughput vector operations. | Heavier operational footprint than current marketplace scale requires. |

## Recommendation

Use `pgvector` first for Zunto production product recommendations.

Reasons:

- Zunto already uses Postgres in production through `DATABASE_URL`.
- Render Postgres supports `pgvector` through `CREATE EXTENSION vector`.
- Product recommendation requires hard SQL filters for price, stock, location, condition, brand, and product family before ranking. Keeping vector search close to SQL constraints reduces data drift and operational complexity.
- A separate vector DB should become phase two only when catalog size, latency, or recall measurements justify extra infrastructure.

## Implemented Production Path

- `market_product_vector` is a derived product-vector index table, created only on PostgreSQL.
- Local SQLite keeps using the current JSON cosine fallback.
- `PRODUCT_VECTOR_BACKEND=auto` prefers pgvector when the table and extension exist; otherwise it falls back safely.
- Product vector sync is triggered from `generate_product_embedding()`, so existing seed and embedding rebuild paths continue to work.
- `rebuild_product_vector_index` rebuilds product embeddings and syncs pgvector when available.

## Non-Negotiable Separation

- Product vectors: `market_product_vector`, lane `homepage_reco_catalog`, source of truth `market.Product`.
- Support FAQ/RAG vectors: lane folders under `assistant/data/rag_index/<lane>/`, source of truth `assistant/data/updated_faq.json`.
- No canonical document or vector row should be duplicated across product retrieval and support RAG.

## Next Production Steps

1. Enable pgvector in production Postgres by applying migrations.
2. Run `python manage.py rebuild_product_vector_index`.
3. Track search latency, candidate count, pgvector hit count, JSON fallback count, and recall eval pass rate.
4. Move support RAG from disk FAISS to a separate pgvector table only after product retrieval is stable.
5. Re-evaluate Qdrant or Milvus when catalog vectors reach a scale where Postgres query plans or filtered ANN recall become a measurable blocker.
