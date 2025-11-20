from abc import ABC, abstractmethod
from typing import Optional, BinaryIO, Union
import io

class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, path: str, content: Union[bytes, BinaryIO]) -> bool:
        """Upload content to storage"""
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download content from storage"""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete content from storage"""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file exists"""
        pass

    @abstractmethod
    async def set_readonly(self, path: str, readonly: bool = True) -> bool:
        """Set file as read-only (if supported)"""
        pass
