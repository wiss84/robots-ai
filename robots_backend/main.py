from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import uvicorn
from langchain_core.messages import HumanMessage
import datetime
import time
from file_upload import router as file_upload_router
import requests
import base64

# Load environment variables
load_dotenv()

# Global variables (will be replaced with proper initialization)
agents = {}
memory_store = None
vector_store = None

# Initialize FastAPI app (lifespan removed)
app = FastAPI(
    title="LangGraph Agents Backend",
    description="Multi-agent system with memory and RAG",
    version="1.0.0",
    debug=True
)

# Serve uploaded files as static
app.mount("/uploaded_files", StaticFiles(directory="uploaded_files"), name="uploaded_files")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    agent_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Add conversation_id field
    file_content: Optional[str] = None  # Add file content field
    user_name: Optional[str] = None  # Add user name field

class ChatResponse(BaseModel):
    response: str
    agent_id: str
    session_id: str
    conversation_id: str  # Add conversation_id to response
    memory_updated: bool = False

class AgentInfo(BaseModel):
    id: str
    name: str
    description: str
    avatar: str
    keywords: List[str]
    capabilities: List[str]
    status: str = "active"

@app.get("/")
async def root():
    return {
        "message": "LangGraph Agents Backend", 
        "version": "1.0.0",
        "status": "running",
        "available_agents": ["travel", "realestate", "news", "finance", "shopping", "image", "coding"]
    }

from agent_coding import router as coding_router
from agent_finance import router as finance_router
from agent_news import router as news_router
from agent_realestate import router as realestate_router
from agent_travel import router as travel_router
from agent_image_generator import router as image_generator_router
from agent_shopping import router as shopping_router
from agent_coding import graph as coding_graph
from agent_finance import graph as finance_graph
from agent_news import graph as news_graph
from agent_realestate import graph as realestate_graph
from agent_travel import graph as travel_graph
from agent_image_generator import graph as image_generator_graph
from agent_shopping import graph as shopping_graph

app.include_router(coding_router)
app.include_router(finance_router)
app.include_router(news_router)
app.include_router(realestate_router)
app.include_router(travel_router)
app.include_router(image_generator_router)
app.include_router(shopping_router)
app.include_router(file_upload_router)

def build_multimodal_message(text, image_base64, mime_type='image/webp'):
    """Build a multimodal message for Gemini: text + image."""
    return [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
    ]

# Unified chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    chat_request: ChatMessage,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        agent_id = chat_request.agent_id
        message = chat_request.message
        session_id = chat_request.session_id or "default"
        conversation_id = chat_request.conversation_id
        if not conversation_id:
            conversation_id = f"thread_{agent_id}_{int(time.time())}"
        agent_graphs = {
            "coding": coding_graph,
            "finance": finance_graph,
            "news": news_graph,
            "realestate": realestate_graph,
            "travel": travel_graph,
            "image": image_generator_graph,
            "shopping": shopping_graph,
        }
        if agent_id not in agent_graphs:
            raise HTTPException(status_code=400, detail=f"Unknown agent_id: {agent_id}")
        # Detect image URL in message
        image_url = None
        import re
        match = re.search(r"\[Image: (http[s]?://[^\]]+)\]", message)
        if match:
            image_url = match.group(1)
            # Remove the [Image: ...] part from the message
            message = re.sub(r"\n?\[Image: http[s]?://[^\]]+\]", "", message).strip()
        image_base64 = None
        mime_type = 'image/webp'
        if image_url:
            # Extract filename from URL and read directly from disk
            match = re.search(r'/uploaded_files/([^/]+)$', image_url)
            if match:
                filename = match.group(1)
                file_path = os.path.join(os.getcwd(), "uploaded_files", filename)
                try:
                    with open(file_path, "rb") as f:
                        image_bytes = f.read()
                        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                        # Try to guess mime type from extension
                        ext = filename.split('.')[-1].lower()
                        if ext in ['jpg', 'jpeg']:
                            mime_type = 'image/jpeg'
                        elif ext == 'png':
                            mime_type = 'image/png'
                        elif ext == 'webp':
                            mime_type = 'image/webp'
                        elif ext == 'gif':
                            mime_type = 'image/gif'
                except Exception as e:
                    print(f"Failed to read/encode image from disk: {e}")
            else:
                print("Could not extract filename from image_url")
        # Build state with multimodal message if image present
        if image_base64:
            message_content = build_multimodal_message(message, image_base64, mime_type)
            state = {"messages": [HumanMessage(content=message_content)]}
        else:
            state = {"messages": [HumanMessage(content=message)]}
        # Add file content to the message if provided
        if chat_request.file_content:
            file_context = f"\n\n[Uploaded File Content:\n{chat_request.file_content}\n]"
            if image_base64:
                # Add file content as an extra text part in multimodal message
                state["messages"][0].content.insert(1, {"type": "text", "text": file_context})
            else:
                state["messages"][0].content += file_context
        # Add user name to the message if provided
        if chat_request.user_name:
            user_context = f"\n\n[User Name: {chat_request.user_name}]"
            if image_base64:
                # Add user name as an extra text part in multimodal message
                state["messages"][0].content.insert(1, {"type": "text", "text": user_context})
            else:
                state["messages"][0].content += user_context
        # Use the original config format for LangGraph 0.2.0
        config = {"configurable": {"thread_id": conversation_id}}
        result = agent_graphs[agent_id].invoke(state, config=config)  # type: ignore
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                response_text = last_message.content
            elif isinstance(last_message, dict) and 'content' in last_message:
                response_text = last_message['content']
            else:
                response_text = str(last_message)
            if isinstance(response_text, list):
                response_text = '\n'.join(str(item).strip() for item in response_text if str(item).strip())
                response_text = response_text.replace('```\n*', '```\n\n*')
                response_text = response_text.replace('```\n-', '```\n\n-')
                response_text = response_text.replace('```\n1.', '```\n\n1.')  
                response_text = response_text.replace('```\n#', '```\n\n#')   
            response_text = str(response_text)
        else:
            response_text = "No response generated. Please try again."
        return ChatResponse(
            response=response_text,
            agent_id=agent_id,
            session_id=session_id,
            conversation_id=conversation_id,
            memory_updated=True
        )
    except Exception as e:
        import traceback
        print("=== ERROR IN /chat ENDPOINT ===")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}