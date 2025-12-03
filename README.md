# XDoc - Intelligent Document Management System

XDoc is a comprehensive structured document generation, management, and vector search system. It is designed to handle enterprise needs for standardized document creation, secure storage, controlled retrieval, and intelligent search using vector embeddings.

The project is composed of two main modules:
- **Backend**: A robust FastAPI application handling document logic, storage, and vector search.
- **Frontend**: A modern web interface for interacting with the system.

## Key Features

- **Document Management**:
  - Template CRUD and versioning.
  - Document generation from templates (PDF, Word, HTML).
  - Secure storage (Local, S3, MinIO).
  - Role-Based Access Control (RBAC) and Field Masking.
- **Vector Search**:
  - Integration with ChromaDB, Pinecone, and Weaviate.
  - Semantic search capabilities using Sentence Transformers.
- **Security**:
  - Encryption for sensitive documents.
  - Detailed audit logging.

## Architecture

### Backend
The backend is built with **FastAPI** and utilizes:
- **Database**: PostgreSQL (with SQLModel).
- **Storage**: Abstracted storage layer supporting Local Filesystem, AWS S3, and MinIO.
- **Vector Store**: Interface for multiple vector databases.
- **Document Generation**: Jinja2 for templating, WeasyPrint for PDF, python-docx for Word.

For a detailed architecture diagram, see [backend/ARCHITECTURE_DIAGRAM.md](backend/ARCHITECTURE_DIAGRAM.md).

### Frontend
The frontend is a Node.js-based application (Vite ecosystem) providing a user-friendly interface to:
- Manage templates.
- Generate and view documents.
- Perform semantic searches.

## Deployment & Installation

### Prerequisites
- **Docker** and **Docker Compose** (optional but recommended for full stack)
- **Python 3.10+** (managed via `uv` recommended)
- **Node.js 18+** (for frontend)

### Quick Start (Docker Compose)

If a `docker-compose.yml` is present in the root or backend directory, you can start the full stack with:

```bash
docker compose up -d
```

*(Note: If running from the backend directory, refer to `backend/README.md` for specific Docker instructions).*

### Manual Installation

#### Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Install Dependencies:**
   We recommend using [uv](https://docs.astral.sh/uv/) for fast dependency management:
   ```bash
   uv sync
   source .venv/bin/activate
   ```
   Alternatively, using pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   Create a `.env` file based on `.env.example` (if available) or configure your database and storage settings.

4. **Run the Server:**
   ```bash
   # Development mode
   fastapi run app/main.py --reload
   ```
   The API will be available at `http://localhost:8000`.
   API Documentation: `http://localhost:8000/docs`.

5. **Run Examples:**
   ```bash
   # Vector Store Example
   python -m app.vector_store.example

   # Document Management Example
   python examples/document_management_example.py
   ```

#### Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install Dependencies:**
   ```bash
   npm install
   ```

3. **Configure Environment:**
   Ensure `.env` is configured correctly (e.g., `VITE_API_URL=http://localhost:8000`).

4. **Run Development Server:**
   ```bash
   npm run dev
   ```
   The frontend is typically accessible at `http://localhost:5173`.

## Documentation

- **Backend Architecture**: [backend/ARCHITECTURE_DIAGRAM.md](backend/ARCHITECTURE_DIAGRAM.md)
- **Document Spec**: [backend/DOCUMENT_MANAGEMENT_SPEC.md](backend/DOCUMENT_MANAGEMENT_SPEC.md)
- **Backend Readme**: [backend/README.md](backend/README.md)

## Contributing

Please ensure you follow the code style and run tests before submitting PRs.
- **Backend Tests**: Run `bash scripts/test.sh` inside the `backend/` directory.
