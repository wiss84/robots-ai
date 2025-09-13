import json
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import uuid
import chess
import chess.engine
import os

class ChessApplyMoveInput(BaseModel):
    fen: str = Field(..., description="The current chess position in FEN notation (e.g., 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1').")
    move: str = Field(..., description="The chess move to make in UCI format (e.g., 'e2e4', 'g8f6', 'd7d5'). Choose from the available legal moves.")

def evaluate_position(board: chess.Board, depth: int = 10) -> dict:
    """
    Evaluate a chess position using Stockfish engine if available.
    Returns evaluation score and best move analysis.
    """
    try:
        # Try to use Stockfish engine if available
        engine_path = os.getenv('STOCKFISH_PATH', 'stockfish')
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            result = engine.analyse(board, chess.engine.Limit(depth=depth))
            evaluation = result["score"].relative.score(mate_score=10000)
            best_move = result.get("pv", [])[0] if result.get("pv") else None
            
            return {
                "evaluation": evaluation,
                "best_move": best_move.uci() if best_move else None,
                "depth": depth,
                "engine_available": True
            }
    except Exception as e:
        # Fallback to simple evaluation if engine not available
        return {
            "evaluation": 0,
            "best_move": None,
            "depth": 0,
            "engine_available": False,
            "error": str(e)
        }

def analyze_moves(board: chess.Board, legal_moves: list, depth: int = 8) -> dict:
    """
    Analyze all legal moves and rank them by strength.
    """
    move_analysis = {}
    
    try:
        engine_path = os.getenv('STOCKFISH_PATH', 'stockfish')
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            for move_uci in legal_moves:
                move = chess.Move.from_uci(move_uci)
                board.push(move)
                
                # Analyze the position after this move
                result = engine.analyse(board, chess.engine.Limit(depth=depth))
                evaluation = result["score"].relative.score(mate_score=10000)
                
                move_analysis[move_uci] = {
                    "evaluation": evaluation,
                    "comment": get_move_comment(board, move_uci, evaluation)
                }
                
                board.pop()  # Undo the move
                
    except Exception as e:
        # Fallback: simple move analysis without engine
        for move_uci in legal_moves:
            move_analysis[move_uci] = {
                "evaluation": 0,
                "comment": "Engine not available for analysis"
            }
    
    return move_analysis

def get_move_comment(board: chess.Board, move_uci: str, evaluation: int) -> str:
    """
    Generate a human-readable comment about the move quality.
    """
    if evaluation > 200:
        return "Excellent move - strong advantage"
    elif evaluation > 100:
        return "Good move - slight advantage"
    elif evaluation > 50:
        return "Decent move - small advantage"
    elif evaluation > -50:
        return "Equal position"
    elif evaluation > -100:
        return "Slightly worse - small disadvantage"
    elif evaluation > -200:
        return "Poor move - disadvantage"
    else:
        return "Bad move - significant disadvantage"

def select_best_move(move_analysis: dict, difficulty: str = "medium") -> str:
    """
    Select the best move based on analysis and difficulty level.
    The agent should use this as a suggestion, not blindly follow it.
    """
    if not move_analysis:
        return None
    
    # Sort moves by evaluation (best first)
    sorted_moves = sorted(move_analysis.items(), key=lambda x: x[1]["evaluation"], reverse=True)
    
    # Filter out moves that are clearly bad (very negative evaluation)
    good_moves = [move for move, analysis in sorted_moves if analysis["evaluation"] > -200]
    
    if not good_moves:
        # If no good moves, return the best available
        return sorted_moves[0][0] if sorted_moves else None
    
    if difficulty == "easy":
        # Pick from top 50% of good moves randomly
        top_moves = good_moves[:max(1, len(good_moves) // 2)]
        import random
        return random.choice(top_moves)
    elif difficulty == "medium":
        # Pick from top 30% of good moves randomly
        top_moves = good_moves[:max(1, len(good_moves) // 3)]
        import random
        return random.choice(top_moves)
    elif difficulty == "hard":
        # Always pick the best move
        return sorted_moves[0][0]
    else:
        # Default to medium difficulty
        top_moves = good_moves[:max(1, len(good_moves) // 3)]
        import random
        return random.choice(top_moves)

@tool("chess_apply_move", args_schema=ChessApplyMoveInput)
def chess_apply_move(fen: str, move: str) -> dict:
    """
    Make a chess move and return the updated game state. Use this tool when you need to make a move in a chess game.
    The tool will validate the move and return the new position, game status, and a comment about the move.
    """
    board = chess.Board(fen)
    try:
        chess_move = chess.Move.from_uci(move)
        if chess_move in board.legal_moves:
            # Analyze the position before making the move
            pre_evaluation = evaluate_position(board)
            
            board.push(chess_move)
            
            # Analyze the position after making the move
            post_evaluation = evaluate_position(board)
            
            status = "active"
            if board.is_checkmate():
                status = "checkmate"
                # Determine who delivered checkmate based on whose turn it is next
                # If it's white's turn but black just moved, black delivered checkmate
                # If it's black's turn but white just moved, white delivered checkmate
                winner = "black" if board.turn else "white"
                comment = f"Checkmate! {winner.capitalize()} wins."
            elif board.is_stalemate():
                status = "stalemate"
                comment = "Stalemate! Game drawn."
            elif board.is_insufficient_material():
                status = "draw"
                comment = "Draw by insufficient material."
            elif board.is_check():
                comment = f"Check! Position evaluation: {post_evaluation['evaluation']}"
            else:
                eval_diff = post_evaluation['evaluation'] - pre_evaluation['evaluation']
                if eval_diff > 50:
                    comment = f"Strong move! Position improved by {eval_diff} centipawns."
                elif eval_diff > 0:
                    comment = f"Good move! Position improved by {eval_diff} centipawns."
                elif eval_diff > -50:
                    comment = f"Equal move. Position changed by {eval_diff} centipawns."
                else:
                    comment = f"Weak move. Position worsened by {abs(eval_diff)} centipawns."
            
            result = {
                "fen": board.fen(),
                "comment": comment,
                "status": status,
                "evaluation": post_evaluation['evaluation'],
                "pre_evaluation": pre_evaluation['evaluation']
            }
            return result
        else:
            result = {
                "fen": fen,
                "comment": f"Illegal move: {move}",
                "status": "illegal"
            }
            return result
    except Exception as e:
        result = {
            "fen": fen,
            "comment": f"Error: {str(e)}",
            "status": "error"
        }
        return result

# Remove the @tool and ChessLegalMovesInput, just define a plain function
import chess

def get_legal_moves_for_fen(fen: str):
    board = chess.Board(fen)
    legal_moves = [move.uci() for move in board.legal_moves]
    
    # Analyze all legal moves
    move_analysis = analyze_moves(board, legal_moves)
    
    # Select the best move based on difficulty
    difficulty = os.getenv('CHESS_DIFFICULTY', 'medium')
    best_move = select_best_move(move_analysis, difficulty)
    
    return {
        "fen": fen,
        "legal_moves": legal_moves,
        "turn": "white" if board.turn else "black",
        "move_analysis": move_analysis,
        "recommended_move": best_move,
        "difficulty": difficulty
    } 