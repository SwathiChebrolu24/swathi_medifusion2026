import asyncio
import sys

if "pytest" in sys.modules:
    import pytest
    pytest.skip("Manual integration script; run directly instead", allow_module_level=True)

async def test_websocket():
    import websockets

    uri = "ws://localhost:8000/ws/1?token=test"
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            message = await websocket.recv()
            print(f"Received: {message}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
