import os
import aiofiles
from typing import Union, BinaryIO
from .base import StorageBackend
import stat

class LocalStorage(StorageBackend):
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)

    def _get_full_path(self, path: str) -> str:
        return os.path.join(self.root_dir, path)

    async def upload(self, path: str, content: Union[bytes, BinaryIO]) -> bool:
        full_path = self._get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        if isinstance(content, bytes):
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content)
        else:
            # Assuming file-like object
            async with aiofiles.open(full_path, 'wb') as f:
                await f.write(content.read())
        return True

    async def download(self, path: str) -> bytes:
        full_path = self._get_full_path(path)
        async with aiofiles.open(full_path, 'rb') as f:
            return await f.read()

    async def delete(self, path: str) -> bool:
        full_path = self._get_full_path(path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    async def exists(self, path: str) -> bool:
        return os.path.exists(self._get_full_path(path))

    async def set_readonly(self, path: str, readonly: bool = True) -> bool:
        full_path = self._get_full_path(path)
        if not os.path.exists(full_path):
            return False

        mode = os.stat(full_path).st_mode
        if readonly:
            os.chmod(full_path, mode & ~stat.S_IWRITE)
        else:
            os.chmod(full_path, mode | stat.S_IWRITE)
        return True
