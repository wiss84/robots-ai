import React, { useState, useEffect } from 'react';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import './Chessboard.css';

interface ChessboardProps {
  gameId?: string;
  onMove?: (move: string) => void;
  onGameStateChange?: (gameState: any) => void;
  isAgentTurn?: boolean;
  position?: string; // FEN position from backend
  onReset?: () => void; // Add onReset callback
}

const ChessboardComponent: React.FC<ChessboardProps> = ({
  gameId,
  onMove,
  onGameStateChange,
  isAgentTurn = false,
  position,
  onReset // Add onReset prop
}) => {
  const [game, setGame] = useState(new Chess());
  
  // Update game position when position prop changes (from backend)
  useEffect(() => {
    if (position) {
      try {
        console.log('Chessboard received new position:', position);
        const newGame = new Chess(position);
        setGame(newGame);
        console.log('Chessboard updated with position:', position);
        console.log('Game FEN after update:', newGame.fen());
      } catch (error) {
        console.error('Invalid FEN position:', position, error);
      }
    }
  }, [position]);

  // Function to make a move
  const makeAMove = (move: any) => {
    const gameCopy = new Chess(game.fen());
    
    try {
      const result = gameCopy.move(move);
      if (result === null) return false; // Invalid move
      
      setGame(gameCopy);
      
      // Call the onMove callback with the move in UCI format
      if (onMove) {
        // Convert SAN to UCI format for backend
        let uciMove = result.from + result.to;
        if (result.promotion) {
          uciMove += result.promotion;
        }
        onMove(uciMove);
      }
      
      // Call the onGameStateChange callback
      if (onGameStateChange) {
        onGameStateChange({
          fen: gameCopy.fen(),
          isGameOver: gameCopy.isGameOver(),
          isCheck: gameCopy.isCheck(),
          isCheckmate: gameCopy.isCheckmate(),
          isDraw: gameCopy.isDraw(),
          isStalemate: gameCopy.isStalemate(),
          turn: gameCopy.turn() === 'w' ? 'white' : 'black'
        });
      }
      
      return true;
    } catch (error) {
      console.error('Invalid move:', error);
      return false;
    }
  };

  // Function to handle piece drop
  const onDrop = (sourceSquare: string, targetSquare: string) => {
    if (isAgentTurn) return false; // Don't allow moves during agent's turn
    
    console.log('Move attempted:', sourceSquare, 'to', targetSquare);
    
    const move = makeAMove({
      from: sourceSquare,
      to: targetSquare,
      promotion: 'q' // Always promote to queen for simplicity
    });
    
    return move;
  };

  // Function to handle square click (for move selection)
  const onSquareClick = (square: string) => {
    if (isAgentTurn) return; // Don't allow interaction during agent's turn
    
    // This can be enhanced for move selection UI
    console.log('Square clicked:', square);
  };

  // Remove local resetGame logic; use onReset callback instead
  // Get game status message
  const getGameStatus = () => {
    if (game.isCheckmate()) return 'Checkmate!';
    if (game.isDraw()) return 'Draw!';
    if (game.isStalemate()) return 'Stalemate!';
    if (game.isCheck()) return 'Check!';
    if (isAgentTurn) return "Agent's turn...";
    return "Your turn";
  };

  return (
    <div className="chessboard-container">
      <div className="chessboard-header">
        <h3>Chess Game</h3>
        {gameId && <span className="game-id">Game ID: {gameId}</span>}
      </div>
      
      <div className="chessboard-wrapper">
        <Chessboard
          position={game.fen()}
          onPieceDrop={onDrop}
          onSquareClick={onSquareClick}
          boardWidth={400}
          customBoardStyle={{
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
          }}
          customDarkSquareStyle={{ backgroundColor: '#779556' }}
          customLightSquareStyle={{ backgroundColor: '#edeed1' }}
        />
      </div>
      
      <div className="chessboard-controls">
        <div className="game-status">
          <span className={`status ${getGameStatus().toLowerCase().replace('!', '').replace(' ', '-')}`}>
            {getGameStatus()}
          </span>
        </div>
        
        <div className="game-actions">
          <button 
            onClick={onReset}
            className="reset-button"
          >
            New Game
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChessboardComponent; 