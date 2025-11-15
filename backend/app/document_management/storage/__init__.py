"""Storage backend abstraction for document storage."""

import os
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional, Dict, Any
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract storage backend."""

    @abstractmethod
    async def upload(
        self,
        file_path: str,
        file_content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload file to storage.

        Args:
            file_path: Destination path
            file_content: File bytes
            metadata: File metadata

        Returns:
            Upload result with storage info
        """
        pass

    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """Download file from storage.

        Args:
            file_path: Path to file

        Returns:
            File bytes
        """
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """Delete file from storage.

        Args:
            file_path: Path to file

        Returns:
            Success status
        """
        pass

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """Check if file exists.

        Args:
            file_path: Path to file

        Returns:
            Existence status
        """
        pass

    @abstractmethod
    async def list_files(
        self,
        prefix: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> list[Dict[str, Any]]:
        """List files in storage with optional filtering.

        Args:
            prefix: Path prefix filter
            tags: Tag filters

        Returns:
            List of file info
        """
        pass

    @abstractmethod
    async def set_readonly(self, file_path: str, readonly: bool = True) -> bool:
        """Set file read-only status.

        Args:
            file_path: Path to file
            readonly: Whether to set readonly

        Returns:
            Success status
        """
        pass

    def calculate_hash(self, content: bytes) -> str:
        """Calculate SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str):
        """Initialize local storage.

        Args:
            base_path: Base directory for storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, file_path: str) -> Path:
        """Get full file path with security check."""
        # Prevent directory traversal
        full_path = (self.base_path / file_path).resolve()
        if not str(full_path).startswith(str(self.base_path.resolve())):
            raise ValueError(f"Invalid path: {file_path}")
        return full_path

    async def upload(
        self,
        file_path: str,
        file_content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload file to local storage."""
        full_path = self._get_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(file_content)

        file_hash = self.calculate_hash(file_content)
        stat = full_path.stat()

        logger.info(f"Uploaded file to {file_path} (size: {stat.st_size})")

        return {
            "path": file_path,
            "size": stat.st_size,
            "hash": file_hash,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

    async def download(self, file_path: str) -> bytes:
        """Download file from local storage."""
        full_path = self._get_full_path(file_path)
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(full_path, "rb") as f:
            content = f.read()

        logger.info(f"Downloaded file {file_path} (size: {len(content)})")
        return content

    async def delete(self, file_path: str) -> bool:
        """Delete file from local storage."""
        full_path = self._get_full_path(file_path)
        if full_path.exists():
            if full_path.is_file():
                full_path.unlink()
                logger.info(f"Deleted file {file_path}")
                return True
            else:
                logger.warning(f"Path is not a file: {file_path}")
        else:
            logger.warning(f"File not found for deletion: {file_path}")
        return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        full_path = self._get_full_path(file_path)
        return full_path.is_file()

    async def list_files(
        self,
        prefix: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> list[Dict[str, Any]]:
        """List files with optional prefix filtering."""
        search_path = self._get_full_path(prefix)
        if not search_path.exists():
            return []

        files = []
        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                rel_path = str(file_path.relative_to(self.base_path))
                files.append({
                    "path": rel_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        return files

    async def set_readonly(self, file_path: str, readonly: bool = True) -> bool:
        """Set file read-only status."""
        full_path = self._get_full_path(file_path)
        if not full_path.exists():
            return False

        if readonly:
            # Remove write permissions (0o444 = r--r--r--)
            full_path.chmod(0o444)
        else:
            # Add write permissions (0o644 = rw-r--r--)
            full_path.chmod(0o644)

        logger.info(f"Set {file_path} readonly={readonly}")
        return True


class S3StorageBackend(StorageBackend):
    """AWS S3 storage backend."""

    def __init__(
        self,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ):
        """Initialize S3 storage.

        Args:
            bucket_name: S3 bucket name
            access_key: AWS access key
            secret_key: AWS secret key
            region: AWS region
            endpoint_url: Custom endpoint (for MinIO)
        """
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 not installed. Install with: pip install boto3")

        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            endpoint_url=endpoint_url,
        )
        logger.info(f"Initialized S3 storage: bucket={bucket_name}, region={region}")

    async def upload(
        self,
        file_path: str,
        file_content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Upload file to S3."""
        extra_args = {}
        if metadata:
            extra_args["Metadata"] = {k: str(v)[:255] for k, v in metadata.items()}

        file_hash = self.calculate_hash(file_content)
        extra_args["Metadata"] = extra_args.get("Metadata", {})
        extra_args["Metadata"]["sha256"] = file_hash

        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=file_path,
            Body=file_content,
            **extra_args,
        )

        logger.info(f"Uploaded to S3: {self.bucket_name}/{file_path} (size: {len(file_content)})")

        return {
            "path": file_path,
            "bucket": self.bucket_name,
            "size": len(file_content),
            "hash": file_hash,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

    async def download(self, file_path: str) -> bytes:
        """Download file from S3."""
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
        content = response["Body"].read()
        logger.info(f"Downloaded from S3: {self.bucket_name}/{file_path} (size: {len(content)})")
        return content

    async def delete(self, file_path: str) -> bool:
        """Delete file from S3."""
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
        logger.info(f"Deleted from S3: {self.bucket_name}/{file_path}")
        return True

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except Exception:
            return False

    async def list_files(
        self,
        prefix: str = "",
        tags: Optional[Dict[str, str]] = None,
    ) -> list[Dict[str, Any]]:
        """List files in S3 with optional prefix filtering."""
        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)

        files = []
        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                files.append({
                    "path": obj["Key"],
                    "size": obj["Size"],
                    "modified": obj["LastModified"].isoformat(),
                })

        return files

    async def set_readonly(self, file_path: str, readonly: bool = True) -> bool:
        """Set file ACL to read-only."""
        acl = "private" if readonly else "private"
        self.s3_client.put_object_acl(
            Bucket=self.bucket_name,
            Key=file_path,
            ACL=acl,
        )
        logger.info(f"Set S3 {file_path} readonly={readonly}")
        return True


class StorageFactory:
    """Factory for creating storage backends."""

    _backends: Dict[str, StorageBackend] = {}

    @staticmethod
    def create_local_backend(base_path: str) -> LocalStorageBackend:
        """Create local storage backend."""
        return LocalStorageBackend(base_path)

    @staticmethod
    def create_s3_backend(
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ) -> S3StorageBackend:
        """Create S3 storage backend."""
        return S3StorageBackend(
            bucket_name=bucket_name,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint_url=endpoint_url,
        )

    @staticmethod
    def get_backend(backend_type: str, **kwargs) -> StorageBackend:
        """Get or create storage backend.

        Args:
            backend_type: "local" or "s3"
            **kwargs: Backend-specific configuration

        Returns:
            Storage backend instance
        """
        if backend_type == "local":
            return StorageFactory.create_local_backend(kwargs["base_path"])
        elif backend_type == "s3":
            return StorageFactory.create_s3_backend(
                bucket_name=kwargs["bucket_name"],
                access_key=kwargs["access_key"],
                secret_key=kwargs["secret_key"],
                region=kwargs.get("region", "us-east-1"),
                endpoint_url=kwargs.get("endpoint_url"),
            )
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")
