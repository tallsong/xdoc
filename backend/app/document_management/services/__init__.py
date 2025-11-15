"""Core services for document management."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, BinaryIO
import json
from io import BytesIO

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for template management."""

    def __init__(self, storage_backend, db_session):
        """Initialize template service.

        Args:
            storage_backend: Storage backend for template files
            db_session: Database session
        """
        self.storage = storage_backend
        self.db = db_session

    async def create_template(
        self,
        name: str,
        category: str,
        file_content: bytes,
        file_type: str,
        placeholders: list[Dict[str, Any]],
        created_by: int,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new template.

        Args:
            name: Template name
            category: Template category
            file_content: Template file bytes
            file_type: File type (pdf, docx, html)
            placeholders: List of placeholder definitions
            created_by: User ID who created
            description: Template description
            metadata: Additional metadata

        Returns:
            Created template info
        """
        from app.document_management.models import Template, TemplateVersion

        logger.info(f"Creating template: {name} (category: {category})")

        # Generate storage path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_hash = self.storage.calculate_hash(file_content)
        storage_path = f"templates/{category}/{name}_{timestamp}_{file_type}"

        # Upload template file
        upload_result = await self.storage.upload(storage_path, file_content)

        # Create template record
        template = Template(
            name=name,
            category=category,
            description=description,
            file_path=storage_path,
            file_type=file_type,
            placeholders=json.dumps(placeholders),
            metadata_json=json.dumps(metadata) if metadata else None,
            created_by=created_by,
        )

        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)

        logger.info(f"Template created: {template.id}")

        return {
            "id": template.id,
            "name": template.name,
            "category": template.category,
            "file_type": template.file_type,
            "version": template.current_version,
            "storage_path": storage_path,
            "file_hash": file_hash,
            "created_at": template.created_at.isoformat(),
        }

    async def update_template(
        self,
        template_id: int,
        file_content: bytes,
        change_summary: Optional[str] = None,
        updated_by: int = 0,
    ) -> Dict[str, Any]:
        """Create new version of template.

        Args:
            template_id: Template ID
            file_content: New template file bytes
            change_summary: Summary of changes
            updated_by: User ID who updated

        Returns:
            Updated template info
        """
        from app.document_management.models import Template, TemplateVersion

        logger.info(f"Updating template: {template_id}")

        template = self.db.query(Template).filter(Template.id == template_id).first()
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Create new version
        new_version = template.current_version + 1
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_hash = self.storage.calculate_hash(file_content)
        storage_path = f"templates/{template.category}/{template.name}_v{new_version}_{timestamp}_{template.file_type}"

        # Upload new version
        await self.storage.upload(storage_path, file_content)

        # Create version record
        version = TemplateVersion(
            template_id=template_id,
            version=new_version,
            file_path=storage_path,
            file_hash=file_hash,
            description=change_summary,
            created_by=updated_by,
            change_summary=change_summary,
        )

        # Update template
        template.current_version = new_version
        template.file_path = storage_path
        template.updated_at = datetime.utcnow()

        self.db.add(version)
        self.db.commit()

        logger.info(f"Template updated to version {new_version}")

        return {
            "id": template.id,
            "version": new_version,
            "storage_path": storage_path,
            "file_hash": file_hash,
            "updated_at": datetime.utcnow().isoformat(),
        }

    async def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Get template details.

        Args:
            template_id: Template ID

        Returns:
            Template info or None
        """
        from app.document_management.models import Template

        template = self.db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return None

        return {
            "id": template.id,
            "name": template.name,
            "category": template.category,
            "description": template.description,
            "file_type": template.file_type,
            "current_version": template.current_version,
            "placeholders": json.loads(template.placeholders),
            "metadata": json.loads(template.metadata_json) if template.metadata_json else {},
            "created_at": template.created_at.isoformat(),
            "updated_at": template.updated_at.isoformat(),
        }

    async def list_templates(
        self,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> list[Dict[str, Any]]:
        """List templates.

        Args:
            category: Filter by category
            active_only: Only active templates

        Returns:
            List of templates
        """
        from app.document_management.models import Template

        query = self.db.query(Template)

        if active_only:
            query = query.filter(Template.is_active == True)

        if category:
            query = query.filter(Template.category == category)

        templates = query.all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "category": t.category,
                "file_type": t.file_type,
                "version": t.current_version,
                "created_at": t.created_at.isoformat(),
            }
            for t in templates
        ]

    async def get_template_version(self, template_id: int, version: int) -> Optional[bytes]:
        """Get template file for specific version.

        Args:
            template_id: Template ID
            version: Version number

        Returns:
            Template file bytes or None
        """
        from app.document_management.models import TemplateVersion

        template_version = (
            self.db.query(TemplateVersion)
            .filter(
                TemplateVersion.template_id == template_id,
                TemplateVersion.version == version,
            )
            .first()
        )

        if not template_version:
            return None

        return await self.storage.download(template_version.file_path)

    async def delete_template(self, template_id: int) -> bool:
        """Soft delete template (mark inactive).

        Args:
            template_id: Template ID

        Returns:
            Success status
        """
        from app.document_management.models import Template

        template = self.db.query(Template).filter(Template.id == template_id).first()
        if not template:
            return False

        template.is_active = False
        self.db.commit()

        logger.info(f"Template deactivated: {template_id}")
        return True
