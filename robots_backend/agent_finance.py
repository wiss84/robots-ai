from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

import os
import json
import time
from agents_system_prompts import FINANCE_AGENT_SYSTEM_PROMPT
from deep_search_tool import deep_search

# Cancellation registry for streaming conversations
CANCELLED_THREADS: set[str] = set()

router = APIRouter(prefix="/finance", tags=["finance"])

def get_system_prompt():
    return FINANCE_AGENT_SYSTEM_PROMPT

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)

tools = [deep_search]

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = []
    if state["messages"] and hasattr(state["messages"][-1], "tool_calls"):
        tool_calls = state["messages"][-1].tool_calls
    if not error and tool_calls:
        for tc in tool_calls:
            content = tc.get("content")
            if not content or (isinstance(content, str) and content.strip() == ""):
                return {
                    "messages": [
                        ToolMessage(
                            content="Tool returned an empty response. Please try a different search query or approach.",
                            tool_call_id=tc["id"],
                        )
                    ]
                }
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\nPlease fix your mistakes.",
                tool_call_id=tc["id"] if tc else "unknown",
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> ToolNode:  # type: ignore
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def assistant(state: MessagesState):
    messages = state["messages"]
    # Do not overwrite multimodal content; pass as-is
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        messages = [SystemMessage(content=system_prompt)] + messages
    response = llm.bind_tools(tools).invoke(messages)
    return {"messages": [response]}

builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", create_tool_node_with_fallback(tools))  # type: ignore
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant", 
    tools_condition,
    {
        "tools": "tools",
        END: END
    }
)
builder.add_edge("tools", "assistant")
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

@router.post("/ask")
def ask_finance_agent(
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
        # Invoke the graph with config - this will maintain conversation history
        result = graph.invoke(state, config=config)  # type: ignore
        
        # Get the last message from the result
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            
            # Handle different message types
            if isinstance(last_message, AIMessage):
                response_content = last_message.content
            elif isinstance(last_message, ToolMessage):
                response_content = last_message.content
            else:
                response_content = str(last_message.content) if hasattr(last_message, 'content') else str(last_message)
            
            # Check if response is empty and provide fallback
            if not response_content or (isinstance(response_content, str) and response_content.strip() == ""):
                response_content = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
            return {"response": response_content, "conversation_id": conversation_id}
        else:
            return {"response": "No response generated. Please try again.", "conversation_id": conversation_id}
            
    except Exception as e:
        print(f"Error in ask_finance_agent: {e}")
        return {"response": f"An error occurred: {str(e)}. Please try again.", "conversation_id": conversation_id}


@router.post("/ask/stream")
async def ask_finance_agent_stream(
    message: str = Body(..., embed=True),
    conversation_id: str = Body(None, embed=True),
):
    """
    SSE streaming endpoint for the finance agent.
    Streams only the assistant node's tokens.
    Emits JSON lines with:
      - {"type":"token","content": "..."} incremental tokens
      - {"type":"done","conversation_id": "..."} when completed
      - {"type":"error","message": "..."} on error
    """
    try:
        if not conversation_id:
            conversation_id = f"thread_{int(time.time())}"

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": 50,
        }
        state = {"messages": [HumanMessage(content=message)]}

        async def event_generator():
            try:
                if conversation_id in CANCELLED_THREADS:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'interrupted'})}\n\n"
                    CANCELLED_THREADS.discard(conversation_id)
                    return

                async for event in graph.astream_events(state, config=config, version="v2"):
                    if conversation_id in CANCELLED_THREADS:
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                        CANCELLED_THREADS.discard(conversation_id)
                        return

                    ev = event.get("event", "")
                    data = event.get("data", {}) or {}
                    metadata = event.get("metadata", {}) or {}
                    node = metadata.get("langgraph_node", "")

                    # Only stream assistant node chunks
                    if (ev.endswith("on_chat_model_stream") or ev == "on_chat_model_stream") and node == "assistant":
                        chunk = data.get("chunk")
                        token = getattr(chunk, "content", None) if chunk else None
                        if token:
                            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

                    # Mark assistant completion
                    if (ev.endswith("on_chat_model_end") or ev == "on_chat_model_end") and node == "assistant":
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        async def err():
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")


@router.post("/ask/interrupt")
async def interrupt_finance_agent(
    conversation_id: str = Body(..., embed=True),
):
    """
    Best-effort interrupt for an active finance stream.
    Marks the given conversation/thread as cancelled so the streaming loop exits promptly.
    """
    try:
        if conversation_id:
            CANCELLED_THREADS.add(conversation_id)
        return {"success": True, "conversation_id": conversation_id}
    except Exception as e:
        return {"success": False, "error": str(e), "conversation_id": conversation_id}
