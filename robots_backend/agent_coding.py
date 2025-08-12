from fastapi import APIRouter, Body
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from composio_langchain import ComposioToolSet, Action, App
import os
import time
import json

# Cancellation registry for streaming conversations
CANCELLED_THREADS: set[str] = set()

from agents_system_prompts import CODING_AGENT_SYSTEM_PROMPT
from agent_coding_tools import (
    file_read_tool,
    create_directory_tool,
    create_file_tool,
    file_delete_tool,
    file_rename_tool,
    project_index_tool,
)
from send_suggestion_tool import send_suggestion_tool
from enhanced_coding_tools import (
    code_search,
    analyze_file,
    project_structure_analysis,
    find_related_files
)
from subtask_tool import (
    create_task_plan,
    manage_task_progress,
    get_task_suggestions
)
composio_toolset = ComposioToolSet(api_key=os.getenv('COMPOSIO_API_KEY'))
search_tools = composio_toolset.get_tools(actions=['COMPOSIO_SEARCH_SEARCH'])

router = APIRouter(prefix="/coding", tags=["coding"])

# Use imported system prompt
def get_system_prompt():
    return CODING_AGENT_SYSTEM_PROMPT

# Import dynamic model configuration
from dynamic_model_config import get_current_gemini_model

# Initialize Gemini LLM with dynamic model selection
def get_llm():
    return get_current_gemini_model(temperature=0.1)

llm = get_llm()

tools = [
    # Basic file operations
    file_read_tool,
    create_directory_tool,
    create_file_tool,
    file_delete_tool,
    file_rename_tool,
    project_index_tool,
    send_suggestion_tool,
    
    # Enhanced coding tools
    code_search,
    analyze_file,
    project_structure_analysis,
    find_related_files,
    
    # Subtask management
    create_task_plan,
    manage_task_progress,
    get_task_suggestions,
    
    # Search tool
    search_tools[0],
]

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = []
    error_message = None

    # Get tool calls from the last message
    if state["messages"] and hasattr(state["messages"][-1], "tool_calls"):
        tool_calls = state["messages"][-1].tool_calls

    if not error and tool_calls:
        for tc in tool_calls:
            # Check if tool returned an error dict
            if isinstance(tc.get("content"), dict) and "error" in tc["content"]:
                error_message = tc["content"]["error"]
                break
            # Check if tool call result is empty or whitespace
            if not tc.get("content") or str(tc.get("content")).strip() == "":
                error_message = "Tool returned an empty response. Please try a different approach."
                break
    
    # If we have an actual exception
    if error and not error_message:
        error_message = f"Error: {repr(error)}"

    # If we found any error message
    if error_message:
        return {
            "messages": [
                SystemMessage(content="An error occurred with the tool. Please adjust your approach."),
                ToolMessage(
                    content=error_message,
                    tool_call_id=tool_calls[0]["id"] if tool_calls else "unknown",
                )
            ]
        }
    
    # Default error response
    return {
        "messages": [
            ToolMessage(
                content="An unexpected error occurred. Please try a different approach.",
                tool_call_id="unknown"
            )
        ]
    }

def create_tool_node_with_fallback(tools: list) -> ToolNode:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def assistant(state: MessagesState):
    messages = state["messages"]
    
    # Get current LLM instance (may have changed due to rate limiting)
    current_llm = get_llm()
    
    # Do not overwrite multimodal content; pass as-is
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        messages = [SystemMessage(content=system_prompt)] + messages
    response = current_llm.bind_tools(tools).invoke(messages)
    return {"messages": [response]}

# Build the graph
def inject_code(state: MessagesState):
    last_tool_msg = state["messages"][-1]

    if isinstance(last_tool_msg, ToolMessage) and isinstance(last_tool_msg.content, dict):
        if "lines" in last_tool_msg.content:
            raw_code = "".join(last_tool_msg.content["lines"])
            path = last_tool_msg.content.get("path", "unknown file")

            # Extract file extension (without dot), lowercase
            ext = os.path.splitext(path)[1].lower().lstrip(".")

            # Map some common extensions to language ids for markdown fences
            lang_map = {
                "py": "python",
                "js": "javascript",
                "jsx": "jsx",
                "ts": "typescript",
                "tsx": "tsx",
                "json": "json",
                "html": "html",
                "css": "css",
                "java": "java",
                "go": "go",
                "sh": "bash",
            }

            if ext == "md":
                # Inject raw markdown without fences to preserve formatting
                content = f"Here is the markdown file `{path}`:\n\n{raw_code}"
            else:
                lang = lang_map.get(ext, "")  # empty means no lang specifier
                fence = f"```{lang}" if lang else "```"
                content = f"Here is the file `{path}`:\n\n{fence}\n{raw_code}\n```"

            state["messages"].append(HumanMessage(content=content))

    return state


inject_code_node = RunnableLambda(inject_code)

# Build the graph (async)
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", create_tool_node_with_fallback(tools))
builder.add_node("inject_code", inject_code_node)

builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant", 
    tools_condition,
    {
        "tools": "tools",
        END: END
    }
)
builder.add_edge("tools", "inject_code")    # after tools run, inject code
builder.add_edge("inject_code", "assistant")  # then assistant again

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

@router.post("/ask")
def ask_coding_agent(
    message: str = Body(..., embed=True), 
    conversation_id: str = Body(None, embed=True)
):
    # Use provided conversation_id or create a new one
    if not conversation_id:
        conversation_id = f"thread_{int(time.time())}"
    
    config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 50}
    
    # Create initial state
    state = {"messages": [HumanMessage(content=message)]}
    
    try:
        result = graph.invoke(state, config=config)
        if result and "messages" in result and result["messages"]:
            # Get the last non-empty message
            last_message = None
            for msg in reversed(result["messages"]):
                if hasattr(msg, 'content') and msg.content and str(msg.content).strip():
                    last_message = msg
                    break
            
            if not last_message:
                print("No valid message found in result:", result)
                from constants import EMPTY_RESPONSE_MESSAGE
                return {
                    "response": EMPTY_RESPONSE_MESSAGE,
                    "conversation_id": conversation_id
                }
            
            # Extract content based on message type
            if isinstance(last_message, AIMessage):
                response_content = last_message.content
            elif isinstance(last_message, ToolMessage):
                if isinstance(last_message.content, dict) and "error" in last_message.content:
                    response_content = f"I encountered an error: {last_message.content['error']}"
                else:
                    response_content = last_message.content
            else:
                response_content = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)
            
            if not response_content or response_content.strip() == "":
                print("Empty response content from message:", last_message)
                return {
                    "response": "I apologize, but I couldn't generate a proper response. Please try rephrasing your question.",
                    "conversation_id": conversation_id
                }
            
            return {"response": response_content, "conversation_id": conversation_id}
        else:
            print("No messages in result:", result)
            return {"response": "No response generated. Please try again.", "conversation_id": conversation_id}
    except Exception as e:
        print(f"Error in ask_coding_agent: {e}")
        return {"response": f"An error occurred: {str(e)}. Please try again.", "conversation_id": conversation_id}


from fastapi.responses import StreamingResponse

@router.post("/ask/stream")
async def ask_coding_agent_stream(
    message: str = Body(..., embed=True),
    conversation_id: str = Body(None, embed=True),
):
    """
    Server-Sent Events (SSE) streaming endpoint for the coding agent.
    Emits JSON lines with:
      - {"type":"token","content": "..."} incremental tokens from the model
      - {"type":"done","conversation_id": "..."} when completed
      - {"type":"error","message": "..."} on error
    """
    try:
        # Use provided conversation_id or create a new one
        if not conversation_id:
            conversation_id = f"thread_{int(time.time())}"

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": 50
        }
        state = {"messages": [HumanMessage(content=message)]}

        async def event_generator():
            try:
                # If this thread was cancelled before we started, exit immediately
                if conversation_id in CANCELLED_THREADS:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'interrupted'})}\n\n"
                    CANCELLED_THREADS.discard(conversation_id)
                    return

                # Stream events from LangGraph execution
                async for event in graph.astream_events(state, config=config, version="v2"):
                    # Allow cooperative cancellation between chunks
                    if conversation_id in CANCELLED_THREADS:
                        # Optionally send a final done event before closing
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                        CANCELLED_THREADS.discard(conversation_id)
                        return

                    # LangChain event names may vary by version; handle common streaming hooks
                    ev = event.get("event", "")
                    data = event.get("data", {}) or {}

                    # Stream tokens from the chat model as they arrive
                    # Common event key: "on_chat_model_stream"
                    if ev.endswith("on_chat_model_stream") or ev == "on_chat_model_stream":
                        chunk = data.get("chunk")
                        token = None
                        # chunk can be a LangChain BaseMessageChunk with 'content', or a raw string
                        if chunk is not None:
                            try:
                                token = getattr(chunk, "content", None)
                                if token is None:
                                    token = str(chunk)
                            except Exception:
                                token = None
                        if token:
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

                # Signal completion
                yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
            except Exception as e:
                # Stream error and close
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        # In case construction failed
        async def err():
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

@router.post("/ask/interrupt")
async def interrupt_coding_agent(
    conversation_id: str = Body(..., embed=True),
):
    """
    Best-effort interrupt for an active coding stream.
    Marks the given conversation/thread as cancelled so the streaming loop exits promptly.
    """
    try:
        if conversation_id:
            CANCELLED_THREADS.add(conversation_id)
        return {"success": True, "conversation_id": conversation_id}
    except Exception as e:
        return {"success": False, "error": str(e), "conversation_id": conversation_id}
