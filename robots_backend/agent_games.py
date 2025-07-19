import json
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
from agents_system_prompts import GAMES_AGENT_SYSTEM_PROMPT
from chess_tool import chess_apply_move, get_legal_moves_for_fen

router = APIRouter(prefix="/games", tags=["games"])

def get_system_prompt():
    return GAMES_AGENT_SYSTEM_PROMPT

# Initialize Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.0,  # Set to 0 for more deterministic behavior
)

# Initialize Composio toolset
composio_toolset = ComposioToolSet(api_key=os.getenv('COMPOSIO_API_KEY'))

# Get search tools
search_tools = composio_toolset.get_tools(actions=['COMPOSIO_SEARCH_SEARCH'])

# Register chess tools
chess_tools = [chess_apply_move]

# Combine all tools
tools = search_tools + chess_tools

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = []
    
    # Get tool calls from the last message
    if state["messages"] and hasattr(state["messages"][-1], "tool_calls"):
        tool_calls = state["messages"][-1].tool_calls
    
    if not error and tool_calls:
        for tc in tool_calls:
            # Check if tool call result is empty or whitespace
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

def assistant(state: MessagesState):
    messages = state["messages"]
    # Do not overwrite multimodal content; pass as-is
    if not messages or not isinstance(messages[0], SystemMessage):
        system_prompt = get_system_prompt()
        messages = [SystemMessage(content=system_prompt)] + messages
    response = llm.bind_tools(tools).invoke(messages)
    return {"messages": [response]}

# Build the graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", create_tool_node_with_fallback(tools))

# Add edges
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

# Compile with memory
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

@router.post("/ask")
def ask_games_agent(
    message: str = Body(..., embed=True),
    conversation_id: str = Body(None, embed=True)
):
    if not conversation_id:
        conversation_id = f"thread_{int(time.time())}"
    config = {"configurable": {"thread_id": conversation_id}, "recursion_limit": 50}
    state = {"messages": [HumanMessage(content=message)]}
    try:
        result = graph.invoke(state, config=config)
        if result and "messages" in result and result["messages"]:
            last_message = result["messages"][-1]
            # Handle different message types
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            else:
                response_content = str(last_message)
            return {"response": response_content, "conversation_id": conversation_id}
        else:
            return {"response": "No response generated. Please try again.", "conversation_id": conversation_id}
    except Exception as e:
        print(f"Error in ask_games_agent: {e}")
        return {"response": f"An error occurred: {str(e)}. Please try again.", "conversation_id": conversation_id}

@router.post("/legal_moves")
def get_legal_moves(data: dict = Body(...)):
    fen = data.get("fen")
    if not fen:
        return {"error": "FEN is required"}
    return get_legal_moves_for_fen(fen) 