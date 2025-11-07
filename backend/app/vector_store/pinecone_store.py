import pinecone
from typing import List, Dict, Any, Optional, Union
import time
from sentence_transformers import SentenceTransformer

from .base import VectorStoreBase, DistanceMetric, VectorSearchResult

class PineconeStore(VectorStoreBase):
    def __init__(
        self,
        embedding_dimension: int,
        api_key: str,
        environment: str,
        index_name: str,
        namespace: Optional[str] = "",
        embedding_model: Optional[str] = "all-MiniLM-L6-v2",
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ):
        super().__init__(embedding_dimension, distance_metric)
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.namespace = namespace
        self.index = None
        self.embedding_model = (
            SentenceTransformer(embedding_model) if embedding_model else None
        )

    def initialize(self) -> None:
        # Initialize Pinecone client
        pinecone.init(api_key=self.api_key, environment=self.environment)
        
        # Map our distance metrics to Pinecone's metrics
        metric_mapping = {
            DistanceMetric.COSINE: "cosine",
            DistanceMetric.EUCLIDEAN: "euclidean",
            DistanceMetric.DOT_PRODUCT: "dotproduct"
        }
        
        # Create index if it doesn't exist
        if self.index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=self.index_name,
                dimension=self.embedding_dimension,
                metric=metric_mapping[self.distance_metric]
            )
        
        self.index = pinecone.Index(self.index_name)
        
        # Update stats
        stats = self.index.describe_index_stats()
        self.stats["vector_count"] = stats.total_vector_count
        self.stats["index_size"] = stats.dimension

    def add_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: List[Dict[str, Any]],
        raw_content: List[str]
    ) -> None:
        if not self.index:
            raise RuntimeError("Index not initialized")

        start_time = time.time()
        
        # Prepare vectors for Pinecone format
        vectors_data = []
        for i in range(len(vectors)):
            # Add raw_content to metadata
            meta = metadata[i].copy()
            meta["raw_content"] = raw_content[i]
            
            vectors_data.append((ids[i], vectors[i], meta))
        
        try:
            # Upsert vectors in batches of 100 (Pinecone's recommended batch size)
            batch_size = 100
            for i in range(0, len(vectors_data), batch_size):
                batch = vectors_data[i:i + batch_size]
                self.index.upsert(
                    vectors=batch,
                    namespace=self.namespace
                )
                
        except Exception as e:
            # Implement retry logic
            for retry in range(3):
                try:
                    for i in range(0, len(vectors_data), batch_size):
                        batch = vectors_data[i:i + batch_size]
                        self.index.upsert(
                            vectors=batch,
                            namespace=self.namespace
                        )
                    break
                except Exception:
                    if retry == 2:
                        raise e
        
        self._update_stats("write", start_time)
        stats = self.index.describe_index_stats()
        self.stats["vector_count"] = stats.total_vector_count

    def add_texts(
        self,
        texts: List[str],
        ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        if not self.embedding_model:
            raise ValueError("Embedding model not initialized")

        vectors = self.embedding_model.encode(texts).tolist()
        self.add_vectors(vectors, ids, metadata, texts)

    def search(
        self,
        query: Union[str, List[float]],
        filter_metadata: Optional[Dict[str, Any]] = None,
        keyword_filter: Optional[str] = None,
        top_k: int = 10
    ) -> List[VectorSearchResult]:
        if not self.index:
            raise RuntimeError("Index not initialized")

        start_time = time.time()

        # Convert query to vector if it's a string
        if isinstance(query, str):
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")
            query_vector = self.embedding_model.encode(query).tolist()
        else:
            query_vector = query

        # Prepare filter
        filter_dict = {}
        if filter_metadata:
            filter_dict.update(filter_metadata)
        if keyword_filter:
            filter_dict["raw_content"] = {"$contains": keyword_filter}

        # Perform the search
        results = self.index.query(
            vector=query_vector,
            filter=filter_dict if filter_dict else None,
            top_k=top_k,
            namespace=self.namespace,
            include_metadata=True
        )

        # Format results
        search_results = []
        for match in results.matches:
            raw_content = match.metadata.pop("raw_content", "")
            result = VectorSearchResult(
                id=match.id,
                similarity_score=float(match.score),
                metadata=match.metadata,
                raw_content=raw_content
            )
            search_results.append(result)

        self._update_stats("search", start_time)
        return search_results

    def delete(self, ids: List[str]) -> None:
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        self.index.delete(ids=ids, namespace=self.namespace)
        stats = self.index.describe_index_stats()
        self.stats["vector_count"] = stats.total_vector_count

    def clear(self) -> None:
        if not self.index:
            raise RuntimeError("Index not initialized")
            
        self.index.delete(delete_all=True, namespace=self.namespace)
        self.stats["vector_count"] = 0

    def get_stats(self) -> Dict[str, Any]:
        stats = super().get_stats()
        if self.index:
            index_stats = self.index.describe_index_stats()
            stats["vector_count"] = index_stats.total_vector_count
            stats["index_size"] = index_stats.dimension
        return stats