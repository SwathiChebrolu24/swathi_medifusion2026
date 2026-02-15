import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws/1?token=test"
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            message = await websocket.recv()
            print(f"Received: {message}")
    except Exception as e:
        print(f"❌ Error: {e}")

asyncio.run(test_websocket())
