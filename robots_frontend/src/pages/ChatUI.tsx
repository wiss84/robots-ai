import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import './Auth.css';
import './AgentSelection.css';
import './ChatUI.css';
import Navbar from '../components/Navbar';
import { useAuth } from '../hooks/useAuth';
import ChatSidebar from '../components/ChatSidebar';
import ChatMessages from '../components/ChatMessages';
import ChatInput from '../components/ChatInput';
import ChatPoses from '../components/ChatPoses';
import ErrorBoundary from '../components/ErrorBoundary';
import UsageMonitor from '../components/UsageMonitor';
import ChessboardComponent from '../components/Chessboard';
import { agentNames } from '../data/AgentDescriptions';
import { Chess } from 'chess.js';
import { parseChessResponse } from '../utils/chessParser';
import { summarizeConversation } from '../utils/conversationSummarizer';

interface ChatMessage {
  role: string;
  type?: 'text' | 'image' | 'file';
  content: string;
  fileName?: string;
  fileUrl?: string;
}

interface GameState {
  isActive: boolean;
  isAgentTurn: boolean;
  gameStatus: string;
}

function ChatUI() {
  const { agentId } = useParams<{ agentId: string }>();
  const { user, loading, supabase } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [conversations, setConversations] = useState<any[]>([]);
  const [conversationId, setConversationId] = useState<string>('');
  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [showAllConversations, setShowAllConversations] = useState(false);
  const [pose, setPose] = useState<'greeting'|'typing'|'thinking'|'arms_crossing'|'wondering'|'painting'>('greeting');
  const idleTimer = useRef<NodeJS.Timeout | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null) as React.RefObject<HTMLDivElement>;
  // Chess position from backend
  const [chessPosition, setChessPosition] = useState<string>('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
  // Add missing state hooks for chess integration
  const [gameId, setGameId] = useState<string | null>(null);
  const latestFenRef = useRef<string>(chessPosition);

  // Game state for games agent
  const [gameState, setGameState] = useState<GameState>({
    // Removed gameId
    isActive: false,
    isAgentTurn: false,
    gameStatus: 'idle'
  });
  
  // Reset chess state helper
  const resetChessState = async () => {
    setGameState({ isActive: true, isAgentTurn: false, gameStatus: 'active' });
    setChessPosition('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    // Inform the agent if a conversation is active
    if (isGamesAgent && agentId && user && conversationId) {
      const startNewGameMsg = "User decided to start a new game.";
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

  // Check if this is the games agent
  const isGamesAgent = agentId === 'games';

  // Get user name and agent name
  const capitalize = (str: string) => str.charAt(0).toUpperCase() + str.slice(1);
  const firstNameRaw = user?.user_metadata?.first_name || 'User';
  const userName = capitalize(firstNameRaw);
  const agentName = agentId ? agentNames[agentId] || 'Assistant' : 'Assistant';

  // Add a helper to generate a UUID (if not already present)
  function generateUUID() {
    // Simple UUID v4 generator
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

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
        setConversationId(convId);
        setConversations(prev => [data[0], ...prev]);
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
    const moveMessage: ChatMessage = { role: 'user', content: move };
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
        if (data.conversation_id) {
          setConversationId(data.conversation_id);
          // Ensure conversation is in the sidebar list
          setConversations(prev => {
            if (!prev.some(c => c.id === data.conversation_id)) {
              return [{ id: data.conversation_id, title: 'New Conversation', agent_id: agentId, user_id: user?.id }, ...prev];
            }
            return prev;
          });
        }
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

  // Fetch conversations for this user and agent
  useEffect(() => {
    if (!user || !agentId) return;
    const fetchConversations = async () => {
      const { data, error } = await supabase
        .from('conversations')
        .select('*')
        .eq('user_id', user.id)
        .eq('agent_id', agentId)
        .order('created_at', { ascending: false });
      if (!error) setConversations(data || []);
    };
    fetchConversations();
  }, [user, agentId, supabase]);

  // When a conversation is selected, fetch its messages
  const handleSelectConversation = async (convId: string) => {
    setConversationId(convId);
    setLoadingMessages(true);
    // Reset chess state when switching conversations
    if (isGamesAgent) resetChessState();
    const { data, error } = await supabase
      .from('messages')
      .select('*')
      .eq('conversation_id', convId)
      .order('created_at', { ascending: true }); // fetch all, oldest to newest
    if (!error) {
      const messages = (data || []).map(m => ({ role: m.role, content: m.content })); // full history
      setMessages(messages);
      
      // Summarize conversation history if there are messages
      if (messages.length > 0) {
        try {
          const summary = await summarizeConversation(messages);
          console.log('Conversation summarized:', summary);
          
          // Store summary for use with first message
          sessionStorage.setItem(`conversation_summary_${convId}`, summary);
          console.log('Conversation summary stored for first message');
        } catch (error) {
          console.error('Error processing conversation:', error);
        }
      }
    }
    setLoadingMessages(false);
  };

  // Create a new conversation in Supabase
  const handleNewChat = async () => {
    if (!user || !agentId) return;
    // Reset chess state for new chat
    if (isGamesAgent) resetChessState();
    const { data, error } = await supabase
      .from('conversations')
      .insert([{ user_id: user.id, agent_id: agentId, title: 'New Conversation' }])
      .select();
    if (!error && data && data[0]) {
      setConversationId(data[0].id);
      setMessages([]);
      setConversations(prev => [data[0], ...prev]);
    }
  };

  // Rename conversation
  const handleRenameConversation = async (convId: string, newTitle: string) => {
    await supabase.from('conversations').update({ title: newTitle }).eq('id', convId);
    setConversations(conversations => conversations.map(c => c.id === convId ? { ...c, title: newTitle } : c));
  };
  // Delete conversation
  const handleDeleteConversation = async (convId: string) => {
    await supabase.from('conversations').delete().eq('id', convId);
    setConversations(conversations => conversations.filter(c => c.id !== convId));
    if (conversationId === convId) {
      setConversationId('');
      setMessages([]);
    }
  };

  // Fetch conversations for this user and agent
  useEffect(() => {
    if (!user || !agentId) return;
    const fetchConversations = async () => {
      const { data, error } = await supabase
        .from('conversations')
        .select('*')
        .eq('user_id', user.id)
        .eq('agent_id', agentId)
        .order('created_at', { ascending: false });
      if (!error) setConversations(data || []);
    };
    fetchConversations();
  }, [user, agentId, supabase]);

  // HandleSend to accept attachedFile
  const handleSend = async (fileInfo?: any) => {
    if (!input.trim() && !fileInfo) return;
    if (!agentId || !user) return;
    
    const userMessage = input.trim();
    setInput('');
    setLoadingMessages(true);
    
    // Handle games agent special logic
    if (isGamesAgent) {
      const lowerMsg = userMessage.trim().toLowerCase();
      if (
        lowerMsg.includes('play chess') ||
        lowerMsg.includes('start chess')
      ) {
        // Add the user's message to the chat history
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        await handleChessTrigger();
        setMessages(prev => [...prev, { role: 'system', content: 'Chess game started! You are white. Make your move.' }]);
        // Send a message to the agent to inform it that a new chess game has started
        const convIdToUse = conversationId;
        const startGameMessage = "User started a new chess game.";
        try {
          await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer test-token'
            },
            body: JSON.stringify({
              agent_id: agentId,
              message: startGameMessage,
              conversation_id: convIdToUse,
              user_name: userName
            })
          });
        } catch (err) {
          setMessages(prev => [...prev, { role: 'system', content: 'Error: Could not notify agent of new chess game.' }]);
        }
        setLoadingMessages(false);
        return;
      }
    }
    
    let convId = conversationId;
    if (!convId) {
      const { data, error } = await supabase
        .from('conversations')
        .insert([{ user_id: user.id, agent_id: agentId, title: 'New Conversation' }])
        .select();
      if (!error && data && data[0]) {
        convId = data[0].id;
        setConversationId(convId);
        setConversations(prev => [data[0], ...prev]);
      } else {
        setLoadingMessages(false);
        return;
      }
    }
    // Compose message content for agent with file content
    let agentMessage = userMessage;
    let chatMessage: ChatMessage = { role: 'user', content: userMessage };
    let fileContent = null;
    
    if (fileInfo) {
      fileContent = fileInfo.extracted_content || fileInfo.content || '';
      agentMessage = `${userMessage}\n\n[File: ${fileInfo.filename}]\n${fileContent}`;
      chatMessage = { role: 'user', content: agentMessage };
    }
    
    // Add user message to UI immediately
    setMessages(prev => [...prev, chatMessage]);
    
    try {
      // Check if we have a conversation summary to send with first message
      const summaryKey = `conversation_summary_${convId}`;
      const conversationSummary = sessionStorage.getItem(summaryKey);
      
      const requestBody: any = { 
        agent_id: agentId, 
        message: agentMessage,
        conversation_id: convId,
        file_content: fileContent,
        user_name: userName 
      };
      
      // Add summary if available (only for first message in loaded conversation)
      if (conversationSummary) {
        requestBody.conversation_summary = conversationSummary;
        // Remove from sessionStorage after sending (so it's only sent once)
        sessionStorage.removeItem(summaryKey);
        console.log('Sending conversation summary with first message:', conversationSummary.substring(0, 100) + '...');
      }
      
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        body: JSON.stringify(requestBody)
      });
      
      console.log('Response status:', res.status);
      console.log('Response ok:', res.ok);
      
      // Update usage stats
      if ((window as any).updateUsage) {
        (window as any).updateUsage();
      }
      
      if (!res.ok) {
        const errorText = await res.text();
        console.error('HTTP Error:', res.status, errorText);
        throw new Error(`HTTP ${res.status}: ${res.statusText} - ${errorText}`);
      }
      
      const data = await res.json();
      console.log('Response data:', data);
      
      // Always update conversationId if present in response
      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      // Check for API quota errors in the response
      if (data.response && (
        data.response.includes('API Quota Exceeded') || 
        data.response.includes('Rate Limit Reached') ||
        data.response.includes('ResourceExhausted')
      )) {
        // Set error pose and show quota error message
        setPose('wondering');
        setMessages(prev => [...prev, { 
          role: 'agent', 
          content: data.response 
        }]);
        
        // Save error message to database
        await supabase.from('messages').insert([
          {
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'agent',
            content: data.response
          }
        ]);
        
        setLoadingMessages(false);
        return;
      }

      // --- Chess agent response handling ---
      let parsed = null;
      try {
        parsed = JSON.parse(data.response);
      } catch (e) {
        // Not JSON, treat as plain chat
      }
      if (isGamesAgent && parsed && parsed.fen) {
        // For chess responses, show the full JSON response in the chat
        setMessages(prev => [...prev, { role: 'agent', content: data.response }]);
        setChessPosition(parsed.fen);
        setGameState({
          // Removed gameId
          isActive: true,
          isAgentTurn: false,
          gameStatus: parsed.status || 'active'
        });
      } else {
        setMessages(prev => [...prev, { role: 'agent', content: data.response }]);
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      
      // Handle specific error types
      let errorMessage = 'Error: Could not reach backend.';
      
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        errorMessage = '⚠️ **Connection Error**\n\nUnable to connect to the server. Please check your internet connection and try again.';
      } else if (err.message.includes('500') || err.message.includes('Internal Server Error')) {
        errorMessage = '⚠️ **Server Error**\n\nThe server encountered an error. Please try again in a moment.';
      } else if (err.message.includes('429') || err.message.includes('Too Many Requests')) {
        errorMessage = '⚠️ **Rate Limit Exceeded**\n\nToo many requests. Please wait a moment before trying again.';
      } else if (err.message.includes('ResourceExhausted') || err.message.includes('quota')) {
        errorMessage = '⚠️ **API Quota Exceeded**\n\nI\'ve reached my current usage limit. Please try again in a few minutes.';
      }
      
      setPose('wondering');
      setMessages(prev => [...prev, { role: 'agent', content: errorMessage }]);
      
      // Save error message to database
      try {
        await supabase.from('messages').insert([
          {
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'agent',
            content: errorMessage
          }
        ]);
      } catch (dbError) {
        console.error('Failed to save error message to database:', dbError);
      }
    }
    setLoadingMessages(false);
    // Rename conversation if it's the first user message (for chess games, this might be the first move)
    const isFirstUserMessage = messages.filter(m => m.role === 'user').length === 0;
    if (isFirstUserMessage && convId) {
      await supabase.from('conversations').update({ title: userMessage.slice(0, 30) }).eq('id', convId);
      setConversations(convs => convs.map(c => c.id === convId ? { ...c, title: userMessage.slice(0, 30) } : c));
    }
  };

  useEffect(() => {
    // Scroll to bottom when messages change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Set pose for greeting on initial load/new chat
  useEffect(() => {
    setPose('greeting');
  }, [agentId]);

  // Set pose to thinking when user is typing
  useEffect(() => {
    if (input && !loadingMessages) {
      setPose('thinking');
    }
  }, [input, loadingMessages]);

  // Set pose to typing/painting when agent is responding
  useEffect(() => {
    if (loadingMessages && messages.length > 0 && messages[messages.length-1].role === 'user') {
      const content = messages[messages.length - 1].content.toLowerCase();
      const isImageAgent = agentId === 'image';
      const hasImageKeywords = content.includes('generate') || content.includes('create') || content.includes('make') || content.includes('draw') || content.includes('paint');
      
      if (isImageAgent && hasImageKeywords) {
        setPose('painting');
      } else {
        setPose('typing');
      }
    }
  }, [loadingMessages, messages, agentId]);

  // Idle pose after 2 minutes
  useEffect(() => {
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => setPose('arms_crossing'), 2 * 60 * 1000);
    return () => { if (idleTimer.current) clearTimeout(idleTimer.current); };
  }, [input, messages, loadingMessages]);

  // Set wondering pose on error (fallback, policy, etc.)
  useEffect(() => {
    if (messages.length > 0 && messages[messages.length - 1].role === 'agent') {
      const content = messages[messages.length - 1].content.trim().toLowerCase();
      if (content.startsWith("i'm sorry") || content.startsWith("i am sorry") || content.startsWith("I apologize")) {
        setPose('wondering');
      }
    }
  }, [messages]);

  // Debug game state for games agent
  useEffect(() => {
    if (isGamesAgent) {
      console.log('Game state updated:', gameState);
    }
  }, [gameState, isGamesAgent]);

  if (loading) {
    return (
      <>
        <Navbar showHomeLink={true} showAgentSelectionLink={true} />
        <div className="chat-root"><div>Loading...</div></div>
      </>
    );
  }
  if (!user) {
    return (
      <>
        <Navbar showHomeLink={true} showAgentSelectionLink={true} />
        <div className="chat-root" style={{ minHeight: '80vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="chat-auth-required" style={{ textAlign: 'center', background: 'rgba(0,0,0,0.04)', padding: '2.5rem 2rem', borderRadius: 16, boxShadow: '0 2px 12px rgba(0,0,0,0.07)' }}>
            <h2 style={{ marginBottom: 16 }}>Sign In Required</h2>
            <p style={{ marginBottom: 24, color: '#888' }}>You must be signed in to chat with an agent.</p>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button className="nav-button" style={{ fontSize: 18, padding: '0.7rem 2.2rem' }} onClick={() => navigate('/signin')}>
                Sign In
              </button>
            </div>
          </div>
        </div>
      </>
    );
  }

  // Show greeting only if no messages yet
  const showGreeting = messages.length === 0;

  const getTimeOfDay = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'morning';
    if (hour < 18) return 'afternoon';
    return 'evening';
  };
  const firstName = capitalize(firstNameRaw);

  return (
    <ErrorBoundary>
      <div className="chat-root">
        <Navbar showHomeLink={true} showAgentSelectionLink={true} />
        <UsageMonitor />
        {/* Sidebar */}
        <ChatSidebar 
          sidebarOpen={sidebarOpen}
          conversations={conversations}
          showAllConversations={showAllConversations}
          renamingId={renamingId}
          renameValue={renameValue}
          dropdownOpen={dropdownOpen}
          handleNewChat={handleNewChat}
          handleSelectConversation={handleSelectConversation}
          handleRenameConversation={handleRenameConversation}
          handleDeleteConversation={handleDeleteConversation}
          setSidebarOpen={setSidebarOpen}
          setDropdownOpen={setDropdownOpen}
          setRenamingId={setRenamingId}
          setRenameValue={setRenameValue}
          setShowAllConversations={setShowAllConversations}
        />
        {/* Main Chat Area */}
        <div className={`chat-main${showGreeting ? ' greeting-mode' : ''}`}>
          <ChatPoses agentId={agentId} pose={pose} />
          {showGreeting && (
            <>
              <div className="chat-greeting-header-outer greeting-mode">
                <div className="chat-greeting-header">
                  {`Good ${getTimeOfDay()}, ${firstName}`}
                </div>
              </div>
              <ChatInput
                input={input}
                setInput={setInput}
                loadingMessages={loadingMessages}
                handleSend={handleSend}
                conversationId={conversationId}
              />
            </>
          )}
          {!showGreeting && (
            <>
              <div style={{ position: 'relative', width: '100%', display: 'flex', gap: '2rem' }}>
                {/* Chat Messages */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <ChatMessages
                    messages={messages}
                    loadingMessages={loadingMessages}
                    messagesEndRef={messagesEndRef}
                    userName={userName}
                    agentName={agentName}
                    agentId={agentId}
                  />
                </div>
                
                {/* Chessboard for Games Agent - Only show when game is active and chessPosition is set */}
                {isGamesAgent && gameState.isActive && chessPosition && (
                  <div style={{ 
                    flex: '0 0 auto', 
                    width: '450px',
                    position: 'sticky',
                    top: '2rem',
                    height: 'fit-content'
                  }}>
                    <ChessboardComponent
                      onMove={(move) => {
                        // Use Chess from chess.js to get the new FEN after the move
                        const chess = new Chess(chessPosition);
                        chess.move({ from: move.slice(0, 2), to: move.slice(2, 4), promotion: move.length > 4 ? move[4] : undefined });
                        const newFen = chess.fen();
                        handleChessMove(move, newFen);
                      }}
                      onGameStateChange={handleGameStateChange}
                      isAgentTurn={gameState.isAgentTurn}
                      position={chessPosition}
                      onReset={resetChessState}
                      onClose={handleCloseChessGame}
                    />
                  </div>
                )}
              </div>
              <ChatInput 
                input={input}
                setInput={setInput}
                loadingMessages={loadingMessages}
                handleSend={handleSend}
                conversationId={conversationId}
              />
            </>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

export default ChatUI;