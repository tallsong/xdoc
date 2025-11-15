"""Document management data models."""

from app.document_management.models.document import Document, DocumentAccessLog
from app.document_management.models.template import Template, TemplateVersion

__all__ = [
    "Document",
    "DocumentAccessLog",
    "Template",
    "TemplateVersion",
]
