import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
from weaviate.collections.classes.filters import Filter
from typing import List, Dict, Any, Optional, Union
import time
import uuid
import logging
from sentence_transformers import SentenceTransformer

from .base import VectorStoreBase, DistanceMetric, VectorSearchResult

logger = logging.getLogger(__name__)

class WeaviateStore(VectorStoreBase):
    def __init__(
        self,
        embedding_dimension: int,
        url: str,
        class_name: str = "Document",
        api_key: Optional[str] = None,
        embedding_model: Optional[str] = "all-MiniLM-L6-v2",
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ):
        super().__init__(embedding_dimension, distance_metric)
        self.url = url
        self.class_name = class_name
        self.api_key = api_key
        self.client = None
        self.collection = None
        self.embedding_model = (
            SentenceTransformer(embedding_model) if embedding_model else None
        )

    def initialize(self) -> None:
        # Initialize Weaviate client (v4)
        auth_config = weaviate.auth.AuthApiKey(api_key=self.api_key) if self.api_key else None

        try:
            if "localhost" in self.url or "127.0.0.1" in self.url:
                # Parse host and port safely
                parts = self.url.replace("http://", "").replace("https://", "").split(":")
                host = parts[0]
                port = int(parts[1]) if len(parts) > 1 else 8080

                self.client = weaviate.connect_to_local(
                    host=host,
                    port=port
                )
            else:
                # For remote connections or custom setups, assume URL is full endpoint
                # Weaviate v4 connect_to_custom needs specific parts
                # This is a bit complex to parse generically from a single URL string
                # but we make a best effort assumption that URL contains scheme, host, port
                from urllib.parse import urlparse
                parsed = urlparse(self.url)
                host = parsed.hostname or self.url
                port = parsed.port or 8080
                secure = parsed.scheme == "https"

                self.client = weaviate.connect_to_custom(
                    http_host=host,
                    http_port=port,
                    http_secure=secure,
                    grpc_host=host,
                    grpc_port=50051, # Default GRPC port, might need config
                    grpc_secure=secure,
                    auth_credentials=auth_config
                )

            # Create collection if not exists
            if not self.client.collections.exists(self.class_name):
                logger.info(f"Creating new Weaviate collection {self.class_name}")

                # Map metrics
                metric_mapping = {
                    DistanceMetric.COSINE: VectorDistances.COSINE,
                    DistanceMetric.EUCLIDEAN: VectorDistances.L2_SQUARED, # Weaviate uses L2 squared for Euclidean
                    DistanceMetric.DOT_PRODUCT: VectorDistances.DOT
                }

                self.client.collections.create(
                    name=self.class_name,
                    vectorizer_config=Configure.Vectorizer.none(),
                    properties=[
                        Property(name="raw_content", data_type=DataType.TEXT),
                        # Metadata fields should be added dynamically or predefined
                    ],
                    vector_index_config=Configure.VectorIndex.hnsw(
                        distance_metric=metric_mapping[self.distance_metric]
                    )
                )

            self.collection = self.client.collections.get(self.class_name)
            self._update_internal_stats()

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate: {e}")
            raise e

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

        with self.collection.batch.dynamic() as batch:
            for i in range(len(vectors)):
                # Combine metadata and raw_content
                properties = metadata[i].copy()
                properties["raw_content"] = raw_content[i]

                # Weaviate requires UUIDs
                # If ids are not UUIDs, we might need to generate them or hash them
                # For simplicity, we use the provided ID if it looks like a UUID, otherwise we hash it
                try:
                    uid = uuid.UUID(ids[i])
                except ValueError:
                    uid = uuid.uuid5(uuid.NAMESPACE_DNS, ids[i])

                batch.add_object(
                    properties=properties,
                    vector=vectors[i],
                    uuid=uid
                )

        if len(self.collection.batch.failed_objects) > 0:
             logger.error(f"Failed to add {len(self.collection.batch.failed_objects)} objects")
             for failed in self.collection.batch.failed_objects:
                 logger.error(f"Error: {failed.message}")

        self._update_stats("write", start_time)
        self._update_internal_stats()

    def add_texts(
        self,
        texts: List[str],
        ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        if not self.embedding_model:
            raise ValueError("Embedding model not initialized")

        logger.info("Converting texts to vectors...")
        vectors = self.embedding_model.encode(texts).tolist()
        logger.info(f"Successfully converted {len(texts)} texts to vectors")
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

        if isinstance(query, str):
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")
            query_vector = self.embedding_model.encode(query).tolist()
        else:
            query_vector = query

        # Build filter
        w_filter = None
        if filter_metadata:
            # Simple equality filter implementation for now
            # A robust implementation would handle complex operators
            conditions = []
            for k, v in filter_metadata.items():
                conditions.append(Filter.by_property(k).equal(v))

            if len(conditions) == 1:
                w_filter = conditions[0]
            elif len(conditions) > 1:
                w_filter = conditions[0]
                for c in conditions[1:]:
                    w_filter = w_filter & c

        if keyword_filter:
            # Weaviate Hybrid Search could be used here, but to stick to the interface strictly:
            # We filter results after vector search OR use Weaviate's hybrid if we want to leverage its power.
            # The interface implies "vector search filtered by keywords".
            # Since `keyword_filter` in other stores is implemented as post-filtering or exact match,
            # let's try to map it to a `like` filter if possible or post-process.
            # Weaviate `like` operator is available for text.
             kw_filter = Filter.by_property("raw_content").like(f"*{keyword_filter}*")
             if w_filter:
                 w_filter = w_filter & kw_filter
             else:
                 w_filter = kw_filter

        result = self.collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            filters=w_filter,
            return_metadata=["distance"],
            return_properties=["raw_content"] # Retrieve all properties is default? No, explicitly ask for raw_content plus others?
            # We need to fetch all properties to return metadata
        )

        search_results = []
        for obj in result.objects:
            meta = obj.properties.copy()
            raw_content = meta.pop("raw_content", "")

            search_results.append(VectorSearchResult(
                id=str(obj.uuid),
                similarity_score=1.0 - obj.metadata.distance if obj.metadata.distance is not None else 0.0,
                metadata=meta,
                raw_content=raw_content
            ))

        self._update_stats("search", start_time)
        return search_results

    def delete(self, ids: List[str]) -> None:
        if not self.collection:
             raise RuntimeError("Collection not initialized")

        # Convert IDs to UUIDs if necessary
        uuids = []
        for i in ids:
            try:
                uuids.append(uuid.UUID(i))
            except ValueError:
                uuids.append(uuid.uuid5(uuid.NAMESPACE_DNS, i))

        self.collection.data.delete_many(
            where=Filter.by_id().contains_any(uuids)
        )
        self._update_internal_stats()

    def clear(self) -> None:
        if not self.collection:
             raise RuntimeError("Collection not initialized")
        # Delete all objects
        # Weaviate doesn't have a direct "clear" collection command without deleting collection itself easily via v4 client?
        # Actually, we can delete the collection and recreate it.
        self.client.collections.delete(self.class_name)
        self.initialize()

    def cleanup_expired(self) -> None:
        """Clean up expired documents based on TTL."""
        # Assuming 'ttl' or 'expires_at' in metadata
        # Weaviate doesn't have native TTL in open source (available in enterprise/cloud) unless configured.
        # We simulate it by deleting objects where expires_at < now
        if not self.collection:
             return

        now = time.time()
        # Assuming expires_at is a timestamp number
        try:
            self.collection.data.delete_many(
                where=Filter.by_property("expires_at").less_than(now)
            )
        except Exception as e:
            logger.warning(f"TTL cleanup failed (maybe property missing): {e}")

    def _update_internal_stats(self):
        if self.collection:
            # Count is expensive in Weaviate? aggregate.over_all(total_count=True)
            agg = self.collection.aggregate.over_all(total_count=True)
            self.stats["vector_count"] = agg.total_count
