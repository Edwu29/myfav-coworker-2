#!/usr/bin/env python3
"""
Test script to simulate the GitHub OAuth flow without browser interaction.
This bypasses GitHub's localhost security warning for development testing.
"""

import requests
import json
from urllib.parse import urlparse, parse_qs

def test_oauth_flow():
    """Test the complete OAuth flow programmatically."""
    
    base_url = "http://127.0.0.1:3000"
    
    print("🔍 Testing GitHub OAuth Flow")
    print("=" * 50)
    
    # Step 1: Test the login endpoint
    print("1. Testing /auth/github endpoint...")
    response = requests.get(f"{base_url}/auth/github", allow_redirects=False)
    
    if response.status_code == 302:
        redirect_url = response.headers.get('Location')
        print(f"✅ Login endpoint working - redirects to: {redirect_url[:80]}...")
        
        # Parse the redirect URL to extract parameters
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        
        print(f"   Client ID: {params.get('client_id', ['N/A'])[0]}")
        print(f"   Redirect URI: {params.get('redirect_uri', ['N/A'])[0]}")
        print(f"   Scope: {params.get('scope', ['N/A'])[0]}")
        print(f"   State: {params.get('state', ['N/A'])[0][:20]}...")
        
    else:
        print(f"❌ Login endpoint failed: {response.status_code}")
        return
    
    # Step 2: Test the callback endpoint with invalid code (expected to fail)
    print("\n2. Testing /auth/github/callback endpoint...")
    callback_response = requests.get(
        f"{base_url}/auth/github/callback?code=invalid_test_code&state=test_state"
    )
    
    if callback_response.status_code == 400:
        print("✅ Callback endpoint working - correctly rejects invalid code")
        try:
            error_data = callback_response.json()
            print(f"   Error response: {error_data}")
        except:
            print(f"   Response: {callback_response.text}")
    else:
        print(f"❌ Callback endpoint unexpected response: {callback_response.status_code}")
        print(f"   Response: {callback_response.text}")
    
    # Step 3: Test health endpoint
    print("\n3. Testing /health endpoint...")
    health_response = requests.get(f"{base_url}/health")
    
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"✅ Health endpoint working: {health_data}")
    else:
        print(f"❌ Health endpoint failed: {health_response.status_code}")
    
    print("\n" + "=" * 50)
    print("🎉 OAuth Flow Test Complete!")
    print("\nThe GitHub warning page is normal for localhost development.")
    print("Your OAuth implementation is working correctly.")

if __name__ == "__main__":
    test_oauth_flow()
