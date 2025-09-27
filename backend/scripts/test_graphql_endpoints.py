#!/usr/bin/env python3
"""Test script for GraphQL endpoints."""

import json
import requests
import sys
from typing import Dict, Any


class GraphQLTester:
    """GraphQL endpoint tester."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize GraphQL tester."""
        self.base_url = base_url
        self.graphql_url = f"{base_url}/graphql/"
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0

    def test_query(self, query: str, variables: Dict[str, Any] = None, test_name: str = ""):
        """Test a GraphQL query."""
        print(f"\n🧪 Testing: {test_name}")

        payload = {
            "query": query,
            "variables": variables or {}
        }

        try:
            response = self.session.post(
                self.graphql_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            self.tests_run += 1

            if response.status_code == 200:
                result = response.json()

                if "errors" in result:
                    print(f"❌ FAIL - GraphQL errors: {result['errors']}")
                    self.tests_failed += 1
                else:
                    print(f"✅ PASS - Query executed successfully")
                    if "data" in result:
                        print(f"📄 Response keys: {list(result['data'].keys())}")
                    self.tests_passed += 1
            else:
                print(f"❌ FAIL - HTTP {response.status_code}: {response.text}")
                self.tests_failed += 1

        except Exception as e:
            print(f"❌ FAIL - Exception: {e}")
            self.tests_failed += 1

    def test_introspection(self):
        """Test GraphQL introspection query."""
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                }
                queryType {
                    name
                }
                mutationType {
                    name
                }
                subscriptionType {
                    name
                }
            }
        }
        """
        self.test_query(introspection_query, test_name="Schema Introspection")

    def test_health_queries(self):
        """Test basic health queries."""
        health_query = """
        query HealthCheck {
            health
            apiInfo
        }
        """
        self.test_query(health_query, test_name="Health Check Queries")

    def test_student_queries(self):
        """Test student-related queries."""

        # Test basic student search
        student_search_query = """
        query StudentSearch($filters: AdvancedStudentSearchFilters) {
            students(filters: $filters, limit: 5) {
                totalCount
                students {
                    uniqueId
                    studentId
                    person {
                        fullName
                    }
                }
                searchTimeMs
            }
        }
        """

        filters = {
            "query": "test",
            "fuzzySearch": False
        }

        self.test_query(
            student_search_query,
            {"filters": filters},
            "Student Search Query"
        )

        # Test students at risk query
        at_risk_query = """
        query StudentsAtRisk($riskThreshold: Float!, $limit: Int!) {
            studentsAtRisk(riskThreshold: $riskThreshold, limit: $limit) {
                uniqueId
                studentId
                person {
                    fullName
                }
                riskAssessment {
                    riskScore
                    riskLevel
                    riskFactors
                }
            }
        }
        """

        self.test_query(
            at_risk_query,
            {"riskThreshold": 0.7, "limit": 10},
            "Students At Risk Query"
        )

    def test_enhanced_queries(self):
        """Test enhanced GraphQL queries."""

        # Test enhanced student type fields
        enhanced_student_query = """
        query EnhancedStudentDetails($studentId: ID!) {
            student(studentId: $studentId) {
                uniqueId
                studentId
                person {
                    fullName
                    schoolEmail
                }
                academicProgress {
                    cumulativeGpa
                    totalCreditHours
                    academicStanding
                }
                financialSummary {
                    currentBalance
                    totalCharges
                    totalPayments
                }
                riskAssessment {
                    riskScore
                    riskLevel
                    riskFactors
                    recommendations
                }
                successPrediction {
                    successProbability
                    confidence
                    keyFactors
                }
            }
        }
        """

        # Use a test UUID (this will likely not exist, but tests the query structure)
        test_student_id = "550e8400-e29b-41d4-a716-446655440000"

        self.test_query(
            enhanced_student_query,
            {"studentId": test_student_id},
            "Enhanced Student Details Query"
        )

    def test_mutations(self):
        """Test GraphQL mutations."""

        # Test grade update mutation
        grade_update_mutation = """
        mutation UpdateGrade(
            $studentId: ID!,
            $assignmentId: ID!,
            $score: Float,
            $maxScore: Float,
            $notes: String
        ) {
            updateGrade(
                studentId: $studentId,
                assignmentId: $assignmentId,
                score: $score,
                maxScore: $maxScore,
                notes: $notes
            ) {
                success
                message
                gradeId
                updatedScore
                validationErrors
            }
        }
        """

        grade_variables = {
            "studentId": "550e8400-e29b-41d4-a716-446655440000",
            "assignmentId": "550e8400-e29b-41d4-a716-446655440001",
            "score": 85.5,
            "maxScore": 100.0,
            "notes": "Good work"
        }

        self.test_query(
            grade_update_mutation,
            grade_variables,
            "Grade Update Mutation"
        )

        # Test collaboration mutations
        collaboration_mutation = """
        mutation StartGradeCollaboration($classId: ID!, $userId: ID!) {
            startGradeCollaboration(classId: $classId, userId: $userId) {
                classId
                activeUsers
                lockedCells
                version
            }
        }
        """

        collaboration_variables = {
            "classId": "550e8400-e29b-41d4-a716-446655440002",
            "userId": "550e8400-e29b-41d4-a716-446655440003"
        }

        self.test_query(
            collaboration_mutation,
            collaboration_variables,
            "Start Grade Collaboration Mutation"
        )

    def test_bulk_operations(self):
        """Test bulk operations."""

        bulk_mutation = """
        mutation BulkUpdateGrades($input: BulkGradeUpdateInput!) {
            bulkUpdateGrades(input: $input) {
                success
                processedCount
                failedCount
                failedIds
                message
            }
        }
        """

        bulk_input = {
            "classId": "550e8400-e29b-41d4-a716-446655440002",
            "grades": [
                {
                    "studentId": "550e8400-e29b-41d4-a716-446655440000",
                    "assignmentId": "550e8400-e29b-41d4-a716-446655440001",
                    "score": 90.0,
                    "maxScore": 100.0
                }
            ],
            "notifyStudents": False
        }

        self.test_query(
            bulk_mutation,
            {"input": bulk_input},
            "Bulk Grade Update Mutation"
        )

    def run_all_tests(self):
        """Run all GraphQL tests."""
        print("🚀 Starting GraphQL API Tests")
        print("=" * 50)

        # Test basic connectivity and schema
        self.test_introspection()
        self.test_health_queries()

        # Test domain-specific queries
        self.test_student_queries()
        self.test_enhanced_queries()

        # Test mutations
        self.test_mutations()
        self.test_bulk_operations()

        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        print(f"Tests run: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")

        if self.tests_failed == 0:
            print("\n🎉 All GraphQL tests passed!")
            return True
        else:
            print(f"\n⚠️  {self.tests_failed} GraphQL tests failed.")
            return False


def main():
    """Main test function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"

    tester = GraphQLTester(base_url)

    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()