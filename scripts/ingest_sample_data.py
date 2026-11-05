"""Index the bundled sample documents locally or in Pinecone."""

import argparse
import json

from retrieval.ingest import ingest_sample_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("local", "pinecone"), default="local")
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--overlap", type=int, default=120)
    args = parser.parse_args()
    result = ingest_sample_data(backend=args.backend, chunk_size=args.chunk_size, overlap=args.overlap)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
