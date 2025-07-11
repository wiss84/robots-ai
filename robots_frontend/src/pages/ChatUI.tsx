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
import { agentNames } from '../data/AgentDescriptions';

interface ChatMessage {
  role: string;
  type?: 'text' | 'image' | 'file';
  content: string;
  fileName?: string;
  fileUrl?: string;
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

  // Get user name and agent name
  const capitalize = (str: string) => str.charAt(0).toUpperCase() + str.slice(1);
  const firstNameRaw = user?.user_metadata?.first_name || 'User';
  const userName = capitalize(firstNameRaw);
  const agentName = agentId ? agentNames[agentId] || 'Assistant' : 'Assistant';

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
    const { data, error } = await supabase
      .from('messages')
      .select('*')
      .eq('conversation_id', convId)
      .order('created_at', { ascending: true });
    if (!error) {
      setMessages((data || []).map(m => ({ role: m.role, content: m.content })));
    }
    setLoadingMessages(false);
  };

  // Create a new conversation in Supabase
  const handleNewChat = async () => {
    if (!user || !agentId) return;
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
      const isImage = fileInfo.content_type && fileInfo.content_type.startsWith('image/');
      chatMessage = {
        role: 'user',
        type: isImage ? 'image' : 'file',
        content: userMessage,
        fileName: fileInfo.filename,
        fileUrl: `http://127.0.0.1:8000/uploaded_files/${fileInfo.filename}`,
      };

      // Use extracted content for all file types
      if (fileInfo.extracted_content) {
        fileContent = fileInfo.extracted_content;
      }

      // For images, include the URL for visual processing (backend will convert to base64)
      if (isImage) {
        agentMessage = userMessage
          ? `${userMessage}\n[Image: http://127.0.0.1:8000/uploaded_files/${fileInfo.filename}]`
          : `[Image: http://127.0.0.1:8000/uploaded_files/${fileInfo.filename}]`;
      }
    }
    setMessages(prev => [...prev, chatMessage]);
    // Save user message to Supabase
    await supabase.from('messages').insert([
      {
        conversation_id: convId,
        user_id: user.id,
        agent_id: agentId,
        role: 'user',
        content: chatMessage.content
      }
    ]);
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
          conversation_id: convId,
          file_content: fileContent,
          user_name: userName // Pass user name to backend
        })
      });
      const data = await res.json();
      // Save agent message to Supabase
      await supabase.from('messages').insert([
        {
          conversation_id: convId,
          user_id: user.id,
          agent_id: agentId,
          role: 'agent',
          content: data.response
        }
      ]);
      setMessages(prev => [...prev, { role: 'agent', content: data.response }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'agent', content: 'Error: Could not reach backend.' }]);
    }
    setLoadingMessages(false);
    if (messages.length === 0 && convId) {
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
    <>
      <Navbar showHomeLink={true} showAgentSelectionLink={true} />
      <div className="chat-root">
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
              <div style={{ position: 'relative', width: '100%' }}>
                <ChatMessages
                  messages={messages}
                  loadingMessages={loadingMessages}
                  messagesEndRef={messagesEndRef}
                  userName={userName}
                  agentName={agentName}
                  agentId={agentId}
                />
                <ChatInput
                  input={input}
                  setInput={setInput}
                  loadingMessages={loadingMessages}
                  handleSend={handleSend}
                  conversationId={conversationId}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

export default ChatUI;