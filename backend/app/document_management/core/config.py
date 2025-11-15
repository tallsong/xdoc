"""Document management configuration."""

from typing import Optional
from pydantic_settings import BaseSettings


class DocumentManagementSettings(BaseSettings):
    """Document management settings."""

    # Storage configuration
    STORAGE_TYPE: str = "local"  # "local" or "s3"
    LOCAL_STORAGE_PATH: str = "/tmp/document_storage"

    # S3 configuration (if STORAGE_TYPE == "s3")
    S3_BUCKET_NAME: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: Optional[str] = None  # For MinIO

    # Document settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024 * 1024  # 10GB
    ALLOWED_FILE_TYPES: list[str] = ["pdf", "docx", "html"]

    # Security settings
    ENABLE_ENCRYPTION: bool = True
    ENABLE_WATERMARK: bool = True
    DEFAULT_WATERMARK: str = "Internal Use Only"
    ENCRYPTION_ALGORITHM: str = "AES-256"

    # Database settings
    DOCUMENT_DB_URL: str = "sqlite:///./document_metadata.db"
    DOCUMENT_DB_ECHO: bool = False

    # Access control settings
    ENABLE_ACCESS_CONTROL: bool = True
    DEFAULT_ACCESS_LEVEL: str = "internal"

    # Retention policies
    DEFAULT_RETENTION_DAYS: Optional[int] = None
    ARCHIVE_RETENTION_DAYS: int = 2555  # ~7 years

    # Logging
    ENABLE_ACCESS_LOGGING: bool = True
    LOG_SENSITIVE_DATA: bool = False

    class Config:
        """Config."""

        env_prefix = "DOC_"
        case_sensitive = True


# Global settings instance
doc_settings = DocumentManagementSettings()
