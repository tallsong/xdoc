from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import time
from enum import Enum

class DistanceMetric(Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot_product"

@dataclass
class VectorSearchResult:
    id: str
    similarity_score: float
    metadata: Dict[str, Any]
    raw_content: str

class VectorStoreBase(ABC):
    def __init__(
        self,
        embedding_dimension: int,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        **kwargs
    ):
        self.embedding_dimension = embedding_dimension
        self.distance_metric = distance_metric
        self.stats = {
            "write_time": 0,
            "search_time": 0,
            "vector_count": 0,
            "index_size": 0
        }

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the vector store with specified configuration"""
        pass

    @abstractmethod
    def add_vectors(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: List[Dict[str, Any]],
        raw_content: List[str]
    ) -> None:
        """Add vectors to the store with associated metadata"""
        pass

    @abstractmethod
    def add_texts(
        self,
        texts: List[str],
        ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        """Add texts to be converted to vectors and stored"""
        pass

    @abstractmethod
    def search(
        self,
        query: Union[str, List[float]],
        filter_metadata: Optional[Dict[str, Any]] = None,
        keyword_filter: Optional[str] = None,
        top_k: int = 10
    ) -> List[VectorSearchResult]:
        """Search for similar vectors with optional filtering"""
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """Delete vectors by their IDs"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all vectors from the store"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics"""
        return self.stats

    def _update_stats(self, operation: str, start_time: float) -> None:
        """Update operation statistics"""
        duration = time.time() - start_time
        if operation == "write":
            self.stats["write_time"] = duration
        elif operation == "search":
            self.stats["search_time"] = duration