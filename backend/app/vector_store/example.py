from typing import List, Dict, Any, Optional
import time
import os
from .factory import VectorStoreFactory
from .base import VectorStoreBase, VectorSearchResult

class VectorDatabaseManager:
    def __init__(
        self,
        store_type: str,
        config: Dict[str, Any],
        backup_store_type: Optional[str] = None,
        backup_config: Optional[Dict[str, Any]] = None
    ):
        self.primary_store = VectorStoreFactory.create_store(store_type, config)
        self.backup_store = None
        if backup_store_type and backup_config:
            self.backup_store = VectorStoreFactory.create_store(
                backup_store_type, backup_config
            )

    def add_texts(
        self,
        texts: List[str],
        ids: List[str],
        metadata: List[Dict[str, Any]]
    ) -> None:
        """Add texts to both primary and backup stores"""
        # Add to primary store
        self.primary_store.add_texts(texts, ids, metadata)
        
        # Add to backup store if available
        if self.backup_store:
            try:
                self.backup_store.add_texts(texts, ids, metadata)
            except Exception as e:
                print(f"Failed to add to backup store: {e}")

    def search(
        self,
        query: str,
        filter_metadata: Optional[Dict[str, Any]] = None,
        keyword_filter: Optional[str] = None,
        top_k: int = 10
    ) -> List[VectorSearchResult]:
        """Search in primary store with fallback to backup"""
        try:
            return self.primary_store.search(
                query,
                filter_metadata,
                keyword_filter,
                top_k
            )
        except Exception as e:
            if self.backup_store:
                print(f"Primary store search failed, using backup: {e}")
                return self.backup_store.search(
                    query,
                    filter_metadata,
                    keyword_filter,
                    top_k
                )
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from both stores"""
        stats = {
            "primary": self.primary_store.get_stats()
        }
        if self.backup_store:
            stats["backup"] = self.backup_store.get_stats()
        return stats

# 使用示例
def example_usage():
    # ChromaDB配置
    chroma_config = {
        "embedding_dimension": 384,
        "collection_name": "test_collection",
            "persist_directory": os.path.join(os.path.dirname(__file__), "vector_store"),
        "embedding_model": "all-MiniLM-L6-v2"
    }
    
        # 创建向量数据库管理器（仅使用ChromaDB）
    manager = VectorDatabaseManager(
        store_type="chroma",
            config=chroma_config
    )
    
    # 添加一些测试数据
    texts = [
        "人工智能正在改变我们的生活",
        "机器学习是人工智能的一个重要分支",
        "深度学习在图像识别领域取得了突破性进展"
    ]
    ids = ["1", "2", "3"]
    metadata = [
        {"category": "AI", "source": "article"},
        {"category": "ML", "source": "textbook"},
        {"category": "DL", "source": "research_paper"}
    ]
    
    # 添加文本
    manager.add_texts(texts, ids, metadata)
    
    # 执行搜索
    results = manager.search(
        query="人工智能应用",
        filter_metadata={"source": "article"},
        keyword_filter="生活",
        top_k=2
    )
    
    # 打印结果
    for result in results:
        print(f"ID: {result.id}")
        print(f"相似度: {result.similarity_score}")
        print(f"内容: {result.raw_content}")
        print(f"元数据: {result.metadata}")
        print("---")
    
    # 获取统计信息
    stats = manager.get_stats()
    print("统计信息:", stats)

if __name__ == "__main__":
    example_usage()