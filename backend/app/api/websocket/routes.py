from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
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
    
    Connect via: ws://localhost:8000/ws/{user_id}?token={jwt_token}
    """
    # MUST accept connection first before any other operations
    await websocket.accept()
    
    # Authenticate user
    try:
        payload = decode_access_token(token)
        token_username = payload.get("sub")
        
        if not token_username:
            await websocket.close(code=1008, reason="Invalid token")
            return
            
        # Note: We accept the connection if token is valid
        # The user_id in URL is just for routing, token validates identity
        
    except Exception as e:
        logger.error(f"WebSocket auth failed: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Register connection with manager
    manager.active_connections[user_id] = manager.active_connections.get(user_id, [])
    manager.active_connections[user_id].append(websocket)
    logger.info(f"WebSocket connected for user {user_id}")
    
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "connection",
            "message": "Connected to MediFusion real-time notifications"
        }, user_id)
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received from user {user_id}: {data}")
            
            # Echo back for now (can add message handling logic here)
            await manager.send_personal_message({
                "type": "echo",
                "message": f"Received: {data}"
            }, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)
