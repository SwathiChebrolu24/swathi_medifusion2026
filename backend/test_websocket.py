"""
WebSocket Test Script
Tests if WebSocket notifications are sent when doctor accepts a case
"""
import requests
import json

API_BASE = "http://localhost:8000"

# Step 1: Login as patient
print("1. Logging in as patient...")
patient_login = requests.post(f"{API_BASE}/auth/login", data={
    "username": "patient1",
    "password": "patient123"
})
if patient_login.status_code != 200:
    print(f"❌ Patient login failed: {patient_login.text}")
    exit(1)
patient_token = patient_login.json()["access_token"]
patient_user = patient_login.json()["user"]
print(f"✅ Patient logged in: {patient_user['username']} (ID: {patient_user['id']})")

# Step 2: Login as doctor
print("\n2. Logging in as doctor...")
doctor_login = requests.post(f"{API_BASE}/auth/login", data={
    "username": "shiva",
    "password": "shiva123"
})
if doctor_login.status_code != 200:
    print(f"❌ Doctor login failed: {doctor_login.text}")
    exit(1)
doctor_token = doctor_login.json()["access_token"]
doctor_user = doctor_login.json()["user"]
print(f"✅ Doctor logged in: {doctor_user['username']} (ID: {doctor_user['id']})")

# Step 3: Get open pool cases
print("\n3. Getting open pool cases...")
pool_response = requests.get(
    f"{API_BASE}/doctor/cases/pool",
    headers={"Authorization": f"Bearer {doctor_token}"}
)
if pool_response.status_code != 200:
    print(f"❌ Failed to get pool cases: {pool_response.text}")
    exit(1)
pool_cases = pool_response.json()
print(f"✅ Found {len(pool_cases)} cases in pool")

if len(pool_cases) == 0:
    print("⚠️ No cases in pool. Please submit a case first.")
    exit(0)

# Step 4: Accept first case
case_to_accept = pool_cases[0]
print(f"\n4. Accepting case {case_to_accept['id']} (patient: {case_to_accept['patient_name']})...")
accept_response = requests.post(
    f"{API_BASE}/doctor/cases/{case_to_accept['id']}/accept",
    headers={"Authorization": f"Bearer {doctor_token}"}
)
if accept_response.status_code != 200:
    print(f"❌ Failed to accept case: {accept_response.text}")
    exit(1)
print(f"✅ Case accepted successfully")

# Step 5: Check backend logs for WebSocket notification
print("\n5. Check the backend logs for:")
print(f"   'WebSocket notification sent to patient {patient_user['id']}'")
print(f"\n6. Check the patient dashboard browser console for:")
print(f"   '📨 WebSocket message: {{type: \"case_update\", message: \"Your case has been accepted...\"}}'")
print(f"\n✅ Test complete! If you see the messages above, WebSocket is working.")
