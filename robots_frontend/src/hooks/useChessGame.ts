import { useState, useRef, useEffect } from 'react';
import { parseChessResponse } from '../utils/chessParser';

interface GameState {
  isActive: boolean;
  isAgentTurn: boolean;
  gameStatus: 'idle' | 'active' | 'check' | 'checkmate' | 'draw' | 'gameover';
}

interface UseChessGameProps {
  agentId: string | undefined;
  conversationId: string;
  userName: string;
  user: any;
  supabase: any;
  setMessages: React.Dispatch<React.SetStateAction<any[]>>;
  setLoadingMessages: (loading: boolean) => void;
  handleSendMessage?: (message: string, fileInfo: any, convId: string) => Promise<void>; // Make optional
}

export const useChessGame = ({
  agentId,
  conversationId,
  userName,
  user,
  supabase,
  setMessages,
  setLoadingMessages,
  handleSendMessage // Optional unified message handler
}: UseChessGameProps) => {
  // Chess position from backend
  const [chessPosition, setChessPosition] = useState<string>('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  // Add missing state hooks for chess integration
  const [gameId, setGameId] = useState<string | null>(null);
  const latestFenRef = useRef<string>(chessPosition);

  // Ref to store the latest handleSendMessage function
  const handleSendMessageRef = useRef(handleSendMessage);
  
  // Update the ref when handleSendMessage changes
  useEffect(() => {
    console.log('Updating handleSendMessageRef with new function in useEffect', {
      hasFunction: !!handleSendMessage
    });
    handleSendMessageRef.current = handleSendMessage;
  }, [handleSendMessage]);

  // Game state for games agent
  const [gameState, setGameState] = useState<GameState>({
    isActive: false,
    isAgentTurn: false,
    gameStatus: 'idle'
  });
  
  // Check if this is the games agent
  const isGamesAgent = agentId === 'games';

  // Chess response handler for useMessageHandler callback
  const handleChessResponse = async (response: string, convId: string) => {
    // Parse agent response using chess parser utility
    const chessResult = parseChessResponse(response, isGamesAgent);
    
    if (chessResult.isChessResponse && chessResult.shouldUpdateBoard && chessResult.fen) {
      // Update chessboard with extracted FEN
      setChessPosition(chessResult.fen);
      setGameState({
        isActive: true,
        isAgentTurn: false,
        gameStatus: 'active'
      });
      
      // Show the cleaned response in chat (without FEN)
      const displayContent = chessResult.displayText || response;
      setMessages(prev => [...prev, { role: 'agent', content: displayContent }]);
      
      // Save agent response to Supabase messages (use same cleaned content as UI)
      if (convId && user) {
        await supabase.from('messages').insert([
          {
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'agent',
            content: displayContent  // Save the cleaned content that user sees
          }
        ]);
      }
    } else {
      // Show response as normal chat (for non-chess responses)
      setMessages(prev => [...prev, { role: 'agent', content: response }]);
      if (convId && user) {
        await supabase.from('messages').insert([
          {
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'agent',
            content: response
          }
        ]);
      }
    }
  };

  // Add a helper to generate a UUID (if not already present)
  function generateUUID() {
    // Simple UUID v4 generator
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  // Reset chess state helper
  const resetChessState = async () => {
    setGameState({ isActive: true, isAgentTurn: false, gameStatus: 'active' });
    setChessPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    
    // Add user-friendly message to UI
    setMessages(prev => [...prev, { role: 'user', content: 'I just started a new chess game' }]);
    
    // Inform the agent if a conversation is active
    if (isGamesAgent && agentId && user && conversationId) {
      const startNewGameMsg = `${userName} decided to start a new game, please acknowledge it`;
      if (handleSendMessageRef.current) {
        console.log('resetChessState: About to send message via handleSendMessageRef', {
          startNewGameMsg,
          conversationId
        });
        await handleSendMessageRef.current(startNewGameMsg, null, conversationId);
      } else {
        console.error('handleSendMessage not available for resetChessState');
        setMessages(prev => [...prev, { role: 'system', content: 'Error: Could not notify agent of new chess game.' }]);
      }
    }
  };

  // Add a helper to clear chess state (set inactive)
  const clearChessState = () => {
    setGameState({ isActive: false, isAgentTurn: false, gameStatus: 'idle' });
    setChessPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  };

  // When user types 'play chess' or 'start chess', trigger chess mode in the frontend only
  const handleChessTrigger = async () => {
    if (!user || !agentId) return;
    // Only create a new conversation if one doesn't exist
    let convId = conversationId;
    if (!convId) {
      const { data, error } = await supabase
        .from('conversations')
        .insert([{ user_id: user.id, agent_id: agentId, title: 'New Chess Game' }])
        .select();
      if (!error && data && data[0]) {
        convId = data[0].id;
      }
    }
    // Now use convId for all subsequent chess moves
    // Generate new gameId and set initial FEN
    const newGameId = generateUUID();
    setGameId(newGameId);
    setChessPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    setGameState({ isActive: true, isAgentTurn: false, gameStatus: 'active' });
    
    // Notify the agent about the game start
    if (isGamesAgent && agentId && user && convId) {
      const startGameMsg = `${userName} just started a chess game. Please respond with your excitement.`;
      if (handleSendMessageRef.current) {
        await handleSendMessageRef.current(startGameMsg, null, convId);
      }
    }
    
    // Fetch legal moves for initial position
    const res = await fetch('http://localhost:8000/games/legal_moves', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer test-token' },
      body: JSON.stringify({ fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' })
    });
    if (res.ok) {
      // Legal moves are fetched but not stored in state since they're not used
    }
  };

  // Update handleChessMove to use unified message handler
  const handleChessMove = async (move: string, newFen?: string) => {
    if (!agentId || !user || !gameId) return;
    const fenToUse = newFen || chessPosition;
    latestFenRef.current = fenToUse;
    
    setChessPosition(fenToUse);
    const moveMessage = { role: 'user', content: `I played ${move}` };  // Show user-friendly message in UI
    setMessages(prev => [...prev, moveMessage]);

    // Fetch legal moves for new FEN and wait for the result
    let newLegalMoves: string[] = [];
    let legalMovesFetchFailed = false;
    let resLegalData: any = {};
    try {
      const resLegal = await fetch('http://localhost:8000/games/legal_moves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer test-token' },
        body: JSON.stringify({ fen: fenToUse })
      });
      if (resLegal.ok) {
        resLegalData = await resLegal.json();
        if (resLegalData.legal_moves) newLegalMoves = resLegalData.legal_moves;
      } else {
        legalMovesFetchFailed = true;
      }
    } catch {
      legalMovesFetchFailed = true;
    }
    // Legal moves are fetched but not stored in state since they're not used

    // If legal moves fetch failed or is empty (and not checkmate/stalemate), show error and do not send to agent
    if (legalMovesFetchFailed) {
      setMessages(prev => [...prev, { role: 'system', content: 'Error: Could not fetch legal moves for this position.' }]);
      setLoadingMessages(false);
      return;
    }
    if (newLegalMoves.length === 0) {
      // Update game state to indicate the game is over
      setGameState(prev => ({
        ...prev,
        gameStatus: 'gameover'
      }));
      
      // Send a message to the agent informing it that the game may be over
      const gameOverMessage = `I just made the move ${move}. The current position is ${fenToUse}. There are no legal moves available. The game may be over (checkmate or stalemate). Please respond appropriately and congratulate the winner or acknowledge the draw.`;
      
      if (handleSendMessageRef.current) {
        // Send the game over message to the agent
        await handleSendMessageRef.current(gameOverMessage, null, conversationId);
      } else {
        // If we can't send to the agent, at least show the automated message
        setMessages(prev => [...prev, { role: 'system', content: 'No legal moves available. The game may be over (checkmate or stalemate).' }]);
      }
      setLoadingMessages(false);
      return;
    }

    // Now send the agent message in natural language using unified message handler
    const agentMessage = `I just made the move ${move}. The current position is ${fenToUse}. Available legal moves are: ${newLegalMoves.join(', ')}. Please make your move using the chess_apply_move.`;

    // Use unified message handler instead of direct API calls
    if (handleSendMessageRef.current) {
      // Don't add this message to UI since we already added the user-friendly message
      // We'll send it through the handler but prevent it from being displayed
      await handleSendMessageRef.current(agentMessage, null, conversationId);
    } else {
      console.error('handleSendMessage not available');
      setLoadingMessages(false);
    }
  };

  // Handle game state change from chessboard
  const handleGameStateChange = (newGameState: any) => {
    setGameState(prev => ({
      ...prev,
      gameStatus: newGameState.isCheckmate ? 'checkmate' : 
                  newGameState.isDraw ? 'draw' : 
                  newGameState.isCheck ? 'check' : 'active'
    }));
  };

  // Handler to close the chess game
  const handleCloseChessGame = async () => {
    setGameState({ ...gameState, isActive: false });
    
    // Add user-friendly message to UI
    setMessages(prev => [...prev, { role: 'user', content: 'I just closed the chess game' }]);
    
    if (isGamesAgent && agentId && user && conversationId) {
      const endGameMsg = `${userName} decided to close the current chess game, please acknowledge it`;
      if (handleSendMessageRef.current) {
        console.log('handleCloseChessGame: About to send message via handleSendMessageRef', {
          endGameMsg,
          conversationId
        });
        await handleSendMessageRef.current(endGameMsg, null, conversationId);
      } else {
        console.error('handleSendMessage not available for handleCloseChessGame');
        setMessages(prev => [...prev, { role: 'system', content: 'Error: Could not notify agent of chess game closure.' }]);
      }
    }
  };

  return {
    chessPosition,
    gameState,
    isGamesAgent,
    resetChessState,
    clearChessState,
    handleChessTrigger,
    handleChessMove,
    handleGameStateChange,
    handleCloseChessGame,
    handleChessResponse // Export the chess response handler
  };
};