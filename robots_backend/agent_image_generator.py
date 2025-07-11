from fastapi import APIRouter, Body
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from composio_langchain import ComposioToolSet, Action, App
import os
from agents_system_prompts import IMAGE_GENERATOR_AGENT_SYSTEM_PROMPT
import time
from typing import Optional

# Import your custom tool
from tools import generate_image
from file_upload import router as file_upload_router

router = APIRouter(prefix="/image", tags=["image"])

def get_system_prompt():
    return IMAGE_GENERATOR_AGENT_SYSTEM_PROMPT

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)

# Get Composio tools
composio_toolset = ComposioToolSet(api_key=os.getenv('COMPOSIO_API_KEY'))
image_search_tools = composio_toolset.get_tools(actions=['COMPOSIO_SEARCH_IMAGE_SEARCH'])

# Combine both tools
tools = image_search_tools + [generate_image]

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

def create_message_content(text: str, image_data: Optional[str] = None):
    """Create message content that can include both text and image"""
    if image_data:
        # Create multimodal content for Gemini
        return [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
        ]
    else:
        # Text-only content
        return text

def assistant(state: MessagesState):
    messages = state["messages"]
    # Do not overwrite multimodal content; pass as-is
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        messages = [SystemMessage(content=system_prompt)] + messages
    response = llm.bind_tools(tools).invoke(messages)
    return {"messages": [response]}

# Custom tool node that can access image data from state
def tools_with_image_context(state: MessagesState):
    """Enhanced tool node that can pass image data to tools"""
    tool_node = create_tool_node_with_fallback(tools)
    
    # If we have image data and the tool call is for generate_image, inject the image
    if state.get("current_image") and state["messages"]:
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                if tool_call.get("name") == "generate_image":
                    # Inject image data into the tool call arguments
                    if "arguments" in tool_call:
                        args = tool_call["arguments"]
                        if isinstance(args, dict) and not args.get("source_image"):
                            args["source_image"] = state["current_image"]
                            args["source_processing"] = "img2img"
    
    return tool_node.invoke(state)

builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", tools_with_image_context)
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
def ask_image_agent(
    message: str = Body(..., embed=True), 
    image: Optional[str] = Body(None, embed=True),  # Optional image data
    conversation_id: str = Body(None, embed=True)
):
    """
    Handle both text-only and text+image requests
    - message: The user's text prompt
    - image: Optional base64 image data for img2img operations
    - conversation_id: Optional conversation ID for memory
    """
    # Use provided conversation_id or create a new one
    if not conversation_id:
        conversation_id = f"thread_{int(time.time())}"
    
    config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 50}
    
    # Create message content (multimodal if image present)
    message_content = create_message_content(message, image)
    
    # Create initial state
    state = {
        "messages": [HumanMessage(content=message_content)],
        "image_data": image if image else None  # Store image data for tool usage
    }
    
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
        print(f"Error in ask_image_agent: {e}")
        return {"response": f"An error occurred: {str(e)}. Please try again.", "conversation_id": conversation_id}

# Register the file upload router
router_list = [router, file_upload_router]