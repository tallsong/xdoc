# Document Management System - Architecture Diagram

## High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                             │
│                   (Web UI, Mobile App, Services)                        │
└────────────────────────────────────────────────┬───────────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   API Router (documents.py)                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │  │
│  │  │  Template    │  │  Document    │  │  Document    │            │  │
│  │  │  Endpoints   │  │  Generation  │  │  Download    │            │  │
│  │  │              │  │  Endpoints   │  │  Endpoints   │            │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                 │                                       │
│                    Dependency Injection (DI)                            │
│                                 │                                       │
│  ┌──────────────────────────────┼──────────────────────────────────┐  │
│  │                              ▼                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐ │  │
│  │  │          Business Logic Layer (Services)                  │ │  │
│  │  ├────────────────────────────────────────────────────────────┤ │  │
│  │  │                                                            │ │  │
│  │  │  ┌──────────────────────────────────────────────────────┐ │ │  │
│  │  │  │ TemplateService                                      │ │ │  │
│  │  │  │  • create_template()                                │ │ │  │
│  │  │  │  • update_template()  (new version)                 │ │ │  │
│  │  │  │  • get_template()                                   │ │ │  │
│  │  │  │  • list_templates()                                 │ │ │  │
│  │  │  │  • delete_template()  (soft)                        │ │ │  │
│  │  │  └──────────────────────────────────────────────────────┘ │ │  │
│  │  │                                                            │ │  │
│  │  │  ┌──────────────────────────────────────────────────────┐ │ │  │
│  │  │  │ DocumentService                                      │ │ │  │
│  │  │  │  • generate_document()                               │ │ │  │
│  │  │  │  • get_document()                                    │ │ │  │
│  │  │  │  • download_document()                               │ │ │  │
│  │  │  │  • list_documents()                                  │ │ │  │
│  │  │  │  • search_documents()                                │ │ │  │
│  │  │  │  • archive_document()                                │ │ │  │
│  │  │  │  • delete_document()                                 │ │ │  │
│  │  │  │  • _log_access()                                     │ │ │  │
│  │  │  └──────────────────────────────────────────────────────┘ │ │  │
│  │  │                                                            │ │  │
│  │  └────────────────────────────────────────────────────────────┘ │  │
│  │                              │                                   │  │
│  └──────────────────────────────┼───────────────────────────────────┘  │
│                                 │                                       │
│                    ┌────────────┴────────────┬──────────────┐           │
└────────────────────┼───────────────────────┼──────────────┼───────────┘
                     │                       │              │
                     ▼                       ▼              ▼
        ┌─────────────────────┐  ┌──────────────────┐  ┌──────────────┐
        │  Storage Layer      │  │  Security Layer  │  │ Generator    │
        └─────────────────────┘  └──────────────────┘  │ Layer        │
                                                       └──────────────┘
```

## Component Interaction Flow

### Document Generation Flow

```
┌──────────────┐
│ API Request  │
│ (generate)   │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ DocumentService      │
│ .generate_document() │
└──────┬───────────────┘
       │
       ├─────────────────────────────────┬─────────────────────────┬──────────────┐
       │                                 │                         │              │
       ▼                                 ▼                         ▼              ▼
┌────────────────┐              ┌──────────────────┐     ┌────────────────┐  ┌──────────┐
│ Template       │              │ Data Validation  │     │ Template       │  │ Security │
│ Retrieval      │──────────────│                  │     │ Renderer       │  │ Manager  │
│ (TemplateFile) │              │ (placeholders)   │     │ (Jinja2)       │  │ (encrypt)│
└────────────────┘              └──────────────────┘     └────────────────┘  └──────────┘
       │                                 │                         │              │
       └─────────────────────────────────┴─────────────────────────┴──────────────┘
                                         │
                                         ▼
                          ┌────────────────────────────┐
                          │ Generator Selection        │
                          │ (PDF/Word/HTML)            │
                          └────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
            ┌────────────────┐ ┌────────────┐ ┌──────────┐
            │ PDFGenerator   │ │ WordGen    │ │ HTMLGen  │
            │ (WeasyPrint)   │ │ (python    │ │          │
            │ +Watermark     │ │  -docx)    │ │          │
            └────────┬───────┘ └────┬───────┘ └────┬─────┘
                     │              │              │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Document Bytes      │
                         │ Generated           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Storage Upload      │
                         │ (Local/S3)          │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Create Document     │
                         │ Record in DB        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Return Document ID  │
                         │ & Metadata          │
                         └─────────────────────┘
```

## Document Access Control Flow

```
┌─────────────────────┐
│ API Request         │
│ (download)          │
│ user_id, user_role  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────┐
│ DocumentService             │
│ .download_document()        │
└────────┬────────────────────┘
         │
         ├──────────────────────────┬──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│ Get Document     │      │ AccessControl    │      │ Check Download  │
│ Metadata         │      │ Manager          │      │ Permission      │
│ from DB          │      │                  │      │                 │
└──────┬───────────┘      │ Check:           │      │ user_role has   │
       │                  │ - User role      │      │ "download"      │
       │                  │ - Access level   │      │ permission      │
       │                  │ - Access denied? │      │                 │
       │                  └────┬─────────────┘      └────┬────────────┘
       │                       │                        │
       └───────────────────────┼────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
         ┌──────────▼─────────┐  ┌────────▼───────────┐
         │ ALLOWED            │  │ DENIED             │
         └────────┬────────────┘  └────────┬───────────┘
                  │                        │
                  ▼                        ▼
         ┌──────────────────┐     ┌──────────────────┐
         │ Download from    │     │ Log Access:      │
         │ Storage          │     │ "denied"         │
         └────────┬─────────┘     │ reason="Access   │
                  │               │ denied"          │
                  ▼               └────────┬─────────┘
         ┌──────────────────┐             │
         │ Log Access:      │             ▼
         │ "download"       │     ┌──────────────────┐
         │ "success"        │     │ Return Error     │
         └────────┬─────────┘     └──────────────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Verify Hash      │
         │ SHA256           │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Return File      │
         │ Bytes            │
         └──────────────────┘
```

## Storage Backend Architecture

```
┌─────────────────────────────────┐
│     Document                    │
│     (file bytes + metadata)     │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          StorageFactory                     │
│  (Backend Selection & Instantiation)        │
└────────────────┬────────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
┌────────────────────┐  ┌────────────────────┐
│ LocalStorageBackend│  │ S3StorageBackend   │
│                    │  │                    │
│ • upload()         │  │ • upload()         │
│ • download()       │  │ • download()       │
│ • delete()         │  │ • delete()         │
│ • exists()         │  │ • exists()         │
│ • list_files()     │  │ • list_files()     │
│ • set_readonly()   │  │ • set_readonly()   │
└────┬───────────────┘  └───┬────────────────┘
     │                      │
     ▼                      ▼
/data/documents/      AWS S3 / MinIO
documents/            s3://bucket/
  ├── reports/        documents/
  ├── contracts/        ├── reports/
  ├── invoices/         ├── contracts/
  └── templates/        └── ...
```

## Security Architecture

```
┌──────────────────────────────────┐
│         User Request             │
│    (user_id, user_role)          │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│   AccessControlManager               │
└────────────────────────────────────────┐
     │                                   │
     ├─ Role Hierarchy:                  │
     │  ┌──────────────────────────────┐ │
     │  │ admin > manager > user > guest
     │  └──────────────────────────────┘ │
     │                                   │
     ├─ Access Level Hierarchy:          │
     │  ┌──────────────────────────────┐ │
     │  │ public > internal > ...      │ │
     │  │ confidential > secret        │ │
     │  └──────────────────────────────┘ │
     │                                   │
     └─ Permission Checking:             │
        ├─ view                          │
        ├─ download                      │
        ├─ edit                          │
        └─ delete                        │
                                         │
         ┌───────────────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│      Document Access Check       │
│    (access_level vs role)        │
└────────────────┬────────────────┘
                 │
         ┌───────┴──────┐
         │              │
    ┌────▼────┐    ┌────▼──┐
    │ ALLOW   │    │ DENY  │
    │         │    │       │
    │ ┌──────────────┐  │ ┌──────────────────┐
    │ │ Encrypt?     │  │ │ Log Failure      │
    │ │ Watermark?   │  │ │ Return Forbidden │
    │ │ Masking?     │  │ │                  │
    │ └──────┬───────┘  │ └──────────────────┘
    │        │          │
    │        ▼          │
    │ ┌──────────────┐  │
    │ │ Download from│  │
    │ │ Storage      │  │
    │ └──────┬───────┘  │
    │        │          │
    │        ▼          │
    │ ┌──────────────┐  │
    │ │ Log Success  │  │
    │ │ Return File  │  │
    │ └──────────────┘  │
    │                   │
    └───────────────────┘
```

## Data Model Relationships

```
Template (1) ──────(1:N)────── TemplateVersion
  │                                 │
  │                          (for version history)
  │
  ├─ id                    ├─ id
  ├─ name                  ├─ template_id (FK)
  ├─ category              ├─ version
  ├─ current_version       ├─ file_path
  ├─ file_path             ├─ file_hash
  ├─ placeholders(JSON)    ├─ description
  ├─ metadata(JSON)        ├─ change_summary
  ├─ created_at            └─ created_at
  ├─ updated_at
  ├─ created_by
  └─ is_active


Document (1) ──────(1:N)────── DocumentAccessLog
  │                                 │
  │                        (for audit trail)
  │
  ├─ id                    ├─ id
  ├─ title                 ├─ document_id (FK)
  ├─ template_id           ├─ user_id
  ├─ template_version      ├─ action
  ├─ doc_type              ├─ ip_address
  ├─ status                ├─ user_agent
  ├─ access_level          ├─ status
  ├─ file_path             ├─ reason
  ├─ file_hash             └─ accessed_at
  ├─ file_size
  ├─ input_data(JSON)
  ├─ metadata(JSON)
  ├─ version
  ├─ parent_document_id
  ├─ created_at
  ├─ updated_at
  ├─ archived_at
  ├─ created_by
  ├─ updated_by
  ├─ is_encrypted
  ├─ is_readonly
  └─ retention_days
```

## Request/Response Flow

```
Request
  │
  ├─ Authenticate (handled by main app)
  │
  ├─ API Endpoint
  │  │
  │  ├─ Validate input
  │  ├─ DI inject service
  │  │
  │  └─ Service Layer
  │     │
  │     ├─ Check permissions
  │     ├─ Interact with storage
  │     ├─ Manage database
  │     ├─ Apply security (encryption, masking)
  │     ├─ Log events
  │     │
  │     └─ Return result
  │
  └─ Response
     │
     ├─ Status code
     ├─ Data (JSON or file stream)
     └─ Headers
```

---

## File Organization Diagram

```
document_management/
│
├── Core Configuration
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   └── README.md
│
├── Data Access Layer
│   ├── models/
│   │   ├── __init__.py
│   │   ├── template.py (Template, TemplateVersion)
│   │   └── document.py (Document, DocumentAccessLog)
│   │
│   └── alembic/versions/
│       └── 001_add_document_management.py (Migration)
│
├── Business Logic
│   └── services/
│       ├── __init__.py (TemplateService)
│       └── document.py (DocumentService)
│
├── Integration Layer
│   ├── generators/
│   │   └── __init__.py (Generators + TemplateRenderer)
│   │
│   ├── storage/
│   │   └── __init__.py (Storage backends)
│   │
│   └── security/
│       └── __init__.py (Security utilities)
│
└── API Layer
    └── api/routes/
        └── documents.py (FastAPI endpoints)
```

---

**Architecture Version:** 1.0  
**Created:** May 20, 2024
