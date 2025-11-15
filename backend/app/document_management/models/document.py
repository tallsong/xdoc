"""Document management models."""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String, Text
from enum import Enum


class DocumentStatus(str, Enum):
    """Document status enum."""

    DRAFT = "draft"
    GENERATED = "generated"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DocumentAccessLevel(str, Enum):
    """Access level enum."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    SECRET = "secret"


class Document(SQLModel, table=True):
    """Document metadata."""

    __tablename__ = "document"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    template_id: int = Field(index=True)
    template_version: int = Field(description="Which version of template was used")
    doc_type: str = Field(index=True, description="Category: report, contract, etc.")
    status: DocumentStatus = Field(default=DocumentStatus.GENERATED, index=True)
    access_level: DocumentAccessLevel = Field(default=DocumentAccessLevel.INTERNAL)
    file_path: str = Field(description="Storage path to document")
    file_hash: str = Field(description="SHA256 hash for integrity")
    file_size: int = Field(description="File size in bytes")
    mime_type: str = Field(default="application/pdf")
    # Data and metadata
    input_data: str = Field(
        sa_column=Column(Text),
        description="JSON of input data used to generate"
    )
    metadata_json: Optional[str] = Field(
        None,
        sa_column=Column(Text),
        description="JSON metadata: tags, custom fields, etc."
    )
    # Versioning
    version: int = Field(default=1, description="Document version")
    parent_document_id: Optional[int] = Field(None, description="Parent doc for versioning")
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = Field(None)
    # User tracking
    created_by: int = Field(description="User ID who created")
    updated_by: Optional[int] = Field(None)
    # Encryption
    is_encrypted: bool = Field(default=False)
    encryption_key_id: Optional[str] = Field(None, description="ID of encryption key used")
    # Archival
    is_readonly: bool = Field(default=False, description="Whether document is read-only")
    retention_days: Optional[int] = Field(None, description="Days to retain before deletion")


class DocumentAccessLog(SQLModel, table=True):
    """Access audit log for documents."""

    __tablename__ = "document_access_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    user_id: int = Field(index=True)
    action: str = Field(index=True, description="download, view, edit, delete, export")
    ip_address: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    status: str = Field(default="success", description="success, failed, denied")
    reason: Optional[str] = Field(None, description="Reason for failed/denied action")
    accessed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
