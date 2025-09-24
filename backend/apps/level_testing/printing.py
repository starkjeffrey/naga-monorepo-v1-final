"""Thermal printer integration for level testing applications.

Handles automatic receipt printing when students complete their applications.
Supports ESC/POS thermal printers via network, USB, or serial connection.
Includes QR code generation for application tracking and payment verification.
"""

import importlib.util
import io
import logging
from datetime import datetime

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Optional: Install python-escpos for direct thermal printing
try:
    from escpos.printer import Network, Serial, Usb

    ESCPOS_AVAILABLE = True
except ImportError:
    ESCPOS_AVAILABLE = False
    logger.warning("python-escpos not installed. Thermal printing unavailable.")

# QR Code generation libraries
try:
    import qrcode

    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("QR code libraries not installed. QR codes unavailable.")

# Check for alternative QR code library availability (segno was removed from dependencies)
SEGNO_AVAILABLE = importlib.util.find_spec("segno") is not None


def print_application_receipt(application) -> bool:
    """Print thermal receipt for completed application.

    Args:
        application: PotentialStudent instance

    Returns:
        bool: True if print successful, False otherwise
    """
    if not ESCPOS_AVAILABLE:
        logger.error("ESC/POS library not available")
        return False

    try:
        printer = get_thermal_printer()
        if not printer:
            return False

        # Print receipt content
        _print_receipt_content(printer, application)

        printer.close()
        logger.info(f"Receipt printed successfully for application {application.id}")
        return True

    except Exception as e:
        logger.error(f"Thermal printing failed for application {application.id}: {e}")
        return False


def get_thermal_printer():
    """Get configured thermal printer connection."""
    printer_config = getattr(settings, "THERMAL_PRINTER", {})
    printer_type = printer_config.get("TYPE", "network")

    try:
        if printer_type == "network":
            host = printer_config.get("HOST", "192.168.1.100")
            port = printer_config.get("PORT", 9100)
            return Network(host, port)

        elif printer_type == "usb":
            vendor_id = printer_config.get("VENDOR_ID", 0x04B8)
            product_id = printer_config.get("PRODUCT_ID", 0x0202)
            return Usb(vendor_id, product_id)

        elif printer_type == "serial":
            device = printer_config.get("DEVICE", "/dev/ttyUSB0")
            baudrate = printer_config.get("BAUDRATE", 9600)
            return Serial(device, baudrate)

        else:
            logger.error(f"Unknown printer type: {printer_type}")
            return None

    except Exception as e:
        logger.error(f"Failed to connect to {printer_type} printer: {e}")
        return None


def generate_application_qr_codes(application) -> tuple[bytes | None, bytes | None]:
    """Generate QR codes for application tracking and payment.

    Args:
        application: PotentialStudent instance

    Returns:
        tuple: (tracking_qr_bytes, payment_qr_bytes) or (None, None) if error
    """
    if not QR_AVAILABLE:
        logger.warning("QR code generation unavailable - missing libraries")
        return None, None

    try:
        # Generate application tracking URL
        base_url = getattr(settings, "BASE_URL", "http://localhost:8000")
        tracking_url = f"{base_url}/level-testing/status/{application.id}/"

        # Generate test number for payment reference
        test_number = generate_test_number(application)
        payment_info = (
            f"PUC Level Test Fee\n"
            f"Student: {application.personal_name_eng} {application.family_name_eng}\n"
            f"Test ID: {test_number}\n"
            f"Amount: $5.00 USD\n"
            f"Phone: {application.phone_number}"
        )

        # Create QR codes using qrcode library for better thermal printer compatibility
        qr_config = {
            "version": 1,  # Small size for thermal printers
            "error_correction": qrcode.constants.ERROR_CORRECT_M,
            "box_size": 10,
            "border": 4,
        }

        # Tracking QR Code
        tracking_qr = qrcode.QRCode(**qr_config)
        tracking_qr.add_data(tracking_url)
        tracking_qr.make(fit=True)

        tracking_img = tracking_qr.make_image(fill_color="black", back_color="white")
        tracking_buffer = io.BytesIO()
        tracking_img.save(tracking_buffer, format="PNG")
        tracking_bytes = tracking_buffer.getvalue()

        # Payment QR Code
        payment_qr = qrcode.QRCode(**qr_config)
        payment_qr.add_data(payment_info)
        payment_qr.make(fit=True)

        payment_img = payment_qr.make_image(fill_color="black", back_color="white")
        payment_buffer = io.BytesIO()
        payment_img.save(payment_buffer, format="PNG")
        payment_bytes = payment_buffer.getvalue()

        return tracking_bytes, payment_bytes

    except Exception as e:
        logger.error(f"QR code generation failed for application {application.id}: {e}")
        return None, None


def _print_receipt_content(printer, application):
    """Print the actual receipt content to thermal printer."""
    # Generate QR codes first
    tracking_qr, payment_qr = generate_application_qr_codes(application)

    # Header
    printer.set(align="center", text_type="B", width=2, height=2)
    printer.text("PUC ENGLISH\n")
    printer.text("LEVEL TESTING\n")
    printer.text("=" * 32 + "\n")

    # Reset formatting
    printer.set(align="left", text_type="normal", width=1, height=1)

    # Application details
    test_number = generate_test_number(application)
    printer.text(f"Application: #{application.id:06d}\n")
    printer.text(f"Test Number: {test_number}\n")
    printer.text(f"Date: {timezone.now().strftime('%d/%m/%Y %H:%M')}\n")
    printer.text("-" * 32 + "\n")

    # Student information
    printer.text("STUDENT INFORMATION:\n")
    printer.text(f"Name: {application.personal_name_eng}\n")
    printer.text(f"      {application.family_name_eng}\n")

    if application.personal_name_khm:
        printer.text(f"Khmer: {application.personal_name_khm}\n")
        printer.text(f"       {application.family_name_khm}\n")

    printer.text(f"Phone: {application.phone_number}\n")

    if application.personal_email:
        printer.text(f"Email: {application.personal_email}\n")

    printer.text(f"DOB: {application.date_of_birth}\n")
    printer.text("-" * 32 + "\n")

    # Program preferences
    printer.text("PROGRAM PREFERENCES:\n")
    printer.text(f"Program: {application.get_preferred_program_display()}\n")
    printer.text(f"Schedule: {application.get_preferred_time_slot_display()}\n")

    if application.preferred_start_term:
        printer.text(f"Start: {application.preferred_start_term}\n")

    printer.text("-" * 32 + "\n")

    # Education background
    if application.current_study_status:
        printer.text("EDUCATION:\n")
        printer.text(f"Status: {application.get_current_study_status_display()}\n")

        if application.current_high_school:
            printer.text(f"School: {application.get_current_high_school_display()}\n")
            if application.current_grade:
                printer.text(f"Grade: {application.current_grade}\n")

        if application.current_university:
            printer.text(f"University: {application.get_current_university_display()}\n")

        if application.work_field:
            printer.text(f"Work: {application.get_work_field_display()}\n")

        printer.text("-" * 32 + "\n")

    # Test fee information
    printer.set(text_type="B")
    printer.text("TEST FEE REQUIRED:\n")
    printer.set(text_type="normal")
    printer.text("Amount: $5.00 USD\n")
    printer.text("Pay at: PUC English Office\n")
    printer.text("-" * 32 + "\n")

    # Next steps
    printer.text("NEXT STEPS:\n")
    printer.text("1. Bring this receipt\n")
    printer.text("2. Pay $5.00 test fee\n")
    printer.text("3. Schedule test appointment\n")
    printer.text("4. Take placement test\n")
    printer.text("-" * 32 + "\n")

    # Contact information
    printer.text("PUC English Office\n")
    printer.text("Pannasastra University\n")
    printer.text("Siem Reap Campus\n")
    printer.text("Tel: +855 XX XXX XXX\n")
    printer.text("\n")

    # QR Codes Section
    printer.text("\n")
    printer.set(align="center", text_type="B")
    printer.text("QR CODES:\n")
    printer.set(text_type="normal")

    # Application Status QR Code
    if tracking_qr:
        printer.text("Scan to check status:\n")
        try:
            printer.image(tracking_qr)
        except Exception as e:
            logger.warning(f"Failed to print tracking QR code: {e}")
            printer.text("(QR code generation failed)\n")
        printer.text("\n")

    # Payment Information QR Code
    if payment_qr:
        printer.text("Payment Information:\n")
        try:
            printer.image(payment_qr)
        except Exception as e:
            logger.warning(f"Failed to print payment QR code: {e}")
            printer.text("(QR code generation failed)\n")
        printer.text("\n")

    # Footer
    printer.set(align="center")
    printer.text("Thank you for applying!\n")
    printer.text("Good luck with your test!\n")
    printer.text("\n")

    # Cut paper
    printer.cut()


def test_printer_connection() -> bool:
    """Test thermal printer connection.

    Returns:
        bool: True if printer responds, False otherwise
    """
    if not ESCPOS_AVAILABLE:
        logger.error("ESC/POS library not available for testing")
        return False

    try:
        printer = get_thermal_printer()
        if not printer:
            return False

        # Print test page
        printer.text("=== PRINTER TEST ===\n")
        printer.text(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        printer.text("Connection: OK\n")
        printer.text("Ready for printing!\n\n")
        printer.cut()
        printer.close()

        logger.info("Printer test successful")
        return True

    except Exception as e:
        logger.error(f"Printer test failed: {e}")
        return False


def generate_test_number(application) -> str:
    """Generate unique test number for application.

    Args:
        application: PotentialStudent instance

    Returns:
        str: Formatted test number (e.g., "LT-2025-001234")
    """
    current_year = timezone.now().year
    return f"LT-{current_year}-{application.id:06d}"


# NEW: Test Completion Printing Functions


def print_completion_slip(completion) -> bool:
    """Print thermal receipt for completed test with internal code and QR code.

    Args:
        completion: TestCompletion instance

    Returns:
        bool: True if print successful, False otherwise
    """
    try:
        # Mock mode for development (console output)
        if getattr(settings, "THERMAL_PRINTER_MOCK", True):
            _print_completion_to_console(completion)
            return True

        # Real thermal printer
        if not ESCPOS_AVAILABLE:
            logger.error("ESC/POS library not available for completion slip printing")
            return False

        printer = get_thermal_printer()
        if not printer:
            return False

        # Print completion slip content
        _print_completion_slip_content(printer, completion)

        printer.close()
        logger.info(f"Completion slip printed successfully for code {completion.internal_code}")
        return True

    except Exception as e:
        logger.error(f"Completion slip printing failed for {completion.internal_code}: {e}")
        return False


def generate_completion_qr_code(completion) -> bytes | None:
    """Generate QR code for test completion tracking.

    Args:
        completion: TestCompletion instance

    Returns:
        bytes: QR code image as PNG bytes, or None if error
    """
    if not QR_AVAILABLE:
        logger.warning("QR code generation unavailable - missing libraries")
        return None

    try:
        # Get the full URL from QR code data
        qr_url = completion.qr_code_data.get("full_url", completion.qr_code_data.get("url", ""))

        if not qr_url:
            logger.error(f"No QR URL available for completion {completion.internal_code}")
            return None

        # Create QR code optimized for thermal printing
        qr_config = {
            "version": 1,
            "error_correction": qrcode.constants.ERROR_CORRECT_M,
            "box_size": 6,  # Smaller for completion slips
            "border": 2,
        }

        qr = qrcode.QRCode(**qr_config)
        qr.add_data(qr_url)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")

        return buffer.getvalue()

    except Exception as e:
        logger.error(f"QR code generation failed for completion {completion.internal_code}: {e}")
        return None


def _print_completion_to_console(completion):
    """Print completion slip to console for development."""
    student = completion.test_attempt.potential_student
    test_date = completion.test_attempt.completed_at
    qr_url = completion.qr_code_data.get("full_url", "No URL")

    slip_content = f"""
{"=" * 50}
THERMAL PRINTER SIMULATION - COMPLETION SLIP
{"=" * 50}

{"=" * 32}
PANNASASTRA UNIVERSITY CAMBODIA
Level Testing Completion
{"=" * 32}

Student: {completion.student_full_name_eng}
Test: {completion.external_test_number} ({student.preferred_program})
Date: {test_date.strftime("%b %d, %Y %I:%M %p") if test_date else "N/A"}

Internal Code: {completion.internal_code}

Please keep this slip for:
• Payment processing
• Results notification
• Telegram registration

QR Code URL: {qr_url}

[QR CODE WOULD BE PRINTED HERE]

{"=" * 32}
Thank you for taking the test!
Please proceed to finance office
for payment processing.
{"=" * 32}

Printed: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
{"=" * 50}
"""
    logger.debug(f"Slip content:\n{slip_content}")


def _print_completion_slip_content(printer, completion):
    """Print the actual completion slip content to thermal printer."""
    student = completion.test_attempt.potential_student
    test_date = completion.test_attempt.completed_at

    # Generate QR code
    qr_bytes = generate_completion_qr_code(completion)

    # Header
    printer.set(align="center", text_type="B", width=2, height=2)
    printer.text("PUC ENGLISH\n")
    printer.text("TEST COMPLETED\n")
    printer.set(text_type="normal", width=1, height=1)
    printer.text("=" * 32 + "\n")

    # Reset formatting
    printer.set(align="left")

    # Test completion details
    printer.text(f"Student: {completion.student_full_name_eng}\n")
    printer.text(f"Test: {completion.external_test_number}\n")
    printer.text(f"Program: {student.preferred_program}\n")
    if test_date:
        printer.text(f"Date: {test_date.strftime('%b %d, %Y %I:%M %p')}\n")
    printer.text("-" * 32 + "\n")

    # Internal tracking code
    printer.set(text_type="B")
    printer.text(f"Internal Code: {completion.internal_code}\n")
    printer.set(text_type="normal")
    printer.text("-" * 32 + "\n")

    # Next steps
    printer.text("NEXT STEPS:\n")
    printer.text("1. Keep this slip safe\n")
    printer.text("2. Go to finance office\n")
    printer.text("3. Pay any required fees\n")
    printer.text("4. Wait for test results\n")
    printer.text("5. Register for classes\n")
    printer.text("-" * 32 + "\n")

    # QR Code Section
    printer.set(align="center", text_type="B")
    printer.text("QR CODE:\n")
    printer.set(text_type="normal")
    printer.text("Scan for digital access\n")

    if qr_bytes:
        try:
            printer.image(qr_bytes)
        except Exception as e:
            logger.warning(f"Failed to print QR code: {e}")
            printer.text("(QR code print failed)\n")
        printer.text("\n")
    else:
        printer.text("QR code unavailable\n\n")

    # Manual code for backup
    printer.set(align="center")
    printer.text(f"Manual Code: {completion.internal_code}\n")
    printer.text("\n")

    # Footer
    printer.text("Thank you!\n")
    printer.text("Good luck with your studies!\n")
    printer.text("\n")

    # Cut paper
    printer.cut()
