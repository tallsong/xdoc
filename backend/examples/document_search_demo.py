"""Document metadata search demo CLI.

Usage:
    source .venv/bin/activate
    python examples/document_search_demo.py "2024 年 5 月的 报告"

This script creates an in-memory SQLite DB, inserts sample Document rows with
`metadata_json`, instantiates the DocumentService with a local storage backend
and runs `search_documents` with the provided query, printing results.
"""

import sys
import json
import asyncio
from datetime import datetime

from sqlmodel import SQLModel, create_engine, Session

from app.document_management.storage import StorageFactory
from app.document_management.models.document import Document
from app.document_management.services.document import DocumentService


async def run(query: str):
    # Create a simple local storage (files not used by this demo)
    storage = StorageFactory.get_backend(backend_type="local", base_path="/tmp/xdoc_demo_cli")

    # In-memory DB
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    session = Session(engine)

    # Insert sample documents
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

    svc = DocumentService(storage_backend=storage, db_session=session)

    # Run search
    results = await svc.search_documents(query=query, limit=20)

    print(f"Search results for: '{query}'\n")
    if not results:
        print("  (no results)")
    else:
        for r in results:
            title = r.get("title")
            created_at = r.get("created_at")
            tags = r.get("metadata", {}).get("tags")
            print(f"  - {title} | created_at={created_at} | tags={tags}")

    session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/document_search_demo.py \"query string\"")
        sys.exit(1)

    query_arg = sys.argv[1]
    asyncio.run(run(query_arg))
