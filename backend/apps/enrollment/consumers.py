"""WebSocket consumers for enrollment real-time updates."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class EnrollmentConsumer(AsyncWebsocketConsumer):
    """Consumer for enrollment real-time updates."""

    async def connect(self):
        """Handle WebSocket connection."""
        # Check if user is authenticated
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return

        # Add to enrollment group
        await self.channel_layer.group_add("enrollment_updates", self.channel_name)

        await self.accept()
        logger.info(f"User {self.scope['user'].email} connected to enrollment updates")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from enrollment group
        await self.channel_layer.group_discard("enrollment_updates", self.channel_name)

        if self.scope["user"] != AnonymousUser():
            logger.info(f"User {self.scope['user'].email} disconnected from enrollment updates")

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
    async def enrollment_update(self, event):
        """Send enrollment update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "enrollment_update",
                    "action": event["action"],  # 'created', 'updated', 'deleted'
                    "enrollment_id": event["enrollment_id"],
                    "class_id": event.get("class_id"),
                    "student_id": event.get("student_id"),
                    "seats_available": event.get("seats_available"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def seat_count_update(self, event):
        """Send seat count update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "seat_count_update",
                    "class_id": event["class_id"],
                    "seats_available": event["seats_available"],
                    "total_seats": event["total_seats"],
                    "enrolled_count": event["enrolled_count"],
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def waitlist_update(self, event):
        """Send waitlist update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "waitlist_update",
                    "class_id": event["class_id"],
                    "waitlist_position": event.get("waitlist_position"),
                    "student_id": event.get("student_id"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )
