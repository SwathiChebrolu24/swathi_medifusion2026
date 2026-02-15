import requests
import time
import random

BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    "/doctors",
    "/metrics",
    "/docs",
    "/openapi.json"
]

print(f"🚀 Starting traffic generation to {BASE_URL}...")
print("Press Ctrl+C to stop manually.")

try:
    for i in range(50):
        endpoint = random.choice(ENDPOINTS)
        url = f"{BASE_URL}{endpoint}"
        try:
            r = requests.get(url)
            print(f"[{i+1}/50] GET {endpoint} -> {r.status_code}")
        except Exception as e:
            print(f"[{i+1}/50] GET {endpoint} -> FAILED: {e}")
        
        time.sleep(random.uniform(0.1, 0.5))

    print("\n✅ Traffic generation complete!")
    print("Go to http://localhost:3000 to see the spikes in Grafana.")

except KeyboardInterrupt:
    print("\n🛑 Stopped by user.")
