"""Enhanced WebSocket consumers for real-time features.

This module provides advanced WebSocket consumers for:
- Collaborative grade entry with conflict resolution
- Real-time dashboard metrics updates
- Live communication and messaging
- System-wide notifications and alerts
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Set

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache

logger = logging.getLogger(__name__)


class GradeEntryCollaborationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for collaborative grade entry with real-time conflict detection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_id = None
        self.user_id = None
        self.group_name = None
        self.active_users: Set[str] = set()

    async def connect(self):
        """Accept WebSocket connection and join grade entry room."""
        self.class_id = self.scope['url_route']['kwargs']['class_id']
        self.user_id = self.scope.get('user', {}).get('id', 'anonymous')
        self.group_name = f"grade_entry_{self.class_id}"

        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Track active user
        self.active_users.add(self.user_id)

        # Notify other users about new participant
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_joined',
                'user_id': self.user_id,
                'timestamp': datetime.now().isoformat()
            }
        )

        logger.info("Grade entry collaboration started for class %s by user %s", self.class_id, self.user_id)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.group_name:
            # Remove user from active set
            self.active_users.discard(self.user_id)

            # Notify other users about disconnection
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_left',
                    'user_id': self.user_id,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'grade_update':
                await self.handle_grade_update(data)
            elif message_type == 'field_lock':
                await self.handle_field_lock(data)
            elif message_type == 'field_unlock':
                await self.handle_field_unlock(data)
            elif message_type == 'cursor_position':
                await self.handle_cursor_position(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_grade_update(self, data: Dict[str, Any]):
        """Handle real-time grade updates with conflict detection."""
        student_id = data.get('student_id')
        assignment_id = data.get('assignment_id')
        new_value = data.get('value')
        field_name = data.get('field_name', 'score')

        # Check for conflicts
        lock_key = f"grade_lock_{self.class_id}_{student_id}_{assignment_id}_{field_name}"
        current_lock = cache.get(lock_key)

        conflict = False
        if current_lock and current_lock != self.user_id:
            conflict = True

        # Broadcast update to all users in the room
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'grade_entry_update',
                'student_id': student_id,
                'assignment_id': assignment_id,
                'field_name': field_name,
                'value': new_value,
                'updated_by': self.user_id,
                'timestamp': datetime.now().isoformat(),
                'conflict': conflict,
                'lock_status': 'locked' if current_lock else 'unlocked'
            }
        )

    async def handle_field_lock(self, data: Dict[str, Any]):
        """Handle field locking for collaborative editing."""
        student_id = data.get('student_id')
        assignment_id = data.get('assignment_id')
        field_name = data.get('field_name', 'score')

        lock_key = f"grade_lock_{self.class_id}_{student_id}_{assignment_id}_{field_name}"

        # Set lock with 30-second timeout
        cache.set(lock_key, self.user_id, 30)

        # Notify other users
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'field_locked',
                'student_id': student_id,
                'assignment_id': assignment_id,
                'field_name': field_name,
                'locked_by': self.user_id,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_field_unlock(self, data: Dict[str, Any]):
        """Handle field unlocking."""
        student_id = data.get('student_id')
        assignment_id = data.get('assignment_id')
        field_name = data.get('field_name', 'score')

        lock_key = f"grade_lock_{self.class_id}_{student_id}_{assignment_id}_{field_name}"
        cache.delete(lock_key)

        # Notify other users
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'field_unlocked',
                'student_id': student_id,
                'assignment_id': assignment_id,
                'field_name': field_name,
                'unlocked_by': self.user_id,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_cursor_position(self, data: Dict[str, Any]):
        """Handle cursor position updates for real-time collaboration."""
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'cursor_update',
                'user_id': self.user_id,
                'student_id': data.get('student_id'),
                'assignment_id': data.get('assignment_id'),
                'field_name': data.get('field_name'),
                'position': data.get('position'),
                'timestamp': datetime.now().isoformat()
            }
        )

    # Message handlers for group sends
    async def grade_entry_update(self, event):
        """Send grade update to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def field_locked(self, event):
        """Send field lock notification to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def field_unlocked(self, event):
        """Send field unlock notification to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def cursor_update(self, event):
        """Send cursor position update to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def user_joined(self, event):
        """Send user joined notification to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def user_left(self, event):
        """Send user left notification to WebSocket."""
        await self.send(text_data=json.dumps(event))


class DashboardMetricsConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time dashboard metrics updates."""

    async def connect(self):
        """Accept WebSocket connection for dashboard updates."""
        await self.channel_layer.group_add(
            "dashboard_metrics",
            self.channel_name
        )
        await self.accept()

        # Send initial metrics
        await self.send_metrics_update()

        logger.info("Dashboard metrics consumer connected")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        await self.channel_layer.group_discard(
            "dashboard_metrics",
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'request_update':
                await self.send_metrics_update()
            elif message_type == 'subscribe_to_metric':
                # Handle specific metric subscriptions
                metric_name = data.get('metric_name')
                await self.subscribe_to_metric(metric_name)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def send_metrics_update(self):
        """Send current dashboard metrics."""
        # Get cached metrics or generate fresh ones
        cache_key = "dashboard_metrics_realtime"
        metrics = cache.get(cache_key)

        if not metrics:
            # Generate mock metrics (in production, this would fetch real data)
            metrics = {
                'student_count': 1247,
                'active_enrollments': 890,
                'pending_payments': 23450.00,
                'system_health': 0.98,
                'last_updated': datetime.now().isoformat()
            }
            cache.set(cache_key, metrics, 300)  # Cache for 5 minutes

        await self.send(text_data=json.dumps({
            'type': 'metrics_update',
            'data': metrics,
            'timestamp': datetime.now().isoformat()
        }))

    async def subscribe_to_metric(self, metric_name: str):
        """Subscribe to specific metric updates."""
        # Add user to metric-specific group
        group_name = f"metric_{metric_name}"
        await self.channel_layer.group_add(group_name, self.channel_name)

        await self.send(text_data=json.dumps({
            'type': 'subscription_confirmed',
            'metric_name': metric_name,
            'timestamp': datetime.now().isoformat()
        }))

    # Message handlers
    async def metrics_broadcast(self, event):
        """Handle metrics broadcast from external triggers."""
        await self.send(text_data=json.dumps(event))


class CommunicationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time messaging and communication."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.user_id = None
        self.group_name = None

    async def connect(self):
        """Accept WebSocket connection for communication room."""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.user_id = self.scope.get('user', {}).get('id', 'anonymous')
        self.group_name = f"communication_{self.room_id}"

        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Notify room about new participant
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_joined_room',
                'user_id': self.user_id,
                'room_id': self.room_id,
                'timestamp': datetime.now().isoformat()
            }
        )

        logger.info("Communication consumer connected to room %s by user %s", self.room_id, self.user_id)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.group_name:
            # Notify room about user leaving
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_left_room',
                    'user_id': self.user_id,
                    'room_id': self.room_id,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'send_message':
                await self.handle_send_message(data)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'mark_read':
                await self.handle_mark_read(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def handle_send_message(self, data: Dict[str, Any]):
        """Handle sending a message to the room."""
        message_content = data.get('content', '')
        message_type = data.get('message_type', 'text')

        # Broadcast message to all room participants
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'new_message',
                'content': message_content,
                'message_type': message_type,
                'sender_id': self.user_id,
                'room_id': self.room_id,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_typing_indicator(self, data: Dict[str, Any]):
        """Handle typing indicator updates."""
        is_typing = data.get('is_typing', False)

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'typing_update',
                'user_id': self.user_id,
                'is_typing': is_typing,
                'room_id': self.room_id,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_mark_read(self, data: Dict[str, Any]):
        """Handle message read status updates."""
        message_id = data.get('message_id')

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'message_read',
                'user_id': self.user_id,
                'message_id': message_id,
                'room_id': self.room_id,
                'timestamp': datetime.now().isoformat()
            }
        )

    # Message handlers
    async def new_message(self, event):
        """Send new message to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def typing_update(self, event):
        """Send typing indicator update to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def message_read(self, event):
        """Send message read update to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def user_joined_room(self, event):
        """Send user joined notification to WebSocket."""
        await self.send(text_data=json.dumps(event))

    async def user_left_room(self, event):
        """Send user left notification to WebSocket."""
        await self.send(text_data=json.dumps(event))