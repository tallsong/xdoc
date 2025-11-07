"""
Pinecone usage example for the project's vector store adapter.

Prerequisites:
- Install pinecone package: pip install pinecone-python sentence-transformers
- Set environment variables:
    PINECONE_API_KEY  - your Pinecone API key
    PINECONE_ENV      - your Pinecone environment (e.g. us-west1-gcp)
    PINECONE_INDEX    - index name to create/use

Run:
    source .venv/bin/activate
    python -m app.vector_store.example_pinecone

This script will exit early with instructions if the env vars are not set.
"""
import os
import time
from typing import List, Dict, Any

try:
    # Local package import (relative package)
    from .factory import VectorStoreFactory
    from .example import VectorDatabaseManager
except Exception:
    # Support running as a module from repository root
    from app.vector_store.factory import VectorStoreFactory


def main():
    api_key = os.environ.get("PINECONE_API_KEY","pcsk_3YSQrS_9AYXxLFo4imLSVGVgX7tN2mHPARXryNAPqjntsDazgBkaoucywndp1shxBYWxh2")
    environment = os.environ.get("PINECONE_ENV", "gcp-starter")
    index_name = os.environ.get("PINECONE_INDEX", "example-index")
    
    # Map environment to Pinecone's expected region format
    if environment == "gcp-starter":
        cloud = "gcp"
        region = "us-central1"  # GCP starter uses us-central1
    else:
        # For custom environments like "us-west1-gcp"
        region = "-".join(environment.split("-")[:-1])  # e.g., "us-west1"
        cloud = environment.split("-")[-1]  # e.g., "gcp"

    if not api_key or not environment:
        print("Missing Pinecone credentials. Please set the following environment variables:")
        print("  PINECONE_API_KEY and PINECONE_ENV")
        print()
        print("Example (Linux/macOS):")
        print("  export PINECONE_API_KEY=your-key")
        print("  export PINECONE_ENV=your-environment")
        print("  export PINECONE_INDEX=your-index-name")
        return

    pinecone_config = {
        "embedding_dimension": 384,
        "api_key": api_key,
        "environment": environment,
        "index_name": index_name,
        "namespace": "default",
        "embedding_model": "all-MiniLM-L6-v2",
        "cloud": cloud,
        "region": region
    }

    # Use factory to create Pinecone store directly
    try:
        print("Initializing Pinecone store (this will create the index if needed)...")
        store = VectorStoreFactory.create_store("pinecone", pinecone_config)
    except Exception as e:
        print("Failed to initialize Pinecone store:", str(e))
        return

    # Simple demo data
    texts: List[str] = [
        "人工智能正在改变我们的生活",
        "机器学习是人工智能的一个重要分支",
        "深度学习在图像识别领域取得了突破性进展"
    ]
    ids: List[str] = ["p1", "p2", "p3"]
    metadata: List[Dict[str, Any]] = [
        {"category": "AI", "source": "article"},
        {"category": "ML", "source": "textbook"},
        {"category": "DL", "source": "research_paper"}
    ]

    try:
        print("Adding texts to Pinecone index...")
        store.add_texts(texts, ids, metadata)
        print("Add completed.")

        time.sleep(1)

        print("Searching for: '人工智能应用' with filter source=article")
        results = store.search(
            query="人工智能应用",
            filter_metadata={"source": "article"},
            keyword_filter=None,
            top_k=3
        )

        print("Results:")
        for r in results:
            print(f"- id={r.id}, score={r.similarity_score:.4f}, meta={r.metadata}, content={r.raw_content}")

        print("\nStore stats:", store.get_stats())

    except Exception as e:
        print("Error during add/search:", str(e))


if __name__ == "__main__":
    main()
