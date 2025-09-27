"""
Performance and Load Testing Suite for Staff-Web V2
Comprehensive performance validation and benchmarking
"""

import asyncio
import time
import statistics
import concurrent.futures
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TestResult:
    """Data class to store test results."""
    endpoint: str
    method: str
    response_time: float
    status_code: int
    success: bool
    error_message: str = None
    payload_size: int = 0


@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    base_url: str = "http://localhost:8000"
    auth_token: str = ""
    concurrent_users: int = 10
    requests_per_user: int = 5
    ramp_up_time: int = 10  # seconds
    test_duration: int = 60  # seconds


class PerformanceTester:
    """Main performance testing class."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.headers = {
            "Authorization": f"Bearer {config.auth_token}",
            "Content-Type": "application/json"
        }

    def make_request(self, method: str, endpoint: str, data: Dict = None) -> TestResult:
        """Make a single HTTP request and measure performance."""
        url = f"{self.config.base_url}{endpoint}"
        start_time = time.time()

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds

            return TestResult(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=response.status_code,
                success=200 <= response.status_code < 300,
                payload_size=len(response.content)
            )

        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            return TestResult(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                status_code=0,
                success=False,
                error_message=str(e)
            )

    def run_single_user_test(self, user_id: int) -> List[TestResult]:
        """Run tests for a single user."""
        user_results = []

        # Define test scenarios for each module
        test_scenarios = [
            # Student Management Tests
            ("GET", "/api/v2/students/search/?query=test&page=1&page_size=10"),
            ("POST", "/api/v2/students/search/", {
                "query": "john",
                "fuzzy_search": True,
                "page": 1,
                "page_size": 25
            }),

            # Academic Management Tests
            ("GET", "/api/v2/academics/schedule/conflicts/"),
            ("GET", "/api/v2/academics/analytics/grade-distribution/550e8400-e29b-41d4-a716-446655440001/"),

            # Financial Management Tests
            ("GET", "/api/v2/finance/analytics/dashboard/?date_range=30"),
            ("POST", "/api/v2/finance/pos/transaction/", {
                "amount": 50.00,
                "payment_method": "cash",
                "description": f"Test transaction user {user_id}",
                "line_items": [
                    {
                        "description": "Test item",
                        "quantity": 1,
                        "unit_price": 50.00,
                        "total_amount": 50.00
                    }
                ]
            }),

            # Innovation AI Tests
            ("POST", "/api/v2/innovation/ai/predictions/", {
                "model_type": "success_prediction",
                "input_data": {
                    "student_id": "550e8400-e29b-41d4-a716-446655440000"
                }
            }),
            ("GET", "/api/v2/innovation/analytics/custom/dashboard/?metrics=enrollment_trends"),
        ]

        for _ in range(self.config.requests_per_user):
            for method, endpoint, *args in test_scenarios:
                data = args[0] if args else None
                result = self.make_request(method, endpoint, data)
                user_results.append(result)

                # Small delay between requests to simulate real usage
                time.sleep(0.1)

        return user_results

    def run_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load test with multiple concurrent users."""
        print(f"Starting load test with {self.config.concurrent_users} users...")
        print(f"Each user will make {self.config.requests_per_user} requests per scenario")

        start_time = time.time()
        all_results = []

        # Use ThreadPoolExecutor for concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.concurrent_users) as executor:
            # Submit all user tests
            futures = []
            for user_id in range(self.config.concurrent_users):
                # Stagger user start times for realistic ramp-up
                time.sleep(self.config.ramp_up_time / self.config.concurrent_users)
                future = executor.submit(self.run_single_user_test, user_id)
                futures.append(future)

            # Collect all results
            for future in concurrent.futures.as_completed(futures):
                try:
                    user_results = future.result()
                    all_results.extend(user_results)
                except Exception as e:
                    print(f"User test failed: {e}")

        end_time = time.time()
        total_duration = end_time - start_time

        # Analyze results
        return self.analyze_results(all_results, total_duration)

    def analyze_results(self, results: List[TestResult], duration: float) -> Dict[str, Any]:
        """Analyze test results and generate performance metrics."""
        if not results:
            return {"error": "No results to analyze"}

        # Group results by endpoint
        endpoint_results = defaultdict(list)
        for result in results:
            endpoint_results[result.endpoint].append(result)

        # Calculate overall metrics
        response_times = [r.response_time for r in results if r.success]
        success_count = sum(1 for r in results if r.success)
        total_requests = len(results)

        analysis = {
            "summary": {
                "total_requests": total_requests,
                "successful_requests": success_count,
                "failed_requests": total_requests - success_count,
                "success_rate": (success_count / total_requests) * 100 if total_requests > 0 else 0,
                "total_duration": duration,
                "requests_per_second": total_requests / duration if duration > 0 else 0,
                "concurrent_users": self.config.concurrent_users
            },
            "response_times": {
                "min": min(response_times) if response_times else 0,
                "max": max(response_times) if response_times else 0,
                "average": statistics.mean(response_times) if response_times else 0,
                "median": statistics.median(response_times) if response_times else 0,
                "p95": self.percentile(response_times, 95) if response_times else 0,
                "p99": self.percentile(response_times, 99) if response_times else 0
            },
            "endpoint_performance": {}
        }

        # Analyze each endpoint
        for endpoint, endpoint_results_list in endpoint_results.items():
            successful = [r for r in endpoint_results_list if r.success]
            response_times = [r.response_time for r in successful]

            analysis["endpoint_performance"][endpoint] = {
                "total_requests": len(endpoint_results_list),
                "successful_requests": len(successful),
                "success_rate": (len(successful) / len(endpoint_results_list)) * 100,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "p95_response_time": self.percentile(response_times, 95) if response_times else 0
            }

        # Error analysis
        errors = [r for r in results if not r.success]
        error_summary = defaultdict(int)
        for error in errors:
            if error.error_message:
                error_summary[error.error_message] += 1
            else:
                error_summary[f"HTTP {error.status_code}"] += 1

        analysis["errors"] = dict(error_summary)

        return analysis

    @staticmethod
    def percentile(data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of numbers."""
        if not data:
            return 0
        data_sorted = sorted(data)
        k = (len(data_sorted) - 1) * (percentile / 100)
        f = int(k)
        c = k - f
        if f == len(data_sorted) - 1:
            return data_sorted[f]
        return data_sorted[f] * (1 - c) + data_sorted[f + 1] * c


class SpecificPerformanceTests:
    """Specific performance tests for critical operations."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.auth_token}",
            "Content-Type": "application/json"
        }

    def test_student_search_performance(self):
        """Test student search performance with various query sizes."""
        print("Testing student search performance...")

        test_queries = [
            {"query": "a", "description": "Single character"},
            {"query": "john", "description": "Common name"},
            {"query": "john smith", "description": "Full name"},
            {"query": "john smith computer science", "description": "Complex query"},
            {"query": "", "description": "Empty query (all students)"}
        ]

        results = []
        for test_query in test_queries:
            for page_size in [10, 25, 50, 100]:
                data = {
                    "query": test_query["query"],
                    "fuzzy_search": True,
                    "page": 1,
                    "page_size": page_size
                }

                start_time = time.time()
                response = requests.post(
                    f"{self.config.base_url}/api/v2/students/search/",
                    headers=self.headers,
                    json=data
                )
                end_time = time.time()

                results.append({
                    "query_type": test_query["description"],
                    "page_size": page_size,
                    "response_time": (end_time - start_time) * 1000,
                    "status_code": response.status_code,
                    "result_count": len(response.json()) if response.status_code == 200 else 0
                })

        return results

    def test_bulk_operations_performance(self):
        """Test performance of bulk operations."""
        print("Testing bulk operations performance...")

        # Test various bulk operation sizes
        bulk_sizes = [10, 50, 100, 250, 500]
        results = []

        for size in bulk_sizes:
            # Generate test student IDs
            student_ids = [f"550e8400-e29b-41d4-a716-44665544{i:04d}" for i in range(size)]

            data = {
                "action": "update_status",
                "target_ids": student_ids,
                "parameters": {"status": "active"},
                "dry_run": True
            }

            start_time = time.time()
            response = requests.post(
                f"{self.config.base_url}/api/v2/students/bulk-actions/",
                headers=self.headers,
                json=data
            )
            end_time = time.time()

            results.append({
                "bulk_size": size,
                "response_time": (end_time - start_time) * 1000,
                "status_code": response.status_code,
                "requests_per_second": size / (end_time - start_time) if end_time > start_time else 0
            })

        return results

    def test_ai_prediction_performance(self):
        """Test AI prediction performance."""
        print("Testing AI prediction performance...")

        prediction_types = [
            "success_prediction",
            "risk_assessment",
            "grade_prediction",
            "scholarship_matching"
        ]

        results = []
        test_student_id = "550e8400-e29b-41d4-a716-446655440000"

        for prediction_type in prediction_types:
            # Test single prediction
            data = {
                "model_type": prediction_type,
                "input_data": {"student_id": test_student_id}
            }

            start_time = time.time()
            response = requests.post(
                f"{self.config.base_url}/api/v2/innovation/ai/predictions/",
                headers=self.headers,
                json=data
            )
            end_time = time.time()

            results.append({
                "prediction_type": prediction_type,
                "response_time": (end_time - start_time) * 1000,
                "status_code": response.status_code,
                "success": response.status_code == 200
            })

        return results

    def test_financial_operations_performance(self):
        """Test financial operations performance."""
        print("Testing financial operations performance...")

        results = []

        # Test POS transaction processing
        transaction_data = {
            "amount": 100.00,
            "payment_method": "cash",
            "description": "Performance test transaction",
            "line_items": [
                {
                    "description": "Test item",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "total_amount": 100.00
                }
            ]
        }

        start_time = time.time()
        response = requests.post(
            f"{self.config.base_url}/api/v2/finance/pos/transaction/",
            headers=self.headers,
            json=transaction_data
        )
        end_time = time.time()

        results.append({
            "operation": "POS Transaction",
            "response_time": (end_time - start_time) * 1000,
            "status_code": response.status_code
        })

        # Test financial analytics
        start_time = time.time()
        response = requests.get(
            f"{self.config.base_url}/api/v2/finance/analytics/dashboard/?date_range=30",
            headers=self.headers
        )
        end_time = time.time()

        results.append({
            "operation": "Financial Analytics",
            "response_time": (end_time - start_time) * 1000,
            "status_code": response.status_code
        })

        return results


def run_comprehensive_performance_test():
    """Run all performance tests and generate report."""

    # Configuration
    config = LoadTestConfig(
        base_url="http://localhost:8000",
        auth_token="",  # Set your test token here
        concurrent_users=10,
        requests_per_user=3,
        ramp_up_time=5
    )

    print("=" * 80)
    print("STAFF-WEB V2 COMPREHENSIVE PERFORMANCE TEST SUITE")
    print("=" * 80)

    # Run load test
    tester = PerformanceTester(config)
    load_results = tester.run_load_test()

    # Run specific performance tests
    specific_tester = SpecificPerformanceTests(config)

    search_results = specific_tester.test_student_search_performance()
    bulk_results = specific_tester.test_bulk_operations_performance()
    ai_results = specific_tester.test_ai_prediction_performance()
    finance_results = specific_tester.test_financial_operations_performance()

    # Generate comprehensive report
    report = {
        "test_timestamp": datetime.now().isoformat(),
        "configuration": {
            "base_url": config.base_url,
            "concurrent_users": config.concurrent_users,
            "requests_per_user": config.requests_per_user,
            "ramp_up_time": config.ramp_up_time
        },
        "load_test_results": load_results,
        "specific_test_results": {
            "student_search": search_results,
            "bulk_operations": bulk_results,
            "ai_predictions": ai_results,
            "financial_operations": finance_results
        }
    }

    # Print summary
    print("\n" + "=" * 80)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 80)

    if "summary" in load_results:
        summary = load_results["summary"]
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Success Rate: {summary['success_rate']:.2f}%")
        print(f"Requests/Second: {summary['requests_per_second']:.2f}")
        print(f"Average Response Time: {load_results['response_times']['average']:.2f}ms")
        print(f"95th Percentile: {load_results['response_times']['p95']:.2f}ms")
        print(f"99th Percentile: {load_results['response_times']['p99']:.2f}ms")

    # Performance benchmarks
    print("\n" + "=" * 40)
    print("PERFORMANCE BENCHMARKS")
    print("=" * 40)

    benchmarks = {
        "Student Search (25 results)": "< 500ms",
        "POS Transaction": "< 300ms",
        "AI Prediction": "< 1000ms",
        "Financial Analytics": "< 800ms",
        "Bulk Operations (100 items)": "< 2000ms",
        "Grade Spreadsheet": "< 600ms"
    }

    for operation, benchmark in benchmarks.items():
        print(f"{operation}: {benchmark}")

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"performance_report_{timestamp}.json"

    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_filename}")

    return report


if __name__ == "__main__":
    run_comprehensive_performance_test()