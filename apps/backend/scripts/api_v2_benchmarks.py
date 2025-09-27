#!/usr/bin/env python3
"""API v2 Performance Benchmarking Script.

This script provides comprehensive performance testing for the Staff-Web V2 API
including response times, throughput, cache effectiveness, and real-time features.
"""

import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Tuple
import requests
import websocket
import threading
from dataclasses import dataclass
from uuid import uuid4

# Configuration
BASE_URL = "http://localhost:8000/api/v2"
WS_BASE_URL = "ws://localhost:8000/ws"
AUTH_TOKEN = "mock-jwt-token-for-testing"  # Replace with actual token
CONCURRENT_USERS = 10
TEST_DURATION = 60  # seconds


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    endpoint: str
    method: str
    response_times: List[float]
    success_count: int
    error_count: int
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float  # requests per second
    cache_hit_ratio: float = 0.0


class APIBenchmarker:
    """Comprehensive API performance benchmarker."""

    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def benchmark_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        iterations: int = 100
    ) -> BenchmarkResult:
        """Benchmark a single API endpoint."""
        response_times = []
        success_count = 0
        error_count = 0

        print(f"Benchmarking {method} {endpoint} ({iterations} iterations)...")

        for i in range(iterations):
            start_time = time.time()

            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                elif method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", json=data)
                elif method == "PUT":
                    response = self.session.put(f"{self.base_url}{endpoint}", json=data)
                elif method == "DELETE":
                    response = self.session.delete(f"{self.base_url}{endpoint}")

                response_time = time.time() - start_time
                response_times.append(response_time)

                if response.status_code < 400:
                    success_count += 1
                else:
                    error_count += 1
                    print(f"  Error {response.status_code}: {response.text[:100]}")

            except Exception as e:
                error_count += 1
                response_time = time.time() - start_time
                response_times.append(response_time)
                print(f"  Exception: {str(e)[:100]}")

            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{iterations}")

        # Calculate statistics
        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = self._percentile(response_times, 95)
            p99_time = self._percentile(response_times, 99)
            total_time = sum(response_times)
            throughput = iterations / total_time if total_time > 0 else 0
        else:
            avg_time = median_time = p95_time = p99_time = throughput = 0

        return BenchmarkResult(
            endpoint=endpoint,
            method=method,
            response_times=response_times,
            success_count=success_count,
            error_count=error_count,
            avg_response_time=avg_time,
            median_response_time=median_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            throughput=throughput
        )

    def benchmark_concurrent_load(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict = None,
        concurrent_users: int = 10,
        duration: int = 30
    ) -> BenchmarkResult:
        """Benchmark endpoint under concurrent load."""
        print(f"Load testing {method} {endpoint} with {concurrent_users} concurrent users for {duration}s...")

        results = []
        start_time = time.time()

        def worker():
            """Worker function for concurrent requests."""
            worker_results = []
            while time.time() - start_time < duration:
                request_start = time.time()
                try:
                    if method == "GET":
                        response = self.session.get(f"{self.base_url}{endpoint}")
                    elif method == "POST":
                        response = self.session.post(f"{self.base_url}{endpoint}", json=data)

                    response_time = time.time() - request_start
                    worker_results.append({
                        'response_time': response_time,
                        'status_code': response.status_code,
                        'success': response.status_code < 400
                    })
                except Exception as e:
                    response_time = time.time() - request_start
                    worker_results.append({
                        'response_time': response_time,
                        'status_code': 0,
                        'success': False,
                        'error': str(e)
                    })
            return worker_results

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(concurrent_users)]
            for future in futures:
                results.extend(future.result())

        # Aggregate results
        response_times = [r['response_time'] for r in results]
        success_count = sum(1 for r in results if r['success'])
        error_count = len(results) - success_count

        if response_times:
            avg_time = statistics.mean(response_times)
            median_time = statistics.median(response_times)
            p95_time = self._percentile(response_times, 95)
            p99_time = self._percentile(response_times, 99)
            throughput = len(results) / duration
        else:
            avg_time = median_time = p95_time = p99_time = throughput = 0

        return BenchmarkResult(
            endpoint=endpoint,
            method=method,
            response_times=response_times,
            success_count=success_count,
            error_count=error_count,
            avg_response_time=avg_time,
            median_response_time=median_time,
            p95_response_time=p95_time,
            p99_response_time=p99_time,
            throughput=throughput
        )

    def benchmark_cache_effectiveness(self, endpoint: str, iterations: int = 50) -> float:
        """Test cache effectiveness by measuring response time improvements."""
        print(f"Testing cache effectiveness for {endpoint}...")

        # First request (cache miss)
        start_time = time.time()
        response = self.session.get(f"{self.base_url}{endpoint}")
        first_request_time = time.time() - start_time

        if response.status_code >= 400:
            print(f"  Cache test failed: {response.status_code}")
            return 0.0

        # Subsequent requests (should be cached)
        cached_times = []
        for i in range(iterations):
            start_time = time.time()
            response = self.session.get(f"{self.base_url}{endpoint}")
            cached_times.append(time.time() - start_time)

        avg_cached_time = statistics.mean(cached_times)
        improvement_ratio = (first_request_time - avg_cached_time) / first_request_time

        print(f"  First request: {first_request_time:.4f}s")
        print(f"  Avg cached: {avg_cached_time:.4f}s")
        print(f"  Improvement: {improvement_ratio:.2%}")

        return max(0, improvement_ratio)

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


class WebSocketBenchmarker:
    """WebSocket performance benchmarker."""

    def __init__(self, ws_base_url: str):
        self.ws_base_url = ws_base_url
        self.results = []

    def benchmark_websocket_latency(self, endpoint: str, message_count: int = 100) -> Dict:
        """Benchmark WebSocket message latency."""
        print(f"Benchmarking WebSocket latency for {endpoint}...")

        latencies = []
        messages_sent = 0
        messages_received = 0
        errors = 0

        def on_message(ws, message):
            nonlocal messages_received
            messages_received += 1
            try:
                data = json.loads(message)
                if 'timestamp' in data:
                    sent_time = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                    receive_time = datetime.now()
                    latency = (receive_time - sent_time).total_seconds()
                    latencies.append(latency)
            except Exception as e:
                print(f"  Error processing message: {e}")

        def on_error(ws, error):
            nonlocal errors
            errors += 1
            print(f"  WebSocket error: {error}")

        def on_open(ws):
            print("  WebSocket connection opened")

            def send_messages():
                nonlocal messages_sent
                for i in range(message_count):
                    test_message = {
                        'type': 'test_message',
                        'id': i,
                        'timestamp': datetime.now().isoformat()
                    }
                    ws.send(json.dumps(test_message))
                    messages_sent += 1
                    time.sleep(0.1)  # 100ms between messages

            threading.Thread(target=send_messages).start()

        # Create WebSocket connection
        ws_url = f"{self.ws_base_url}/{endpoint}/"
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_open=on_open
        )

        # Run for limited time
        ws.run_forever()

        return {
            'endpoint': endpoint,
            'messages_sent': messages_sent,
            'messages_received': messages_received,
            'errors': errors,
            'latencies': latencies,
            'avg_latency': statistics.mean(latencies) if latencies else 0,
            'p95_latency': WebSocketBenchmarker._percentile(latencies, 95) if latencies else 0
        }

    @staticmethod
    def _percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]


def run_comprehensive_benchmarks():
    """Run comprehensive API v2 performance benchmarks."""
    print("=" * 60)
    print("API v2 Performance Benchmark Suite")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Duration: {TEST_DURATION}s")
    print(f"Concurrent Users: {CONCURRENT_USERS}")
    print("=" * 60)

    benchmarker = APIBenchmarker(BASE_URL, AUTH_TOKEN)
    results = []

    # Core API endpoints to benchmark
    endpoints_to_test = [
        # Student API
        ("/students/search/", "GET"),
        ("/students/bulk-actions/", "POST"),

        # Innovation API
        ("/innovation/ai/predictions/", "POST"),
        ("/innovation/automation/workflows/", "GET"),
        ("/innovation/analytics/custom/dashboard/", "GET"),
        ("/innovation/communications/threads/", "GET"),

        # Academic API
        ("/academics/grades/spreadsheet/test-class-id/", "GET"),

        # Finance API
        ("/finance/pos/transaction/", "POST"),
        ("/finance/analytics/", "GET"),

        # System endpoints
        ("/health/", "GET"),
        ("/info/", "GET")
    ]

    # 1. Basic Performance Tests
    print("\n1. BASIC PERFORMANCE TESTS")
    print("-" * 40)

    for endpoint, method in endpoints_to_test:
        test_data = None
        if method == "POST":
            if "predictions" in endpoint:
                test_data = {
                    "model_type": "success_prediction",
                    "input_data": {"student_id": str(uuid4())},
                    "confidence_threshold": 0.7
                }
            elif "bulk-actions" in endpoint:
                test_data = {
                    "action": "update_status",
                    "target_ids": [str(uuid4())],
                    "parameters": {"status": "active"},
                    "dry_run": True
                }
            elif "pos" in endpoint:
                test_data = {
                    "amount": "100.00",
                    "payment_method": "cash",
                    "description": "Test payment"
                }

        try:
            result = benchmarker.benchmark_endpoint(endpoint, method, test_data, 50)
            results.append(result)
            print(f"✓ {method} {endpoint}: {result.avg_response_time:.3f}s avg, {result.throughput:.1f} req/s")
        except Exception as e:
            print(f"✗ {method} {endpoint}: Failed - {e}")

    # 2. Load Testing
    print("\n2. LOAD TESTING")
    print("-" * 40)

    critical_endpoints = [
        ("/students/search/", "GET"),
        ("/innovation/analytics/custom/dashboard/", "GET"),
        ("/health/", "GET")
    ]

    for endpoint, method in critical_endpoints:
        try:
            load_result = benchmarker.benchmark_concurrent_load(
                endpoint, method, None, CONCURRENT_USERS, 30
            )
            results.append(load_result)
            print(f"✓ Load test {method} {endpoint}: {load_result.throughput:.1f} req/s, {load_result.p95_response_time:.3f}s P95")
        except Exception as e:
            print(f"✗ Load test {method} {endpoint}: Failed - {e}")

    # 3. Cache Effectiveness Tests
    print("\n3. CACHE EFFECTIVENESS")
    print("-" * 40)

    cacheable_endpoints = [
        "/students/search/",
        "/innovation/analytics/custom/dashboard/",
        "/innovation/automation/workflows/"
    ]

    for endpoint in cacheable_endpoints:
        try:
            cache_ratio = benchmarker.benchmark_cache_effectiveness(endpoint, 20)
            print(f"✓ Cache test {endpoint}: {cache_ratio:.1%} improvement")
        except Exception as e:
            print(f"✗ Cache test {endpoint}: Failed - {e}")

    # 4. WebSocket Performance (if available)
    print("\n4. WEBSOCKET PERFORMANCE")
    print("-" * 40)

    ws_benchmarker = WebSocketBenchmarker(WS_BASE_URL)
    websocket_endpoints = [
        "dashboard/metrics",
        # Note: Other WS endpoints require specific parameters
    ]

    for ws_endpoint in websocket_endpoints:
        try:
            # Note: WebSocket tests are more complex and may need running server
            print(f"○ WebSocket {ws_endpoint}: Test configured (requires active server)")
        except Exception as e:
            print(f"✗ WebSocket {ws_endpoint}: Failed - {e}")

    # 5. Results Summary
    print("\n" + "=" * 60)
    print("BENCHMARK RESULTS SUMMARY")
    print("=" * 60)

    # Performance targets
    targets = {
        'students/search': 0.3,  # 300ms
        'analytics': 0.5,        # 500ms
        'ai/predictions': 2.0,   # 2s (first call)
        'health': 0.1,           # 100ms
        'info': 0.1              # 100ms
    }

    print(f"{'Endpoint':<40} {'Avg Time':<12} {'P95 Time':<12} {'Throughput':<12} {'Status'}")
    print("-" * 80)

    for result in results:
        # Determine target
        target = 1.0  # Default 1s
        for key, val in targets.items():
            if key in result.endpoint:
                target = val
                break

        # Status check
        status = "✓ PASS" if result.avg_response_time <= target else "✗ FAIL"

        print(f"{result.endpoint:<40} {result.avg_response_time:.3f}s{'':<6} "
              f"{result.p95_response_time:.3f}s{'':<6} {result.throughput:.1f} req/s{'':<4} {status}")

    # Overall health assessment
    print("\n" + "=" * 60)
    print("PERFORMANCE ASSESSMENT")
    print("=" * 60)

    passing_tests = sum(1 for r in results if r.avg_response_time <= 1.0)  # Simplified check
    total_tests = len(results)
    success_rate = (passing_tests / total_tests * 100) if total_tests > 0 else 0

    print(f"Passing Tests: {passing_tests}/{total_tests} ({success_rate:.1f}%)")

    if success_rate >= 80:
        print("🟢 Overall Performance: EXCELLENT")
    elif success_rate >= 60:
        print("🟡 Overall Performance: GOOD")
    else:
        print("🔴 Overall Performance: NEEDS IMPROVEMENT")

    # Recommendations
    print("\nRECOMMENDations:")
    slow_endpoints = [r for r in results if r.avg_response_time > 1.0]
    if slow_endpoints:
        print("• Optimize slow endpoints:")
        for endpoint in slow_endpoints[:3]:  # Top 3 slowest
            print(f"  - {endpoint.endpoint} ({endpoint.avg_response_time:.3f}s)")

    print("• Implement Redis caching for frequently accessed data")
    print("• Consider database query optimization")
    print("• Monitor real-world usage patterns")

    return results


if __name__ == "__main__":
    # Run benchmarks
    results = run_comprehensive_benchmarks()

    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"benchmark_results_{timestamp}.json"

    # Convert results to JSON-serializable format
    json_results = []
    for result in results:
        json_results.append({
            'endpoint': result.endpoint,
            'method': result.method,
            'avg_response_time': result.avg_response_time,
            'median_response_time': result.median_response_time,
            'p95_response_time': result.p95_response_time,
            'p99_response_time': result.p99_response_time,
            'throughput': result.throughput,
            'success_count': result.success_count,
            'error_count': result.error_count
        })

    with open(filename, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_config': {
                'base_url': BASE_URL,
                'concurrent_users': CONCURRENT_USERS,
                'test_duration': TEST_DURATION
            },
            'results': json_results
        }, f, indent=2)

    print(f"\nDetailed results saved to: {filename}")