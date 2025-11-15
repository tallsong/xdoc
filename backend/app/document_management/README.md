# Document Management and Generation System

## Overview

A comprehensive, enterprise-grade document management system for Python that supports:

- **Template Management**: Version-controlled templates with placeholder support
- **Document Generation**: Automatic document creation from templates with data
- **Storage Management**: Local or cloud storage (S3/MinIO) with classification
- **Security**: Encryption, field masking, access control, and audit logging
- **Retrieval**: Fast search and filtering by metadata
- **Versioning**: Track document versions and compare changes

## Features

### 1. Template Management
- Upload Word/PDF/HTML templates
- Define placeholders with types (text, number, date, image, table)
- Version control with change tracking
- Category-based organization
- Metadata support for custom configurations

### 2. Document Generation
- Fill templates with JSON/structured data
- Automatic document naming (e.g., `report_20240520_v1.pdf`)
- Support for dynamic elements (tables, images)
- Watermarking (e.g., "Internal Use Only")
- PDF and Word output formats
- Template rendering with Jinja2

### 3. Storage Management
- **Local Storage**: File-based storage with classification
- **Cloud Storage**: AWS S3 or MinIO support
- Document classification by type/time/tags
- Long-term archival with read-only permissions
- Metadata-based search with <3s response time

### 4. Security Features
- Document encryption (PDF password, Word restrictions)
- Sensitive field masking (SSN, ID, credit card, etc.)
- Role-based access control (admin, manager, user, guest)
- Access level hierarchy (public, internal, confidential, secret)
- Comprehensive audit logging (who, when, what action)
- Document integrity verification (SHA256 hashing)

### 5. Document Comparison
- Track document versions
- Compare changes between versions
- View modification history

## Architecture

```
document_management/
├── core/
│   ├── config.py          # Configuration settings
│   └── __init__.py
├── models/
│   ├── document.py        # Document & AccessLog models
│   ├── template.py        # Template & TemplateVersion models
│   └── __init__.py
├── services/
│   ├── __init__.py        # TemplateService
│   └── document.py        # DocumentService
├── generators/
│   └── __init__.py        # PDF, Word, HTML generators
├── storage/
│   └── __init__.py        # Storage backends (Local, S3)
├── security/
│   └── __init__.py        # Encryption, masking, access control
└── __init__.py
```

## Installation

### 1. Add Dependencies

Add these to `requirements.txt`:

```
python-docx>=0.8.11          # Word document generation
reportlab>=4.0.0              # PDF generation
weasyprint>=58.0              # HTML to PDF
PyPDF2>=3.0.0                 # PDF manipulation
jinja2>=3.1.4                 # Template rendering (already in project)
boto3>=1.26.0                 # AWS S3 support (optional)
pydantic-settings>=2.0        # Settings management
```

### 2. Database Setup

Run migrations to create tables:

```bash
alembic upgrade head
```

This creates:
- `template` - Template definitions
- `template_versions` - Version history
- `document` - Document metadata
- `document_access_log` - Audit logs

### 3. Configure Storage

Set environment variables or update `app/document_management/core/config.py`:

**Local Storage (default):**
```python
STORAGE_TYPE = "local"
LOCAL_STORAGE_PATH = "/data/documents"
```

**AWS S3:**
```python
STORAGE_TYPE = "s3"
S3_BUCKET_NAME = "my-bucket"
S3_ACCESS_KEY = "xxx"
S3_SECRET_KEY = "yyy"
S3_REGION = "us-east-1"
```

**MinIO (self-hosted S3-compatible):**
```python
STORAGE_TYPE = "s3"
S3_BUCKET_NAME = "documents"
S3_ENDPOINT_URL = "http://minio:9000"
S3_ACCESS_KEY = "minioadmin"
S3_SECRET_KEY = "minioadmin"
```

## Usage

### 1. Create a Template

```python
from app.document_management.services import TemplateService
from app.document_management.storage import StorageFactory

# Initialize
storage = StorageFactory.get_backend("local", base_path="/data/documents")
template_service = TemplateService(storage, db_session)

# Create template
template_info = await template_service.create_template(
    name="Weekly Report",
    category="reports",
    file_content=open("templates/report.html", "rb").read(),
    file_type="html",
    placeholders=[
        {"name": "report_date", "type": "date", "required": True},
        {"name": "department", "type": "text", "required": True},
        {"name": "metrics", "type": "table", "required": False},
    ],
    created_by=1,
    description="Weekly status report template"
)
```

### 2. Generate Document

```python
from app.document_management.services.document import DocumentService

doc_service = DocumentService(storage, db_session)

document = await doc_service.generate_document(
    template_id=1,
    data={
        "report_date": "2024-05-20",
        "department": "Engineering",
        "metrics": [
            {"name": "Uptime", "value": "99.98%", "target": "99.9%"},
        ],
    },
    created_by=1,
    doc_type="report",
    title="Weekly Report May 20",
    access_level="internal",
    encrypt=False,
    watermark="Internal Use Only",
    tags=["weekly", "may-2024"],
    retention_days=90,
)
```

### 3. Access Document

```python
# Get document metadata
doc_info = await doc_service.get_document(
    document_id=1,
    user_id=1,
    user_role="manager"
)

# Download document
content = await doc_service.download_document(
    document_id=1,
    user_id=1,
    user_role="manager"
)
```

### 4. Search & Filter

```python
# Search by query
results = await doc_service.search_documents(
    query="May 2024",
    doc_type="report",
    date_from=datetime(2024, 5, 1),
    date_to=datetime(2024, 5, 31),
    limit=50
)

# List with filters
documents = await doc_service.list_documents(
    filters={
        "doc_type": "report",
        "status": "generated",
        "created_by": 1,
    },
    user_role="manager",
    limit=100,
    offset=0
)
```

### 5. Archive & Security

```python
# Archive document (set to read-only)
await doc_service.archive_document(document_id=1, readonly=True)

# Mask sensitive data
from app.document_management.security import FieldMasker

masked_data = FieldMasker.mask_data({
    "name": "John Doe",
    "id_number": "123456789",
    "email": "john@example.com",
})
# Result: id_number masked as "****6789"
```

## API Endpoints

### Templates

- `POST /api/v1/documents/templates` - Create template
- `GET /api/v1/documents/templates/{id}` - Get template
- `GET /api/v1/documents/templates` - List templates

### Documents

- `POST /api/v1/documents/generate` - Generate document
- `GET /api/v1/documents/documents/{id}` - Get document metadata
- `GET /api/v1/documents/documents/{id}/download` - Download document
- `GET /api/v1/documents/documents` - List documents
- `POST /api/v1/documents/documents/{id}/archive` - Archive document
- `DELETE /api/v1/documents/documents/{id}` - Delete document
- `POST /api/v1/documents/search` - Search documents

## Examples

See `template_examples/` for:
- `report_template.html` - HTML template example
- `templates_config.json` - Template configuration
- `sample_data.json` - Sample data for template filling

## Performance Characteristics

- **Generation**: <2s for average documents
- **Search**: <3s for metadata queries
- **Upload/Download**: 99%+ success rate
- **Storage**: Supports 10GB+ files
- **Concurrent Access**: Thread-safe with proper DB pooling

## Security Best Practices

1. **Access Control**: Always validate user role and permissions
2. **Encryption**: Enable for confidential/secret documents
3. **Audit Logging**: Enable to track all access
4. **Field Masking**: Use for sensitive data in templates
5. **Retention**: Set appropriate retention policies
6. **Storage**: Use S3 with encryption at rest for production

## Database Schema

### Template
- `id`: Primary key
- `name`: Template name
- `category`: Category (reports, contracts, etc.)
- `current_version`: Active version number
- `file_path`: Storage path to template
- `placeholders`: JSON list of placeholder definitions
- `file_type`: pdf, docx, or html

### Document
- `id`: Primary key
- `title`: Document title
- `template_id`: Reference to template
- `doc_type`: Document type/category
- `status`: generated, archived, deleted
- `access_level`: public, internal, confidential, secret
- `file_path`: Storage location
- `file_hash`: SHA256 for integrity
- `input_data`: JSON of data used for generation
- `created_at`, `updated_at`: Timestamps
- `is_encrypted`: Encryption status

### DocumentAccessLog
- `id`: Primary key
- `document_id`: Document accessed
- `user_id`: User who accessed
- `action`: view, download, edit, delete
- `status`: success, failed, denied
- `accessed_at`: Access timestamp

## Troubleshooting

### Template Not Found
- Check template ID exists
- Verify template is active (`is_active = true`)

### Document Generation Failed
- Verify all required placeholders provided
- Check template file is valid
- Check storage backend is accessible

### Access Denied
- Verify user role has permission
- Check document access_level matches user role
- Check access control is enabled

### Storage Issues
- Verify storage backend configuration
- Check disk space (local) or S3 credentials
- Check file permissions

## Future Enhancements

- [ ] Document version diff/compare UI
- [ ] Batch document generation
- [ ] Scheduled document generation
- [ ] Advanced OCR for PDF templates
- [ ] Signature capture integration
- [ ] Digital signatures (PKI)
- [ ] Template marketplace
- [ ] Multi-language support
- [ ] Document workflow automation
- [ ] Integration with email/messaging

## Contributing

See main project README for contribution guidelines.

## License

See main LICENSE file.
