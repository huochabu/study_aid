from fastapi import WebSocket
from typing import Dict, List
import logging
import json

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Store active connections: client_id (file_id) -> List[WebSocket]
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"WebSocket connected: {client_id}")

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"WebSocket disconnected: {client_id}")

    async def broadcast(self, message: dict, client_id: str):
        """Broadcast message to all connections subscribing to this client_id (file_id)"""
        if client_id in self.active_connections:
            # Filter out closed connections during iteration if needed, 
            # but simpler to just try-send and let the loop handle it implies safety
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                    logger.info(f"Sent WS message to {client_id}")
                except Exception as e:
                    logger.error(f"Error sending WS message to {client_id}: {e}")
