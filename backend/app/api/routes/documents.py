"""API routes for document management."""

import logging
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


# Pydantic models for request/response
class TemplatePlaceholder(BaseModel):
    """Template placeholder definition."""

    name: str
    type: str = Field(description="Type: text, number, date, image, table")
    required: bool = False
    description: Optional[str] = None


class CreateTemplateRequest(BaseModel):
    """Create template request."""

    name: str
    category: str
    description: Optional[str] = None
    placeholders: List[TemplatePlaceholder]
    metadata: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    """Template response."""

    id: int
    name: str
    category: str
    file_type: str
    current_version: int
    created_at: str


class GenerateDocumentRequest(BaseModel):
    """Generate document request."""

    template_id: int
    data: Dict[str, Any]
    doc_type: str
    title: Optional[str] = None
    access_level: str = "internal"
    encrypt: bool = False
    watermark: Optional[str] = None
    tags: Optional[List[str]] = None
    retention_days: Optional[int] = None


class DocumentResponse(BaseModel):
    """Document response."""

    id: int
    title: str
    doc_type: str
    status: str
    file_size: int
    created_at: str
    access_level: str


class SearchDocumentsRequest(BaseModel):
    """Search documents request."""

    query: str
    doc_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50


# Dependency to get services
def get_document_service():
    """Get document service (simplified - in production use proper DI)."""
    from app.document_management.storage import StorageFactory
    from app.document_management.services.document import DocumentService
    from app.core.db import SessionLocal

    # Initialize storage backend
    storage = StorageFactory.get_backend(
        backend_type="local",
        base_path="/tmp/document_storage",
    )

    # Get DB session
    db = SessionLocal()

    # Create service
    service = DocumentService(storage, db)
    return service


def get_template_service():
    """Get template service (simplified - in production use proper DI)."""
    from app.document_management.storage import StorageFactory
    from app.document_management.services import TemplateService
    from app.core.db import SessionLocal

    # Initialize storage backend
    storage = StorageFactory.get_backend(
        backend_type="local",
        base_path="/tmp/document_storage",
    )

    # Get DB session
    db = SessionLocal()

    # Create service
    service = TemplateService(storage, db)
    return service


# Template routes
@router.post("/templates", response_model=TemplateResponse)
async def create_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    placeholders: str = Form(...),  # JSON string
    metadata: Optional[str] = Form(None),  # JSON string
    created_by: int = Form(...),
    template_service: Any = Depends(get_template_service),
):
    """Create a new document template."""
    import json

    try:
        file_content = await file.read()
        file_type = file.filename.split(".")[-1].lower()

        # Parse JSON strings
        placeholders_list = json.loads(placeholders)
        metadata_dict = json.loads(metadata) if metadata else None

        result = await template_service.create_template(
            name=name,
            category=category,
            file_content=file_content,
            file_type=file_type,
            placeholders=placeholders_list,
            created_by=created_by,
            description=description,
            metadata=metadata_dict,
        )

        return TemplateResponse(**result)

    except Exception as e:
        logger.error(f"Template creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create template: {str(e)}",
        )


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    template_service: Any = Depends(get_template_service),
):
    """Get template details."""
    template = await template_service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return TemplateResponse(**template)


@router.get("/templates")
async def list_templates(
    category: Optional[str] = Query(None),
    template_service: Any = Depends(get_template_service),
):
    """List templates."""
    templates = await template_service.list_templates(category=category)
    return {"templates": templates}


# Document routes
@router.post("/generate", response_model=DocumentResponse)
async def generate_document(
    request: GenerateDocumentRequest,
    user_id: int = Query(...),
    document_service: Any = Depends(get_document_service),
):
    """Generate document from template."""
    try:
        result = await document_service.generate_document(
            template_id=request.template_id,
            data=request.data,
            created_by=user_id,
            doc_type=request.doc_type,
            title=request.title,
            access_level=request.access_level,
            encrypt=request.encrypt,
            watermark=request.watermark,
            tags=request.tags,
            retention_days=request.retention_days,
        )

        return DocumentResponse(**result)

    except Exception as e:
        logger.error(f"Document generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate document: {str(e)}",
        )


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    user_id: int = Query(...),
    user_role: str = Query(default="user"),
    document_service: Any = Depends(get_document_service),
):
    """Get document details."""
    doc = await document_service.get_document(
        document_id=document_id,
        user_id=user_id,
        user_role=user_role,
    )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or access denied",
        )

    return DocumentResponse(**doc)


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    user_id: int = Query(...),
    user_role: str = Query(default="user"),
    document_service: Any = Depends(get_document_service),
):
    """Download document."""
    content = await document_service.download_document(
        document_id=document_id,
        user_id=user_id,
        user_role=user_role,
    )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied or document not found",
        )

    return FileResponse(
        content=content,
        filename=f"document_{document_id}.pdf",
        media_type="application/pdf",
    )


@router.get("/documents")
async def list_documents(
    doc_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    user_role: str = Query(default="user"),
    document_service: Any = Depends(get_document_service),
):
    """List documents."""
    filters = {}
    if doc_type:
        filters["doc_type"] = doc_type
    if status:
        filters["status"] = status

    documents = await document_service.list_documents(
        filters=filters,
        user_role=user_role,
        limit=limit,
        offset=skip,
    )

    return {"documents": documents, "total": len(documents)}


@router.post("/documents/{document_id}/archive")
async def archive_document(
    document_id: int,
    user_id: int = Query(...),
    document_service: Any = Depends(get_document_service),
):
    """Archive document."""
    success = await document_service.archive_document(document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {"message": "Document archived"}


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    user_id: int = Query(...),
    document_service: Any = Depends(get_document_service),
):
    """Delete document."""
    success = await document_service.delete_document(document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {"message": "Document deleted"}


@router.post("/search")
async def search_documents(
    request: SearchDocumentsRequest,
    user_role: str = Query(default="user"),
    document_service: Any = Depends(get_document_service),
):
    """Search documents."""
    documents = await document_service.search_documents(
        query=request.query,
        doc_type=request.doc_type,
        date_from=request.date_from,
        date_to=request.date_to,
        limit=request.limit,
    )

    return {"documents": documents, "total": len(documents)}
