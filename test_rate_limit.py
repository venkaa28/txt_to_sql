#!/usr/bin/env python3
"""
Quick test script to verify rate limiting works.
Run the backend first, then run this script.
"""

import requests
import time

API_URL = "http://localhost:8000/query"

def test_rate_limit():
    print("Testing rate limiting...")
    print(f"Making 12 requests quickly (limit is 10/minute)\n")

    for i in range(12):
        try:
            response = requests.post(
                API_URL,
                json={"query": "How many trips?"},
                timeout=5
            )
            print(f"Request {i+1}: Status {response.status_code}")

            if response.status_code == 429:
                print(f"✓ Rate limit kicked in at request {i+1}")
                print(f"  Response: {response.json()}")
                break
        except requests.exceptions.RequestException as e:
            print(f"Request {i+1}: Error - {e}")

        time.sleep(0.1)  # Small delay between requests

    print("\nTest complete!")

if __name__ == "__main__":
    test_rate_limit()
