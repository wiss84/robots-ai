from fastapi import APIRouter, Body
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from agents_system_prompts import TRAVEL_AGENT_SYSTEM_PROMPT
import time
from osm_tools import osm_route, osm_poi_search
from composio_tools_filtered import filtered_composio_image_search, filtered_composio_google_search, filtered_composio_google_maps_search

from composio import Composio
import os
from composio_langchain import LangchainProvider
from dotenv import load_dotenv
load_dotenv()


# Get Composio tools
composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'), allow_tracking=False, timeout=60, provider=LangchainProvider())
flight_search = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_FLIGHTS"])
hotel_search = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_HOTELS"])

# Import dynamic model configuration
from dynamic_model_config import get_current_gemini_model

router = APIRouter(prefix="/travel", tags=["travel"])

def get_system_prompt():
    return TRAVEL_AGENT_SYSTEM_PROMPT

# Initialize Gemini LLM with dynamic model selection
def get_llm():
    return get_current_gemini_model(temperature=0.1)

tools = flight_search + hotel_search + [filtered_composio_google_search, filtered_composio_google_maps_search, filtered_composio_image_search,  osm_route, osm_poi_search]

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = []
    if state["messages"] and hasattr(state["messages"][-1], "tool_calls"):
        tool_calls = state["messages"][-1].tool_calls
    if not error and tool_calls:
        for tc in tool_calls:
            if not tc.get("content") or str(tc.get("content")).strip() == "":
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

def create_tool_node_with_fallback(tools: list) -> ToolNode:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def assistant(state: MessagesState, config=None):
    messages = state["messages"]

    # Get current LLM instance (may have changed due to rate limiting)
    current_llm = get_llm()

    # Do not overwrite multimodal content; pass as-is
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        messages = [SystemMessage(content=system_prompt)] + messages
    response = current_llm.bind_tools(tools).invoke(messages)
    return {"messages": [response]}

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
builder.add_edge("tools", "assistant")
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

@router.post("/ask")
def ask_travel_agent(
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
        result = graph.invoke(state, config=config)
        
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
            if not response_content or response_content.strip() == "":
                response_content = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
            return {"response": response_content, "conversation_id": conversation_id}
        else:
            return {"response": "No response generated. Please try again.", "conversation_id": conversation_id}
            
    except Exception as e:
        print(f"Error in ask_coding_agent: {e}")
        return {"response": f"An error occurred: {str(e)}. Please try again.", "conversation_id": conversation_id}
