import unittest
import os
import shutil
from app.vector_store.factory import VectorStoreFactory
from app.vector_store.chroma import ChromaDBStore
from app.vector_store.base import VectorSearchResult

class TestVectorStore(unittest.TestCase):
    def setUp(self):
        self.persist_dir = "./test_chroma_db"
        if os.path.exists(self.persist_dir):
            shutil.rmtree(self.persist_dir)

    def tearDown(self):
        if os.path.exists(self.persist_dir):
            shutil.rmtree(self.persist_dir)

    def test_chroma_store(self):
        print("\nTesting ChromaDB Store...")
        config = {
            "embedding_dimension": 384,
            "collection_name": "test_collection",
            "persist_directory": self.persist_dir,
            "embedding_model": "all-MiniLM-L6-v2"
        }

        store = VectorStoreFactory.create_store("chroma", config)

        # Test add texts
        texts = ["Hello world", "Artificial Intelligence", "Machine Learning"]
        ids = ["1", "2", "3"]
        metadata = [{"source": "test"}, {"source": "test"}, {"source": "test"}]

        store.add_texts(texts, ids, metadata)

        # Test search
        results = store.search("AI", top_k=2)
        self.assertTrue(len(results) > 0)
        print(f"Search results: {results}")

        # Test optimize (should be no-op but run without error)
        store.optimize()

        # Test cleanup (should run without error)
        store.cleanup_expired()

        # Test stats
        stats = store.get_stats()
        print(f"Stats: {stats}")
        self.assertTrue(stats["vector_count"] >= 3)

    # Weaviate and Pinecone require running services/API keys, so we mock or skip
    # For this environment, we only strictly test Chroma as it is local.

if __name__ == "__main__":
    unittest.main()
