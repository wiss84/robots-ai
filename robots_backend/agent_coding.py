from fastapi import APIRouter, Body
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
import os
import time
import json
import asyncio
import logging
from dotenv import load_dotenv
from rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

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
from composio_tools_filtered import filtered_composio_google_search
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
    get_task_suggestions,
    check_subtask_code_quality,
)

# Versioning and Code Quality tools
from versioning_tools import (
    snapshot_file,
    list_file_versions,
    restore_file_version,
)
from code_quality_tool import analyze_code_quality, ensure_frontend_configs

load_dotenv()

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
 
    # Versioning tools
    snapshot_file,
    list_file_versions,
    restore_file_version,
 
    # Code quality
    check_subtask_code_quality,
    analyze_code_quality,
    ensure_frontend_configs,
    
    # Search tool
    filtered_composio_google_search,
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

def assistant(state: MessagesState, config=None):
    messages = state["messages"]

    # Get current LLM instance (may have changed due to rate limiting)
    current_llm = get_llm()

    # Get conversation_id from the config parameter (this is the proper way in LangGraph)
    conversation_id = 'unknown'
    if config and isinstance(config, dict) and 'configurable' in config:
        conversation_id = config['configurable'].get('thread_id', 'unknown')

    # Ensure we have a proper system message with conversation context
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        # Add conversation context to system prompt
        system_prompt += f"\n\n[CONTEXT] conversation_id={conversation_id}. When you call the tools create_task_plan or manage_task_progress, you MUST include this exact conversation_id in the tool arguments."
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
    conversation_id: str = Body(None, embed=True),
    conversation_summary: str = Body(None, embed=True),
):
    # Use provided conversation_id or create a new one
    if not conversation_id:
        conversation_id = f"thread_{int(time.time())}"
    
    config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 500}
    
    # Create initial state - conversation context will be added by assistant function
    system_prompt = get_system_prompt()

    # Add conversation summary to message if provided
    final_message = message
    if conversation_summary:
        final_message = f"[Previous Conversation Summary: {conversation_summary}]\n\n{message}"

    state = {"messages": [HumanMessage(content=final_message)]}
    
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
    conversation_summary: str = Body(None, embed=True),
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

        # Rate limiting check BEFORE starting stream
        estimated_tokens = rate_limiter.estimate_tokens(message)
        model_to_use, delay_message = await rate_limiter.check_and_wait_if_needed(estimated_tokens)

        # Extract agent_id from conversation_id if possible (format: thread_{agent_id}_{timestamp})
        agent_id_for_context = ""
        if conversation_id and conversation_id.startswith("thread_"):
            parts = conversation_id.split("_")
            if len(parts) >= 2:
                agent_id_for_context = parts[1]  # Extract agent_id from conversation_id

        # Handle rate limiting messages for streaming
        if delay_message:
            async def rate_limit_generator():
                if "Switched to" in delay_message and "summarized" in delay_message:
                    # Model switch with summarization needed - format for frontend recognition
                    continue_msg = f"[[CONTINUE]] 🔄 {delay_message} Please retry your request."
                    yield f"data: {json.dumps({'type': 'token', 'content': continue_msg})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                else:
                    # Rate limit delay needed - format for frontend recognition
                    seconds = getattr(rate_limiter, "delay_when_approaching_limit", 30)
                    delay_banner_msg = f"[[DELAY:{seconds}]] ⏳ Rate limit delay: Please wait {seconds} seconds before retrying"
                    yield f"data: {json.dumps({'type': 'token', 'content': delay_banner_msg})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
            return StreamingResponse(rate_limit_generator(), media_type="text/event-stream")

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": 500
        }
        # Create initial state - conversation context will be added by assistant function
        system_prompt = get_system_prompt()

        # Add conversation summary to message if provided
        final_message = message
        if conversation_summary:
            final_message = f"[Previous Conversation Summary: {conversation_summary}]\n\n{message}"

        state = {"messages": [HumanMessage(content=final_message)]}

        async def event_generator():
            tokens_used = 0
            final_result = None
            
            # Track real token usage from streaming events
            real_input_tokens = 0
            real_output_tokens = 0
            real_total_tokens = 0
            
            try:
                # If this thread was cancelled before we started, exit immediately
                if conversation_id in CANCELLED_THREADS:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'interrupted'})}\n\n"
                    CANCELLED_THREADS.discard(conversation_id)
                    return

                # Stream events and also capture the final result for token counting
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
                    metadata = event.get("metadata", {}) or {}
                    node = metadata.get("langgraph_node", "")

                    # Stream tokens from the chat model as they arrive (only from assistant node)
                    # Common event key: "on_chat_model_stream"
                    if (ev.endswith("on_chat_model_stream") or ev == "on_chat_model_stream") and node == "assistant":
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
                            # Count tokens for rate limiting (rough estimation during streaming)
                            token_count = len(str(token)) // 4  # 4 chars ≈ 1 token
                            tokens_used += max(token_count, 1)
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

                    # Capture real token usage from chat model end events
                    if ev == "on_chat_model_end" and node == "assistant":
                        output_data = data.get("output", {})
                        
                        # Try to extract usage_metadata from the output
                        usage = None
                        if hasattr(output_data, 'usage_metadata'):
                            usage = output_data.usage_metadata
                        elif isinstance(output_data, dict) and "usage_metadata" in output_data:
                            usage = output_data["usage_metadata"]
                        
                        # Extract token counts if usage metadata exists
                        if usage:
                            if isinstance(usage, dict):
                                real_input_tokens += usage.get('input_tokens', 0)
                                real_output_tokens += usage.get('output_tokens', 0)
                                real_total_tokens += usage.get('total_tokens', 0)
                            elif hasattr(usage, 'input_tokens'):
                                real_input_tokens += getattr(usage, 'input_tokens', 0)
                                real_output_tokens += getattr(usage, 'output_tokens', 0)
                                real_total_tokens += getattr(usage, 'total_tokens', 0)

                    # Capture the final result when the graph execution completes
                    if ev == "on_chain_end" and not final_result:
                        final_result = data.get("output")

                # Signal completion
                yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
            except Exception as e:
                # CAPTURE API ERRORS HERE for rate limiter processing
                api_error_encountered = str(e)
                logger.warning(f"API error in streaming: {api_error_encountered}")

                # Check if this is a quota exceeded error that should trigger model switching
                if "ResourceExhausted" in api_error_encountered or "quota" in api_error_encountered.lower():
                    try:
                        # Try to switch models with conversation context
                        new_model, switch_message = rate_limiter.record_request_with_error_handling(
                            model_to_use,
                            estimated_tokens,
                            api_error_encountered,
                            agent_id_for_context,
                            conversation_id
                        )

                        # Return error message as token content instead of error event
                        # This prevents frontend from throwing exception and breaking streaming
                        if switch_message and "Automatically switched to" in switch_message:
                            # Format for frontend [[CONTINUE]] pattern recognition
                            error_content = f"[[CONTINUE]] 🔄 {switch_message} Please retry your request."
                        elif switch_message == "ALL_MODELS_EXHAUSTED":
                            # Format for frontend [[CONTINUE]] pattern recognition
                            error_content = "[[CONTINUE]] 🚫 **All Daily Quotas Exhausted**\\n\\nAll available models have reached their daily request limits. This means:\\n\\n✅ **You've used all 1,500 daily requests** across all models\\n🔄 **Quotas reset daily** at midnight UTC\\n⏰ **Try again tomorrow** for fresh quotas\\n\\nThank you for being a power user! 💪"
                        elif switch_message and switch_message.startswith("TEMPORARY_API_ISSUE:"):
                            failed_model = switch_message.split(":")[1]
                            # Format for frontend [[CONTINUE]] pattern recognition
                            error_content = f"[[CONTINUE]] 🌐 **Temporary API Issue Detected**\\n\\nGoogle Gemini API is experiencing temporary issues with the {failed_model} model:\\n\\n🔧 **This appears to be a temporary problem** from Google's side\\n⏰ **Please try again in a few hours**\\n🔄 **Quotas will resume normally** once the API issue is resolved\\n\\nThis is not related to your usage limits."
                        else:
                            # Format for frontend [[CONTINUE]] pattern recognition
                            error_content = "[[CONTINUE]] ⚠️ **Service Temporarily Unavailable**\\n\\nI'm currently unable to process your request due to API limitations. Please try again in a few hours or tomorrow."

                        # Return as token instead of error event to prevent frontend exception
                        yield f"data: {json.dumps({'type': 'token', 'content': error_content})}\n\n"
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                    except Exception as switch_error:
                        logger.warning(f"Error in model switching: {switch_error}")
                        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                else:
                    # Non-quota error, return as-is
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                # Use real token counts from streaming events
                if real_total_tokens > 0:
                    print(f"✅ Real token usage from streaming events: {real_input_tokens} input + {real_output_tokens} output = {real_total_tokens} total")
                    rate_limiter.record_request(model_to_use, real_total_tokens)
                elif tokens_used > 0:
                    # Fallback to estimated tokens if no real usage available
                    print(f"⚠️ Using estimated tokens for streaming: {tokens_used}")
                    rate_limiter.record_request(model_to_use, tokens_used)

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        # Handle API errors with model switching for streaming
        if "ResourceExhausted" in str(e) or "quota" in str(e).lower():
            try:
                # Extract agent_id from conversation_id if possible
                agent_id_for_context = ""
                if conversation_id and conversation_id.startswith("thread_"):
                    parts = conversation_id.split("_")
                    if len(parts) >= 2:
                        agent_id_for_context = parts[1]

                # Try to switch models with conversation context
                new_model, switch_message = rate_limiter.record_request_with_error_handling(
                    model_to_use if 'model_to_use' in locals() else rate_limiter.current_model,
                    estimated_tokens if 'estimated_tokens' in locals() else 1000,
                    str(e),
                    agent_id_for_context,
                    conversation_id
                )

                async def err():
                    if switch_message and "Automatically switched to" in switch_message:
                        yield f"data: {json.dumps({'type': 'error', 'message': '🔄 ' + switch_message})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                return StreamingResponse(err(), media_type="text/event-stream")
            except Exception as switch_error:
                async def err():
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                return StreamingResponse(err(), media_type="text/event-stream")
        else:
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
