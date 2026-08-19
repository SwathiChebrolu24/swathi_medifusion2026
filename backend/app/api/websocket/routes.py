from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.websocket_manager import manager
from app.core.security import decode_access_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time notifications.
    Connect via: ws://host/ws/{user_id}?token=<jwt>
    """
    # Authenticate before accepting
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    # Accept and register using the manager
    await manager.connect(websocket, user_id)
    logger.info(f"WebSocket connected: user_id={user_id}")

    try:
        # Welcome message
        await manager.send_personal_message({
            "type": "connection",
            "message": "Connected to MediFusion real-time notifications"
        }, user_id)

        # Keep alive
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WS message from user {user_id}: {data}")
            await manager.send_personal_message({
                "type": "echo",
                "message": f"Received: {data}"
            }, user_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
