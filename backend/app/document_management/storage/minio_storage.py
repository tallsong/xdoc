from minio import Minio
from minio.error import S3Error
from typing import Union, BinaryIO
from .base import StorageBackend
import io
import logging

logger = logging.getLogger(__name__)

class MinioStorage(StorageBackend):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False
    ):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket_name = bucket_name

        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
        except S3Error as e:
             logger.error(f"Failed to check/create bucket: {e}")
             # We might continue or raise depending on if bucket is strictly required now.
             # Often Minio constructor shouldn't fail if bucket check fails due to connection issues?
             # But here we are in init.

    async def upload(self, path: str, content: Union[bytes, BinaryIO]) -> bool:
        try:
            if isinstance(content, bytes):
                data = io.BytesIO(content)
                length = len(content)
            else:
                data = content
                # Need length for minio put_object
                content.seek(0, 2)
                length = content.tell()
                content.seek(0)

            self.client.put_object(
                self.bucket_name,
                path,
                data,
                length
            )
            return True
        except S3Error as e:
            logger.error(f"Minio upload error: {e}")
            return False

    async def download(self, path: str) -> bytes:
        try:
            response = self.client.get_object(self.bucket_name, path)
            return response.read()
        finally:
            if 'response' in locals():
                response.close()

    async def delete(self, path: str) -> bool:
        try:
            self.client.remove_object(self.bucket_name, path)
            return True
        except S3Error:
            return False

    async def exists(self, path: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, path)
            return True
        except S3Error:
            return False

    async def set_readonly(self, path: str, readonly: bool = True) -> bool:
        # Minio (S3) doesn't have simple chmod.
        # Similar to S3, we might use retention policies if bucket supports it.
        return True
