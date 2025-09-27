"""
Comprehensive Security Validation Suite for Staff-Web V2
Tests authentication, authorization, input validation, and security compliance
"""

import requests
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import base64
import hashlib
import hmac


@dataclass
class SecurityTestResult:
    """Data class for security test results."""
    test_name: str
    passed: bool
    severity: str  # "critical", "high", "medium", "low"
    description: str
    details: str = ""
    recommendation: str = ""


class SecurityTester:
    """Main security testing class."""

    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = ""):
        self.base_url = base_url
        self.auth_token = auth_token
        self.results: List[SecurityTestResult] = []

        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "SecurityTester/1.0"
        }

        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    def run_all_tests(self) -> List[SecurityTestResult]:
        """Run all security tests."""
        print("Starting comprehensive security validation...")

        # Authentication & Authorization Tests
        self.test_authentication_bypass()
        self.test_weak_authentication()
        self.test_token_validation()
        self.test_authorization_controls()
        self.test_privilege_escalation()

        # Input Validation Tests
        self.test_sql_injection()
        self.test_xss_prevention()
        self.test_command_injection()
        self.test_xxe_protection()
        self.test_path_traversal()
        self.test_file_upload_security()

        # Data Security Tests
        self.test_sensitive_data_exposure()
        self.test_data_encryption()
        self.test_session_management()

        # API Security Tests
        self.test_rate_limiting()
        self.test_cors_configuration()
        self.test_http_methods()
        self.test_api_versioning_security()

        # Infrastructure Security Tests
        self.test_security_headers()
        self.test_information_disclosure()
        self.test_error_handling()

        # Business Logic Security Tests
        self.test_business_logic_flaws()
        self.test_payment_security()
        self.test_grade_manipulation()

        return self.results

    def add_result(self, test_name: str, passed: bool, severity: str, description: str,
                   details: str = "", recommendation: str = ""):
        """Add a test result."""
        result = SecurityTestResult(
            test_name=test_name,
            passed=passed,
            severity=severity,
            description=description,
            details=details,
            recommendation=recommendation
        )
        self.results.append(result)

    # ========================================================================
    # AUTHENTICATION & AUTHORIZATION TESTS
    # ========================================================================

    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities."""
        test_endpoints = [
            "/api/v2/students/search/",
            "/api/v2/finance/analytics/dashboard/",
            "/api/v2/innovation/ai/predictions/"
        ]

        for endpoint in test_endpoints:
            # Test without any authentication
            response = requests.get(f"{self.base_url}{endpoint}")

            passed = response.status_code == 401
            self.add_result(
                f"Authentication Required - {endpoint}",
                passed,
                "critical" if not passed else "low",
                f"Endpoint should require authentication",
                f"Status code: {response.status_code}",
                "Ensure all protected endpoints require valid authentication"
            )

            # Test with invalid token
            invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
            response = requests.get(f"{self.base_url}{endpoint}", headers=invalid_headers)

            passed = response.status_code == 401
            self.add_result(
                f"Invalid Token Rejection - {endpoint}",
                passed,
                "critical" if not passed else "low",
                f"Invalid tokens should be rejected",
                f"Status code: {response.status_code}",
                "Implement proper token validation"
            )

    def test_weak_authentication(self):
        """Test for weak authentication mechanisms."""
        # Test weak password acceptance (if registration endpoint exists)
        weak_passwords = [
            "123456",
            "password",
            "admin",
            "12345678",
            "qwerty"
        ]

        auth_data = {
            "username": "testuser",
            "email": "test@example.com"
        }

        for weak_password in weak_passwords:
            auth_data["password"] = weak_password

            response = requests.post(
                f"{self.base_url}/api/auth/register/",
                json=auth_data
            )

            # Should reject weak passwords
            passed = response.status_code >= 400
            self.add_result(
                f"Weak Password Rejection - {weak_password}",
                passed,
                "medium" if not passed else "low",
                f"System should reject weak passwords",
                f"Password '{weak_password}' response: {response.status_code}",
                "Implement strong password policy with complexity requirements"
            )

    def test_token_validation(self):
        """Test JWT token validation."""
        # Test expired token
        expired_payload = {
            "user_id": 1,
            "exp": int(time.time()) - 3600  # Expired 1 hour ago
        }

        # Create fake expired token (simplified)
        expired_token = base64.b64encode(json.dumps(expired_payload).encode()).decode()

        headers = {"Authorization": f"Bearer {expired_token}"}
        response = requests.get(f"{self.base_url}/api/v2/students/search/", headers=headers)

        passed = response.status_code == 401
        self.add_result(
            "Expired Token Rejection",
            passed,
            "high" if not passed else "low",
            "Expired tokens should be rejected",
            f"Response: {response.status_code}",
            "Implement proper token expiration validation"
        )

        # Test malformed token
        malformed_tokens = [
            "Bearer malformed.token.here",
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",
            "Bearer ....",
            "invalid_format"
        ]

        for token in malformed_tokens:
            headers = {"Authorization": token}
            response = requests.get(f"{self.base_url}/api/v2/students/search/", headers=headers)

            passed = response.status_code == 401
            self.add_result(
                f"Malformed Token Rejection",
                passed,
                "high" if not passed else "low",
                "Malformed tokens should be rejected",
                f"Token format: {token[:50]}...",
                "Validate token structure before processing"
            )

    def test_authorization_controls(self):
        """Test role-based authorization controls."""
        # Test accessing admin-only endpoints with regular user token
        admin_endpoints = [
            "/api/v2/admin/users/",
            "/api/v2/admin/system/settings/",
            "/api/v2/admin/reports/audit/"
        ]

        for endpoint in admin_endpoints:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers)

            # Should return 403 Forbidden for non-admin users
            passed = response.status_code == 403 or response.status_code == 404
            self.add_result(
                f"Admin Access Control - {endpoint}",
                passed,
                "critical" if not passed else "low",
                "Admin endpoints should be protected",
                f"Status: {response.status_code}",
                "Implement proper role-based access control"
            )

    def test_privilege_escalation(self):
        """Test for privilege escalation vulnerabilities."""
        # Test parameter tampering for privilege escalation
        privilege_tests = [
            {"role": "admin"},
            {"is_admin": True},
            {"permissions": ["admin", "superuser"]},
            {"user_type": "administrator"}
        ]

        for test_data in privilege_tests:
            response = requests.post(
                f"{self.base_url}/api/v2/auth/update-profile/",
                headers=self.headers,
                json=test_data
            )

            # Should not allow privilege escalation
            passed = response.status_code >= 400 or "admin" not in str(response.content).lower()
            self.add_result(
                f"Privilege Escalation Prevention",
                passed,
                "critical" if not passed else "low",
                "Users should not be able to escalate privileges",
                f"Test data: {test_data}",
                "Validate user permissions on server side"
            )

    # ========================================================================
    # INPUT VALIDATION TESTS
    # ========================================================================

    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities."""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE students; --",
            "' UNION SELECT * FROM users --",
            "admin'--",
            "' OR 1=1#",
            "'; EXEC xp_cmdshell('dir'); --"
        ]

        test_endpoints = [
            ("/api/v2/students/search/", {"query": ""}),
            ("/api/v2/academics/schedule/conflicts/", {"term_id": ""}),
            ("/api/v2/finance/audit/payment-summary/", {"cashier_id": ""})
        ]

        for endpoint, base_data in test_endpoints:
            for payload in sql_payloads:
                test_data = base_data.copy()
                # Try SQL injection in different parameters
                for key in test_data.keys():
                    test_data[key] = payload

                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        headers=self.headers,
                        json=test_data
                    )

                    # Check for SQL error indicators
                    error_indicators = [
                        "syntax error",
                        "mysql",
                        "postgresql",
                        "sqlite",
                        "ORA-",
                        "Microsoft ODBC",
                        "Exception"
                    ]

                    response_text = response.text.lower()
                    sql_error_found = any(indicator in response_text for indicator in error_indicators)

                    passed = not sql_error_found and response.status_code < 500
                    self.add_result(
                        f"SQL Injection Prevention - {endpoint}",
                        passed,
                        "critical" if not passed else "low",
                        f"SQL injection should be prevented",
                        f"Payload: {payload[:50]}..., Response code: {response.status_code}",
                        "Use parameterized queries and input validation"
                    )

    def test_xss_prevention(self):
        """Test for Cross-Site Scripting (XSS) vulnerabilities."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "';alert('xss');//",
            "<iframe src='javascript:alert(\"xss\")'></iframe>"
        ]

        for payload in xss_payloads:
            test_data = {"query": payload}

            response = requests.post(
                f"{self.base_url}/api/v2/students/search/",
                headers=self.headers,
                json=test_data
            )

            # Check if payload is reflected without encoding
            passed = payload not in response.text
            self.add_result(
                f"XSS Prevention",
                passed,
                "high" if not passed else "low",
                "XSS payloads should be sanitized",
                f"Payload: {payload[:50]}...",
                "Implement proper output encoding and CSP headers"
            )

    def test_command_injection(self):
        """Test for command injection vulnerabilities."""
        command_payloads = [
            "; ls -la",
            "| whoami",
            "&& dir",
            "; cat /etc/passwd",
            "|| ping -c 1 google.com",
            "`id`",
            "$(whoami)"
        ]

        # Test file upload and document processing endpoints
        for payload in command_payloads:
            test_data = {"filename": f"test{payload}.txt"}

            response = requests.post(
                f"{self.base_url}/api/v2/innovation/documents/ocr/",
                headers=self.headers,
                json=test_data
            )

            # Should not execute commands
            passed = response.status_code >= 400 or "root" not in response.text.lower()
            self.add_result(
                f"Command Injection Prevention",
                passed,
                "critical" if not passed else "low",
                "Command injection should be prevented",
                f"Payload: {payload}",
                "Validate and sanitize all user inputs"
            )

    def test_xxe_protection(self):
        """Test for XML External Entity (XXE) vulnerabilities."""
        xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
            <!ELEMENT foo ANY >
            <!ENTITY xxe SYSTEM "file:///etc/passwd" >
        ]>
        <foo>&xxe;</foo>"""

        # Test if any endpoints accept XML
        response = requests.post(
            f"{self.base_url}/api/v2/innovation/documents/intelligence/",
            headers={"Content-Type": "application/xml", "Authorization": f"Bearer {self.auth_token}"},
            data=xxe_payload
        )

        # Should not process XXE or should return appropriate error
        passed = "root:" not in response.text and response.status_code >= 400
        self.add_result(
            "XXE Protection",
            passed,
            "high" if not passed else "low",
            "XXE attacks should be prevented",
            f"Response code: {response.status_code}",
            "Disable external entity processing in XML parsers"
        )

    def test_path_traversal(self):
        """Test for path traversal vulnerabilities."""
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd"
        ]

        for payload in traversal_payloads:
            # Test file access endpoints
            response = requests.get(
                f"{self.base_url}/api/v2/files/{payload}",
                headers=self.headers
            )

            passed = "root:" not in response.text and response.status_code >= 400
            self.add_result(
                f"Path Traversal Prevention",
                passed,
                "high" if not passed else "low",
                "Path traversal should be prevented",
                f"Payload: {payload}",
                "Validate file paths and restrict file access"
            )

    def test_file_upload_security(self):
        """Test file upload security controls."""
        # Test malicious file types
        malicious_files = [
            ("malware.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("script.php", b"<?php system($_GET['cmd']); ?>", "application/x-php"),
            ("test.jsp", b"<% Runtime.getRuntime().exec(\"calc\"); %>", "application/x-jsp"),
            ("large_file.txt", b"A" * (10 * 1024 * 1024), "text/plain"),  # 10MB file
        ]

        for filename, content, content_type in malicious_files:
            files = {"document": (filename, content, content_type)}

            response = requests.post(
                f"{self.base_url}/api/v2/innovation/documents/ocr/",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                files=files
            )

            # Should reject malicious files
            passed = response.status_code >= 400
            self.add_result(
                f"Malicious File Upload Prevention - {filename}",
                passed,
                "high" if not passed else "low",
                "Malicious files should be rejected",
                f"File: {filename}, Response: {response.status_code}",
                "Implement file type validation and size limits"
            )

    # ========================================================================
    # DATA SECURITY TESTS
    # ========================================================================

    def test_sensitive_data_exposure(self):
        """Test for sensitive data exposure."""
        # Check if sensitive data is returned in responses
        response = requests.get(
            f"{self.base_url}/api/v2/students/550e8400-e29b-41d4-a716-446655440000/",
            headers=self.headers
        )

        if response.status_code == 200:
            response_text = response.text.lower()

            # Check for sensitive data that shouldn't be exposed
            sensitive_indicators = [
                "password",
                "secret",
                "private_key",
                "api_key",
                "token",
                "ssn",
                "social_security"
            ]

            exposed_data = [indicator for indicator in sensitive_indicators if indicator in response_text]

            passed = len(exposed_data) == 0
            self.add_result(
                "Sensitive Data Exposure",
                passed,
                "high" if not passed else "low",
                "Sensitive data should not be exposed",
                f"Exposed data: {exposed_data}",
                "Remove sensitive data from API responses"
            )

    def test_data_encryption(self):
        """Test data encryption in transit."""
        # Test if HTTPS is enforced
        try:
            http_response = requests.get(self.base_url.replace("https://", "http://"))

            # Should redirect to HTTPS or reject HTTP
            passed = http_response.status_code in [301, 302, 403, 404] or "https" in http_response.url
            self.add_result(
                "HTTPS Enforcement",
                passed,
                "high" if not passed else "low",
                "HTTP should redirect to HTTPS",
                f"HTTP response code: {http_response.status_code}",
                "Implement HTTPS redirect and HSTS headers"
            )
        except:
            # If HTTP fails completely, that's actually good
            self.add_result(
                "HTTPS Enforcement",
                True,
                "low",
                "HTTP requests properly rejected",
                "HTTP connection failed as expected",
                "Continue enforcing HTTPS"
            )

    def test_session_management(self):
        """Test session management security."""
        # Test session timeout
        old_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE2NDA5OTUyMDB9.old"

        headers = {"Authorization": f"Bearer {old_token}"}
        response = requests.get(f"{self.base_url}/api/v2/students/search/", headers=headers)

        passed = response.status_code == 401
        self.add_result(
            "Session Timeout",
            passed,
            "medium" if not passed else "low",
            "Old sessions should timeout",
            f"Response: {response.status_code}",
            "Implement proper session timeout"
        )

    # ========================================================================
    # API SECURITY TESTS
    # ========================================================================

    def test_rate_limiting(self):
        """Test API rate limiting."""
        # Make rapid requests to test rate limiting
        endpoint = f"{self.base_url}/api/v2/students/search/"
        rapid_requests = 50

        responses = []
        start_time = time.time()

        for i in range(rapid_requests):
            response = requests.get(endpoint, headers=self.headers)
            responses.append(response.status_code)

        end_time = time.time()

        # Check if rate limiting kicked in
        rate_limited = any(status == 429 for status in responses)

        passed = rate_limited or (end_time - start_time) > 10  # Should be rate limited or slow
        self.add_result(
            "Rate Limiting",
            passed,
            "medium" if not passed else "low",
            "API should implement rate limiting",
            f"Made {rapid_requests} requests in {end_time - start_time:.2f}s",
            "Implement rate limiting to prevent abuse"
        )

    def test_cors_configuration(self):
        """Test CORS configuration."""
        # Test with potentially dangerous origin
        dangerous_headers = {
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }

        response = requests.options(
            f"{self.base_url}/api/v2/students/search/",
            headers=dangerous_headers
        )

        # Should not allow all origins
        cors_header = response.headers.get("Access-Control-Allow-Origin", "")
        passed = cors_header != "*" and "evil.com" not in cors_header

        self.add_result(
            "CORS Configuration",
            passed,
            "medium" if not passed else "low",
            "CORS should be properly configured",
            f"CORS header: {cors_header}",
            "Configure CORS to allow only trusted origins"
        )

    def test_http_methods(self):
        """Test HTTP method security."""
        endpoint = f"{self.base_url}/api/v2/students/search/"

        # Test potentially dangerous methods
        dangerous_methods = ["TRACE", "TRACK", "DEBUG", "OPTIONS"]

        for method in dangerous_methods:
            response = requests.request(method, endpoint, headers=self.headers)

            # These methods should generally be disabled
            passed = response.status_code in [405, 501, 404]
            self.add_result(
                f"HTTP Method Security - {method}",
                passed,
                "low",
                f"{method} method should be disabled",
                f"Response: {response.status_code}",
                "Disable unnecessary HTTP methods"
            )

    def test_api_versioning_security(self):
        """Test API versioning security."""
        # Test if old API versions are accessible
        old_versions = ["/api/v1/", "/api/v0/", "/api/"]

        for version in old_versions:
            response = requests.get(f"{self.base_url}{version}students/", headers=self.headers)

            # Old versions should be deprecated/secured
            passed = response.status_code in [404, 410, 403]
            self.add_result(
                f"API Version Security - {version}",
                passed,
                "low",
                "Old API versions should be secured",
                f"Response: {response.status_code}",
                "Deprecate and secure old API versions"
            )

    # ========================================================================
    # INFRASTRUCTURE SECURITY TESTS
    # ========================================================================

    def test_security_headers(self):
        """Test security headers."""
        response = requests.get(f"{self.base_url}/api/v2/students/search/", headers=self.headers)

        required_headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=",
            "Content-Security-Policy": "default-src"
        }

        for header, expected_value in required_headers.items():
            header_value = response.headers.get(header, "")
            passed = expected_value.lower() in header_value.lower()

            self.add_result(
                f"Security Header - {header}",
                passed,
                "medium" if not passed else "low",
                f"{header} should be properly set",
                f"Value: {header_value}",
                f"Set {header} header for security"
            )

    def test_information_disclosure(self):
        """Test for information disclosure."""
        # Test server header disclosure
        response = requests.get(self.base_url)

        server_header = response.headers.get("Server", "")
        passed = not any(tech in server_header.lower() for tech in ["apache", "nginx", "iis", "python", "django"])

        self.add_result(
            "Server Information Disclosure",
            passed,
            "low",
            "Server information should not be disclosed",
            f"Server header: {server_header}",
            "Remove or obfuscate server headers"
        )

        # Test for debug information
        debug_indicators = ["traceback", "debug", "stack trace", "error"]
        response_text = response.text.lower()

        debug_found = any(indicator in response_text for indicator in debug_indicators)
        passed = not debug_found

        self.add_result(
            "Debug Information Disclosure",
            passed,
            "medium" if not passed else "low",
            "Debug information should not be disclosed",
            f"Debug indicators found: {debug_found}",
            "Disable debug mode in production"
        )

    def test_error_handling(self):
        """Test error handling security."""
        # Test with malformed request
        malformed_data = '{"invalid": json}'

        response = requests.post(
            f"{self.base_url}/api/v2/students/search/",
            headers=self.headers,
            data=malformed_data  # Intentionally malformed JSON
        )

        # Should return generic error without stack trace
        error_indicators = ["traceback", "line", "file", "exception", "django"]
        response_text = response.text.lower()

        stack_trace_found = any(indicator in response_text for indicator in error_indicators)
        passed = not stack_trace_found and response.status_code == 400

        self.add_result(
            "Error Handling Security",
            passed,
            "medium" if not passed else "low",
            "Errors should not expose system details",
            f"Response code: {response.status_code}",
            "Implement generic error responses"
        )

    # ========================================================================
    # BUSINESS LOGIC SECURITY TESTS
    # ========================================================================

    def test_business_logic_flaws(self):
        """Test for business logic vulnerabilities."""
        # Test negative amount in financial transactions
        transaction_data = {
            "amount": -100.00,
            "payment_method": "cash",
            "description": "Negative amount test"
        }

        response = requests.post(
            f"{self.base_url}/api/v2/finance/pos/transaction/",
            headers=self.headers,
            json=transaction_data
        )

        # Should reject negative amounts
        passed = response.status_code >= 400
        self.add_result(
            "Negative Amount Prevention",
            passed,
            "high" if not passed else "low",
            "Negative amounts should be rejected",
            f"Response: {response.status_code}",
            "Validate business logic constraints"
        )

    def test_payment_security(self):
        """Test payment processing security."""
        # Test payment without proper validation
        payment_data = {
            "amount": 999999.99,
            "payment_method": "cash",
            "description": "Large amount test"
        }

        response = requests.post(
            f"{self.base_url}/api/v2/finance/pos/transaction/",
            headers=self.headers,
            json=payment_data
        )

        # Should have reasonable limits
        passed = response.status_code >= 400 or "approved" not in response.text.lower()
        self.add_result(
            "Payment Amount Validation",
            passed,
            "high" if not passed else "low",
            "Large payments should require validation",
            f"Amount: {payment_data['amount']}, Response: {response.status_code}",
            "Implement payment amount limits and validation"
        )

    def test_grade_manipulation(self):
        """Test grade manipulation prevention."""
        # Test grade tampering
        grade_data = [{
            "student_id": "550e8400-e29b-41d4-a716-446655440000",
            "assignment_id": "550e8400-e29b-41d4-a716-446655440001",
            "score": 150,  # Invalid score > 100
            "notes": "Grade manipulation test"
        }]

        response = requests.post(
            f"{self.base_url}/api/v2/academics/grades/spreadsheet/550e8400-e29b-41d4-a716-446655440002/bulk-update/",
            headers=self.headers,
            json=grade_data
        )

        # Should validate grade ranges
        passed = response.status_code >= 400 or "error" in response.text.lower()
        self.add_result(
            "Grade Range Validation",
            passed,
            "medium" if not passed else "low",
            "Grade scores should be validated",
            f"Score: {grade_data[0]['score']}, Response: {response.status_code}",
            "Implement grade range validation"
        )

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests

        # Group by severity
        critical_failures = [r for r in self.results if not r.passed and r.severity == "critical"]
        high_failures = [r for r in self.results if not r.passed and r.severity == "high"]
        medium_failures = [r for r in self.results if not r.passed and r.severity == "medium"]
        low_failures = [r for r in self.results if not r.passed and r.severity == "low"]

        # Calculate security score
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        total_weight = sum(weights[r.severity] for r in self.results)
        failed_weight = sum(weights[r.severity] for r in self.results if not r.passed)

        security_score = ((total_weight - failed_weight) / total_weight * 100) if total_weight > 0 else 0

        report = {
            "test_timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "security_score": security_score
            },
            "failures_by_severity": {
                "critical": len(critical_failures),
                "high": len(high_failures),
                "medium": len(medium_failures),
                "low": len(low_failures)
            },
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "description": r.description,
                    "details": r.details,
                    "recommendation": r.recommendation
                }
                for r in self.results
            ],
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on test results."""
        recommendations = []

        failed_critical = [r for r in self.results if not r.passed and r.severity == "critical"]
        failed_high = [r for r in self.results if not r.passed and r.severity == "high"]

        if failed_critical:
            recommendations.append("🚨 CRITICAL: Address authentication and authorization issues immediately")

        if failed_high:
            recommendations.append("⚠️ HIGH: Fix input validation and data security issues")

        recommendations.extend([
            "Implement comprehensive security testing in CI/CD pipeline",
            "Regular security audits and penetration testing",
            "Security awareness training for development team",
            "Implement security monitoring and alerting",
            "Regular security updates and dependency scanning"
        ])

        return recommendations


def run_security_validation():
    """Run comprehensive security validation."""
    print("=" * 80)
    print("STAFF-WEB V2 COMPREHENSIVE SECURITY VALIDATION")
    print("=" * 80)

    # Initialize tester
    tester = SecurityTester(
        base_url="http://localhost:8000",
        auth_token=""  # Set your test token here
    )

    # Run all tests
    results = tester.run_all_tests()

    # Generate report
    report = tester.generate_report()

    # Print summary
    print("\n" + "=" * 40)
    print("SECURITY TEST SUMMARY")
    print("=" * 40)

    summary = report["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Security Score: {summary['security_score']:.1f}/100")

    # Print failures by severity
    failures = report["failures_by_severity"]
    if failures["critical"] > 0:
        print(f"\n🚨 CRITICAL FAILURES: {failures['critical']}")
    if failures["high"] > 0:
        print(f"⚠️ HIGH FAILURES: {failures['high']}")
    if failures["medium"] > 0:
        print(f"📊 MEDIUM FAILURES: {failures['medium']}")
    if failures["low"] > 0:
        print(f"📝 LOW FAILURES: {failures['low']}")

    # Print recommendations
    print("\n" + "=" * 40)
    print("SECURITY RECOMMENDATIONS")
    print("=" * 40)
    for rec in report["recommendations"]:
        print(f"• {rec}")

    # Save detailed report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"security_report_{timestamp}.json"

    with open(report_filename, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {report_filename}")

    return report


if __name__ == "__main__":
    run_security_validation()