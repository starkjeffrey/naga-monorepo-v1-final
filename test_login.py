#!/usr/bin/env python3
"""Test script for JWT login endpoint."""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8001"
LOGIN_URL = f"{BASE_URL}/api/auth/login/"
PROFILE_URL = f"{BASE_URL}/api/auth/profile/"

# Test credentials
credentials = {
    "email": "stark.jeffrey@pucsr.edu.kh",
    "password": "Nolbu0728!"
}

print("=" * 60)
print("Testing Django JWT Authentication")
print("=" * 60)

print(f"\n1. Testing login endpoint: {LOGIN_URL}")
print(f"   Credentials: {credentials['email']}")

try:
    response = requests.post(LOGIN_URL, json=credentials)
    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print("   ✅ Login successful!")
        print(f"\n   Response data:")
        print(f"   - Access Token: {data.get('access_token', 'N/A')[:50]}...")
        print(f"   - Token Type: {data.get('token_type', 'N/A')}")
        print(f"   - Expires In: {data.get('expires_in', 'N/A')} seconds")

        user = data.get('user', {})
        print(f"\n   User Information:")
        print(f"   - ID: {user.get('id', 'N/A')}")
        print(f"   - Email: {user.get('email', 'N/A')}")
        print(f"   - Full Name: {user.get('full_name', 'N/A')}")
        print(f"   - Is Staff: {user.get('is_staff', False)}")
        print(f"   - Is Superuser: {user.get('is_superuser', False)}")
        print(f"   - Roles: {', '.join(user.get('roles', []))}")

        # Test profile endpoint with token
        print(f"\n2. Testing profile endpoint: {PROFILE_URL}")
        headers = {
            "Authorization": f"Bearer {data.get('access_token', '')}"
        }

        profile_response = requests.get(PROFILE_URL, headers=headers)
        print(f"   Status: {profile_response.status_code}")

        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print("   ✅ Profile retrieved successfully!")
            print(f"   - Email: {profile_data.get('email', 'N/A')}")
            print(f"   - Roles: {', '.join(profile_data.get('roles', []))}")
        else:
            print(f"   ❌ Profile request failed: {profile_response.text}")
    else:
        print(f"   ❌ Login failed: {response.text}")

except requests.exceptions.ConnectionError:
    print("   ❌ Could not connect to server. Is Django running on port 8001?")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("For React integration, use these endpoints:")
print("- POST /api/auth/login/    - Get JWT tokens")
print("- POST /api/auth/refresh/  - Refresh access token")
print("- GET  /api/auth/profile/  - Get user profile (requires token)")
print("- POST /api/auth/logout/   - Logout (client-side)")
print("=" * 60)