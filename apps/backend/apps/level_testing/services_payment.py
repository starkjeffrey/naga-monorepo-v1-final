"""Payment-first workflow services for level testing.

This module contains services for the payment-first workflow including:
- Telegram bot integration for verification
- Thermal printer service for receipts
- QR code generation service
"""

import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for Telegram bot integration.

    Handles sending verification codes and managing Telegram
    user registration for test notifications.
    """

    def __init__(self):
        self.bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "PUCLevelTestBot")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"

    def send_verification_code(self, phone: str, code: str, student_name: str) -> bool:
        """Send verification code via Telegram.

        Args:
            phone: Student's phone number
            code: 6-digit verification code
            student_name: Student's name for personalization

        Returns:
            True if code was sent successfully
        """
        try:
            # In production, this would integrate with actual Telegram Bot API
            # For now, we'll simulate the sending
            logger.info(f"Sending Telegram verification code {code} to {phone} for {student_name}")

            # Simulate sending message via Telegram Bot API

            # TODO: Implement actual Telegram Bot API call
            # Example:
            # import requests
            # response = requests.post(
            #     f"{self.api_url}/sendMessage",
            #     json={
            #         'chat_id': chat_id,  # Need to get chat_id from phone
            #         'text': message,
            #         'parse_mode': 'Markdown'
            #     }
            # )
            # return response.status_code == 200

            return True  # Simulated success

        except Exception as e:
            logger.exception(f"Error sending Telegram verification: {e}")
            return False

    def get_user_info(self, phone: str) -> dict | None:
        """Get Telegram user info by phone number.

        Args:
            phone: User's phone number

        Returns:
            Dictionary with user info or None if not found
        """
        try:
            # In production, this would look up the user by phone
            # For now, return simulated data
            logger.info(f"Looking up Telegram user for phone: {phone}")

            # TODO: Implement actual user lookup
            # This might involve:
            # 1. Looking up chat history for users who shared contact
            # 2. Using a database of registered users
            # 3. Using Telegram's contact import API

            # Simulated response
            return {
                "id": "123456789",
                "username": "student_user",
                "first_name": "Student",
                "last_name": "User",
                "phone": phone,
            }

        except Exception as e:
            logger.exception(f"Error getting Telegram user info: {e}")
            return None

    def send_test_reminder(self, telegram_id: str, test_date, location: str) -> bool:
        """Send test reminder to student.

        Args:
            telegram_id: Student's Telegram ID
            test_date: Scheduled test date
            location: Test location

        Returns:
            True if reminder was sent successfully
        """
        try:
            (
                f"📅 *Level Test Reminder*\n\n"
                f"Your test is scheduled for:\n"
                f"📆 Date: {test_date.strftime('%B %d, %Y')}\n"
                f"🕐 Time: {test_date.strftime('%I:%M %p')}\n"
                f"📍 Location: {location}\n\n"
                f"Please arrive 15 minutes early.\n"
                f"Don't forget to bring your ID!"
            )

            # TODO: Implement actual message sending
            logger.info(f"Sending test reminder to Telegram ID: {telegram_id}")

            return True

        except Exception as e:
            logger.exception(f"Error sending test reminder: {e}")
            return False

    def send_test_results(self, telegram_id: str, score: int, level: str) -> bool:
        """Send test results to student.

        Args:
            telegram_id: Student's Telegram ID
            score: Test score
            level: Recommended level

        Returns:
            True if results were sent successfully
        """
        try:
            # TODO: Implement actual message sending
            logger.info(f"Sending test results to Telegram ID: {telegram_id}")

            return True

        except Exception as e:
            logger.exception(f"Error sending test results: {e}")
            return False


class ThermalPrinterService:
    """Service for thermal printer integration.

    Handles printing receipts with QR codes for the payment-first workflow.
    """

    def __init__(self):
        self.printer_ip = getattr(settings, "THERMAL_PRINTER_IP", "192.168.1.100")
        self.printer_port = getattr(settings, "THERMAL_PRINTER_PORT", 9100)
        self.enabled = getattr(settings, "THERMAL_PRINTER_ENABLED", False)

    def print_payment_receipt(self, token, qr_image_bytes: bytes) -> bool:
        """Print payment receipt with QR code.

        Args:
            token: TestAccessToken instance
            qr_image_bytes: QR code image as bytes

        Returns:
            True if receipt was printed successfully
        """
        try:
            if not self.enabled:
                logger.info("Thermal printer is disabled, skipping print")
                return False

            # In production, this would send to actual thermal printer
            # Using ESC/POS commands for thermal printers

            receipt_text = self._format_receipt(token)

            # TODO: Implement actual thermal printer communication
            # Example using python-escpos:
            # from escpos.printer import Network
            # printer = Network(self.printer_ip, self.printer_port)
            # printer.text(receipt_text)
            # printer.image(qr_image_bytes)
            # printer.cut()
            # printer.close()

            logger.info(f"Printing receipt for access code: {token.access_code}")
            logger.debug(f"Receipt text:\n{receipt_text}")

            return True

        except Exception as e:
            logger.exception(f"Error printing receipt: {e}")
            return False

    def _format_receipt(self, token) -> str:
        """Format receipt text for thermal printer.

        Args:
            token: TestAccessToken instance

        Returns:
            Formatted receipt text
        """
        receipt = []
        receipt.append("=" * 40)
        receipt.append("     PUC LEVEL TESTING RECEIPT")
        receipt.append("=" * 40)
        receipt.append("")
        receipt.append(f"Date: {timezone.now().strftime('%Y-%m-%d %H:%M')}")
        receipt.append(f"Access Code: {token.access_code}")
        receipt.append("")
        receipt.append("STUDENT INFORMATION:")
        receipt.append(f"Name: {token.student_name}")
        receipt.append(f"Phone: {token.student_phone}")
        receipt.append("")
        receipt.append("PAYMENT DETAILS:")
        receipt.append(f"Amount: ${token.payment_amount}")
        receipt.append(f"Method: {token.get_payment_method_display()}")
        receipt.append(f"Cashier: {token.cashier.get_full_name()}")
        receipt.append("")
        receipt.append("INSTRUCTIONS:")
        receipt.append("1. Scan QR code with your phone")
        receipt.append("2. Complete application form online")
        receipt.append("3. Bring this receipt to test")
        receipt.append("")
        receipt.append("QR CODE:")
        receipt.append("[QR code printed below]")
        receipt.append("")
        receipt.append("-" * 40)
        receipt.append("Thank you for choosing PUC!")
        receipt.append("For support: +855 23 123 456")
        receipt.append("=" * 40)

        return "\n".join(receipt)

    def print_test_slip(self, student_name: str, test_number: str, test_date, location: str) -> bool:
        """Print test appointment slip.

        Args:
            student_name: Student's name
            test_number: Test number
            test_date: Test date and time
            location: Test location

        Returns:
            True if slip was printed successfully
        """
        try:
            if not self.enabled:
                return False

            slip_text = []
            slip_text.append("=" * 40)
            slip_text.append("    PUC LEVEL TEST APPOINTMENT")
            slip_text.append("=" * 40)
            slip_text.append("")
            slip_text.append(f"Student: {student_name}")
            slip_text.append(f"Test Number: {test_number}")
            slip_text.append("")
            slip_text.append("TEST DETAILS:")
            slip_text.append(f"Date: {test_date.strftime('%B %d, %Y')}")
            slip_text.append(f"Time: {test_date.strftime('%I:%M %p')}")
            slip_text.append(f"Location: {location}")
            slip_text.append("")
            slip_text.append("IMPORTANT:")
            slip_text.append("• Arrive 15 minutes early")
            slip_text.append("• Bring this slip")
            slip_text.append("• Bring photo ID")
            slip_text.append("")
            slip_text.append("=" * 40)

            logger.info(f"Printing test slip for: {student_name}")

            # TODO: Send to actual printer

            return True

        except Exception as e:
            logger.exception(f"Error printing test slip: {e}")
            return False
