#!/usr/bin/env python3
"""Test script for WebSocket connections."""

import asyncio
import json
import sys
import websockets
from datetime import datetime
from typing import Dict, Any


class WebSocketTester:
    """WebSocket endpoint tester."""

    def __init__(self, base_url: str = "ws://localhost:8000"):
        """Initialize WebSocket tester."""
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0

    async def test_connection(self, endpoint: str, test_name: str, test_messages: list = None):
        """Test WebSocket connection to an endpoint."""
        print(f"\n🔌 Testing: {test_name}")
        print(f"📡 Endpoint: {self.base_url}{endpoint}")

        try:
            self.tests_run += 1

            # Try to connect
            async with websockets.connect(f"{self.base_url}{endpoint}") as websocket:
                print(f"✅ Connection established")

                # Send test messages if provided
                if test_messages:
                    for message in test_messages:
                        print(f"📤 Sending: {message}")
                        await websocket.send(json.dumps(message))

                        # Wait for response with timeout
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            print(f"📥 Received: {response}")
                        except asyncio.TimeoutError:
                            print(f"⏰ No response within 5 seconds")

                print(f"✅ PASS - {test_name}")
                self.tests_passed += 1

        except websockets.exceptions.ConnectionClosed as e:
            print(f"❌ Connection closed: {e}")
            self.tests_failed += 1
        except websockets.exceptions.InvalidURI as e:
            print(f"❌ Invalid URI: {e}")
            self.tests_failed += 1
        except Exception as e:
            print(f"❌ FAIL - {test_name}: {e}")
            self.tests_failed += 1

    async def test_grade_collaboration(self):
        """Test grade collaboration WebSocket."""
        test_class_id = "550e8400-e29b-41d4-a716-446655440000"
        endpoint = f"/ws/v2/grades/collaboration/{test_class_id}/"

        test_messages = [
            {
                "action": "get_state"
            },
            {
                "action": "lock_cell",
                "cell_reference": "student_123_assignment_456"
            },
            {
                "action": "update_grade",
                "student_id": "550e8400-e29b-41d4-a716-446655440001",
                "assignment_id": "550e8400-e29b-41d4-a716-446655440002",
                "score": 85.5,
                "max_score": 100.0
            },
            {
                "action": "unlock_cell",
                "cell_reference": "student_123_assignment_456"
            }
        ]

        await self.test_connection(
            endpoint,
            "Enhanced Grade Collaboration WebSocket",
            test_messages
        )

    async def test_dashboard_metrics(self):
        """Test dashboard metrics WebSocket."""
        endpoint = "/ws/v2/dashboard/metrics/"

        test_messages = [
            {
                "action": "get_metrics"
            },
            {
                "action": "subscribe_metric",
                "metric_type": "student_count"
            }
        ]

        await self.test_connection(
            endpoint,
            "Real-time Dashboard Metrics WebSocket",
            test_messages
        )

    async def test_notifications(self):
        """Test notifications WebSocket."""
        endpoint = "/ws/v2/notifications/"

        test_messages = [
            {
                "action": "mark_read",
                "notification_id": "550e8400-e29b-41d4-a716-446655440003"
            }
        ]

        await self.test_connection(
            endpoint,
            "Real-time Notifications WebSocket",
            test_messages
        )

    async def test_legacy_endpoints(self):
        """Test legacy WebSocket endpoints for compatibility."""
        legacy_endpoints = [
            ("/ws/enrollment/", "Legacy Enrollment WebSocket"),
            ("/ws/attendance/", "Legacy Attendance WebSocket"),
            ("/ws/payments/", "Legacy Payments WebSocket"),
            ("/ws/grades/live-entry/550e8400-e29b-41d4-a716-446655440000/", "Legacy Grade Entry WebSocket"),
            ("/ws/dashboard/metrics/", "Legacy Dashboard Metrics WebSocket"),
            ("/ws/communications/test-room/", "Legacy Communications WebSocket"),
        ]

        for endpoint, test_name in legacy_endpoints:
            await self.test_connection(endpoint, test_name)

    async def test_connection_resilience(self):
        """Test WebSocket connection resilience and error handling."""
        print(f"\n🛡️ Testing Connection Resilience")

        # Test invalid endpoint
        await self.test_connection(
            "/ws/invalid/endpoint/",
            "Invalid Endpoint (should fail gracefully)"
        )

        # Test endpoint with invalid class ID
        await self.test_connection(
            "/ws/v2/grades/collaboration/invalid-id/",
            "Invalid Class ID (should handle errors)"
        )

    async def run_all_tests(self):
        """Run all WebSocket tests."""
        print("🚀 Starting WebSocket Tests")
        print("=" * 50)

        # Test enhanced v2 endpoints
        await self.test_grade_collaboration()
        await self.test_dashboard_metrics()
        await self.test_notifications()

        # Test legacy endpoints
        await self.test_legacy_endpoints()

        # Test error scenarios
        await self.test_connection_resilience()

        # Print summary
        print("\n" + "=" * 50)
        print("📊 WebSocket Test Summary")
        print("=" * 50)
        print(f"Tests run: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")

        if self.tests_failed == 0:
            print("\n🎉 All WebSocket tests passed!")
            return True
        else:
            print(f"\n⚠️  {self.tests_failed} WebSocket tests failed.")
            print("Note: Some failures may be expected (e.g., authentication required)")
            return False


async def main():
    """Main test function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "ws://localhost:8000"

    tester = WebSocketTester(base_url)

    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())