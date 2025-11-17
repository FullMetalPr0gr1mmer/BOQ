"""
Test Query Router Integration
Tests the exact failing case: "fetch me ran_lld"
"""
import requests
import json
import os

# Bypass proxy for localhost
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'

# Backend API endpoint
BASE_URL = "http://127.0.0.1:8003"  # Use 127.0.0.1 instead of localhost
LOGIN_ENDPOINT = f"{BASE_URL}/login"  # No /auth prefix
CHAT_ENDPOINT = f"{BASE_URL}/ai/chat"

# Configure session to bypass proxy
session = requests.Session()
session.trust_env = False  # Don't use system proxy settings

def login():
    """Login to get auth token"""
    response = session.post(
        LOGIN_ENDPOINT,
        data={
            "username": "admin",
            "password": "admin"
        }
    )

    if response.status_code == 200:
        token = response.json().get("access_token")
        print(f"[OK] Login successful")
        return token
    else:
        print(f"[ERROR] Login failed: {response.status_code}")
        print(response.text)
        return None

def test_query_router(token):
    """Test the exact failing case"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # The exact failing case
    test_message = "fetch me ran_lld"

    payload = {
        "message": test_message,
        "conversation_id": None,
        "project_context": None,
        "chat_context": "chat"  # Use chat tab (not documents)
    }

    print(f"\n[TEST] Sending message: '{test_message}'")
    print("="*80)

    response = session.post(
        CHAT_ENDPOINT,
        headers=headers,
        json=payload
    )

    if response.status_code == 200:
        result = response.json()

        print(f"\n[OK] Response received successfully!")
        print("="*80)
        print(f"Response: {result['response']}")
        print(f"\nActions taken: {result.get('actions_taken', [])}")

        # Check if data was returned
        if result.get('data'):
            data = result['data']
            print(f"\nData returned:")
            print(f"  - Success: {data.get('success')}")
            print(f"  - Row count: {data.get('row_count')}")
            print(f"  - Columns: {data.get('columns')}")
            if data.get('data'):
                print(f"  - First 3 rows:")
                for i, row in enumerate(data['data'][:3]):
                    print(f"    Row {i+1}: {row}")

        # Verify no hallucination
        response_text = result['response'].lower()
        hallucination_keywords = ['excavator', 'le automation', 'boq project']

        hallucinated = any(keyword in response_text for keyword in hallucination_keywords)

        if hallucinated:
            print(f"\n[WARNING] Possible hallucination detected!")
            print(f"Response contains keywords: {[k for k in hallucination_keywords if k in response_text]}")
        else:
            print(f"\n[OK] No hallucination detected - response is factual!")

        return True
    else:
        print(f"[ERROR] Request failed: {response.status_code}")
        print(response.text)
        return False

def main():
    print("="*80)
    print("QUERY ROUTER INTEGRATION TEST")
    print("Testing: 'fetch me ran_lld' - should NOT hallucinate")
    print("="*80)

    # Login
    token = login()
    if not token:
        print("[ERROR] Cannot proceed without authentication")
        return

    # Test query router
    success = test_query_router(token)

    if success:
        print("\n" + "="*80)
        print("[OK] TEST PASSED - Query router working correctly!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("[ERROR] TEST FAILED")
        print("="*80)

if __name__ == "__main__":
    main()
