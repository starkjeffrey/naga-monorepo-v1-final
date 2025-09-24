"""WebSocket consumers for payment real-time updates."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class PaymentConsumer(AsyncWebsocketConsumer):
    """Consumer for payment real-time updates."""

    async def connect(self):
        """Handle WebSocket connection."""
        # Check if user is authenticated
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return

        # Add to payment updates group
        await self.channel_layer.group_add("payment_updates", self.channel_name)

        await self.accept()
        logger.info(f"User {self.scope['user'].email} connected to payment updates")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from payment group
        await self.channel_layer.group_discard("payment_updates", self.channel_name)

        if self.scope["user"] != AnonymousUser():
            logger.info(f"User {self.scope['user'].email} disconnected from payment updates")

    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            if message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong", "timestamp": text_data_json.get("timestamp")}))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    # Message handlers
    async def payment_update(self, event):
        """Send payment update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "payment_update",
                    "action": event["action"],  # 'created', 'updated', 'cancelled', 'refunded'
                    "payment_id": event["payment_id"],
                    "invoice_id": event.get("invoice_id"),
                    "student_id": event.get("student_id"),
                    "amount": str(event.get("amount", 0)),
                    "status": event.get("status"),
                    "payment_method": event.get("payment_method"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def invoice_update(self, event):
        """Send invoice update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "invoice_update",
                    "action": event["action"],  # 'created', 'updated', 'paid', 'overdue'
                    "invoice_id": event["invoice_id"],
                    "student_id": event.get("student_id"),
                    "total_amount": str(event.get("total_amount", 0)),
                    "paid_amount": str(event.get("paid_amount", 0)),
                    "balance": str(event.get("balance", 0)),
                    "status": event.get("status"),
                    "due_date": event.get("due_date"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def balance_update(self, event):
        """Send balance update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "balance_update",
                    "student_id": event["student_id"],
                    "current_balance": str(event["current_balance"]),
                    "previous_balance": str(event.get("previous_balance", 0)),
                    "change_amount": str(event.get("change_amount", 0)),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def cashier_update(self, event):
        """Send cashier session update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "cashier_update",
                    "session_id": event["session_id"],
                    "action": event["action"],  # 'opened', 'closed', 'payment_processed'
                    "total_processed": str(event.get("total_processed", 0)),
                    "transaction_count": event.get("transaction_count", 0),
                    "timestamp": event.get("timestamp"),
                }
            )
        )
