#!/usr/bin/env python3
"""
Comprehensive test suite for Home Assistant Bridge Service
"""

import httpx
import json
import asyncio
import time
from typing import Dict, Any, List


class HABridgeTester:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        api_key: str = "test-api-key-12345",
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.results = {}

    def test_endpoint(
        self, endpoint: str, name: str, requires_auth: bool = False
    ) -> Dict[str, Any]:
        """Test a single endpoint"""
        try:
            headers = self.headers if requires_auth else {}
            response = httpx.get(
                f"{self.base_url}{endpoint}", headers=headers, timeout=10
            )

            result = {
                "endpoint": endpoint,
                "name": name,
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "response_time": response.elapsed.total_seconds(),
                "content_type": response.headers.get("content-type", ""),
                "error": None,
            }

            if response.status_code == 200:
                try:
                    if result["content_type"].startswith("application/json"):
                        data = response.json()
                        result["data"] = data
                        if isinstance(data, dict):
                            if "count" in data:
                                result["count"] = data["count"]
                            elif "status" in data:
                                result["status"] = data["status"]
                    else:
                        result["data"] = response.text
                except Exception as e:
                    result["data"] = response.text
            else:
                result["error"] = response.text[:200]

        except Exception as e:
            result = {
                "endpoint": endpoint,
                "name": name,
                "status_code": 0,
                "success": False,
                "error": str(e),
                "response_time": 0,
            }

        return result

    def test_core_endpoints(self):
        """Test core API endpoints"""
        print("🔍 Testing Core API Endpoints")
        print("=" * 50)

        endpoints = [
            ("/health", "Health Check", False),
            ("/api/v1/services/test", "Services Test", False),
            ("/api/v1/services/all", "All Services", True),
            ("/api/v1/config/health", "Config Health", True),
            ("/metrics", "Metrics", False),
            ("/status", "Status", False),
        ]

        for endpoint, name, requires_auth in endpoints:
            result = self.test_endpoint(endpoint, name, requires_auth)
            self.results[f"core_{endpoint.replace('/', '_').replace(':', '')}"] = result

            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(
                f"{status} {name}: {result['status_code']} ({result['response_time']:.3f}s)"
            )

            if result["success"] and "count" in result:
                print(f"   📊 Count: {result['count']}")
            elif result["success"] and "status" in result:
                print(f"   📊 Status: {result['status']}")
            elif result["error"]:
                print(f"   ❌ Error: {result['error'][:100]}")

            print()

    def test_states_endpoints(self):
        """Test states-related endpoints"""
        print("🏠 Testing States Endpoints")
        print("=" * 50)

        # Test states endpoints
        states_endpoints = [
            ("/api/v1/states/all", "All States", True),
            (
                "/api/v1/states/binary_sensor.samba_backup_running",
                "Specific Entity",
                True,
            ),
        ]

        for endpoint, name, requires_auth in states_endpoints:
            result = self.test_endpoint(endpoint, name, requires_auth)
            self.results[f"states_{endpoint.replace('/', '_').replace(':', '')}"] = (
                result
            )

            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(
                f"{status} {name}: {result['status_code']} ({result['response_time']:.3f}s)"
            )

            if result["success"] and "count" in result:
                print(f"   📊 Count: {result['count']}")
            elif result["error"]:
                print(f"   ❌ Error: {result['error'][:100]}")

            print()

    def test_authentication(self):
        """Test authentication and rate limiting"""
        print("🔐 Testing Authentication")
        print("=" * 50)

        # Test without auth
        result_no_auth = self.test_endpoint("/api/v1/services/all", "No Auth", False)
        print(
            f"{'❌ FAIL' if result_no_auth['status_code'] == 401 else '⚠️  WARN'} No Auth: {result_no_auth['status_code']}"
        )

        # Test with invalid auth
        try:
            response = httpx.get(
                f"{self.base_url}/api/v1/services/all",
                headers={"Authorization": "Bearer invalid-key"},
                timeout=10,
            )
            print(
                f"{'❌ FAIL' if response.status_code == 401 else '⚠️  WARN'} Invalid Auth: {response.status_code}"
            )
        except Exception as e:
            print(f"❌ FAIL Invalid Auth: Connection Error")

        # Test with valid auth
        result_valid_auth = self.test_endpoint(
            "/api/v1/services/all", "Valid Auth", True
        )
        print(
            f"{'✅ PASS' if result_valid_auth['success'] else '❌ FAIL'} Valid Auth: {result_valid_auth['status_code']}"
        )

        print()

    def test_performance(self):
        """Test performance and caching"""
        print("⚡ Testing Performance")
        print("=" * 50)

        # Test multiple requests to see caching effect
        endpoint = "/api/v1/services/all"
        times = []

        for i in range(5):
            result = self.test_endpoint(endpoint, f"Request {i+1}", True)
            times.append(result["response_time"])
            print(f"Request {i+1}: {result['response_time']:.3f}s")

        avg_time = sum(times) / len(times)
        print(f"Average Response Time: {avg_time:.3f}s")
        print(
            f"Performance: {'✅ Good' if avg_time < 1.0 else '⚠️  Slow' if avg_time < 3.0 else '❌ Poor'}"
        )
        print()

    def test_error_handling(self):
        """Test error handling"""
        print("🛡️ Testing Error Handling")
        print("=" * 50)

        # Test non-existent endpoint
        result_404 = self.test_endpoint(
            "/api/v1/nonexistent", "Non-existent Endpoint", True
        )
        print(
            f"{'✅ PASS' if result_404['status_code'] == 404 else '❌ FAIL'} 404 Handling: {result_404['status_code']}"
        )

        # Test invalid entity
        result_invalid = self.test_endpoint(
            "/api/v1/states/entity/invalid.entity", "Invalid Entity", True
        )
        print(
            f"{'✅ PASS' if result_invalid['status_code'] in [404, 400] else '❌ FAIL'} Invalid Entity: {result_invalid['status_code']}"
        )

        print()

    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Home Assistant Bridge Service - Comprehensive Test Suite")
        print("=" * 70)
        print()

        self.test_core_endpoints()
        self.test_states_endpoints()
        self.test_authentication()
        self.test_performance()
        self.test_error_handling()

        # Summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["success"])

        print("📊 Test Summary")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if passed_tests == total_tests:
            print("🎉 All tests passed! Service is working correctly.")
        else:
            print("⚠️  Some tests failed. Check the details above.")

        return self.results


if __name__ == "__main__":
    tester = HABridgeTester()
    tester.run_all_tests()
