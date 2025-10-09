from fastapi import APIRouter, Body
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
import time
from composio_tools_filtered import filtered_composio_google_search

from agents_system_prompts import CODING_ASK_AGENT_SYSTEM_PROMPT

# Import dynamic model configuration
from dynamic_model_config import get_current_gemini_model

router = APIRouter(prefix="/coding-ask", tags=["coding-ask"])

# System prompt for the ask-only coding agent
def get_system_prompt():
    return CODING_ASK_AGENT_SYSTEM_PROMPT

# Initialize Gemini LLM with dynamic model selection
def get_llm():
    return get_current_gemini_model(temperature=0.1)

# Only search tools for the ask mode
tools = [filtered_composio_google_search]

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

    # Add system prompt if not present
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        messages = [SystemMessage(content=system_prompt)] + messages
    response = current_llm.bind_tools(tools).invoke(messages)
    return {"messages": [response]}

# Build the graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", create_tool_node_with_fallback(tools))

builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant", 
    tools_condition,
    {
        "tools": "tools",
        END: END
    }
)
builder.add_edge("tools", "assistant")  # after tools run, back to assistant

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

@router.post("/ask")
def ask_coding_ask_agent(
    message: str = Body(..., embed=True), 
    conversation_id: str = Body(None, embed=True)
):
    # Use provided conversation_id or create a new one
    if not conversation_id:
        conversation_id = f"thread_ask_{int(time.time())}"
    
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
        print(f"Error in ask_coding_ask_agent: {e}")
        return {"response": f"An error occurred: {str(e)}. Please try again.", "conversation_id": conversation_id}
