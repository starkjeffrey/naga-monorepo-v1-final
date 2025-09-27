"""WebSocket consumers for attendance real-time updates."""

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class AttendanceConsumer(AsyncWebsocketConsumer):
    """Consumer for attendance real-time updates."""

    async def connect(self):
        """Handle WebSocket connection."""
        # Check if user is authenticated
        if self.scope["user"] == AnonymousUser():
            await self.close()
            return

        # Add to attendance group
        await self.channel_layer.group_add("attendance_updates", self.channel_name)

        await self.accept()
        logger.info(f"User {self.scope['user'].email} connected to attendance updates")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Remove from attendance group
        await self.channel_layer.group_discard("attendance_updates", self.channel_name)

        if self.scope["user"] != AnonymousUser():
            logger.info(f"User {self.scope['user'].email} disconnected from attendance updates")

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
    async def attendance_update(self, event):
        """Send attendance update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "attendance_update",
                    "action": event["action"],  # 'marked', 'updated', 'deleted'
                    "student_id": event["student_id"],
                    "class_id": event.get("class_id"),
                    "session_id": event.get("session_id"),
                    "status": event.get("status"),  # 'present', 'absent', 'late', 'excused'
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def session_update(self, event):
        """Send attendance session update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "session_update",
                    "session_id": event["session_id"],
                    "class_id": event["class_id"],
                    "status": event["status"],  # 'active', 'completed', 'cancelled'
                    "present_count": event.get("present_count"),
                    "total_count": event.get("total_count"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )

    async def bulk_attendance_update(self, event):
        """Send bulk attendance update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "bulk_attendance_update",
                    "session_id": event["session_id"],
                    "class_id": event["class_id"],
                    "updated_count": event["updated_count"],
                    "present_count": event.get("present_count"),
                    "timestamp": event.get("timestamp"),
                }
            )
        )
