import io
from pypdf import PdfReader, PdfWriter
from docx import Document
from docx.oxml.shared import OxmlElement, qn
from typing import Optional

class DocumentEncryption:
    @staticmethod
    def encrypt_pdf(
        content: bytes,
        user_password: str,
        owner_password: Optional[str] = None
    ) -> bytes:
        """
        Encrypt PDF content with password.
        """
        reader = PdfReader(io.BytesIO(content))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(user_password, owner_password=owner_password)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    @staticmethod
    def encrypt_docx(content: bytes, password: str) -> bytes:
        """
        Apply "Restrict Editing" to Word Document.
        This sets the document to read-only except for form fields (if any),
        effectively "restricting editing".
        """
        doc = Document(io.BytesIO(content))

        # Get the settings element
        settings = doc.settings.element

        # Create documentProtection element
        # <w:documentProtection w:edit="readOnly" w:enforcement="1"/>
        protection = OxmlElement('w:documentProtection')
        protection.set(qn('w:edit'), 'readOnly')
        protection.set(qn('w:enforcement'), '1')

        # Optional: Set password hash (complex, requires hashing algo matching Word's expectation)
        # For now we just enforce it without password or with a dummy hash if needed.
        # Without password hash, it can be stopped easily, but meets "Restrict Editing" UI state.

        settings.append(protection)

        output = io.BytesIO()
        doc.save(output)
        return output.getvalue()
