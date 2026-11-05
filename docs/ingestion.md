# Document ingestion and data model

`models/documents.py` defines validated `DocumentRecord` and `DocumentChunk` Pydantic schemas. `retrieval/chunking.py` splits normalized text into overlapping chunks and derives stable source-linked chunk IDs. `retrieval/embeddings.py` provides deterministic local feature-hash vectors and an optional OpenAI embedding adapter. `retrieval/ingest.py` loads Markdown metadata, chunks documents, embeds them, and writes to a local JSONL index or Pinecone namespace.

## Local format

Each line in `data/local_index.jsonl` is a JSON record with `id`, `values`, and metadata. This is an inspection-friendly demo index; stage 3 will add search and ranking over the local corpus.

## Pinecone

Install the Pinecone SDK, configure credentials and index/namespace, and run the script with `--backend pinecone`. The selected embedding vector dimension must match the configured Pinecone index. Local feature-hash vectors are for repeatable demos and should not be presented as semantic search quality.
