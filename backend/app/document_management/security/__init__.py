"""Security utilities for document management."""

import re
import logging
from typing import Any, Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class FieldMasker:
    """Utility for masking sensitive fields."""

    # Define common sensitive field patterns
    SENSITIVE_PATTERNS = {
        "id_number": re.compile(r"^\d{6,18}$"),  # ID numbers
        "phone": re.compile(r"1\d{10}|09\d{8}"),  # Phone numbers
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "credit_card": re.compile(r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}"),
        "ssn": re.compile(r"\d{3}-\d{2}-\d{4}"),
    }

    SENSITIVE_FIELD_NAMES = {
        "password",
        "secret",
        "token",
        "key",
        "credential",
        "api_key",
        "private_key",
        "identity",
        "id_card",
        "ssn",
        "credit_card",
        "bank_account",
    }

    @staticmethod
    def is_sensitive_field_name(field_name: str) -> bool:
        """Check if field name indicates sensitive data."""
        field_lower = field_name.lower()
        return any(sensitive in field_lower for sensitive in FieldMasker.SENSITIVE_FIELD_NAMES)

    @staticmethod
    def mask_value(value: str, pattern: str = "default") -> str:
        """Mask a sensitive value.

        Args:
            value: Value to mask
            pattern: Masking pattern (default, partial, full)

        Returns:
            Masked value
        """
        if not isinstance(value, str) or len(value) == 0:
            return value

        if pattern == "full":
            return "*" * len(value)
        elif pattern == "partial":
            # Show first and last 2 chars
            if len(value) <= 4:
                return "*" * len(value)
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
        else:  # default
            # Show last 4 chars for most fields
            if len(value) <= 4:
                return "*" * len(value)
            return "*" * (len(value) - 4) + value[-4:]

    @staticmethod
    def mask_data(data: Dict[str, Any], sensitive_fields: Optional[list[str]] = None) -> Dict[str, Any]:
        """Mask sensitive fields in data dictionary.

        Args:
            data: Data dictionary to mask
            sensitive_fields: List of field names to mask. If None, auto-detect.

        Returns:
            Data with masked sensitive fields
        """
        masked = {}

        for key, value in data.items():
            should_mask = False

            # Check if field is in explicit sensitive list
            if sensitive_fields and key in sensitive_fields:
                should_mask = True
            # Check if field name indicates sensitive data
            elif FieldMasker.is_sensitive_field_name(key):
                should_mask = True
            # Check if value matches sensitive pattern
            elif isinstance(value, str):
                for pattern in FieldMasker.SENSITIVE_PATTERNS.values():
                    if pattern.search(value):
                        should_mask = True
                        break

            if should_mask and isinstance(value, str):
                masked[key] = FieldMasker.mask_value(value)
            elif isinstance(value, dict):
                masked[key] = FieldMasker.mask_data(value, sensitive_fields)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                masked[key] = [FieldMasker.mask_data(item, sensitive_fields) for item in value]
            else:
                masked[key] = value

        return masked


class DocumentEncryption:
    """PDF/Word document encryption utilities."""

    @staticmethod
    def encrypt_pdf(
        pdf_content: bytes,
        user_password: str = "",
        owner_password: str = "",
    ) -> bytes:
        """Encrypt PDF with passwords.

        Args:
            pdf_content: PDF file bytes
            user_password: User password (can't print, copy, etc.)
            owner_password: Owner password (can modify permissions)

        Returns:
            Encrypted PDF bytes
        """
        try:
            import PyPDF2
        except ImportError:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")

        try:
            from io import BytesIO

            reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            writer = PyPDF2.PdfWriter()

            # Copy all pages
            for page in reader.pages:
                writer.add_page(page)

            # Add encryption
            if owner_password:
                writer.encrypt(user_password=user_password, owner_password=owner_password)
            else:
                writer.encrypt(user_password=user_password)

            output = BytesIO()
            writer.write(output)
            logger.info("PDF encrypted successfully")
            return output.getvalue()

        except Exception as e:
            logger.error(f"PDF encryption failed: {e}")
            raise

    @staticmethod
    def encrypt_docx(
        docx_content: bytes,
        password: str,
    ) -> bytes:
        """Encrypt DOCX with password (restrict editing).

        Args:
            docx_content: DOCX file bytes
            password: Password for opening

        Returns:
            Encrypted DOCX bytes
        """
        try:
            from docx import Document
            from io import BytesIO
            import zipfile
            import xml.etree.ElementTree as ET

            # Note: python-docx doesn't support built-in encryption.
            # This is a placeholder for encryption library integration.
            # In production, use office365-rest-python-client or similar
            logger.warning("DOCX encryption requires additional setup with Office 365 client")
            return docx_content

        except Exception as e:
            logger.error(f"DOCX encryption failed: {e}")
            raise


class AccessControlManager:
    """Manage document access permissions."""

    def __init__(self):
        """Initialize access control manager."""
        # In-memory store for role-based permissions
        # In production, use database for persistence
        self.role_permissions: Dict[str, set[str]] = {
            "admin": {"view", "download", "edit", "delete", "share"},
            "manager": {"view", "download", "edit", "share"},
            "user": {"view", "download"},
            "guest": {"view"},
        }

    def check_permission(
        self,
        user_role: str,
        required_permission: str,
    ) -> bool:
        """Check if user has permission.

        Args:
            user_role: User's role
            required_permission: Required permission

        Returns:
            Permission granted status
        """
        if user_role not in self.role_permissions:
            return False

        return required_permission in self.role_permissions[user_role]

    def get_user_permissions(self, user_role: str) -> set[str]:
        """Get all permissions for a role.

        Args:
            user_role: User's role

        Returns:
            Set of permissions
        """
        return self.role_permissions.get(user_role, set())

    def can_access_document(
        self,
        user_role: str,
        document_access_level: str,
    ) -> bool:
        """Check if user can access document based on access level.

        Args:
            user_role: User's role
            document_access_level: Document access level (public, internal, confidential, secret)

        Returns:
            Access granted status
        """
        access_hierarchy = {
            "public": ["guest", "user", "manager", "admin"],
            "internal": ["user", "manager", "admin"],
            "confidential": ["manager", "admin"],
            "secret": ["admin"],
        }

        allowed_roles = access_hierarchy.get(document_access_level, [])
        return user_role in allowed_roles
