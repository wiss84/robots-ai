from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import ORJSONResponse
from file_create import router as file_create_router
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
from websocket_suggestions import router as websocket_suggestions_router
from websocket_file_changes import router as websocket_file_changes_router
from project_index import router as project_index_router
from server_sent_events import router as sse_router
import re
from rate_limiter import rate_limiter

# Load environment variables
load_dotenv()

# Initialize FastAPI app (lifespan removed)
app = FastAPI(
    title="LangGraph Agents Backend",
    description="Multi-agent system with memory and RAG",
    version="1.0.0",
    debug=True,
    default_response_class=ORJSONResponse
)
app.include_router(file_create_router)
app.include_router(websocket_suggestions_router)
app.include_router(websocket_file_changes_router)
app.include_router(project_index_router)
app.include_router(sse_router)

# Serve uploaded files as static
import os

def get_uploaded_files_directory():
    """
    Get uploaded files directory that works both in Docker and outside Docker
    """
    # Check if we're running in Docker (common indicators)
    is_docker = (
        os.path.exists('/.dockerenv') or
        os.environ.get('PYTHONPATH') == '/app' or
        os.getcwd() == '/app'
    )

    if is_docker:
        # We're in Docker - use the mounted volume path
        uploaded_files_dir = "/app/uploaded_files"
    else:
        # We're running normally - use relative paths
        uploaded_files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files")

    return os.path.abspath(uploaded_files_dir)

app.mount(
    "/uploaded_files",
    StaticFiles(directory=get_uploaded_files_directory()),
    name="uploaded_files"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:4173",  # Vite preview
        "http://127.0.0.1:4173",
        "ws://localhost:8000",    # WebSocket server
        "ws://127.0.0.1:8000"     # WebSocket server alternate
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
    response: str | dict  # Allow both string and dict for image responses
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
from agent_coding_ask import router as coding_ask_router
from agent_finance import router as finance_router
from agent_news import router as news_router
from agent_realestate import router as realestate_router
from agent_travel import router as travel_router
from agent_image_generator import router as image_generator_router
from agent_shopping import router as shopping_router
from agent_coding import graph as coding_graph
from agent_coding_ask import graph as coding_ask_graph
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
app.include_router(coding_ask_router)
app.include_router(finance_router)
app.include_router(news_router)
app.include_router(realestate_router)
app.include_router(travel_router)
app.include_router(image_generator_router)
app.include_router(shopping_router)
app.include_router(games_router)
app.include_router(file_upload_router)
app.include_router(summarize_router)
app.include_router(websocket_suggestions_router)
app.include_router(websocket_file_changes_router)
app.include_router(project_index_router)

def build_multimodal_message(text, image_base64, mime_type='image/webp'):
    """Build a multimodal message for Gemini: text + image."""
    return [
        {"type": "text", "text": text},
        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}}
    ]

def extract_real_token_usage(result):
    """
    Extract real token counts from LangChain response messages.
    Only counts tokens from the LAST message (current request).

    Returns:
        dict with 'input_tokens', 'output_tokens', 'total_tokens'
    """
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    if not result or not isinstance(result, dict) or "messages" not in result:
        return {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}

    # Only check the LAST message (the current response)
    if len(result["messages"]) > 0:
        last_message = result["messages"][-1]
        
        # Only AIMessage objects contain usage metadata
        if hasattr(last_message, 'usage_metadata') and last_message.usage_metadata:
            usage = last_message.usage_metadata

            # Extract token counts from usage metadata
            if isinstance(usage, dict):
                input_tokens = usage.get('input_tokens', 0)
                output_tokens = usage.get('output_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)

    return {
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': total_tokens
    }

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
        
        # Rate limiting check
        estimated_tokens = rate_limiter.estimate_tokens(message)
        print(f"📊 Rate limit check - Estimated tokens: {estimated_tokens}")
        model_to_use, delay_message = await rate_limiter.check_and_wait_if_needed(estimated_tokens)
        
        # If there's a delay message, inform the frontend to show countdown and auto-retry
        if delay_message:
            print(f"Rate limiting: {delay_message}")
            # If model switch requires summarization, keep existing behavior
            if "Switched to" in delay_message and "summarized" in delay_message:
                return ChatResponse(
                    response=f"🔄 {delay_message}",
                    conversation_id=conversation_id,
                    session_id=session_id
                )
            else:
                # Return a standardized waiting message for the client to handle a countdown and auto-retry
                seconds = getattr(rate_limiter, "delay_when_approaching_limit", 30)
                return ChatResponse(
                    response=f"⏳ Waiting {seconds} seconds to avoid rate limits...",
                    conversation_id=conversation_id,
                    session_id=session_id
                )
        
        print(f"Using model: {model_to_use}")
        
        agent_graphs = {
            "coding": coding_graph,
            "coding-ask": coding_ask_graph,
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
        
        # Handle image base64 data
        image_base64 = None
        mime_type = None
        
        # Check for image data in the message
        match = re.search(r"\[Image: (data:([^;]+);base64,[^\]]+)\]", message)
        if match:
            data_url = match.group(1)
            mime_type = match.group(2)
            image_base64 = data_url.split('base64,')[1]
            # Remove the [Image: ...] part from the message
            message = re.sub(r"\n?\[Image: data:[^;]+;base64,[^\]]+\]", "", message).strip()
        
        # Add user name to message if provided
        if hasattr(chat_request, 'user_name') and chat_request.user_name:
            message = f"[User Name: {chat_request.user_name}]\n{message}"
        
        # Add file content to message if provided
        if hasattr(chat_request, 'file_content') and chat_request.file_content:
            if chat_request.file_content.startswith('data:'):
                # It's base64 data, likely an image
                try:
                    data_parts = chat_request.file_content.split(',', 1)
                    mime_type = data_parts[0].split(':')[1].split(';')[0]
                    # Use image_base64 only for actual images
                    if mime_type.startswith('image/'):
                        image_base64 = data_parts[1]
                    else:
                        # For non-image files with base64 content, try to decode
                        import base64
                        try:
                            file_content = base64.b64decode(data_parts[1]).decode('utf-8')
                            message = f"{message}\n\nFile Content:\n{file_content}"
                        except:
                            print("Error decoding base64 file content")
                except:
                    print("Error parsing base64 data")
            else:
                # Format the file content nicely
                content_lines = chat_request.file_content.splitlines()
                if len(content_lines) > 50:  # Truncate very long files
                    content = '\n'.join(content_lines[:50]) + '\n... (truncated for brevity)'
                else:
                    content = chat_request.file_content
                message = f"{message}\n\nFile Content:\n{content}"
        
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
        config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 60}

        print(f"Invoking graph for agent {agent_id}...")

        # Invoke the graph
        result = await graph.ainvoke(state, config=config)

        print(f"Graph invocation completed, processing result...")

        # Extract real token counts from the response
        real_token_usage = extract_real_token_usage(result)

        if real_token_usage['total_tokens'] > 0:
            # Use actual API token counts
            actual_tokens = real_token_usage['total_tokens']
            print(f"✅ Real token usage: {real_token_usage['input_tokens']} input + {real_token_usage['output_tokens']} output = {actual_tokens} total")
        else:
            # Fall back to estimation
            response_tokens = 0
            if result and "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if hasattr(last_message, 'content'):
                    response_tokens = rate_limiter.estimate_tokens(str(last_message.content))
            actual_tokens = estimated_tokens + response_tokens
            print(f"⚠️ Estimated token usage: {estimated_tokens} input + {response_tokens} output = {actual_tokens} total")

        # Show current token count before recording (without triggering resets)
        current_usage = rate_limiter.usage[model_to_use]
        print(f"📊 Before recording: {model_to_use} - Tokens: {current_usage.tokens_this_minute}/{rate_limiter.model_limits[model_to_use].tokens_per_minute}, Requests: {current_usage.requests_this_minute}/{rate_limiter.model_limits[model_to_use].requests_per_minute}")

        rate_limiter.record_request(model_to_use, actual_tokens)

        # Show updated stats after recording
        updated_usage = rate_limiter.usage[model_to_use]
        print(f"📊 After recording: {model_to_use} - Tokens: {updated_usage.tokens_this_minute}/{rate_limiter.model_limits[model_to_use].tokens_per_minute}, Requests: {updated_usage.requests_this_minute}/{rate_limiter.model_limits[model_to_use].requests_per_minute}")
        
        # Extract the response
        if result and "messages" in result and result["messages"]:
            print(f"Graph execution successful with {len(result['messages'])} messages")
            last_message = result["messages"][-1]

            # Handle different message types
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            else:
                response_content = str(last_message)

            # Ensure response_content is a string (handle lists, etc.)
            if not isinstance(response_content, str):
                if isinstance(response_content, list):
                    # Join list elements with newlines, filtering out empty strings
                    response_content = '\n'.join([str(item) for item in response_content if item])
                else:
                    response_content = str(response_content)

            # Check if response is empty and provide fallback
            if not response_content or str(response_content).strip() == "":
                from constants import EMPTY_RESPONSE_MESSAGE
                response_content = EMPTY_RESPONSE_MESSAGE

            response = ChatResponse(
                response=response_content,
                conversation_id=conversation_id,
                session_id=session_id
            )

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
        
        # Handle specific API quota errors with enhanced model switching
        from constants import API_QUOTA_ERROR_MESSAGE, RATE_LIMIT_ERROR_MESSAGE
        error_message = str(e)

        # Use enhanced rate limiter error handling for quota exceeded errors
        if "ResourceExhausted" in error_message or "quota" in error_message.lower():
            # Try to switch models and get updated model information
            new_model, switch_message = rate_limiter.record_request_with_error_handling(
                model_to_use if 'model_to_use' in locals() else rate_limiter.current_model,
                estimated_tokens if 'estimated_tokens' in locals() else 1000,
                error_message,
                agent_id if 'agent_id' in locals() else "",
                conversation_id if 'conversation_id' in locals() else ""
            )

            # If model was switched, return informative message
            if switch_message and "Automatically switched to" in switch_message:
                return ChatResponse(
                    response=f"🔄 {switch_message} Please retry your request.",
                    conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                    session_id=session_id if 'session_id' in locals() else "error"
                )
            else:
                # Handle different exhaustion scenarios
                if switch_message == "ALL_MODELS_EXHAUSTED":
                    # All models have reached daily limits
                    return ChatResponse(
                        response="🚫 **All Daily Quotas Exhausted**\n\nAll available models have reached their daily request limits. This means:\n\n✅ **You've used all 1,500 daily requests** across all models\n🔄 **Quotas reset daily** at midnight UTC\n⏰ **Try again tomorrow** for fresh quotas\n\nThank you for being a power user! 💪",
                        conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                        session_id=session_id if 'session_id' in locals() else "error"
                    )
                elif switch_message and switch_message.startswith("TEMPORARY_API_ISSUE:"):
                    # Temporary API issue, not daily limit exhaustion
                    failed_model = switch_message.split(":")[1]
                    return ChatResponse(
                        response="🌐 **Temporary API Issue Detected**\n\nGoogle Gemini API is experiencing temporary issues with the " + failed_model + " model:\n\n🔧 **This appears to be a temporary problem** from Google's side\n⏰ **Please try again tomorrow or at midnight**\n🔄 **Quotas should resume normally** once the API issue is resolved\n\nThis is not related to your usage limits.",
                        conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                        session_id=session_id if 'session_id' in locals() else "error"
                    )
                else:
                    # Fallback to the enhanced general message
                    return ChatResponse(
                        response=API_QUOTA_ERROR_MESSAGE,
                        conversation_id=conversation_id if 'conversation_id' in locals() else "error",
                        session_id=session_id if 'session_id' in locals() else "error"
                    )
        elif "rate limit" in error_message.lower() or "too many requests" in error_message.lower():
            return ChatResponse(
                response=RATE_LIMIT_ERROR_MESSAGE,
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

@app.get("/rate-limit-stats")
async def get_rate_limit_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current rate limiting statistics"""
    return rate_limiter.get_usage_stats()