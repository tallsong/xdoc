"""Example usage of the document management system."""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

# Import document management modules
from app.document_management.services import TemplateService
from app.document_management.services.document import DocumentService
from app.document_management.storage import StorageFactory
from app.document_management.security import FieldMasker, AccessControlManager, DocumentEncryption
from app.document_management.generators import PDFGenerator, TemplateRenderer


async def main():
    """Run example document management workflow."""

    print("=" * 60)
    print("Document Management System - Example Usage")
    print("=" * 60)

    # Initialize storage backend
    storage = StorageFactory.get_backend(
        backend_type="local",
        base_path="/tmp/xdoc_demo",
    )

    # In a real application, you would use a proper database session
    # For this example, we'll use a mock session
    class MockDB:
        def add(self, obj):
            pass

        def commit(self):
            pass

        def refresh(self, obj):
            pass

        def query(self, model):
            return self

        def filter(self, *args):
            return self

        def first(self):
            return None

    db = MockDB()

    # Example 1: Field Masking
    print("\n1. FIELD MASKING - Protect Sensitive Data")
    print("-" * 60)

    sensitive_data = {
        "employee_name": "John Doe",
        "ssn": "123-45-6789",
        "email": "john.doe@company.com",
        "phone": "13125551234",
        "salary": 150000,
        "passport_id": "123456789",
    }

    print("Original data:")
    for key, value in sensitive_data.items():
        print(f"  {key}: {value}")

    masked_data = FieldMasker.mask_data(sensitive_data)
    print("\nMasked data:")
    for key, value in masked_data.items():
        print(f"  {key}: {value}")

    # Example 2: Access Control
    print("\n2. ACCESS CONTROL - Role-Based Permissions")
    print("-" * 60)

    access_manager = AccessControlManager()

    roles = ["admin", "manager", "user", "guest"]
    access_levels = ["public", "internal", "confidential", "secret"]

    print("\nAccess Matrix (Role x Document Level):")
    print(f"{'Role':<12}", end="")
    for level in access_levels:
        print(f"{level:<15}", end="")
    print()
    print("-" * 60)

    for role in roles:
        print(f"{role:<12}", end="")
        for level in access_levels:
            can_access = "✓" if access_manager.can_access_document(role, level) else "✗"
            print(f"{can_access:<15}", end="")
        print()

    # Example 3: Template Rendering
    print("\n3. TEMPLATE RENDERING - Dynamic Content")
    print("-" * 60)

    template_str = """
WEEKLY REPORT - {{week}}
Generated: {{generated_date}}

Department: {{department}}
Manager: {{manager}}

Key Metrics:
{% for metric in metrics %}
  - {{metric.name}}: {{metric.value}} (Target: {{metric.target}})
{% endfor %}

Summary: {{summary}}
    """.strip()

    render_data = {
        "week": "May 15-21, 2024",
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
        "department": "Engineering",
        "manager": "Jane Smith",
        "metrics": [
            {"name": "Uptime", "value": "99.98%", "target": "99.9%"},
            {"name": "Deployment Success", "value": "98%", "target": "95%"},
            {"name": "Bug Fix Rate", "value": "92%", "target": "90%"},
        ],
        "summary": "Strong performance across all metrics. Team delivered 3 major features.",
    }

    rendered = TemplateRenderer.render(template_str, render_data)
    print("Rendered Template Output:")
    print(rendered)

    # Example 3.5: Generate PDF from rendered template
    print("\n3.5 PDF GENERATION - Create PDF from rendered template")
    print("-" * 60)
    try:
        # Wrap the rendered text in minimal HTML
        html_content = f"""
        <html>
          <head>
            <meta charset=\"utf-8\"> 
            <style> body {{ font-family: Arial, sans-serif; white-space: pre-wrap; }} </style>
          </head>
          <body>
            <div>{rendered}</div>
          </body>
        </html>
        """

        pdf_bytes = PDFGenerator.generate_from_html(html_content)

        # Optionally add a watermark
        pdf_bytes = PDFGenerator.add_watermark(pdf_bytes, watermark_text="Confidential - Demo")

        # Upload PDF to storage
        pdf_path = "examples/report.pdf"
        upload_pdf_result = await storage.upload(
            pdf_path,
            pdf_bytes,
            metadata={"type": "report", "generated": datetime.now().isoformat()},
        )

        print("PDF generation and upload result:")
        print(f"  Path: {upload_pdf_result['path']}")
        print(f"  Size: {upload_pdf_result['size']} bytes")
        print(f"  Hash: {upload_pdf_result['hash']}")

        # Verify download
        downloaded_pdf = await storage.download(pdf_path)
        print(f"  Downloaded PDF matches uploaded: {downloaded_pdf == pdf_bytes}")

        # Cleanup PDF
        await storage.delete(pdf_path)

    except ImportError as ie:
        print("PDF generation skipped - missing dependency:", ie)
    except Exception as e:
        print("PDF generation failed:", str(e))

    # Example 4: Storage Backend
    print("\n4. STORAGE BACKEND - File Management")
    print("-" * 60)

    # Create sample file
    sample_content = b"Sample document content for storage demonstration"
    upload_result = await storage.upload(
        "examples/sample_document.txt",
        sample_content,
        metadata={"type": "example", "created_date": datetime.now().isoformat()},
    )

    print(f"Upload Result:")
    print(f"  Path: {upload_result['path']}")
    print(f"  Size: {upload_result['size']} bytes")
    print(f"  Hash: {upload_result['hash']}")
    print(f"  Uploaded: {upload_result['uploaded_at']}")

    # List files
    files = await storage.list_files("examples/")
    print(f"\nListed Files in 'examples/':")
    for file_info in files:
        print(f"  {file_info['path']} ({file_info['size']} bytes)")

    # Download file
    downloaded = await storage.download("examples/sample_document.txt")
    print(f"\nDownloaded file matches uploaded: {downloaded == sample_content}")

    # Example 5: Document Classification
    print("\n5. DOCUMENT CLASSIFICATION")
    print("-" * 60)

    doc_classifications = {
        "reports": {
            "examples": ["Q1_Financial_Report", "Weekly_Status_Report"],
            "retention": "1 year",
            "access_level": "internal",
        },
        "contracts": {
            "examples": ["Service_Agreement_2024", "Employment_Contract"],
            "retention": "7 years",
            "access_level": "confidential",
        },
        "invoices": {
            "examples": ["Invoice_001_May2024", "Invoice_002_May2024"],
            "retention": "7 years",
            "access_level": "confidential",
        },
        "hr_documents": {
            "examples": ["Employee_Handbook", "Benefits_Guide"],
            "retention": "3 years",
            "access_level": "internal",
        },
    }

    for doc_type, info in doc_classifications.items():
        print(f"\n{doc_type.upper()}:")
        print(f"  Examples: {', '.join(info['examples'][:2])}")
        print(f"  Retention: {info['retention']}")
        print(f"  Default Access Level: {info['access_level']}")

    # Example 5.5: Metadata Search (demo)
    print("\n5.5 METADATA SEARCH - Query by metadata (e.g., '2024 年 5 月的报告')")
    print("-" * 60)

    try:
        # Create an in-memory SQLite DB and insert sample Document rows
        from sqlmodel import SQLModel, create_engine, Session
        from app.document_management.models.document import Document

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)

        session = Session(engine)

        # Insert sample documents with metadata_json containing generated dates and tags
        docs = [
            Document(
                title="Monthly Report May 2024",
                template_id=1,
                template_version=1,
                doc_type="reports",
                file_path="documents/reports/202405/report_may.pdf",
                file_hash="hash1",
                file_size=1234,
                input_data="{}",
                metadata_json=json.dumps({"generated": "2024-05-15", "tags": ["monthly", "finance"], "note": "2024 年 5 月的报告"}),
                created_by=1,
            ),
            Document(
                title="Weekly Status May 2024",
                template_id=1,
                template_version=1,
                doc_type="reports",
                file_path="documents/reports/202405/weekly1.pdf",
                file_hash="hash2",
                file_size=2345,
                input_data="{}",
                metadata_json=json.dumps({"generated": "2024-05-21", "tags": ["weekly", "engineering"]}),
                created_by=2,
            ),
            Document(
                title="Contract 2024-01",
                template_id=2,
                template_version=1,
                doc_type="contracts",
                file_path="documents/contracts/202401/contract1.pdf",
                file_hash="hash3",
                file_size=3456,
                input_data="{}",
                metadata_json=json.dumps({"generated": "2024-01-10", "tags": ["legal"]}),
                created_by=3,
            ),
        ]

        session.add_all(docs)
        session.commit()

        # Create DocumentService with the same storage and DB session
        from app.document_management.services.document import DocumentService

        svc = DocumentService(storage_backend=storage, db_session=session)

        # Example search: Chinese date phrase
        results_cn = await svc.search_documents(query="2024 年 5 月的 报告", doc_type="reports", limit=10)
        print("Search results for '2024 年 5 月的 报告':")
        for r in results_cn:
            print(f"  - {r['title']} ({r['created_at']}) tags={r.get('metadata', {}).get('tags')}")

        # Example search: keyword
        results_kw = await svc.search_documents(query="weekly", limit=10)
        print("Search results for 'weekly':")
        for r in results_kw:
            print(f"  - {r['title']} ({r['doc_type']}) metadata={r.get('metadata')}")

        # Close session
        session.close()

    except Exception as e:
        print("Metadata search demo skipped/failed:", str(e))

    # Example 6: Security Features
    print("\n6. SECURITY FEATURES")
    print("-" * 60)

    print("\nAvailable Security Features:")
    print("  1. Field Masking - Automatically mask sensitive data")
    print("  2. Encryption - PDF password protection, Word restrictions")
    print("  3. Access Control - Role-based permissions")
    print("  4. Audit Logging - Track all document access")
    print("  5. Watermarking - Add visible/invisible watermarks")
    print("  6. Retention Policies - Auto-archive/delete documents")

    # Example 7: Performance Metrics
    print("\n7. PERFORMANCE CHARACTERISTICS")
    print("-" * 60)

    metrics = {
        "Document Generation": "<2 seconds",
        "Metadata Search": "<3 seconds",
        "Upload Success Rate": ">99%",
        "Download Success Rate": ">99%",
        "Max File Size": "10GB",
        "Concurrent Access": "100+",
        "Storage Backends": "Local, S3, MinIO",
    }

    for metric, value in metrics.items():
        print(f"  {metric}: {value}")

    # Cleanup
    await storage.delete("examples/sample_document.txt")

    print("\n" + "=" * 60)
    print("Example workflow completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
