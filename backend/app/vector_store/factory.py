from typing import Dict, Any, Optional, Type
from .base import VectorStoreBase
from .chroma import ChromaDBStore
from .pinecone_store import PineconeStore
from .weaviate_store import WeaviateStore

class VectorStoreFactory:
    _stores: Dict[str, Type[VectorStoreBase]] = {
        "chroma": ChromaDBStore,
        "pinecone": PineconeStore,
        "weaviate": WeaviateStore
    }

    @classmethod
    def register_store(cls, name: str, store_class: Type[VectorStoreBase]) -> None:
        """Register a new vector store implementation"""
        cls._stores[name] = store_class

    @classmethod
    def create_store(
        cls,
        store_type: str,
        config: Dict[str, Any]
    ) -> VectorStoreBase:
        """
        Create a vector store instance based on configuration
        
        Args:
            store_type: Type of vector store ("chroma", "pinecone", etc.)
            config: Configuration dictionary for the store
            
        Returns:
            Initialized vector store instance
        """
        if store_type not in cls._stores:
            raise ValueError(f"Unsupported vector store type: {store_type}")
            
        store_class = cls._stores[store_type]
        store = store_class(**config)
        store.initialize()
        return store

# 示例配置
DEFAULT_CONFIGS = {
    "chroma": {
        "embedding_dimension": 384,
        "collection_name": "default",
        "persist_directory": "./vector_store",
        "embedding_model": "all-MiniLM-L6-v2"
    },
    "pinecone": {
        "embedding_dimension": 384,
        "api_key": "<your-api-key>",  # Set via env var PINECONE_API_KEY
        "environment": "gcp-starter",  # Or your Pinecone environment
        "index_name": "xdoc-test",
        "namespace": "default",
        "embedding_model": "all-MiniLM-L6-v2"
    }
}