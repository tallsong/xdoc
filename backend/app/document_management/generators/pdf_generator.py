import io
from weasyprint import HTML, CSS
from typing import Optional, Dict, Any
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from pypdf import PdfReader, PdfWriter
import logging

logger = logging.getLogger(__name__)

class PDFGenerator:
    @staticmethod
    def generate_from_html(html_content: str, css_content: Optional[str] = None) -> bytes:
        """
        Generate PDF from HTML using WeasyPrint.
        """
        try:
            font_config = None
            # Check for CJK fonts if needed, but for now standard

            html = HTML(string=html_content)
            css = [CSS(string=css_content)] if css_content else []

            # Generate PDF to bytes
            doc = html.render(stylesheets=css)
            output = io.BytesIO()
            doc.write_pdf(output)
            return output.getvalue()

        except Exception as e:
            logger.error(f"PDF Generation failed: {e}")
            raise e

    @staticmethod
    def add_watermark(pdf_content: bytes, watermark_text: str) -> bytes:
        """
        Add watermark to existing PDF content.
        """
        # Create watermark PDF
        packet = io.BytesIO()
        # Use ReportLab to create a watermark
        c = canvas.Canvas(packet, pagesize=A4)
        c.setFont("Helvetica", 50)
        c.setFillColorRGB(0.5, 0.5, 0.5, 0.5)  # Grey, semi-transparent
        c.saveState()
        c.translate(300, 400)
        c.rotate(45)
        c.drawCentredString(0, 0, watermark_text)
        c.restoreState()
        c.save()

        packet.seek(0)
        watermark_pdf = PdfReader(packet)
        watermark_page = watermark_pdf.pages[0]

        # Read original PDF
        original_pdf = PdfReader(io.BytesIO(pdf_content))
        writer = PdfWriter()

        # Merge
        for page in original_pdf.pages:
            page.merge_page(watermark_page)
            writer.add_page(page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
