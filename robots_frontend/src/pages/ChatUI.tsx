import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import './Auth.css';
import './AgentSelection.css';
import './ChatUI.css';
import Navbar from '../components/Navbar';
import { useAuth } from '../hooks/useAuth';
import { useChessGame } from '../hooks/useChessGame';
import { useConversations } from '../hooks/useConversations';
import { useMessageHandler } from '../hooks/useMessageHandler';
import { usePoseManager } from '../hooks/usePoseManager';
import { useFileChangeSocket } from '../hooks/useFileChangeSocket';
import { useSuggestionsSocket } from '../hooks/useSuggestionsSocket';
import ChatSidebar from '../components/ChatSidebar';
import ChatMessages from '../components/ChatMessages';
import ChatInput from '../components/ChatInput';
import ChatPoses from '../components/ChatPoses';
import ErrorBoundary from '../components/ErrorBoundary';
import UsageMonitor from '../components/UsageMonitor';
import ChessboardComponent from '../components/Chessboard';
import { agentNames } from '../data/AgentDescriptions';
import { Chess } from 'chess.js';

interface ChatMessage {
  role: string;
  type?: 'text' | 'image' | 'video' | 'file';
  content: string;
  fileName?: string;
  fileUrl?: string;
}

import CodingAgentPanel from '../components/CodingAgentPanel';
import type { AgentSuggestion } from '../components/MonacoFileEditor';

function ChatUI() {
  const { agentId } = useParams<{ agentId: string }>();
  
  // --- Agent-driven suggestion state ---
  const [agentSuggestion, setAgentSuggestion] = useState<AgentSuggestion | null>(null);

  const onSuggestionMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      console.log('Suggestions WebSocket message received:', data);
      if (data.type === 'agent_suggestion' && data.data) {
        setAgentSuggestion(data.data);
      }
    } catch (err) {
      console.error('Suggestions WebSocket message parse error:', err);
    }
  }, [setAgentSuggestion]);

  // Memoized WebSocket URL
  const backendUrl = useMemo(() => {
    // First try environment variable
    if (import.meta.env.VITE_WS_BACKEND_URL) {
      return import.meta.env.VITE_WS_BACKEND_URL;
    }
    // If not set, construct from window location
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${window.location.host}`;
  }, []);

  const { user, loading, supabase } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);

  const [dropdownOpen, setDropdownOpen] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [showAllConversations, setShowAllConversations] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null) as React.RefObject<HTMLDivElement>;
  const [isSummarizing, setIsSummarizing] = useState(false);
  // Get user name and agent name
  const capitalize = (str: string) => str.charAt(0).toUpperCase() + str.slice(1);
  const userName = useMemo(() => {
    const userNameRaw = user?.user_metadata?.first_name || 'User';
    return capitalize(userNameRaw);
  }, [user]);

  // Use the pose manager hook first to get setPose for other hooks
  const {
    pose,
    setPose,
    isAgentMode,
    toggleAgentMode
  } = usePoseManager({
    agentId,
    messages,
    loadingMessages,
    gameState: { isActive: false, isAgentTurn: false, gameStatus: 'idle' }, // temporary until chess hook
    isGamesAgent: agentId === 'games'
  });

  // Determine the effective agent ID based on mode
  const effectiveAgentId = useMemo(() => {
    if (agentId === 'coding') {
      return isAgentMode ? 'coding' : 'coding-ask';
    }
    return agentId;
  }, [agentId, isAgentMode]);

  // WebSocket connections - only for coding agent in agent mode
  const suggestionsUrl = useMemo(() => {
    // Only connect to suggestions socket when in agent mode (CodingAgentPanel)
    if (agentId !== 'coding' || !isAgentMode) return null;
    return `${backendUrl}/ws/suggestions?agent_type=coding`;
  }, [agentId, backendUrl, isAgentMode]);

  useSuggestionsSocket(suggestionsUrl, onSuggestionMessage);

  const fileChangesUrl = useMemo(() => {
    // Only connect to file changes socket when in agent mode (CodingAgentPanel)
    return (agentId === 'coding' && isAgentMode) ? `${backendUrl}/ws/file-changes` : null;
  }, [agentId, backendUrl, isAgentMode]);

  const { lastMessage: fileChangeMessage } = useFileChangeSocket(fileChangesUrl);

  // Declare clearChessState with a temporary function first to avoid circular dependency
  const [clearChessState, setClearChessState] = useState<(() => void)>(() => () => {});

  // Create a ref to hold the handleSendMessage function
  const handleSendMessageRef = useRef<(userMessage: string, fileInfo: any, convId: string) => Promise<void>>(async () => {
    console.log('handleSendMessage not yet initialized');
  });

  // Use the conversations hook
  const {
    conversations,
    conversationId,
    agentConversations,
    setConversationId,
    handleSelectConversation,
    handleNewChat,
    handleRenameConversation,
    handleDeleteConversation,
    ensureConversation,
    loadConversation
  } = useConversations({
    user,
    agentId: effectiveAgentId,
    supabase,
    setMessages,
    setLoadingMessages,
    setIsSummarizing,
    clearChessState, // Now using state variable
    isGamesAgent: agentId === 'games',
    setPose
  });
  const agentName = agentId ? agentNames[agentId] || 'Assistant' : 'Assistant';

  // Use the chess game hook FIRST to get chess response handler
  const {
    chessPosition,
    gameState,
    isGamesAgent: isGamesAgentFromHook,
    resetChessState,
    clearChessState: actualClearChessState,
    handleChessTrigger,
    handleChessMove,
    handleGameStateChange,
    handleCloseChessGame,
    handleChessResponse
  } = useChessGame({
    agentId,
    conversationId, // Now we have the real conversationId
    userName,
    user,
    supabase,
    setMessages,
    setLoadingMessages,
    handleSendMessage: async (message: string, fileInfo: any, convId: string) => {
      // Use the ref to call the actual handleSendMessage function
      return handleSendMessageRef.current(message, fileInfo, convId);
    }
  });

  // Update the clearChessState state with the actual function from useChessGame
  useEffect(() => {
    if (actualClearChessState) {
      setClearChessState(() => actualClearChessState);
    }
  }, [actualClearChessState]);

  // Use the message handler hook with chess response callback
  const { handleSend: handleSendMessage, handleCancel, handleHiddenContinue } = useMessageHandler({
    user,
    agentId: effectiveAgentId,
    supabase,
    messages,
    setMessages,
    setLoadingMessages,
    setPose,
    handleRenameConversation,
    setConversationId,
    isGamesAgent: effectiveAgentId === 'games',
    userName,
    onChessResponse: isGamesAgentFromHook ? handleChessResponse : undefined
  });

  // Update the ref when handleSendMessage changes
  useEffect(() => {
    handleSendMessageRef.current = handleSendMessage;
  }, [handleSendMessage]);

  // Handle mode switching - separate conversations for ask mode vs agent mode
  useEffect(() => {
    if (agentId === 'coding' && effectiveAgentId) {
      // When switching modes, load the appropriate conversation for the new mode
      const currentEffectiveId = effectiveAgentId;
      const existingConvId = agentConversations[currentEffectiveId];
      
      if (existingConvId && existingConvId !== conversationId) {
        // Load existing conversation for this mode
        loadConversation(existingConvId, currentEffectiveId);
      } else if (!existingConvId && conversationId) {
        // No conversation exists for this mode, clear messages
        setMessages([]);
        setConversationId('');
      }
    }
  }, [effectiveAgentId, agentId, agentConversations, conversationId, loadConversation, setMessages, setConversationId]);

  // HandleSend to accept attachedFile
  const handleSend = useCallback(async (message: string, fileInfo?: any) => {
    if (!message.trim() && !fileInfo) return;
    if (!agentId || !user) return;

    const convId = await ensureConversation();
    if (!convId) return;

    const userMessage = message.trim();

    // Handle games agent special logic for chess
    if (isGamesAgentFromHook) {
      const lowerMsg = userMessage.trim().toLowerCase();
      if (
        lowerMsg.includes('play chess') ||
        lowerMsg.includes('start chess')
      ) {
        // Add the user's message to the chat history
        setMessages((prev: ChatMessage[]) => [...prev, { role: 'user', content: userMessage }]);
        await handleChessTrigger();
        return;
      }
    }

    // Use the message handler hook for all other messages
    await handleSendMessage(userMessage, fileInfo, convId);
  }, [agentId, user, isGamesAgentFromHook, handleChessTrigger, handleSendMessage, ensureConversation]);


  // --- Agent switch handoff logic ---
  const onAgentSwitch = useCallback((newAgentId: string) => {
    navigate(`/chat/${newAgentId}`);
    // Resume previous conversation if it exists, otherwise start new
    const prevConvId = agentConversations[newAgentId];
    if (prevConvId) {
      loadConversation(prevConvId, newAgentId);
    } else {
      setConversationId('');
      setMessages([]);
    }
  }, [navigate, agentConversations, loadConversation, setConversationId, setMessages]);

  const onAcceptSuggestion = useCallback(async (suggestion: AgentSuggestion, successCallback: (newContent: string) => void) => {
    if (!suggestion) return;

    try {
      console.log('Accepting suggestion for file:', suggestion.filePath);
      const httpBackendUrl = (import.meta.env.VITE_WS_BACKEND_URL || '').replace(/^ws/, 'http');
      const res = await fetch(`${httpBackendUrl}/project/files/write`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          path: suggestion.filePath,
          content: suggestion.proposedContent,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        console.error('Failed to write file:', res.status, errText);
        alert(`Failed to write file: ${errText}`);
        return;
      }

      console.log('File written successfully');
      setAgentSuggestion(null);
      successCallback(suggestion.proposedContent);

    } catch (err) {
      console.error('Error accepting suggestion:', err);
      alert(`An unexpected error occurred: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, []);

  const onRejectSuggestion = useCallback((suggestion: AgentSuggestion) => {
    console.log('Rejecting suggestion for file:', suggestion.filePath);
    setAgentSuggestion(null);
  }, []);

  useEffect(() => {
    // Scroll to bottom when messages change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const isCodingAgent = agentId === 'coding';
  const showCodingAgentPanel = isCodingAgent && isAgentMode;



  const showGreeting = messages.length === 0;

  // Helper to get time of day
  const getTimeOfDay = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'morning';
    if (hour < 18) return 'afternoon';
    return 'evening';
  };

  return (
    <ErrorBoundary>
      <div className="chat-root">
        <Navbar showHomeLink={true} showAgentSelectionLink={true} />
        <UsageMonitor />
        {
          loading ? (
            <div className="chat-root"><div>Loading...</div></div>
          ) : !user ? (
            <div className="chat-container">
              <div className="chat-auth-required">
                <h2>Sign In Required</h2>
                <p>You must be signed in to chat with an agent.</p>
                <div className="button-container">
                  <button className="nav-button" onClick={() => navigate('/signin')}>
                    Sign In
                  </button>
                </div>
              </div>
            </div>
          ) : showCodingAgentPanel ? (
            <CodingAgentPanel
              setMessages={setMessages}
              messagesEndRef={messagesEndRef}
              userName={user?.user_metadata?.name || 'User'}
              agentName={agentName}
              isSummarizing={isSummarizing}
              agentId={agentId || ''}
              user={user}
              conversations={conversations}
              messages={messages}
              loadingMessages={loadingMessages}
              handleSend={handleSend}
              handleCancel={handleCancel}
              conversationId={conversationId}
              onAgentSwitch={onAgentSwitch}
              showAllConversations={showAllConversations}
              sidebarOpen={sidebarOpen}
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
              agentSuggestion={agentSuggestion}
              onAcceptSuggestion={onAcceptSuggestion}
              onRejectSuggestion={onRejectSuggestion}
              onToggleAgentMode={toggleAgentMode}
              fileChangeMessage={fileChangeMessage}
              onContinue={handleHiddenContinue}
            />
          ) : (
            <>
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
                {showGreeting ? (
                  <>
                    <div className="chat-greeting-header-outer greeting-mode">
                      <div className="chat-greeting-header">
                        {`Good ${getTimeOfDay()}, ${userName}`}
                      </div>
                    </div>
                    <ChatInput
                      loadingMessages={loadingMessages}
                      handleSend={handleSend}
                      conversationId={conversationId}
                      currentAgentId={agentId || ''}
                      onAgentSwitch={onAgentSwitch}
                      isCodingAgent={isCodingAgent}
                      isAgentMode={isAgentMode}
                      onToggleAgentMode={toggleAgentMode}
                      onCancel={handleCancel}
                    />
                  </>
                ) : (
                  <>
                    <div className="chat-content-wrapper">
                      {/* Chat Area (Messages + Input) */}
                      <div className="chat-area">
                        <ChatMessages
                          messages={messages}
                          loadingMessages={loadingMessages}
                          messagesEndRef={messagesEndRef}
                          userName={userName}
                          agentName={agentName}
                          agentId={agentId}
                          isSummarizing={isSummarizing}
                          conversationId={conversationId}
                          onContinue={handleHiddenContinue}
                        />
                        <ChatInput
                          loadingMessages={loadingMessages}
                          handleSend={handleSend}
                          conversationId={conversationId}
                          currentAgentId={agentId || ''}
                          onAgentSwitch={onAgentSwitch}
                          isCodingAgent={isCodingAgent}
                          isAgentMode={isAgentMode}
                          onToggleAgentMode={toggleAgentMode}
                          onCancel={handleCancel}
                        />
                      </div>
                      {/* Chessboard for Games Agent - Only show when game is active and chessPosition is set */}
                      {isGamesAgentFromHook && gameState.isActive && chessPosition && (
                        <div className="chess-game-container">
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
                  </>
                )}
              </div>
              {/* Pose Container Column */}
              <div className="pose-column">
                <ChatPoses agentId={agentId} pose={pose} />
              </div>
            </>
          )
        }
      </div>
    </ErrorBoundary>
  );
}
export default ChatUI;