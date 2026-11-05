# Hybrid search and retrieval

`retrieval/sparse.py` implements BM25 over the bundled sample corpus. `retrieval/dense.py` searches the local vector index by cosine-equivalent dot product for normalized vectors, or queries the configured Pinecone namespace when `VECTOR_BACKEND=pinecone`. `retrieval/hybrid.py` fuses candidate rankings with weighted reciprocal rank fusion (RRF), preserving component scores and source metadata. Use `aretrieve()` from async API or agent code; synchronous `hybrid_search()` is available for scripts.

Metadata filters support department, document type, access level, and inclusive creation date bounds. Both retrieval paths apply the same filters. Pinecone receives equivalent metadata filters server-side. Local sparse scoring uses raw BM25; dense similarity and BM25 scores have different scales, so hybrid order is based on RRF rather than directly adding the raw values.

## Configure

Run local ingestion first: `python scripts/ingest_sample_data.py`. To use Pinecone, set `VECTOR_BACKEND=pinecone`, Pinecone credentials/index/namespace, and select an embedding provider consistent with the index dimension. Pinecone mode requires the remote index to already contain the ingested chunks. The local feature-hash embedder is only a deterministic demo feature representation; use a hosted semantic embedding provider for semantic dense retrieval.
