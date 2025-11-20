import chromadb
from chromadb.config import Settings
from chromadb.api import Collection
from typing import List, Dict, Any, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import time

from .base import VectorStoreBase, DistanceMetric, VectorSearchResult

class ChromaDBStore(VectorStoreBase):
    def __init__(
        self,
        embedding_dimension: int,
        collection_name: str = "default",
        persist_directory: Optional[str] = None,
        embedding_model: Optional[str] = "all-MiniLM-L6-v2",
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ):
        super().__init__(embedding_dimension, distance_metric)
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.embedding_model = (
            SentenceTransformer(embedding_model) if embedding_model else None
        )

    def initialize(self) -> None:
        settings = Settings()
        if self.persist_directory:
            settings.persist_directory = self.persist_directory
            os.makedirs(self.persist_directory, exist_ok=True)

        self.client = chromadb.Client(settings)
        
        # Map our distance metrics to ChromaDB's metrics
        metric_mapping = {
            DistanceMetric.COSINE: "cosine",
            DistanceMetric.EUCLIDEAN: "l2",
            DistanceMetric.DOT_PRODUCT: "ip"
        }
        
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            print(f"Found existing collection: {self.collection_name}")
        except chromadb.errors.NotFoundError:
            print(f"Creating new collection: {self.collection_name}")
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"dimension": self.embedding_dimension}
            )

    def add_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: List[Dict[str, Any]],
        raw_content: List[str]
    ) -> None:
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        start_time = time.time()
        
        try:
            self.collection.add(
                embeddings=vectors,
                documents=raw_content,
                metadatas=metadata,
                ids=ids
            )
            print(f"Successfully added {len(vectors)} vectors to collection")
            
            self._update_stats("write", start_time)
            self.stats["vector_count"] = self.collection.count()
            
        except Exception as e:
            # Implement retry logic here
            for retry in range(3):
                try:
                    self.collection.add(
                        embeddings=vectors,
                        documents=raw_content,
                        metadatas=metadata,
                        ids=ids
                    )
                    print(f"Successfully added vectors on retry {retry + 1}")
                    break
                except Exception:
                    if retry == 2:
                        print(f"Failed to add vectors after 3 retries: {str(e)}")
                        raise e
                    print(f"Retry {retry + 1} failed, attempting again...")

    def add_texts(
        self,
        texts: List[str],
        ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        if not self.embedding_model:
            raise ValueError("Embedding model not initialized")

        print("Converting texts to vectors...")
        vectors = self.embedding_model.encode(texts).tolist()
        print(f"Successfully converted {len(texts)} texts to vectors")
        self.add_vectors(vectors, ids, metadata, texts)

    def search(
        self,
        query: Union[str, List[float]],
        filter_metadata: Optional[Dict[str, Any]] = None,
        keyword_filter: Optional[str] = None,
        top_k: int = 10
    ) -> List[VectorSearchResult]:
        if not self.collection:
            raise RuntimeError("Collection not initialized")

        start_time = time.time()

        # Convert query to vector if it's a string
        if isinstance(query, str):
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")
            print("Converting query to vector...")
            query_vector = self.embedding_model.encode(query).tolist()
        else:
            query_vector = query

        # Prepare where clause for metadata filtering
        where = None
        if filter_metadata:
            where = filter_metadata

        # Perform the search
        print("Executing search...")
        results = self.collection.query(
            query_embeddings=[query_vector],
            where=where,
            n_results=top_k
        )

        # Format results
        search_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                result = VectorSearchResult(
                    id=results["ids"][0][i],
                    similarity_score=float(results["distances"][0][i]),
                    metadata=dict(results["metadatas"][0][i]),
                    raw_content=results["documents"][0][i]
                )
                search_results.append(result)

        # Apply keyword filter if specified
        if keyword_filter:
            print(f"Applying keyword filter: {keyword_filter}")
            search_results = [
                r for r in search_results
                if keyword_filter.lower() in r.raw_content.lower()
            ]

        self._update_stats("search", start_time)
        print(f"Found {len(search_results)} results")
        return search_results

    def delete(self, ids: List[str]) -> None:
        if not self.collection:
            raise RuntimeError("Collection not initialized")
            
        self.collection.delete(ids=ids)
        self.stats["vector_count"] = self.collection.count()

    def clear(self) -> None:
        if not self.collection:
            raise RuntimeError("Collection not initialized")
            
        self.collection.delete()
        self.stats["vector_count"] = 0

    def optimize(self) -> None:
        # ChromaDB doesn't have explicit optimize/vacuum API exposed easily in client yet?
        # But we can implement it as a no-op or if there is one.
        # Currently no-op.
        pass

    def cleanup_expired(self) -> None:
        """Clean up expired documents based on TTL."""
        if not self.collection:
             return

        now = time.time()
        try:
            # Query for documents where expires_at < now
            # Chroma filtering: {"expires_at": {"$lt": now}}
            self.collection.delete(
                where={"expires_at": {"$lt": now}}
            )
        except Exception as e:
            print(f"TTL cleanup failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        if self.collection:
            stats["vector_count"] = self.collection.count()
            if self.persist_directory:
                stats["index_size"] = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(self.persist_directory)
                    for filename in filenames
                )
        return stats