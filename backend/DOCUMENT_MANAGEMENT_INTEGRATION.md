# Document Management Integration Guide

## Quick Start

### Step 1: Install Dependencies

```bash
# Install document management dependencies
pip install python-docx reportlab weasyprint PyPDF2 boto3

# Or install from requirements file
pip install -r requirements_document_management.txt
```

### Step 2: Database Setup

```bash
# Apply migrations to create tables
cd backend
alembic upgrade head
```

### Step 3: Configure Storage

Edit `.env` or environment variables:

```bash
# Local Storage (Development)
DOC_STORAGE_TYPE=local
DOC_LOCAL_STORAGE_PATH=/tmp/xdoc_documents

# S3 Storage (Production)
DOC_STORAGE_TYPE=s3
DOC_S3_BUCKET_NAME=xdoc-documents
DOC_S3_ACCESS_KEY=your_access_key
DOC_S3_SECRET_KEY=your_secret_key
DOC_S3_REGION=us-east-1
```

### Step 4: Include in FastAPI App

Update `app/api/main.py`:

```python
from app.api.routes import documents

api_router = APIRouter()
api_router.include_router(documents.router)
```

### Step 5: Test the System

```bash
# Run tests
pytest tests/test_document_management.py -v

# Run example
python examples/document_management_example.py
```

---

## Core Concepts

### Templates

Templates are reusable document patterns with placeholders. They support:

- **File Types:** PDF, Word (DOCX), HTML
- **Placeholders:** Dynamic content areas marked with `{{placeholder_name}}`
- **Versions:** Tracked changes with rollback capability
- **Categories:** Organization (reports, contracts, invoices, etc.)

Example template (HTML):
```html
<h1>{{report_title}}</h1>
<p>Date: {{report_date}}</p>
<p>Department: {{department}}</p>
```

### Documents

Documents are generated instances of templates with actual data:

- **Unique ID:** Every document has unique ID
- **Versioning:** Multiple versions tracked with parent relationships
- **Status:** generated, archived, deleted
- **Metadata:** Tags, custom fields for classification
- **Audit Trail:** Full access log

### Storage

Files stored with classification:
```
documents/
├── reports/           # By type
│   └── 2024-05-20/   # By date
│       ├── report_001.pdf
│       └── report_002.pdf
├── contracts/
│   └── 2024-05-20/
│       └── contract_001.pdf
└── templates/         # Template backups
    └── reports/
        └── weekly_report.html
```

### Security Layers

1. **Authentication:** User identity (handled by main app)
2. **Authorization:** Role-based (admin, manager, user, guest)
3. **Access Control:** Document access levels (public, internal, confidential, secret)
4. **Encryption:** Optional PDF/Word encryption
5. **Audit:** Complete access logging

---

## Common Workflows

### Workflow 1: Create and Use a Report Template

```python
import asyncio
from app.document_management.services import TemplateService
from app.document_management.storage import StorageFactory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

async def setup_report_template():
    # Initialize
    storage = StorageFactory.get_backend("local", base_path="/tmp/xdoc")
    db = sessionmaker(bind=create_engine("sqlite:///xdoc.db"))()
    template_service = TemplateService(storage, db)
    
    # Read template file
    with open("templates/weekly_report.html", "rb") as f:
        template_content = f.read()
    
    # Create template
    template = await template_service.create_template(
        name="Weekly Report",
        category="reports",
        file_content=template_content,
        file_type="html",
        placeholders=[
            {"name": "report_date", "type": "date", "required": True},
            {"name": "department", "type": "text", "required": True},
            {"name": "metrics", "type": "table", "required": False},
            {"name": "summary", "type": "text", "required": True},
        ],
        created_by=1,
        description="Weekly status report template",
    )
    
    print(f"Template created: {template['id']}")
    return template['id']

# Run
template_id = asyncio.run(setup_report_template())
```

### Workflow 2: Generate Document from Template

```python
async def generate_report():
    # Setup
    storage = StorageFactory.get_backend("local", base_path="/tmp/xdoc")
    db = sessionmaker(bind=create_engine("sqlite:///xdoc.db"))()
    from app.document_management.services.document import DocumentService
    doc_service = DocumentService(storage, db)
    
    # Generate document
    document = await doc_service.generate_document(
        template_id=1,
        data={
            "report_date": "2024-05-20",
            "department": "Engineering",
            "metrics": [
                {"name": "Uptime", "value": "99.98%", "target": "99.9%"},
                {"name": "Response Time", "value": "120ms", "target": "150ms"},
            ],
            "summary": "Strong performance. All targets met.",
        },
        created_by=1,
        doc_type="report",
        title="Weekly Report - May 20",
        access_level="internal",
        watermark="Confidential",
        tags=["weekly", "may-2024", "engineering"],
        retention_days=365,  # Keep for 1 year
    )
    
    print(f"Document generated: {document['id']}")
    return document['id']

doc_id = asyncio.run(generate_report())
```

### Workflow 3: Secure Document Download

```python
async def download_document_securely(doc_id, user_id, user_role):
    # Setup
    storage = StorageFactory.get_backend("local", base_path="/tmp/xdoc")
    db = sessionmaker(bind=create_engine("sqlite:///xdoc.db"))()
    from app.document_management.services.document import DocumentService
    doc_service = DocumentService(storage, db)
    
    # Check access
    doc_info = await doc_service.get_document(
        document_id=doc_id,
        user_id=user_id,
        user_role=user_role,
    )
    
    if not doc_info:
        print("Access denied")
        return None
    
    # Download
    content = await doc_service.download_document(
        document_id=doc_id,
        user_id=user_id,
        user_role=user_role,
    )
    
    if content:
        # Save locally
        with open(f"downloaded_{doc_id}.pdf", "wb") as f:
            f.write(content)
        print(f"Document downloaded: {len(content)} bytes")
    
    return content

# Download with role-based access
asyncio.run(download_document_securely(doc_id=1, user_id=5, user_role="manager"))
```

### Workflow 4: Search and Archive

```python
async def search_and_archive():
    storage = StorageFactory.get_backend("local", base_path="/tmp/xdoc")
    db = sessionmaker(bind=create_engine("sqlite:///xdoc.db"))()
    from app.document_management.services.document import DocumentService
    doc_service = DocumentService(storage, db)
    
    # Search for May reports
    from datetime import datetime, timedelta
    results = await doc_service.search_documents(
        query="May",
        doc_type="report",
        date_from=datetime(2024, 5, 1),
        date_to=datetime(2024, 5, 31),
    )
    
    print(f"Found {len(results)} documents")
    
    # Archive old documents
    for doc in results:
        if (datetime.now() - datetime.fromisoformat(doc['created_at'])).days > 90:
            await doc_service.archive_document(doc['id'], readonly=True)
            print(f"Archived document {doc['id']}")

asyncio.run(search_and_archive())
```

---

## API Usage Examples

### Create Template via API

```bash
curl -X POST http://localhost:8000/api/v1/documents/templates \
  -F "file=@templates/report.html" \
  -F "name=Weekly Report" \
  -F "category=reports" \
  -F "description=Weekly status report" \
  -F 'placeholders={"name":"report_date","type":"date","required":true}' \
  -F "created_by=1"
```

### Generate Document via API

```bash
curl -X POST http://localhost:8000/api/v1/documents/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": 1,
    "data": {
      "report_date": "2024-05-20",
      "department": "Engineering"
    },
    "doc_type": "report",
    "title": "Weekly Report",
    "access_level": "internal",
    "encrypt": false,
    "watermark": "Confidential"
  }' \
  -G --data-urlencode "user_id=1"
```

### Download Document via API

```bash
curl -X GET "http://localhost:8000/api/v1/documents/documents/1/download?user_id=1&user_role=manager" \
  -o report.pdf
```

### Search Documents via API

```bash
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "May 2024",
    "doc_type": "report",
    "limit": 50
  }'
```

---

## Troubleshooting

### Issue: "Template not found"
**Solution:** 
- Check template ID exists: `template_service.get_template(template_id)`
- Ensure template is active: `is_active = true`
- Verify database connection

### Issue: "Document generation failed"
**Solution:**
- Verify all required placeholders provided in data
- Check template file format (PDF, DOCX, HTML)
- Ensure storage backend is accessible
- Check logs for specific error

### Issue: "Access denied"
**Solution:**
- Verify user role: must be appropriate for document access_level
- Check permissions: user role must have "download" permission
- Verify document is not deleted or archived

### Issue: "Storage backend error"
**Solution:**
- Local: Check directory exists and has write permissions
- S3: Verify credentials and bucket exists
- MinIO: Check endpoint URL and connectivity

---

## Performance Optimization Tips

1. **Batch Generation:**
   - Generate multiple documents in parallel
   - Reuse database connections

2. **Caching:**
   - Cache template files in memory
   - Cache user permissions

3. **Search Optimization:**
   - Create indexes on frequently filtered columns
   - Use pagination to limit results

4. **Storage:**
   - Use S3 for large-scale deployments
   - Enable compression for text-heavy documents
   - Implement cleanup policies for old documents

---

## Monitoring Checklist

- [ ] Document generation success rate > 98%
- [ ] Average generation time < 2 seconds
- [ ] Search response time < 3 seconds
- [ ] Storage utilization tracked
- [ ] Failed access attempts logged
- [ ] Encryption/decryption working
- [ ] Audit logs being written
- [ ] Database backup strategy in place

---

## Support & Resources

- **Documentation:** See `app/document_management/README.md`
- **Technical Spec:** See `DOCUMENT_MANAGEMENT_SPEC.md`
- **Examples:** See `examples/document_management_example.py`
- **Tests:** See `tests/test_document_management.py`
- **Template Examples:** See `template_examples/`

---

**Last Updated:** May 20, 2024
