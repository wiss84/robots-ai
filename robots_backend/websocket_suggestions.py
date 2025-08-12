from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from fastapi.security.utils import get_authorization_scheme_param
from fastapi import Depends
from typing import Optional, Dict, List, Set, Any
from jose import JWTError, jwt  # Only if using JWT, else replace validation logic
import os
import json
import asyncio
import time
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define models for agent suggestions
class AgentSuggestion(BaseModel):
    filePath: str
    originalContent: str
    proposedContent: str
    description: str
    suggestion_id: Optional[str] = None
    timestamp: Optional[float] = None
    agent_type: Optional[str] = "coding"

class ConnectionInfo(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    websocket: WebSocket
    agent_type: str
    user_id: Optional[str]
    connected_at: float
    last_ping: float
    connection_id: str

# Enhanced Connection manager with modern features
class EnhancedConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, ConnectionInfo] = {}
        self.connections_by_agent: Dict[str, Set[str]] = defaultdict(set)
        self.heartbeat_interval = 30  # seconds
        self.connection_timeout = 60  # seconds
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background task for connection cleanup"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())
    
    async def _cleanup_stale_connections(self):
        """Background task to clean up stale connections"""
        while True:
            try:
                current_time = time.time()
                stale_connections = []
                
                for conn_id, conn_info in self.active_connections.items():
                    if current_time - conn_info.last_ping > self.connection_timeout:
                        stale_connections.append(conn_id)
                
                for conn_id in stale_connections:
                    logger.info(f"Cleaning up stale connection: {conn_id}")
                    await self._force_disconnect(conn_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(30)
    
    async def connect(self, websocket: WebSocket, agent_type: str, user_id: Optional[str] = None) -> str:
        """Connect a new WebSocket with enhanced tracking"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        current_time = time.time()
        
        conn_info = ConnectionInfo(
            websocket=websocket,
            agent_type=agent_type,
            user_id=user_id,
            connected_at=current_time,
            last_ping=current_time,
            connection_id=connection_id
        )
        
        self.active_connections[connection_id] = conn_info
        self.connections_by_agent[agent_type].add(connection_id)
        
        logger.info(f"New connection: {connection_id} for agent: {agent_type}")
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection"""
        if connection_id in self.active_connections:
            conn_info = self.active_connections[connection_id]
            self.connections_by_agent[conn_info.agent_type].discard(connection_id)
            del self.active_connections[connection_id]
            logger.info(f"Disconnected: {connection_id}")
    
    async def _force_disconnect(self, connection_id: str):
        """Force disconnect a stale connection"""
        if connection_id in self.active_connections:
            conn_info = self.active_connections[connection_id]
            try:
                await conn_info.websocket.close()
            except Exception:
                pass  # Connection might already be closed
            await self.disconnect(connection_id)
    
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
                logger.error(f"Error sending to connection {connection_id}: {e}")
                await self._force_disconnect(connection_id)
        return False
    
    async def broadcast_to_agent_type(self, agent_type: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all connections of a specific agent type"""
        sent_count = 0
        connection_ids = list(self.connections_by_agent[agent_type])
        
        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, message):
                sent_count += 1
        
        return sent_count
    
    async def send_suggestion(self, suggestion: AgentSuggestion, agent_type: str = None) -> int:
        """Send suggestion to connections"""
        if not suggestion.suggestion_id:
            suggestion.suggestion_id = str(uuid.uuid4())
        if not suggestion.timestamp:
            suggestion.timestamp = time.time()
        
        target_agent = agent_type or suggestion.agent_type or "coding"
        
        message = {
            "type": "agent_suggestion",
            "data": suggestion.dict()
        }
        
        return await self.broadcast_to_agent_type(target_agent, message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        stats = {
            "total_connections": len(self.active_connections),
            "connections_by_agent": {}
        }
        
        for agent_type, conn_ids in self.connections_by_agent.items():
            stats["connections_by_agent"][agent_type] = len(conn_ids)
        
        return stats

router = APIRouter()
manager = EnhancedConnectionManager()

# Example secret key for JWT (replace with your actual secret if using JWT)
SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

async def validate_token(token: str) -> bool:
    # Replace with your actual validation logic (JWT or DB check)
    try:
        # Example for JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Optionally check claims, expiration, etc.
        return True
    except JWTError:
        return False

# Endpoint to send a suggestion to connected clients
@router.post("/suggestions/send")
async def send_suggestion(suggestion: AgentSuggestion, agent_type: str = "coding"):
    sent_count = await manager.send_suggestion(suggestion, agent_type)
    return {
        "status": "suggestion sent",
        "sent_to_connections": sent_count,
        "suggestion_id": suggestion.suggestion_id
    }

# Endpoint to get connection statistics
@router.get("/suggestions/stats")
async def get_connection_stats():
    return manager.get_connection_stats()

# Enhanced WebSocket endpoint for real-time suggestions
@router.websocket("/ws/suggestions")
async def websocket_suggestions(websocket: WebSocket):
    connection_id = None
    
    try:
        # Get query parameters
        params = dict(websocket.query_params)
        agent_type = params.get('agent_type', 'coding')  # Default to 'coding' if not provided
        token: Optional[str] = websocket.query_params.get("token")
        agent_type: str = websocket.query_params.get("agent_type", "coding")
        user_id: Optional[str] = websocket.query_params.get("user_id")
        
        if not token:
            # Try to get token from headers (e.g., 'Authorization: Bearer <token>')
            auth_header = websocket.headers.get("authorization")
            if auth_header:
                scheme, param = get_authorization_scheme_param(auth_header)
                if scheme.lower() == "bearer":
                    token = param
        
        # Token validation (commented out for development)
        # if not token or not await validate_token(token):
        #     await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        #     return
        
        # Extract token and user_id from query params
        token = params.get('token')
        user_id = None  # You can get user_id from token if needed
        
        # Connect to the enhanced manager with the correct agent_type
        connection_id = await manager.connect(websocket, agent_type, user_id)
        
        # Send initial connection confirmation
        await manager.send_to_connection(connection_id, {
            "type": "init",
            "connection_id": connection_id,
            "agent_type": agent_type,
            "timestamp": time.time()
        })
        
        # Keep the connection alive and handle messages
        while True:
            # Wait for a message from the frontend
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Update ping time for any message received
                manager.update_ping(connection_id)
                
                # Handle different message types
                if message_type == "ping":
                    await manager.send_to_connection(connection_id, {
                        "type": "pong",
                        "timestamp": time.time()
                    })
                    
                elif message_type == "request_suggestion":
                    # This would trigger the agent to generate a suggestion
                    file_path = message.get("file_path")
                    context = message.get("context", {})
                    
                    await manager.send_to_connection(connection_id, {
                        "type": "ack",
                        "message": "Suggestion request received",
                        "file_path": file_path,
                        "request_id": message.get("request_id")
                    })
                    
                elif message_type == "feedback":
                    # Handle feedback on suggestions (accept/reject)
                    feedback = message.get("feedback")
                    suggestion_id = message.get("suggestion_id")
                    
                    logger.info(f"Received feedback: {feedback} for suggestion: {suggestion_id}")
                    
                    await manager.send_to_connection(connection_id, {
                        "type": "feedback_received",
                        "suggestion_id": suggestion_id,
                        "feedback": feedback,
                        "timestamp": time.time()
                    })
                    
                elif message_type == "heartbeat":
                    # Explicit heartbeat from client
                    await manager.send_to_connection(connection_id, {
                        "type": "heartbeat_ack",
                        "timestamp": time.time()
                    })
                    
                else:
                    # Unknown message type
                    await manager.send_to_connection(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": time.time()
                    })
                    
            except json.JSONDecodeError:
                # Not a JSON message, treat as plain text
                await manager.send_to_connection(connection_id, {
                    "type": "echo",
                    "message": data,
                    "timestamp": time.time()
                })
                
    except WebSocketDisconnect:
        if connection_id:
            await manager.disconnect(connection_id)
        logger.info(f"WebSocket disconnected: {connection_id}")
        
    except Exception as e:
        logger.error(f"WebSocket error for connection {connection_id}: {e}")
        if connection_id:
            await manager.disconnect(connection_id)
        try:
            await websocket.close()
        except Exception:
            pass  # Connection might already be closed
