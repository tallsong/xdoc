"""Template management models."""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship, Column, String, Text


class TemplateVersion(SQLModel, table=True):
    """Template version tracking."""

    __tablename__ = "template_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="template.id", index=True)
    version: int = Field(index=True)
    file_path: str = Field(description="Path to template file in storage")
    file_hash: str = Field(description="SHA256 hash for integrity check")
    description: Optional[str] = Field(None, description="Version description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(description="User ID who created this version")
    change_summary: Optional[str] = Field(None, description="Summary of changes from previous version")

    # Relationship
    template: Optional["Template"] = Relationship(back_populates="versions")


class Template(SQLModel, table=True):
    """Document template definition."""

    __tablename__ = "template"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Template name")
    category: str = Field(index=True, description="Category: report, contract, invoice, etc.")
    description: Optional[str] = Field(None)
    current_version: int = Field(default=1, description="Current active version")
    file_path: str = Field(description="Path to current template file in storage")
    placeholders: str = Field(
        sa_column=Column(Text),
        description="JSON list of placeholder fields: [{name, type, required, description}]"
    )
    metadata: Optional[str] = Field(
        None,
        sa_column=Column(Text),
        description="JSON metadata for template configuration"
    )
    file_type: str = Field(description="Type: pdf, docx, html")
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(description="User ID who created template")

    # Relationships
    versions: list[TemplateVersion] = Relationship(back_populates="template", cascade_delete=True)
