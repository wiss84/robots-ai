from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv
import uvicorn
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import datetime
import time
from file_upload import router as file_upload_router
import requests
import base64
import traceback

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
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:4173",  # Vite preview
        "http://127.0.0.1:4173"
    ],
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
    messages: Optional[List[Dict[str, str]]] = None # Add messages field
    conversation_summary: Optional[str] = None  # Add conversation summary field

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    session_id: str

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
        "available_agents": ["travel", "realestate", "news", "finance", "shopping", "image", "coding", "games"]
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
from agent_games import router as games_router
from agent_games import graph as games_graph
from summarize import router as summarize_router

app.include_router(coding_router)
app.include_router(finance_router)
app.include_router(news_router)
app.include_router(realestate_router)
app.include_router(travel_router)
app.include_router(image_generator_router)
app.include_router(shopping_router)
app.include_router(games_router)
app.include_router(file_upload_router)
app.include_router(summarize_router)

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
    print("=== Received chat message ===")
    print(chat_request.message)
    try:
        print(f"=== CHAT REQUEST RECEIVED ===")
        print(f"Agent ID: {chat_request.agent_id}")
        print(f"Message: {chat_request.message[:100]}...")
        print(f"Conversation ID: {chat_request.conversation_id}")
        
        agent_id = chat_request.agent_id
        message = chat_request.message
        session_id = chat_request.session_id or "default"
        conversation_id = chat_request.conversation_id
        if not conversation_id:
            conversation_id = f"thread_{agent_id}_{int(time.time())}"
        
        print(f"Processing with conversation_id: {conversation_id}")
        
        agent_graphs = {
            "coding": coding_graph,
            "finance": finance_graph,
            "news": news_graph,
            "realestate": realestate_graph,
            "travel": travel_graph,
            "image": image_generator_graph,
            "shopping": shopping_graph,
            "games": games_graph,
        }
        
        if agent_id not in agent_graphs:
            print(f"ERROR: Unknown agent_id: {agent_id}")
            raise HTTPException(status_code=400, detail=f"Unknown agent_id: {agent_id}")
        
        print(f"Agent {agent_id} found, proceeding...")
        
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
        
        # Process image if provided
        if image_url:
            try:
                response = requests.get(image_url)
                response.raise_for_status()
                image_base64 = base64.b64encode(response.content).decode('utf-8')
                # Try to detect MIME type
                content_type = response.headers.get('content-type', 'image/webp')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    mime_type = 'image/jpeg'
                elif 'png' in content_type:
                    mime_type = 'image/png'
                elif 'gif' in content_type:
                    mime_type = 'image/gif'
            except Exception as e:
                print(f"Error processing image: {e}")
                # Continue without image if there's an error
        
        # Add user name to message if provided
        if hasattr(chat_request, 'user_name') and chat_request.user_name:
            message = f"[User Name: {chat_request.user_name}]\n{message}"
        
        # Add file content to message if provided
        if hasattr(chat_request, 'file_content') and chat_request.file_content:
            message = f"{message}\n\nFile Content:\n{chat_request.file_content}"
        
        # Load conversation summary into agent memory if provided
        if hasattr(chat_request, 'conversation_summary') and chat_request.conversation_summary:
            print(f"Loading conversation summary into agent memory: {chat_request.conversation_summary[:100]}...")
            # Add summary as context to the message
            summary_context = f"[Previous Conversation Summary: {chat_request.conversation_summary}]"
            message = f"{summary_context}\n\n{message}"
        
        print(f"Final message to agent: {message[:200]}...")
        
        # Create the appropriate message based on whether there's an image
        if image_base64:
            from langchain_core.messages import HumanMessage
            human_message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": message
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    }
                ]
            )
        else:
            from langchain_core.messages import HumanMessage
            human_message = HumanMessage(content=message)
        

        # Get the appropriate graph
        graph = agent_graphs[agent_id]

        # Create initial state (revert to single message)
        state = {"messages": [human_message]}

        # Configure the graph with conversation history
        config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 50}

        print(f"Invoking graph for agent {agent_id}...")

        # Invoke the graph
        result = graph.invoke(state, config=config)

        print(f"Graph invocation completed, processing result...")
        
        # Extract the response
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            
            # Handle different message types
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            else:
                response_content = str(last_message)
            
            # Debug logging for response content type
            print(f"Response content type: {type(response_content)}")
            if isinstance(response_content, list):
                print(f"Response content is a list with {len(response_content)} items")
                for i, item in enumerate(response_content):
                    print(f"  Item {i}: {type(item)} - {str(item)[:100]}...")
            
            # Ensure response_content is a string (handle lists, etc.)
            if not isinstance(response_content, str):
                if isinstance(response_content, list):
                    # Join list elements with newlines, filtering out empty strings
                    response_content = '\n'.join([str(item) for item in response_content if item])
                else:
                    response_content = str(response_content)
            
            # Check if response is empty and provide fallback
            if not response_content:
                response_content = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
            print(f"Response content length: {len(response_content)}")
            print(f"Response preview: {response_content[:100]}...")
            
            response = ChatResponse(
                response=response_content,
                conversation_id=conversation_id,
                session_id=session_id
            )
            
            print(f"Returning response successfully")
            return response
        else:
            print(f"No messages in result, returning fallback")
            return ChatResponse(
                response="No response generated. Please try again.",
                conversation_id=conversation_id,
                session_id=session_id
            )
            
    except Exception as e:
        import traceback
        print("=== ERROR IN /chat ENDPOINT ===")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        traceback.print_exc()
        
        # Handle specific API quota errors
        error_message = str(e)
        if "ResourceExhausted" in error_message or "quota" in error_message.lower():
            return ChatResponse(
                response="⚠️ **API Quota Exceeded**\n\nI've reached my current usage limit. Please try again in a few minutes, or consider:\n\n• Taking a short break between requests\n• Rephrasing your question more concisely\n• Using a different agent temporarily\n\nThis is a temporary limitation and should resolve shortly.",
                conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                session_id=session_id if 'session_id' in locals() else "error"
            )
        elif "rate limit" in error_message.lower() or "too many requests" in error_message.lower():
            return ChatResponse(
                response="⚠️ **Rate Limit Reached**\n\nI'm processing too many requests right now. Please wait a moment and try again.",
                conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                session_id=session_id if 'session_id' in locals() else "error"
            )
        else:
            # Generic error handling
            return ChatResponse(
                response=f"An unexpected error occurred: {error_message}. Please try again or contact support if the problem persists.",
                conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                session_id=session_id if 'session_id' in locals() else "error"
            )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2025-01-01T00:00:00Z"}