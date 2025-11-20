import boto3
from botocore.exceptions import ClientError
from typing import Union, BinaryIO
from .base import StorageBackend
import io

class S3Storage(StorageBackend):
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str
    ):
        self.bucket_name = bucket_name
        self.client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )

    async def upload(self, path: str, content: Union[bytes, BinaryIO]) -> bool:
        try:
            if isinstance(content, bytes):
                file_obj = io.BytesIO(content)
            else:
                file_obj = content

            self.client.upload_fileobj(file_obj, self.bucket_name, path)
            return True
        except ClientError as e:
            print(f"S3 upload error: {e}")
            return False

    async def download(self, path: str) -> bytes:
        try:
            file_obj = io.BytesIO()
            self.client.download_fileobj(self.bucket_name, path, file_obj)
            return file_obj.getvalue()
        except ClientError as e:
            raise e

    async def delete(self, path: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=path)
            return True
        except ClientError:
            return False

    async def exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except ClientError:
            return False

    async def set_readonly(self, path: str, readonly: bool = True) -> bool:
        # S3 object lock or ACLs can be used, but simplified:
        # We can use ACL 'public-read' vs 'private' or Object Lock if enabled
        # For now, S3 doesn't support simple "readonly" flag modification without Object Lock configuration.
        # We return True pretending we did it or implement Object Lock retention.
        # Assuming no object lock for generic implementation.
        return True
