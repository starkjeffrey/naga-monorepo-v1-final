"""Enhanced WebSocket consumers for real-time collaboration and live updates."""

import json
import logging
from typing import Dict, Any
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from apps.scheduling.models import ClassHeader
from apps.people.models import StudentProfile
from apps.grading.models import Grade, Assignment
from apps.enrollment.models import ClassHeaderEnrollment

logger = logging.getLogger(__name__)


class EnhancedGradeEntryCollaborationConsumer(AsyncWebsocketConsumer):
    """Enhanced real-time collaborative grade entry with conflict resolution."""

    async def connect(self):
        """Handle WebSocket connection."""
        self.class_id = self.scope['url_route']['kwargs']['class_id']
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Join class-specific room
        self.room_group_name = f'grade_collaboration_{self.class_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Add user to active users list
        await self.add_active_user()

        # Send current collaboration state
        await self.send_collaboration_state()

        # Notify other users about new participant
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'user_name': self.user.get_full_name() or self.user.username,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            # Remove user from active users
            await self.remove_active_user()

            # Unlock any cells locked by this user
            await self.unlock_user_cells()

            # Notify other users about departure
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user_id': str(self.user.id),
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'lock_cell':
                await self.handle_lock_cell(data)
            elif action == 'unlock_cell':
                await self.handle_unlock_cell(data)
            elif action == 'update_grade':
                await self.handle_update_grade(data)
            elif action == 'cursor_move':
                await self.handle_cursor_move(data)
            elif action == 'bulk_update':
                await self.handle_bulk_update(data)
            elif action == 'get_state':
                await self.send_collaboration_state()
            else:
                await self.send_error(f"Unknown action: {action}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON data")
        except Exception as e:
            logger.error("Error handling WebSocket message: %s", e)
            await self.send_error("Internal server error")

    async def handle_lock_cell(self, data: Dict[str, Any]):
        """Handle cell locking request."""
        cell_ref = data.get('cell_reference')
        if not cell_ref:
            await self.send_error("Missing cell_reference")
            return

        # Check if cell is already locked
        lock_key = f"cell_lock:{self.class_id}:{cell_ref}"
        existing_lock = await self.get_cache_value(lock_key)

        if existing_lock and existing_lock != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'lock_failed',
                'cell_reference': cell_ref,
                'locked_by': existing_lock,
                'message': 'Cell is already locked by another user'
            }))
            return

        # Acquire lock
        await self.set_cache_value(lock_key, str(self.user.id), 300)  # 5-minute lock

        # Notify all users about the lock
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'cell_locked',
                'cell_reference': cell_ref,
                'user_id': str(self.user.id),
                'user_name': self.user.get_full_name() or self.user.username,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_unlock_cell(self, data: Dict[str, Any]):
        """Handle cell unlocking request."""
        cell_ref = data.get('cell_reference')
        if not cell_ref:
            await self.send_error("Missing cell_reference")
            return

        # Release lock
        lock_key = f"cell_lock:{self.class_id}:{cell_ref}"
        await self.delete_cache_value(lock_key)

        # Notify all users about the unlock
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'cell_unlocked',
                'cell_reference': cell_ref,
                'user_id': str(self.user.id),
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_update_grade(self, data: Dict[str, Any]):
        """Handle grade update with real-time broadcast."""
        try:
            student_id = data.get('student_id')
            assignment_id = data.get('assignment_id')
            score = data.get('score')
            max_score = data.get('max_score')

            if not all([student_id, assignment_id]):
                await self.send_error("Missing required fields")
                return

            # Update grade in database
            grade_data = await self.update_grade_db(
                student_id, assignment_id, score, max_score
            )

            if grade_data:
                # Broadcast update to all connected users
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'grade_updated',
                        'student_id': student_id,
                        'assignment_id': assignment_id,
                        'score': score,
                        'max_score': max_score,
                        'updated_by': str(self.user.id),
                        'updated_by_name': self.user.get_full_name() or self.user.username,
                        'timestamp': datetime.now().isoformat(),
                        'grade_id': str(grade_data['grade_id'])
                    }
                )

                # Send success confirmation to sender
                await self.send(text_data=json.dumps({
                    'type': 'update_success',
                    'student_id': student_id,
                    'assignment_id': assignment_id,
                    'grade_id': str(grade_data['grade_id'])
                }))
            else:
                await self.send_error("Failed to update grade")

        except Exception as e:
            logger.error("Grade update error: %s", e)
            await self.send_error("Grade update failed")

    async def handle_cursor_move(self, data: Dict[str, Any]):
        """Handle cursor movement for real-time user awareness."""
        cell_ref = data.get('cell_reference')

        # Broadcast cursor position to other users
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'cursor_moved',
                'cell_reference': cell_ref,
                'user_id': str(self.user.id),
                'user_name': self.user.get_full_name() or self.user.username,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def handle_bulk_update(self, data: Dict[str, Any]):
        """Handle bulk grade updates."""
        updates = data.get('updates', [])

        if not updates:
            await self.send_error("No updates provided")
            return

        success_count = 0
        failed_updates = []

        for update in updates:
            try:
                grade_data = await self.update_grade_db(
                    update.get('student_id'),
                    update.get('assignment_id'),
                    update.get('score'),
                    update.get('max_score')
                )
                if grade_data:
                    success_count += 1
                else:
                    failed_updates.append(update)
            except Exception as e:
                logger.error("Bulk update error for item %s: %s", update, e)
                failed_updates.append(update)

        # Broadcast bulk update completion
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'bulk_update_completed',
                'success_count': success_count,
                'failed_count': len(failed_updates),
                'updated_by': str(self.user.id),
                'updated_by_name': self.user.get_full_name() or self.user.username,
                'timestamp': datetime.now().isoformat()
            }
        )

    # Event handlers for group messages
    async def user_joined(self, event):
        """Handle user joined event."""
        await self.send(text_data=json.dumps({
            'type': 'user_joined',
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'timestamp': event['timestamp']
        }))

    async def user_left(self, event):
        """Handle user left event."""
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))

    async def cell_locked(self, event):
        """Handle cell locked event."""
        await self.send(text_data=json.dumps({
            'type': 'cell_locked',
            'cell_reference': event['cell_reference'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'timestamp': event['timestamp']
        }))

    async def cell_unlocked(self, event):
        """Handle cell unlocked event."""
        await self.send(text_data=json.dumps({
            'type': 'cell_unlocked',
            'cell_reference': event['cell_reference'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))

    async def grade_updated(self, event):
        """Handle grade updated event."""
        # Don't send update back to the user who made the change
        if event['updated_by'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'grade_updated',
                'student_id': event['student_id'],
                'assignment_id': event['assignment_id'],
                'score': event['score'],
                'max_score': event['max_score'],
                'updated_by': event['updated_by'],
                'updated_by_name': event['updated_by_name'],
                'timestamp': event['timestamp'],
                'grade_id': event['grade_id']
            }))

    async def cursor_moved(self, event):
        """Handle cursor moved event."""
        # Don't send cursor position back to the user who moved it
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'cursor_moved',
                'cell_reference': event['cell_reference'],
                'user_id': event['user_id'],
                'user_name': event['user_name'],
                'timestamp': event['timestamp']
            }))

    async def bulk_update_completed(self, event):
        """Handle bulk update completed event."""
        await self.send(text_data=json.dumps({
            'type': 'bulk_update_completed',
            'success_count': event['success_count'],
            'failed_count': event['failed_count'],
            'updated_by': event['updated_by'],
            'updated_by_name': event['updated_by_name'],
            'timestamp': event['timestamp']
        }))

    # Helper methods
    async def send_error(self, message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }))

    async def send_collaboration_state(self):
        """Send current collaboration state to client."""
        state = await self.get_collaboration_state()
        await self.send(text_data=json.dumps({
            'type': 'collaboration_state',
            'state': state,
            'timestamp': datetime.now().isoformat()
        }))

    async def add_active_user(self):
        """Add user to active users list."""
        key = f"active_users:{self.class_id}"
        active_users = await self.get_cache_value(key, [])
        if str(self.user.id) not in active_users:
            active_users.append(str(self.user.id))
            await self.set_cache_value(key, active_users, 1800)

    async def remove_active_user(self):
        """Remove user from active users list."""
        key = f"active_users:{self.class_id}"
        active_users = await self.get_cache_value(key, [])
        if str(self.user.id) in active_users:
            active_users.remove(str(self.user.id))
            await self.set_cache_value(key, active_users, 1800)

    async def unlock_user_cells(self):
        """Unlock all cells locked by this user."""
        # This would require scanning cache keys, which is expensive
        # In production, consider using a separate data structure
        pass

    async def get_collaboration_state(self) -> Dict[str, Any]:
        """Get current collaboration state."""
        active_users_key = f"active_users:{self.class_id}"
        active_users = await self.get_cache_value(active_users_key, [])

        return {
            'class_id': self.class_id,
            'active_users': active_users,
            'user_count': len(active_users)
        }

    @database_sync_to_async
    def update_grade_db(self, student_id: str, assignment_id: str, score: float, max_score: float):
        """Update grade in database."""
        try:
            enrollment = ClassHeaderEnrollment.objects.get(
                student_profile__unique_id=student_id,
                class_header__unique_id=self.class_id
            )
            assignment = Assignment.objects.get(unique_id=assignment_id)

            grade, created = Grade.objects.get_or_create(
                class_header_enrollment=enrollment,
                assignment=assignment,
                defaults={
                    'score': score,
                    'max_score': max_score
                }
            )

            if not created:
                grade.score = score
                grade.max_score = max_score
                grade.save()

            return {'grade_id': grade.unique_id}

        except Exception as e:
            logger.error("Database grade update failed: %s", e)
            return None

    @database_sync_to_async
    def get_cache_value(self, key: str, default=None):
        """Get value from cache."""
        return cache.get(key, default)

    @database_sync_to_async
    def set_cache_value(self, key: str, value, timeout: int):
        """Set value in cache."""
        return cache.set(key, value, timeout)

    @database_sync_to_async
    def delete_cache_value(self, key: str):
        """Delete value from cache."""
        return cache.delete(key)


class RealTimeDashboardConsumer(AsyncWebsocketConsumer):
    """Real-time dashboard metrics consumer."""

    async def connect(self):
        """Handle WebSocket connection for dashboard."""
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Join dashboard metrics room
        self.room_group_name = 'dashboard_metrics'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial metrics
        await self.send_dashboard_metrics()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'get_metrics':
                await self.send_dashboard_metrics()
            elif action == 'subscribe_metric':
                metric_type = data.get('metric_type')
                await self.subscribe_to_metric(metric_type)
            else:
                await self.send_error(f"Unknown action: {action}")

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON data")

    async def send_dashboard_metrics(self):
        """Send current dashboard metrics."""
        metrics = await self.get_dashboard_metrics()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_metrics',
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }))

    async def metrics_updated(self, event):
        """Handle metrics updated event."""
        await self.send(text_data=json.dumps({
            'type': 'metrics_updated',
            'metric_type': event['metric_type'],
            'value': event['value'],
            'timestamp': event['timestamp']
        }))

    async def subscribe_to_metric(self, metric_type: str):
        """Subscribe to specific metric updates."""
        # Store subscription preferences
        pass

    @database_sync_to_async
    def get_dashboard_metrics(self):
        """Get current dashboard metrics from database."""
        # Implementation would calculate real-time metrics
        return {
            'total_students': StudentProfile.objects.count(),
            'total_classes': ClassHeader.objects.count(),
            'active_enrollments': ClassHeaderEnrollment.objects.filter(status='enrolled').count(),
            'last_updated': datetime.now().isoformat()
        }

    async def send_error(self, message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notification consumer."""

    async def connect(self):
        """Handle WebSocket connection for notifications."""
        self.user = self.scope.get('user')

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # Join user-specific notification room
        self.room_group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)

        except json.JSONDecodeError:
            await self.send_error("Invalid JSON data")

    async def notification_received(self, event):
        """Handle new notification event."""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
            'timestamp': event['timestamp']
        }))

    async def mark_notification_read(self, notification_id: str):
        """Mark notification as read."""
        # Implementation would mark notification as read
        pass

    async def send_error(self, message: str):
        """Send error message to client."""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }))