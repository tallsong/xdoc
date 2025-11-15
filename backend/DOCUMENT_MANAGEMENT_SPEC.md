# Document Management System - Technical Specification

## Executive Summary

This document specifies the implementation of a comprehensive structured document generation and management system for the XDoc platform. The system addresses the enterprise need for standardized document generation, secure storage, and controlled retrieval with full audit trails.

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  - Template CRUD, Document Generation, Search, Download      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                       │
│  ├─ TemplateService (Template management & versioning)       │
│  ├─ DocumentService (Generation, search, lifecycle)          │
│  └─ SecurityManager (Access control, encryption)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Integration Layer                          │
│  ├─ Generators (PDF, Word, HTML)                             │
│  ├─ Storage Backends (Local, S3, MinIO)                      │
│  └─ Security Utils (Encryption, Masking, Audit)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Persistence & Storage Layer                     │
│  ├─ PostgreSQL/SQLite (Metadata, Audit Logs)                 │
│  └─ File Storage (Local, S3, MinIO)                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Details

#### API Layer (`app/api/routes/documents.py`)
- RESTful endpoints for all document operations
- Request/response validation with Pydantic
- Error handling and logging

#### Services Layer
- **TemplateService** (`services/__init__.py`): Template CRUD and versioning
- **DocumentService** (`services/document.py`): Document lifecycle management
- **SecurityManager**: Access control, encryption, audit logging

#### Generators (`generators/__init__.py`)
- PDFGenerator: HTML-to-PDF conversion, watermarking
- WordGenerator: DOCX template filling
- HTMLGenerator: HTML template rendering
- TemplateRenderer: Jinja2-based placeholder rendering

#### Storage (`storage/__init__.py`)
- StorageBackend: Abstract interface
- LocalStorageBackend: File-based storage
- S3StorageBackend: AWS S3 and MinIO support
- StorageFactory: Backend instantiation

#### Security (`security/__init__.py`)
- FieldMasker: Sensitive data masking
- DocumentEncryption: PDF/DOCX encryption
- AccessControlManager: Role-based permissions

#### Models (`models/`)
- Template: Template definition and metadata
- TemplateVersion: Template version history
- Document: Document metadata
- DocumentAccessLog: Audit trail

## 2. Data Models

### 2.1 Template Model

```python
Template:
  id: int (PK)
  name: str                    # Template name
  category: str                # reports, contracts, invoices
  description: Optional[str]
  current_version: int         # Active version
  file_path: str               # Storage path
  placeholders: JSON           # [{name, type, required, description}]
  metadata: JSON               # Custom config
  file_type: str               # pdf, docx, html
  is_active: bool              # Soft delete
  created_at: datetime
  updated_at: datetime
  created_by: int              # User ID
  versions: [TemplateVersion]  # Version history
```

### 2.2 TemplateVersion Model

```python
TemplateVersion:
  id: int (PK)
  template_id: int (FK)        # Reference to template
  version: int                 # Version number
  file_path: str               # Storage path
  file_hash: str               # SHA256 hash
  description: Optional[str]
  change_summary: Optional[str]# Changes from previous
  created_at: datetime
  created_by: int              # Who created
```

### 2.3 Document Model

```python
Document:
  id: int (PK)
  title: str                   # Document title
  template_id: int             # Template used
  template_version: int        # Which version
  doc_type: str                # Category
  status: enum                 # generated, archived, deleted
  access_level: enum           # public, internal, confidential, secret
  file_path: str               # Storage location
  file_hash: str               # SHA256 hash
  file_size: int               # Bytes
  mime_type: str               # application/pdf, etc.
  input_data: JSON             # Data used for generation
  metadata: JSON               # tags, custom fields
  version: int                 # Document version
  parent_document_id: Optional[int]  # For versioning
  created_at: datetime
  updated_at: datetime
  archived_at: Optional[datetime]
  created_by: int
  updated_by: Optional[int]
  is_encrypted: bool
  encryption_key_id: Optional[str]
  is_readonly: bool            # Archived/immutable
  retention_days: Optional[int]# Auto-delete policy
```

### 2.4 DocumentAccessLog Model

```python
DocumentAccessLog:
  id: int (PK)
  document_id: int (FK)        # Document accessed
  user_id: int                 # User who accessed
  action: str                  # view, download, edit, delete
  ip_address: Optional[str]
  user_agent: Optional[str]
  status: str                  # success, failed, denied
  reason: Optional[str]        # Why denied/failed
  accessed_at: datetime
```

## 3. Functional Specifications

### 3.1 Template Management

#### 3.1.1 Create Template
```
Input:
  - Template file (PDF, DOCX, or HTML)
  - Name, Category, Description
  - Placeholder definitions
  - Metadata (optional)

Process:
  1. Validate file format
  2. Calculate file hash (SHA256)
  3. Upload to storage backend
  4. Create Template record in database
  5. Create initial TemplateVersion record

Output:
  - Template ID
  - Current version
  - Storage path
  - File hash
```

#### 3.1.2 Update Template (Create New Version)
```
Input:
  - Template ID
  - New template file
  - Change summary

Process:
  1. Validate template exists and is active
  2. Calculate new version number
  3. Upload new file to storage
  4. Create TemplateVersion record
  5. Update Template.current_version
  6. Preserve old version for rollback

Output:
  - New version number
  - Storage path
  - File hash
```

#### 3.1.3 List Templates
```
Input:
  - Optional category filter
  - Optional active_only flag

Output:
  - List of templates with:
    - ID, Name, Category
    - Current version
    - Creation date
```

#### 3.1.4 Get Template Version
```
Input:
  - Template ID
  - Version number (optional, defaults to current)

Output:
  - Template file bytes
  - Metadata
```

### 3.2 Document Generation

#### 3.2.1 Generate Document
```
Input:
  - Template ID
  - Data (JSON object)
  - Document type
  - Title (optional, auto-generated if not provided)
  - Access level (default: internal)
  - Encryption flag (default: false)
  - Watermark text (optional)
  - Tags (optional)
  - Retention days (optional)

Process:
  1. Validate template exists
  2. Fetch template file from storage
  3. Render template with data using Jinja2
  4. Apply watermark if requested
  5. Encrypt if requested
  6. Generate document name: {name}_{timestamp}_{version}.{format}
  7. Calculate document hash
  8. Upload to storage (path: documents/{type}/{date}/{name}.{format})
  9. Create Document record
  10. Log generation event

Output:
  - Document ID
  - Title
  - File size
  - File hash
  - Status: "generated"
  - Creation timestamp
```

#### 3.2.2 Search Documents
```
Input:
  - Query string (searches title, doc_type)
  - Optional filters:
    - Document type
    - Date range
    - Access level
    - Created by

Process:
  1. Build query based on filters
  2. Execute search (response time: <3 seconds)
  3. Apply access control checks
  4. Return results with pagination

Output:
  - List of matching documents (max 50)
  - Total count
```

### 3.3 Document Retrieval

#### 3.3.1 Get Document
```
Input:
  - Document ID
  - User ID
  - User role

Process:
  1. Fetch document metadata
  2. Check if user has access:
     - Check role permissions
     - Check access_level hierarchy
  3. Log access event
  4. Return metadata

Output:
  - Document metadata (title, size, created_at, tags, etc.)
```

#### 3.3.2 Download Document
```
Input:
  - Document ID
  - User ID
  - User role

Process:
  1. Check permissions (same as Get Document)
  2. Check "download" permission
  3. Verify not deleted
  4. Download from storage
  5. Log access with "download" action
  6. Verify hash matches

Output:
  - Document file bytes
  - Correct HTTP headers for download
```

### 3.4 Security Features

#### 3.4.1 Access Control

**Role Hierarchy:**
- Admin: All permissions (view, download, edit, delete, share)
- Manager: Most permissions (view, download, edit, share)
- User: Limited permissions (view, download)
- Guest: Minimal permissions (view)

**Access Level Hierarchy:**
- Public: All roles can access
- Internal: user, manager, admin
- Confidential: manager, admin
- Secret: admin only

#### 3.4.2 Field Masking

**Sensitive Field Patterns:**
- ID numbers: 6-18 digits
- Phone numbers: 10+ digits
- Email addresses
- Credit card: 4-4-4-4 digits
- SSN: xxx-xx-xxxx

**Masking Patterns:**
- Default: Show last 4 characters
- Partial: Show first 2 and last 2 characters
- Full: Completely masked

**Example:**
```
SSN: 123-45-6789 → ****6789
ID: 123456789 → *****6789
Email: john@example.com → john@example.com (partially)
```

#### 3.4.3 Encryption

**PDF Encryption:**
- User password: Restricts printing, copying
- Owner password: Allows modifications
- Uses PyPDF2 library

**DOCX Encryption:**
- Restrict editing via password
- Uses Office 365 client integration

#### 3.4.4 Audit Logging

**Logged Events:**
- Template creation/update
- Document generation
- Document access (view/download)
- Permission denied attempts
- Encryption/decryption
- Document archival/deletion

**Log Retention:**
- Kept indefinitely
- Searchable by user, document, date, action

### 3.5 Storage Management

#### 3.5.1 Storage Backends

**Local Storage:**
- Base path: configurable
- Directory structure: `documents/{type}/{date}/{name}`
- File permissions: 644 (rw-r--r--)
- Read-only mode: 444 (r--r--r--)

**S3/MinIO:**
- Bucket: configurable
- Key pattern: `documents/{type}/{date}/{name}`
- Metadata: file_hash, upload_date, etc.
- ACL: private by default

#### 3.5.2 Document Classification

```
documents/
├── reports/
│   ├── 2024-05-20/
│   └── 2024-05-21/
├── contracts/
│   ├── 2024-05-20/
│   └── 2024-05-21/
├── invoices/
│   ├── 2024-05-20/
│   └── 2024-05-21/
└── templates/
    ├── reports/
    └── contracts/
```

#### 3.5.3 Archival Policy

```
Status: "archived"
├── Set is_readonly = true
├── Set file permissions to 444 (read-only)
├── Set retention_days if specified
├── Archive date recorded
└── Future deletion scheduled if retention_days set
```

## 4. API Endpoints

### 4.1 Template Endpoints

```
POST   /api/v1/documents/templates
       - Create template
       - Content-Type: multipart/form-data
       - Returns: TemplateResponse

GET    /api/v1/documents/templates/{template_id}
       - Get template details
       - Returns: TemplateResponse

GET    /api/v1/documents/templates
       - List templates
       - Query params: category, active_only
       - Returns: {templates: [...]}

PUT    /api/v1/documents/templates/{template_id}
       - Update template (create new version)
       - Returns: {version, storage_path, file_hash}

DELETE /api/v1/documents/templates/{template_id}
       - Soft delete (deactivate)
       - Returns: {message: "Template deactivated"}
```

### 4.2 Document Endpoints

```
POST   /api/v1/documents/generate
       - Generate document
       - Body: GenerateDocumentRequest
       - Returns: DocumentResponse

GET    /api/v1/documents/documents/{document_id}
       - Get document metadata
       - Query params: user_id, user_role
       - Returns: DocumentResponse

GET    /api/v1/documents/documents/{document_id}/download
       - Download document
       - Query params: user_id, user_role
       - Returns: File stream

GET    /api/v1/documents/documents
       - List documents
       - Query params: doc_type, status, skip, limit, user_role
       - Returns: {documents: [...], total}

POST   /api/v1/documents/documents/{document_id}/archive
       - Archive document
       - Query params: user_id
       - Returns: {message: "Document archived"}

DELETE /api/v1/documents/documents/{document_id}
       - Delete document
       - Query params: user_id
       - Returns: {message: "Document deleted"}

POST   /api/v1/documents/search
       - Search documents
       - Body: SearchDocumentsRequest
       - Returns: {documents: [...], total}
```

## 5. Performance Requirements

### 5.1 Response Times
- Document generation: < 2 seconds
- Metadata search: < 3 seconds
- Document download: Depends on file size
- Template listing: < 1 second

### 5.2 Throughput
- Concurrent requests: 100+
- Document upload rate: 99%+ success
- Document download rate: 99%+ success

### 5.3 Storage Capacity
- Max file size: 10GB
- Estimated storage per document: ~2-50MB (typical)
- Typical retention: 1-7 years

## 6. Security Requirements

### 6.1 Authentication & Authorization
- User role required for all document operations
- Access control based on role + document access_level

### 6.2 Data Protection
- Encryption for sensitive documents
- Field masking for PII
- HTTPS for all API communication

### 6.3 Audit & Compliance
- All access logged
- Immutable audit trail
- Document integrity verified via SHA256 hash

## 7. Database Schema

### 7.1 Indexes

```
Template:
  - PRIMARY KEY (id)
  - INDEX (category)
  - INDEX (name)
  - INDEX (is_active)

TemplateVersion:
  - PRIMARY KEY (id)
  - FOREIGN KEY (template_id)
  - INDEX (template_id)
  - INDEX (version)

Document:
  - PRIMARY KEY (id)
  - INDEX (title)
  - INDEX (doc_type)
  - INDEX (status)
  - INDEX (created_at)
  - INDEX (template_id)

DocumentAccessLog:
  - PRIMARY KEY (id)
  - FOREIGN KEY (document_id)
  - INDEX (document_id)
  - INDEX (user_id)
  - INDEX (action)
  - INDEX (accessed_at)
```

## 8. Configuration

### 8.1 Environment Variables

```bash
# Storage
DOC_STORAGE_TYPE=local
DOC_LOCAL_STORAGE_PATH=/data/documents

# S3/MinIO
DOC_STORAGE_TYPE=s3
DOC_S3_BUCKET_NAME=documents
DOC_S3_ACCESS_KEY=xxx
DOC_S3_SECRET_KEY=yyy
DOC_S3_REGION=us-east-1
DOC_S3_ENDPOINT_URL=http://minio:9000  # For MinIO

# Security
DOC_ENABLE_ENCRYPTION=true
DOC_ENABLE_WATERMARK=true
DOC_DEFAULT_WATERMARK="Internal Use Only"

# Database
DOC_DOCUMENT_DB_URL=postgresql://user:pass@host/dbname
```

## 9. Error Handling

### 9.1 Common Errors

```
400 Bad Request
  - Invalid template file
  - Missing required placeholders
  - Invalid data provided

404 Not Found
  - Template not found
  - Document not found

403 Forbidden
  - Access denied (role check failed)
  - Access denied (access level too high)
  - No download permission

500 Internal Server Error
  - Storage backend error
  - Encryption failed
  - Database error
```

## 10. Testing

### 10.1 Unit Tests

- FieldMasker: Masking logic for various data types
- AccessControlManager: Permission checking
- TemplateRenderer: Template rendering with Jinja2
- StorageBackend: Upload, download, delete operations

### 10.2 Integration Tests

- Template creation and versioning
- Document generation with various templates
- Document search and filtering
- Access control enforcement
- Audit logging

### 10.3 Performance Tests

- Large file upload/download
- Concurrent document generation
- Search with millions of documents
- Storage backend performance

## 11. Deployment

### 11.1 Prerequisites

- Python 3.10+
- PostgreSQL or SQLite
- S3/MinIO (if using cloud storage)
- Dependencies: see requirements.txt

### 11.2 Migration

```bash
# Apply database migrations
alembic upgrade head
```

### 11.3 Initialization

```bash
# Create storage directories
mkdir -p /data/documents/templates
mkdir -p /data/documents/documents
```

## 12. Monitoring & Observability

### 12.1 Metrics to Track

- Document generation success rate
- Average generation time
- Storage usage by type
- Access pattern by user/role
- Failed access attempts

### 12.2 Alerts

- Failed document generation
- Storage quota exceeded
- Access denied attempts (potential security issue)
- Encryption failures
- Database connection errors

---

**Document Version:** 1.0  
**Last Updated:** May 20, 2024  
**Author:** Document Management System Team
