from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, Any, Optional
import json
import asyncio
import time
import uuid
import logging
from collections import defaultdict
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define models for file change events
class FileChangeEvent(BaseModel):
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    file_path: str
    is_directory: bool
    timestamp: float
    old_path: Optional[str] = None  # For move events

class FileConnectionInfo(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    websocket: WebSocket
    user_id: Optional[str]
    connected_at: float
    last_ping: float
    connection_id: str

# Connection manager for file change notifications
class FileChangeConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, FileConnectionInfo] = {}
        self.heartbeat_interval = 10  # seconds
        self.connection_timeout = 60  # seconds
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task to clean up stale connections"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())
    
    async def _cleanup_stale_connections(self):
        """Remove connections that haven't pinged recently"""
        while True:
            try:
                current_time = time.time()
                stale_connections = []
                
                for conn_id, conn_info in self.active_connections.items():
                    if current_time - conn_info.last_ping > self.connection_timeout:
                        stale_connections.append(conn_id)
                
                for conn_id in stale_connections:
                    await self._force_disconnect(conn_id)
                    logger.info(f"Cleaned up stale connection: {conn_id}")
                
                await asyncio.sleep(self.heartbeat_interval)
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    async def _force_disconnect(self, connection_id: str):
        """Force disconnect a connection"""
        if connection_id in self.active_connections:
            try:
                conn_info = self.active_connections[connection_id]
                await conn_info.websocket.close()
            except Exception:
                pass  # Connection might already be closed
            finally:
                del self.active_connections[connection_id]
    
    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None) -> str:
        """Connect a new WebSocket for file change notifications"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        current_time = time.time()
        
        conn_info = FileConnectionInfo(
            websocket=websocket,
            user_id=user_id,
            connected_at=current_time,
            last_ping=current_time,
            connection_id=connection_id
        )
        
        self.active_connections[connection_id] = conn_info
        
        logger.info(f"New file change connection: {connection_id}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            logger.info(f"File change connection disconnected: {connection_id}")
    
    def update_ping(self, connection_id: str):
        """Update last ping time for a connection"""
        if connection_id in self.active_connections:
            self.active_connections[connection_id].last_ping = time.time()
    
    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                conn_info = self.active_connections[connection_id]
                await conn_info.websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(f"Error sending to file change connection {connection_id}: {e}")
                await self._force_disconnect(connection_id)
        return False
    
    async def broadcast_file_change(self, event: FileChangeEvent) -> int:
        """Broadcast file change event to all connected clients"""
        message = {
            "type": "file_change",
            "data": {
                "event_type": event.event_type,
                "file_path": event.file_path,
                "is_directory": event.is_directory,
                "timestamp": event.timestamp,
                "old_path": event.old_path
            }
        }
        
        sent_count = 0
        disconnected_connections = []
        
        for conn_id, conn_info in self.active_connections.items():
            try:
                await conn_info.websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting to connection {conn_id}: {e}")
                disconnected_connections.append(conn_id)
        
        # Clean up failed connections
        for conn_id in disconnected_connections:
            await self._force_disconnect(conn_id)
        
        logger.info(f"Broadcasted file change event to {sent_count} connections")
        return sent_count
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "connection_id": conn_id,
                    "user_id": conn_info.user_id,
                    "connected_at": conn_info.connected_at,
                    "last_ping": conn_info.last_ping
                }
                for conn_id, conn_info in self.active_connections.items()
            ]
        }

# Global connection manager instance
file_change_manager = FileChangeConnectionManager()

# Create router for file change WebSocket endpoints
router = APIRouter()

# Function to be called by the file watcher
async def notify_file_change(event_type: str, file_path: str, is_directory: bool = False, old_path: Optional[str] = None):
    """Function to be called by the file system watcher to notify clients"""
    event = FileChangeEvent(
        event_type=event_type,
        file_path=file_path,
        is_directory=is_directory,
        timestamp=time.time(),
        old_path=old_path
    )
    
    await file_change_manager.broadcast_file_change(event)

# Endpoint to get file change connection statistics
@router.get("/file-changes/stats")
async def get_file_change_stats():
    return file_change_manager.get_connection_stats()

# WebSocket endpoint for file change notifications
@router.websocket("/ws/file-changes")
async def websocket_file_changes(websocket: WebSocket):
    connection_id = None
    
    try:
        user_id: Optional[str] = websocket.query_params.get("user_id")
        
        # Connect to the manager
        connection_id = await file_change_manager.connect(websocket, user_id)
        
        # Send initial connection confirmation
        await file_change_manager.send_to_connection(connection_id, {
            "type": "init",
            "connection_id": connection_id,
            "timestamp": time.time()
        })
        
        # Keep the connection alive and handle messages
        last_ping_time = time.time()
        while True:
            try:
                # Send a ping to the client periodically
                if time.time() - last_ping_time > file_change_manager.heartbeat_interval:
                    await file_change_manager.send_to_connection(connection_id, {"type": "ping"})
                    last_ping_time = time.time()

                # Wait for a message from the frontend with a timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                continue # No message received, continue to next loop iteration to send ping if needed


            
            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "pong":
                    file_change_manager.update_ping(connection_id)
                    continue
                
                # Update ping time for any message received
                file_change_manager.update_ping(connection_id)

                if message_type == "heartbeat":
                    # Explicit heartbeat from client
                    await file_change_manager.send_to_connection(connection_id, {
                        "type": "heartbeat_ack",
                        "timestamp": time.time()
                    })
                else:
                    # Unknown message type
                    await file_change_manager.send_to_connection(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": time.time()
                    })
            except json.JSONDecodeError:
                # Not a JSON message, treat as plain text
                await file_change_manager.send_to_connection(connection_id, {
                    "type": "echo",
                    "message": data,
                    "timestamp": time.time()
                })

                
                # Update ping time for any message received
                file_change_manager.update_ping(connection_id)
                
                # Handle different message types
                if message_type == "ping":
                    await file_change_manager.send_to_connection(connection_id, {
                        "type": "pong",
                        "timestamp": time.time()
                    })
                    
                elif message_type == "heartbeat":
                    # Explicit heartbeat from client
                    await file_change_manager.send_to_connection(connection_id, {
                        "type": "heartbeat_ack",
                        "timestamp": time.time()
                    })
                    
                else:
                    # Unknown message type
                    await file_change_manager.send_to_connection(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": time.time()
                    })
                    
            except json.JSONDecodeError:
                # Not a JSON message, treat as plain text
                await file_change_manager.send_to_connection(connection_id, {
                    "type": "echo",
                    "message": data,
                    "timestamp": time.time()
                })
                
    except WebSocketDisconnect:
        if connection_id:
            await file_change_manager.disconnect(connection_id)
        logger.info(f"File change WebSocket disconnected: {connection_id}")
        
    except Exception as e:
        logger.error(f"Error in file change WebSocket: {e}")
        if connection_id:
            await file_change_manager.disconnect(connection_id)