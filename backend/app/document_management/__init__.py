"""Document Management and Generation System.

A comprehensive system for structured document generation, template management,
secure storage, and retrieval with encryption and access control.
"""

__version__ = "1.0.0"

from app.document_management.models import (
    Document,
    DocumentAccessLog,
    Template,
    TemplateVersion,
)
from app.document_management.services import (
    TemplateService,
)
from app.document_management.services.document import DocumentService

__all__ = [
    "Document",
    "DocumentAccessLog",
    "Template",
    "TemplateVersion",
    "TemplateService",
    "DocumentService",
]
