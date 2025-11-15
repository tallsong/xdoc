"""Tests for document management system."""

import pytest
import json
from datetime import datetime, timedelta
from io import BytesIO

from app.document_management.storage import LocalStorageBackend, StorageFactory
from app.document_management.security import FieldMasker, AccessControlManager
from app.document_management.generators import TemplateRenderer, PDFGenerator


class TestLocalStorage:
    """Test local storage backend."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage backend."""
        return LocalStorageBackend(str(tmp_path))

    @pytest.mark.asyncio
    async def test_upload_and_download(self, storage):
        """Test file upload and download."""
        content = b"test file content"
        result = await storage.upload("test/file.txt", content)

        assert result["path"] == "test/file.txt"
        assert result["size"] == len(content)
        assert "hash" in result

        downloaded = await storage.download("test/file.txt")
        assert downloaded == content

    @pytest.mark.asyncio
    async def test_exists(self, storage):
        """Test file existence check."""
        await storage.upload("test/file.txt", b"content")
        assert await storage.exists("test/file.txt")
        assert not await storage.exists("test/nonexistent.txt")

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test file deletion."""
        await storage.upload("test/file.txt", b"content")
        assert await storage.delete("test/file.txt")
        assert not await storage.exists("test/file.txt")

    @pytest.mark.asyncio
    async def test_list_files(self, storage):
        """Test file listing."""
        await storage.upload("test/file1.txt", b"content1")
        await storage.upload("test/file2.txt", b"content2")

        files = await storage.list_files("test/")
        assert len(files) == 2
        assert any(f["path"] == "test/file1.txt" for f in files)

    @pytest.mark.asyncio
    async def test_set_readonly(self, storage):
        """Test setting file as read-only."""
        await storage.upload("test/file.txt", b"content")
        assert await storage.set_readonly("test/file.txt", readonly=True)


class TestFieldMasker:
    """Test field masking utilities."""

    def test_mask_value(self):
        """Test value masking."""
        # Default masking - show last 4
        assert FieldMasker.mask_value("123456789") == "*****6789"

        # Partial masking
        assert FieldMasker.mask_value("123456789", pattern="partial") == "12***789"

        # Full masking
        assert FieldMasker.mask_value("123456789", pattern="full") == "*********"

    def test_sensitive_field_names(self):
        """Test sensitive field name detection."""
        assert FieldMasker.is_sensitive_field_name("password")
        assert FieldMasker.is_sensitive_field_name("api_key")
        assert FieldMasker.is_sensitive_field_name("credit_card")
        assert not FieldMasker.is_sensitive_field_name("name")

    def test_mask_data(self):
        """Test data masking."""
        data = {
            "name": "John Doe",
            "ssn": "123-45-6789",
            "email": "john@example.com",
            "phone": "13125551234",
        }

        masked = FieldMasker.mask_data(data)
        assert masked["name"] == "John Doe"  # Not sensitive
        assert "****" in masked["ssn"]  # Masked
        assert "@" in masked["email"]  # Email partially masked
        assert "****" in masked["phone"]  # Phone masked

    def test_mask_nested_data(self):
        """Test masking nested dictionaries."""
        data = {
            "user": {
                "name": "John",
                "password": "secret123",
            },
            "items": [
                {"name": "Item 1", "api_key": "key123"},
            ],
        }

        masked = FieldMasker.mask_data(data)
        assert masked["user"]["name"] == "John"
        assert "****" in masked["user"]["password"]
        assert "****" in masked["items"][0]["api_key"]


class TestAccessControl:
    """Test access control manager."""

    @pytest.fixture
    def access_manager(self):
        """Create access manager."""
        return AccessControlManager()

    def test_admin_permissions(self, access_manager):
        """Test admin role permissions."""
        assert access_manager.check_permission("admin", "view")
        assert access_manager.check_permission("admin", "download")
        assert access_manager.check_permission("admin", "edit")
        assert access_manager.check_permission("admin", "delete")

    def test_user_permissions(self, access_manager):
        """Test user role permissions."""
        assert access_manager.check_permission("user", "view")
        assert access_manager.check_permission("user", "download")
        assert not access_manager.check_permission("user", "delete")

    def test_guest_permissions(self, access_manager):
        """Test guest role permissions."""
        assert access_manager.check_permission("guest", "view")
        assert not access_manager.check_permission("guest", "download")

    def test_access_level_hierarchy(self, access_manager):
        """Test access level hierarchy."""
        # Public - accessible by all
        assert access_manager.can_access_document("guest", "public")
        assert access_manager.can_access_document("user", "public")

        # Internal - user and above
        assert access_manager.can_access_document("user", "internal")
        assert not access_manager.can_access_document("guest", "internal")

        # Confidential - manager and above
        assert access_manager.can_access_document("manager", "confidential")
        assert not access_manager.can_access_document("user", "confidential")

        # Secret - admin only
        assert access_manager.can_access_document("admin", "secret")
        assert not access_manager.can_access_document("manager", "secret")


class TestTemplateRenderer:
    """Test template rendering."""

    def test_simple_template_rendering(self):
        """Test simple template rendering."""
        template_str = "Hello {{name}}, your email is {{email}}"
        data = {"name": "John", "email": "john@example.com"}

        result = TemplateRenderer.render(template_str, data)
        assert result == "Hello John, your email is john@example.com"

    def test_loop_rendering(self):
        """Test loop rendering in template."""
        template_str = """
{% for item in items -%}
- {{ item.name }}: ${{ item.price }}
{% endfor %}
        """.strip()

        data = {
            "items": [
                {"name": "Item 1", "price": 100},
                {"name": "Item 2", "price": 200},
            ]
        }

        result = TemplateRenderer.render(template_str, data)
        assert "Item 1: $100" in result
        assert "Item 2: $200" in result

    def test_conditional_rendering(self):
        """Test conditional rendering."""
        template_str = """
{% if user.is_admin -%}
Admin Panel
{% else -%}
User Panel
{% endif %}
        """.strip()

        data = {"user": {"is_admin": True}}
        result = TemplateRenderer.render(template_str, data)
        assert "Admin Panel" in result

    def test_json_rendering(self):
        """Test JSON template rendering."""
        json_template = """
{
  "name": "{{report_name}}",
  "date": "{{report_date}}",
  "items": [
    {% for item in items %}
    {
      "name": "{{item.name}}",
      "value": {{item.value}}
    }{{ "," if not loop.last else "" }}
    {% endfor %}
  ]
}
        """.strip()

        data = {
            "report_name": "Q1 Report",
            "report_date": "2024-05-20",
            "items": [
                {"name": "Item 1", "value": 100},
                {"name": "Item 2", "value": 200},
            ],
        }

        result = TemplateRenderer.render_json(json_template, data)
        assert result["name"] == "Q1 Report"
        assert result["date"] == "2024-05-20"
        assert len(result["items"]) == 2


class TestStorageFactory:
    """Test storage factory."""

    def test_create_local_backend(self, tmp_path):
        """Test creating local backend."""
        backend = StorageFactory.create_local_backend(str(tmp_path))
        assert isinstance(backend, LocalStorageBackend)

    def test_get_backend_local(self, tmp_path):
        """Test get_backend for local storage."""
        backend = StorageFactory.get_backend(
            backend_type="local",
            base_path=str(tmp_path),
        )
        assert isinstance(backend, LocalStorageBackend)

    def test_invalid_backend_type(self):
        """Test invalid backend type."""
        with pytest.raises(ValueError):
            StorageFactory.get_backend(backend_type="invalid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
