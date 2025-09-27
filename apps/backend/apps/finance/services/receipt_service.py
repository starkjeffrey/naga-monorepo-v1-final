"""Receipt service for generating receipts in various formats.

Handles receipt generation for payments with proper formatting
and multi-language support.
"""

from io import BytesIO

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.finance.models import Payment


class ReceiptService:
    """Service for generating receipts in various formats.

    Handles receipt generation for payments with proper formatting
    and multi-language support.
    """

    @staticmethod
    def generate_pdf_receipt(payment: Payment) -> HttpResponse:
        """Generate a PDF receipt for a payment.

        Args:
            payment: Payment instance

        Returns:
            HttpResponse with PDF content
        """
        buffer = BytesIO()

        # Create PDF with A4 size (common in Cambodia)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
        )

        # Container for PDF elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#003366"),
            spaceAfter=6,
            alignment=TA_CENTER,
        )

        # Header
        elements.append(Paragraph("Pannasastra University of Cambodia", title_style))
        elements.append(Paragraph("Siem Reap Campus", styles["Heading2"]))
        elements.append(Spacer(1, 0.25 * inch))

        # Receipt title
        receipt_title = ParagraphStyle(
            "ReceiptTitle",
            parent=styles["Heading2"],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        elements.append(Paragraph("PAYMENT RECEIPT", receipt_title))
        elements.append(Spacer(1, 0.25 * inch))

        # Receipt details
        receipt_data = [
            ["Receipt Number:", payment.payment_reference],
            ["Date:", payment.payment_date.strftime("%B %d, %Y")],
            ["Time:", payment.processed_date.strftime("%I:%M %p")],
        ]

        receipt_table = Table(receipt_data, colWidths=[2 * inch, 4 * inch])
        receipt_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ],
            ),
        )
        elements.append(receipt_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Student information
        student = payment.invoice.student
        student_data = [
            ["Student Name:", str(student)],
            ["Student ID:", student.student_id],
            [
                "Program:",
                (student.get_current_program_display() if hasattr(student, "get_current_program_display") else "N/A"),
            ],
        ]

        student_table = Table(student_data, colWidths=[2 * inch, 4 * inch])
        student_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f0f0")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ],
            ),
        )
        elements.append(student_table)
        elements.append(Spacer(1, 0.25 * inch))

        # Payment details
        payment_data = [
            ["Payment Method:", payment.get_payment_method_display()],
            ["Amount Paid:", f"${payment.amount:,.2f} {payment.currency}"],
            ["Reference:", payment.external_reference or "N/A"],
        ]

        if payment.notes:
            payment_data.append(["Notes:", payment.notes])

        payment_table = Table(payment_data, colWidths=[2 * inch, 4 * inch])
        payment_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ],
            ),
        )
        elements.append(payment_table)
        elements.append(Spacer(1, 0.5 * inch))

        # Footer
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.grey,
        )

        elements.append(Paragraph(f"Processed by: {payment.processed_by}", footer_style))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("Thank you for your payment!", footer_style))

        # Build PDF
        doc.build(elements)

        # Return response
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="receipt_{payment.payment_reference}.pdf"'

        return response

    @staticmethod
    def generate_email_receipt(payment: Payment) -> str:
        """Generate an HTML email receipt.

        Args:
            payment: Payment instance

        Returns:
            HTML string for email
        """
        student = payment.invoice.student

        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; }}
                .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .details {{ background-color: #f0f0f0; padding: 15px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; }}
                table {{ width: 100%; }}
                td {{ padding: 5px; }}
                .label {{ font-weight: bold; width: 150px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Pannasastra University of Cambodia</h1>
                <h2>Payment Receipt</h2>
            </div>
            <div class="content">
                <p>Dear {student.person.personal_name},</p>
                <p>Thank you for your payment. Please find your receipt details below:</p>

                <div class="details">
                    <table>
                        <tr>
                            <td class="label">Receipt Number:</td>
                            <td>{payment.payment_reference}</td>
                        </tr>
                        <tr>
                            <td class="label">Date:</td>
                            <td>{payment.payment_date.strftime("%B %d, %Y")}</td>
                        </tr>
                        <tr>
                            <td class="label">Amount:</td>
                            <td>${payment.amount:,.2f} {payment.currency}</td>
                        </tr>
                        <tr>
                            <td class="label">Payment Method:</td>
                            <td>{payment.get_payment_method_display()}</td>
                        </tr>
                    </table>
                </div>

                <p>If you have any questions, please contact the finance office.</p>
            </div>
            <div class="footer">
                <p>This is an automated receipt. Please do not reply to this email.</p>
                <p>&copy; {timezone.now().year} Pannasastra University of Cambodia</p>
            </div>
        </body>
        </html>
        """

        return html
