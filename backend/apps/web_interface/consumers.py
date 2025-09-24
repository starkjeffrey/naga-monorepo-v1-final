"""WebSocket consumers for real-time updates."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for general notifications and system updates."""

    async def connect(self):
        """Handle WebSocket connection."""
        # Check if user is authenticated
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return

        # Add to notification group
        self.user_group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        # Add to general notifications group
        await self.channel_layer.group_add("notifications", self.channel_name)

        await self.accept()
        logger.info(f"User {self.scope['user'].email} connected to notifications")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from notification groups
        if hasattr(self, "user_group_name"):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

        await self.channel_layer.group_discard("notifications", self.channel_name)

        if self.scope["user"] != AnonymousUser():
            logger.info(f"User {self.scope['user'].email} disconnected from notifications")

    async def receive(self, text_data):
        """Handle messages from WebSocket."""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get("type")

            if message_type == "ping":
                # Send pong response
                await self.send(text_data=json.dumps({"type": "pong", "timestamp": text_data_json.get("timestamp")}))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {text_data}")

    # Message handlers
    async def notification_message(self, event):
        """Send notification to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "message": event["message"],
                    "level": event.get("level", "info"),
                    "timestamp": event.get("timestamp"),
                    "user_id": event.get("user_id"),
                }
            )
        )

    async def system_message(self, event):
        """Send system message to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "system",
                    "message": event["message"],
                    "level": event.get("level", "info"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def user_message(self, event):
        """Send user-specific message to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "user_message",
                    "message": event["message"],
                    "level": event.get("level", "info"),
                    "timestamp": event.get("timestamp"),
                    "data": event.get("data", {}),
                }
            )
        )
