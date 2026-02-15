import requests
import sys

url = "http://127.0.0.1:8000/auth/signup"
headers = {
    "Origin": "http://localhost:3000",
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type"
}

try:
    print("--- OPTIONS ---")
    response = requests.options(url, headers=headers)
    print(f"Status: {response.status_code}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"ACAO: {response.headers['Access-Control-Allow-Origin']}")
    else:
        print("ACAO: MISSING")
        
    print("\n--- POST ---")
    post_headers = {"Origin": "http://localhost:3000", "Content-Type": "application/json"}
    response = requests.post(url, json={"username": "test_post", "password": "pw", "full_name": "Test", "email": "p@t.com", "role": "patient"}, headers=post_headers)
    print(f"Status: {response.status_code}")
    if "Access-Control-Allow-Origin" in response.headers:
        print(f"ACAO: {response.headers['Access-Control-Allow-Origin']}")
    else:
        print("ACAO: MISSING")
    
    print(f"Response: {response.text[:100]}")
        
except Exception as e:
    print(f"Error: {e}")
