import json
from fastapi import APIRouter, Body
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from composio import Composio
import os
import time
from composio_langchain import LangchainProvider
from dotenv import load_dotenv
from agents_system_prompts import GAMES_AGENT_SYSTEM_PROMPT
from chess_tool import chess_apply_move, get_legal_moves_for_fen

# Import dynamic model configuration
from dynamic_model_config import get_current_gemini_model

router = APIRouter(prefix="/games", tags=["games"])

def get_system_prompt():
    return GAMES_AGENT_SYSTEM_PROMPT

# Initialize Gemini LLM with dynamic model selection
def get_llm():
    return get_current_gemini_model(temperature=0.0)  # Set to 0 for more deterministic behavior

load_dotenv()

# Initialize Composio toolset
composio = Composio(api_key=os.getenv('COMPOSIO_API_KEY'), provider=LangchainProvider())

# Get search tools
search_tools = composio.tools.get(user_id=os.getenv('COMPOSIO_USER_ID'), tools=["COMPOSIO_SEARCH_SEARCH"])

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

def validate_chess_response(state: MessagesState):
    """Validate that chess responses only contain tool-generated FEN data"""
    messages = state["messages"]
    
    # Check if original message was chess-related
    human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    if not human_messages:
        return {"messages": []}
    
    last_human_message = human_messages[-1].content
    is_chess_message = ("Available legal moves are:" in last_human_message and 
                       "position is" in last_human_message)
    
    if not is_chess_message:
        return {"messages": []}  # Not chess, let it pass
    
    # Find the latest AI response
    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage) and not hasattr(msg, 'tool_calls')]
    if not ai_messages:
        return {"messages": []}  # No AI response yet
    
    latest_ai_response = ai_messages[-1]
    
    # Check if the AI response contains FEN-like patterns (fake FEN)
    import re
    fen_pattern = r"position is ([a-zA-Z0-9\/\s\-]+)"
    contains_fake_fen = re.search(fen_pattern, latest_ai_response.content)
    
    # Check if there are any tool messages with chess_apply_move results
    tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]
    has_real_chess_tool_result = False
    real_fen = None
    
    for tool_msg in tool_messages:
        try:
            # Try to parse tool result as chess tool output
            if isinstance(tool_msg.content, str):
                import ast
                tool_result = ast.literal_eval(tool_msg.content)
                if isinstance(tool_result, dict) and "fen" in tool_result:
                    has_real_chess_tool_result = True
                    real_fen = tool_result["fen"]
                    break
        except:
            continue
    
    # If AI provided fake FEN but no real tool result, force tool usage
    if contains_fake_fen and not has_real_chess_tool_result:
        return force_chess_tool_execution(state)
    
    # If AI provided fake FEN but we have real tool result, replace fake with real
    if contains_fake_fen and has_real_chess_tool_result and real_fen:
        # Replace the fake FEN in AI response with real FEN
        corrected_content = re.sub(
            fen_pattern, 
            f"position is {real_fen}", 
            latest_ai_response.content
        )
        corrected_ai_message = AIMessage(content=corrected_content)
        
        # Replace the fake AI message with corrected one
        new_messages = []
        for msg in messages:
            if msg == latest_ai_response:
                new_messages.append(corrected_ai_message)
            else:
                new_messages.append(msg)
        
        return {"messages": new_messages[len(state["messages"]):]}
    
    return {"messages": []}

def force_chess_tool_execution(state: MessagesState):
    """Force chess tool execution when AI provides fake data"""
    messages = state["messages"]
    
    # Extract chess info from original human message
    human_messages = [msg for msg in messages if isinstance(msg, HumanMessage)]
    last_human_message = human_messages[-1].content
    
    import re
    fen_match = re.search(r"position is ([a-zA-Z0-9\/\s\-]+?)\.", last_human_message)
    moves_match = re.search(r"Available legal moves are: ([a-zA-Z0-9,\s]+?)\.", last_human_message)
    
    if not fen_match or not moves_match:
        return {"messages": [AIMessage(content="I couldn't parse the chess position from your message.")]}
    
    fen = fen_match.group(1).strip()
    legal_moves_str = moves_match.group(1)
    legal_moves = [move.strip() for move in legal_moves_str.split(",")]
    
    # Get AI's reasoning but use it only for move selection
    ai_messages = [msg for msg in messages if isinstance(msg, AIMessage)]
    ai_reasoning = ai_messages[-1].content if ai_messages else ""
    
    # Use LLM to select move based on reasoning
    move_selection_prompt = f"""
    Choose exactly ONE move from: {', '.join(legal_moves)}
    Your reasoning: {ai_reasoning}
    Respond with ONLY the move (like 'e2e4'):
    """

    # Get current LLM instance for dynamic model selection
    current_llm = get_llm()
    move_response = current_llm.invoke([HumanMessage(content=move_selection_prompt)])
    selected_move = move_response.content.strip()
    
    if selected_move not in legal_moves:
        selected_move = legal_moves[0]
    
    # Execute chess tool
    try:
        tool_result = chess_apply_move(fen=fen, move=selected_move)
        tool_call_id = f"forced_{int(time.time())}"
        
        # Create tool call and result
        ai_with_tool = AIMessage(
            content=f"I'll make the move {selected_move}.",
            tool_calls=[{
                "id": tool_call_id,
                "name": "chess_apply_move", 
                "args": {"fen": fen, "move": selected_move}
            }]
        )
        
        tool_message = ToolMessage(
            content=str(tool_result),
            tool_call_id=tool_call_id
        )
        
        # Create final AI response with real FEN
        if isinstance(tool_result, dict) and "fen" in tool_result:
            final_response = f"I've made the move {selected_move}. The new position is {tool_result['fen']}. {tool_result.get('comment', '')}"
        else:
            final_response = f"I made the move {selected_move}."
            
        final_ai_message = AIMessage(content=final_response)
        
        return {"messages": [ai_with_tool, tool_message, final_ai_message]}
        
    except Exception as e:
        return {"messages": [AIMessage(content=f"Error: {str(e)}")]}

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

# Build the graph
builder = StateGraph(MessagesState)
builder.add_node("assistant", assistant)
builder.add_node("tools", create_tool_node_with_fallback(tools))
builder.add_node("validate_chess", validate_chess_response)

# Add edges
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant", 
    tools_condition,
    {
        "tools": "tools",
        END: "validate_chess"
    }
)
builder.add_edge("tools", "assistant")
builder.add_edge("validate_chess", END)

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