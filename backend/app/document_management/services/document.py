"""Document generation and management service."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import json
import hashlib
from io import BytesIO

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document generation and management."""

    def __init__(
        self,
        storage_backend,
        db_session,
        security_manager=None,
    ):
        """Initialize document service.

        Args:
            storage_backend: Storage backend for documents
            db_session: Database session
            security_manager: Security manager for encryption
        """
        self.storage = storage_backend
        self.db = db_session
        self.security = security_manager

    async def generate_document(
        self,
        template_id: int,
        data: Dict[str, Any],
        created_by: int,
        doc_type: str,
        title: Optional[str] = None,
        access_level: str = "internal",
        encrypt: bool = False,
        watermark: Optional[str] = None,
        tags: Optional[List[str]] = None,
        retention_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate document from template.

        Args:
            template_id: Template ID
            data: Data to fill into template
            created_by: User ID who created
            doc_type: Document type/category
            title: Document title
            access_level: Access level
            encrypt: Whether to encrypt document
            watermark: Watermark text
            tags: Document tags
            retention_days: Retention period

        Returns:
            Generated document info
        """
        from app.document_management.models import Template, Document, DocumentStatus
        from app.document_management.generators import PDFGenerator, WordGenerator, TemplateRenderer

        logger.info(f"Generating document from template {template_id}")

        # Get template
        template = self.db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Get template file
        template_content = await self.storage.download(template.file_path)

        # Render template content
        if template.file_type == "html":
            template_str = template_content.decode("utf-8")
            rendered = TemplateRenderer.render(template_str, data)
            doc_bytes = rendered.encode("utf-8")

            # Convert HTML to PDF if needed
            doc_bytes = PDFGenerator.generate_from_html(rendered)
            final_type = "pdf"
        elif template.file_type == "docx":
            generator = WordGenerator()
            doc_bytes = generator.generate(template_content, data)
            final_type = "docx"
        elif template.file_type == "pdf":
            # For PDF templates, placeholder filling is limited
            # Would need specialized PDF library
            doc_bytes = template_content
            final_type = "pdf"
        else:
            raise ValueError(f"Unsupported template type: {template.file_type}")

        # Add watermark if requested
        if watermark and final_type == "pdf":
            doc_bytes = PDFGenerator.add_watermark(doc_bytes, watermark_text=watermark)

        # Encrypt if requested
        if encrypt and self.security:
            from app.document_management.security import DocumentEncryption

            if final_type == "pdf":
                doc_bytes = DocumentEncryption.encrypt_pdf(
                    doc_bytes,
                    user_password="",
                    owner_password="secure",
                )
            elif final_type == "docx":
                doc_bytes = DocumentEncryption.encrypt_docx(doc_bytes, password="secure")

        # Generate document name
        if not title:
            title = f"{template.name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Generate storage path
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        storage_path = f"documents/{doc_type}/{timestamp}/{title}.{final_type}"

        # Calculate hash
        file_hash = hashlib.sha256(doc_bytes).hexdigest()

        # Upload document
        upload_result = await self.storage.upload(storage_path, doc_bytes)

        # Create document record
        document = Document(
            title=title,
            template_id=template_id,
            template_version=template.current_version,
            doc_type=doc_type,
            status=DocumentStatus.GENERATED,
            access_level=access_level,
            file_path=storage_path,
            file_hash=file_hash,
            file_size=len(doc_bytes),
            mime_type=f"application/{final_type}",
            input_data=json.dumps(data),
            # store metadata under metadata_json to avoid ORM reserved attribute name
            metadata_json=json.dumps({
                "tags": tags or [],
                "watermark": watermark,
            }),
            created_by=created_by,
            is_encrypted=encrypt,
            retention_days=retention_days,
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        logger.info(f"Document generated: {document.id} (size: {len(doc_bytes)})")

        return {
            "id": document.id,
            "title": document.title,
            "template_id": template_id,
            "doc_type": doc_type,
            "status": document.status.value,
            "file_size": len(doc_bytes),
            "file_hash": file_hash,
            "created_at": document.created_at.isoformat(),
            "access_level": access_level,
        }

    async def get_document(
        self,
        document_id: int,
        user_id: int,
        user_role: str,
    ) -> Optional[Dict[str, Any]]:
        """Get document with access control.

        Args:
            document_id: Document ID
            user_id: User ID requesting
            user_role: User role

        Returns:
            Document info or None
        """
        from app.document_management.models import Document
        from app.document_management.security import AccessControlManager

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return None

        # Check access
        access_manager = AccessControlManager()
        if not access_manager.can_access_document(user_role, doc.access_level):
            logger.warning(f"Access denied for document {document_id} by user {user_id}")
            return None

        # Log access
        await self._log_access(document_id, user_id, "view", "success")

        return {
            "id": doc.id,
            "title": doc.title,
            "template_id": doc.template_id,
            "doc_type": doc.doc_type,
            "status": doc.status.value,
            "file_size": doc.file_size,
            "created_at": doc.created_at.isoformat(),
            "access_level": doc.access_level.value,
            "tags": json.loads(doc.metadata_json or "{}").get("tags", []) if doc.metadata_json else [],
        }

    async def download_document(
        self,
        document_id: int,
        user_id: int,
        user_role: str,
    ) -> Optional[bytes]:
        """Download document content with access control.

        Args:
            document_id: Document ID
            user_id: User ID requesting
            user_role: User role

        Returns:
            Document bytes or None if access denied
        """
        from app.document_management.models import Document
        from app.document_management.security import AccessControlManager

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            await self._log_access(document_id, user_id, "download", "failed", "Document not found")
            return None

        # Check access
        access_manager = AccessControlManager()
        if not access_manager.can_access_document(user_role, doc.access_level):
            await self._log_access(document_id, user_id, "download", "denied", "Access denied")
            return None

        # Check permissions
        if not access_manager.check_permission(user_role, "download"):
            await self._log_access(document_id, user_id, "download", "denied", "No download permission")
            return None

        # Download file
        try:
            content = await self.storage.download(doc.file_path)
            await self._log_access(document_id, user_id, "download", "success")
            logger.info(f"Document downloaded: {document_id} by user {user_id}")
            return content
        except Exception as e:
            await self._log_access(document_id, user_id, "download", "failed", str(e))
            logger.error(f"Download failed: {e}")
            return None

    async def list_documents(
        self,
        filters: Optional[Dict[str, Any]] = None,
        user_role: str = "user",
        limit: int = 100,
        offset: int = 0,
    ) -> list[Dict[str, Any]]:
        """List documents with filtering.

        Args:
            filters: Filter criteria (doc_type, status, tags, date_range)
            user_role: User role for access control
            limit: Result limit
            offset: Result offset

        Returns:
            List of documents
        """
        from app.document_management.models import Document

        query = self.db.query(Document)

        if filters:
            if "doc_type" in filters:
                query = query.filter(Document.doc_type == filters["doc_type"])

            if "status" in filters:
                query = query.filter(Document.status == filters["status"])

            if "date_range" in filters:
                start_date, end_date = filters["date_range"]
                query = query.filter(
                    Document.created_at >= start_date,
                    Document.created_at <= end_date,
                )

            if "created_by" in filters:
                query = query.filter(Document.created_by == filters["created_by"])

        # Order by created_at descending
        query = query.order_by(Document.created_at.desc())

        # Pagination
        documents = query.limit(limit).offset(offset).all()

        return [
            {
                "id": doc.id,
                "title": doc.title,
                "doc_type": doc.doc_type,
                "status": doc.status.value,
                "file_size": doc.file_size,
                "created_at": doc.created_at.isoformat(),
                "access_level": doc.access_level.value,
            }
            for doc in documents
        ]

    async def archive_document(
        self,
        document_id: int,
        readonly: bool = True,
    ) -> bool:
        """Archive document (mark as readonly and set retention).

        Args:
            document_id: Document ID
            readonly: Set as readonly

        Returns:
            Success status
        """
        from app.document_management.models import Document, DocumentStatus

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False

        doc.status = DocumentStatus.ARCHIVED
        doc.archived_at = datetime.utcnow()
        doc.is_readonly = readonly

        if readonly:
            # Set file as readonly in storage
            await self.storage.set_readonly(doc.file_path, readonly=True)

        self.db.commit()

        logger.info(f"Document archived: {document_id}")
        return True

    async def delete_document(self, document_id: int) -> bool:
        """Delete document.

        Args:
            document_id: Document ID

        Returns:
            Success status
        """
        from app.document_management.models import Document, DocumentStatus

        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return False

        # Delete from storage
        await self.storage.delete(doc.file_path)

        # Mark as deleted in DB
        doc.status = DocumentStatus.DELETED
        self.db.commit()

        logger.info(f"Document deleted: {document_id}")
        return True

    async def search_documents(
        self,
        query: str,
        doc_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Dict[str, Any]]:
        """Search documents by metadata.

        Args:
            query: Search query
            doc_type: Filter by document type
            date_from: Start date filter
            date_to: End date filter
            limit: Result limit

        Returns:
            List of matching documents
        """
        from app.document_management.models import Document
        import re

        # Try to parse date queries like "2024 年 5 月" or "May 2024" to derive date_from/date_to
        if query and (not date_from and not date_to):
            # Chinese pattern: 2024 年 5 月
            m = re.search(r"(?P<year>\d{4})\s*年\s*(?P<month>\d{1,2})\s*月", query)
            if m:
                y = int(m.group("year"))
                mo = int(m.group("month"))
                date_from = datetime(y, mo, 1)
                # compute last day of month
                if mo == 12:
                    date_to = datetime(y + 1, 1, 1) - timedelta(seconds=1)
                else:
                    date_to = datetime(y, mo + 1, 1) - timedelta(seconds=1)
            else:
                # English month-year like 'May 2024'
                m2 = re.search(r"(?P<month_name>[A-Za-z]+)\s+(?P<year>\d{4})", query)
                if m2:
                    try:
                        month_name = m2.group("month_name")
                        y = int(m2.group("year"))
                        mo = datetime.strptime(month_name, "%B").month
                        date_from = datetime(y, mo, 1)
                        if mo == 12:
                            date_to = datetime(y + 1, 1, 1) - timedelta(seconds=1)
                        else:
                            date_to = datetime(y, mo + 1, 1) - timedelta(seconds=1)
                    except Exception:
                        # ignore parse errors
                        date_from = date_to = None

        # Build base query: search title, doc_type, and metadata_json text (fast LIKE)
        like_expr = f"%{query}%" if query else "%"
        search_q = self.db.query(Document).filter(
            (Document.title.ilike(like_expr))
            | (Document.doc_type.ilike(like_expr))
            | (Document.metadata_json.ilike(like_expr))
        )

        if doc_type:
            search_q = search_q.filter(Document.doc_type == doc_type)

        if date_from:
            search_q = search_q.filter(Document.created_at >= date_from)
        if date_to:
            search_q = search_q.filter(Document.created_at <= date_to)

        # Order by created_at desc and limit
        candidates = search_q.order_by(Document.created_at.desc()).limit(limit * 5).all()

        # Post-filtering: if query was a date expression but metadata contains more precise 'generated' fields,
        # prefer metadata checks. This step operates in-memory but only on a limited candidate set for speed.
        results: list[Dict[str, Any]] = []
        for doc in candidates:
            add = False
            # If query had date filters, we've already applied them via created_at
            # Also check metadata_json for more precise matches (e.g., metadata.generated contains ISO date)
            try:
                meta = json.loads(doc.metadata_json) if doc.metadata_json else {}
            except Exception:
                meta = {}

            # If the raw query appears in metadata values, match
            if query:
                qlow = query.lower()
                # check keys and values in metadata
                for k, v in meta.items():
                    try:
                        if qlow in str(k).lower() or qlow in str(v).lower():
                            add = True
                            break
                    except Exception:
                        continue

            # If not matched by metadata, fall back to title/doc_type matching
            if not add:
                if query.lower() in (doc.title or "").lower() or query.lower() in (doc.doc_type or "").lower():
                    add = True

            if add:
                results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "doc_type": doc.doc_type,
                    "status": doc.status.value,
                    "created_at": doc.created_at.isoformat(),
                    "metadata": meta,
                })

            if len(results) >= limit:
                break

        return results

    async def _log_access(
        self,
        document_id: int,
        user_id: int,
        action: str,
        status: str,
        reason: Optional[str] = None,
    ) -> None:
        """Log document access.

        Args:
            document_id: Document ID
            user_id: User ID
            action: Action performed
            status: Action status
            reason: Reason for action
        """
        from app.document_management.models import DocumentAccessLog

        log = DocumentAccessLog(
            document_id=document_id,
            user_id=user_id,
            action=action,
            status=status,
            reason=reason,
        )

        self.db.add(log)
        self.db.commit()
