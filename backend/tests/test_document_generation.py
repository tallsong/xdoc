import unittest
import os
import shutil
import asyncio
from app.document_management.generators.template_renderer import TemplateRenderer
from app.document_management.generators.pdf_generator import PDFGenerator
from app.document_management.generators.word_generator import WordGenerator
from app.document_management.storage.local_storage import LocalStorage
from app.document_management.security.encryption import DocumentEncryption

class TestDocumentGeneration(unittest.TestCase):
    def setUp(self):
        self.test_dir = "./test_docs"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_template_renderer(self):
        print("\nTesting Template Renderer...")
        template = "Hello {{ name }}!"
        data = {"name": "World"}
        result = TemplateRenderer.render(template, data)
        self.assertEqual(result, "Hello World!")

    def test_pdf_generation(self):
        print("\nTesting PDF Generation...")
        html = "<h1>Hello World</h1>"
        pdf_bytes = PDFGenerator.generate_from_html(html)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Test Watermark
        watermarked = PDFGenerator.add_watermark(pdf_bytes, "TEST")
        self.assertTrue(len(watermarked) > len(pdf_bytes))

    def test_word_generation(self):
        print("\nTesting Word Generation...")
        # Create a simple docx template
        from docx import Document
        import io

        doc = Document()
        doc.add_paragraph("Hello {{name}}")

        buf = io.BytesIO()
        doc.save(buf)
        template_bytes = buf.getvalue()

        generated = WordGenerator.generate(template_bytes, {"name": "World"})
        self.assertTrue(len(generated) > 0)

    def test_local_storage(self):
        print("\nTesting Local Storage...")
        async def run_test():
            storage = LocalStorage(self.test_dir)
            await storage.upload("test.txt", b"content")

            exists = await storage.exists("test.txt")
            self.assertTrue(exists)

            content = await storage.download("test.txt")
            self.assertEqual(content, b"content")

            await storage.delete("test.txt")
            exists = await storage.exists("test.txt")
            self.assertFalse(exists)

        asyncio.run(run_test())

    def test_encryption(self):
        print("\nTesting Encryption...")
        # Create dummy PDF
        html = "<h1>Secret</h1>"
        pdf_bytes = PDFGenerator.generate_from_html(html)

        encrypted = DocumentEncryption.encrypt_pdf(pdf_bytes, "password")
        self.assertTrue(len(encrypted) > 0)
        # Verify it's different from original
        self.assertNotEqual(pdf_bytes, encrypted)

if __name__ == "__main__":
    unittest.main()
