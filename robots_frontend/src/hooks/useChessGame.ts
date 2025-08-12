import { useState, useRef } from 'react';
import { parseChessResponse } from '../utils/chessParser';

interface GameState {
  isActive: boolean;
  isAgentTurn: boolean;
  gameStatus: string;
}

interface UseChessGameProps {
  agentId: string | undefined;
  conversationId: string;
  userName: string;
  user: any;
  supabase: any;
  setMessages: React.Dispatch<React.SetStateAction<any[]>>;
  setLoadingMessages: (loading: boolean) => void;
}

export const useChessGame = ({
  agentId,
  conversationId,
  userName,
  user,
  supabase,
  setMessages,
  setLoadingMessages
}: UseChessGameProps) => {
  // Chess position from backend
  const [chessPosition, setChessPosition] = useState<string>('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  // Add missing state hooks for chess integration
  const [gameId, setGameId] = useState<string | null>(null);
  const latestFenRef = useRef<string>(chessPosition);

  // Game state for games agent
  const [gameState, setGameState] = useState<GameState>({
    isActive: false,
    isAgentTurn: false,
    gameStatus: 'idle'
  });
  
  // Check if this is the games agent
  const isGamesAgent = agentId === 'games';

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
    // Inform the agent if a conversation is active
    if (isGamesAgent && agentId && user && conversationId) {
      const startNewGameMsg = "User decided to start a new chess game.";
      try {
        await fetch('http://localhost:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
          },
          body: JSON.stringify({
            agent_id: agentId,
            message: startNewGameMsg,
            conversation_id: conversationId,
            user_name: userName
          })
        });
      } catch (err) {
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

  // Update handleChessMove to use /games/legal_moves
  const handleChessMove = async (move: string, newFen?: string) => {
    if (!agentId || !user || !gameId) return;
    const fenToUse = newFen || chessPosition;
    latestFenRef.current = fenToUse;
    
    // Debug: Log the FEN being used
    console.log('handleChessMove - fenToUse:', fenToUse);
    console.log('handleChessMove - move:', move);
    
    setChessPosition(fenToUse);
    const moveMessage = { role: 'user', content: move };
    setMessages(prev => [...prev, moveMessage]);
    setLoadingMessages(true);

    // Save user move to Supabase messages
    if (conversationId && user) {
      await supabase.from('messages').insert([
        {
          conversation_id: conversationId,
          user_id: user.id,
          agent_id: agentId,
          role: 'user',
          content: move
        }
      ]);
    }

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

    // Debug log for legal moves
    console.log('Legal moves:', newLegalMoves);

    // If legal moves fetch failed or is empty (and not checkmate/stalemate), show error and do not send to agent
    if (legalMovesFetchFailed) {
      console.log('Returning early: legal moves fetch failed');
      setMessages(prev => [...prev, { role: 'system', content: 'Error: Could not fetch legal moves for this position.' }]);
      setLoadingMessages(false);
      return;
    }
    if (newLegalMoves.length === 0) {
      console.log('Returning early: no legal moves available');
      setMessages(prev => [...prev, { role: 'system', content: 'No legal moves available. The game may be over (checkmate or stalemate).' }]);
      setLoadingMessages(false);
      return;
    }

    // Now send the agent message in natural language
    const agentMessage = `I just made the move ${move}. The current position is ${fenToUse}. Available legal moves are: ${newLegalMoves.join(', ')}. Please make your move using the chess tool.`;

    // Debug log to verify what is being sent to /chat
    console.log('About to send to /chat');
    console.log('Sending to /chat:', agentMessage);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        body: JSON.stringify({
          agent_id: agentId,
          message: agentMessage,
          conversation_id: conversationId,
          user_name: userName
        })
      });
      if (res.ok) {
        const data = await res.json();
        // Parse agent response using chess parser utility
        const chessResult = parseChessResponse(data.response, isGamesAgent);
        
        if (chessResult.isChessResponse && chessResult.shouldUpdateBoard && chessResult.fen) {
          // Debug: Log the FEN from agent response
          console.log('Agent response FEN:', chessResult.fen);
          
          // Update chessboard with extracted FEN
          setChessPosition(chessResult.fen);
          setGameState({
            isActive: true,
            isAgentTurn: false,
            gameStatus: 'active'
          });
          
          // Show the cleaned response in chat (without FEN)
          const displayContent = chessResult.displayText || data.response;
          setMessages(prev => [...prev, { role: 'agent', content: displayContent }]);
          
          // Save agent response to Supabase messages
          if (conversationId && user) {
            await supabase.from('messages').insert([
              {
                conversation_id: conversationId,
                user_id: user.id,
                agent_id: agentId,
                role: 'agent',
                content: data.response
              }
            ]);
          }
        } else {
          // Show response as normal chat (for non-chess responses or other agents)
          setMessages(prev => [...prev, { role: 'agent', content: data.response }]);
          if (conversationId && user) {
            await supabase.from('messages').insert([
              {
                conversation_id: conversationId,
                user_id: user.id,
                agent_id: agentId,
                role: 'agent',
                content: data.response
              }
            ]);
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'agent', content: 'Error: Could not reach backend.' }]);
    }
    setLoadingMessages(false);
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
    if (isGamesAgent && agentId && user && conversationId) {
      const endGameMsg = "User decided to end the current chess game";
      try {
        await fetch('http://localhost:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
          },
          body: JSON.stringify({
            agent_id: agentId,
            message: endGameMsg,
            conversation_id: conversationId,
            user_name: userName
          })
        });
      } catch (err) {
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
    handleCloseChessGame
  };
};