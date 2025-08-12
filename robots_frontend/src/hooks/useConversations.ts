import { useState, useEffect, useCallback } from 'react';
import { summarizeConversationRolling } from '../utils/conversationSummarizer';

interface UseConversationsProps {
  user: any;
  agentId: string | undefined;
  supabase: any;
  setMessages: (messages: any) => void;
  setLoadingMessages: (loading: boolean) => void;
  setIsSummarizing: (summarizing: boolean) => void;
  clearChessState: () => void;
  isGamesAgent: boolean;
  setPose: (pose: 'greeting'|'typing'|'thinking'|'arms_crossing'|'wondering'|'painting') => void;
}

export const useConversations = ({
  user,
  agentId,
  supabase,
  setMessages,
  setLoadingMessages,
  setIsSummarizing,
  clearChessState,
  isGamesAgent,
  setPose
}: UseConversationsProps) => {
  const [conversations, setConversations] = useState<any[]>([]);
  const [conversationId, setConversationId] = useState<string>('');
  const [agentConversations, setAgentConversations] = useState<{ [agentId: string]: string }>({});

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

  // Reusable function to load a conversation and trigger summarization
  const loadConversation = useCallback(async (convId: string, agentIdToUse: string) => {
    setConversationId(convId);
    if (agentIdToUse) {
      setAgentConversations((prev: any) => ({ ...prev, [agentIdToUse]: convId }));
    }
    setLoadingMessages(true);
    setIsSummarizing(true);
    if (agentIdToUse === 'games') clearChessState();

    // Fetch all messages for display
    const { data: allData, error: allError } = await supabase
      .from('messages')
      .select('*')
      .eq('conversation_id', convId)
      .order('created_at', { ascending: true });

    if (!allError) {
      const messages = (allData || []).map((m: any) => {
        // Extract filename from file_url if it exists
        let fileName = undefined;
        if (m.file_url) {
          const urlParts = m.file_url.split('/');
          fileName = urlParts[urlParts.length - 1]; // Get the last part (filename)
        }
        
        return {
          role: m.role,
          content: m.content,
          type: m.type,
          fileUrl: m.file_url,
          fileName: fileName
        };
      });
      setMessages(messages);
    }

    // Fetch summary and last_summary_created_at
    const { data: convData } = await supabase
      .from('conversations')
      .select('summary, last_summary_created_at')
      .eq('id', convId)
      .single();

    const previousSummary = convData?.summary || '';
    const lastSummaryCreatedAt = convData?.last_summary_created_at;

    let recentMessages = [];
    if (!lastSummaryCreatedAt) {
      recentMessages = (allData || []).map((m: any) => ({ 
        role: m.role, 
        content: m.content, 
        created_at: m.created_at 
      }));
    } else {
      const { data: recentData } = await supabase
        .from('messages')
        .select('*')
        .eq('conversation_id', convId)
        .gt('created_at', lastSummaryCreatedAt)
        .order('created_at', { ascending: true })
        .limit(30);
      recentMessages = (recentData || []).map((m: any) => ({ 
        role: m.role, 
        content: m.content, 
        created_at: m.created_at 
      }));
    }

    if (recentMessages.length > 0) {
      try {
        const summary = await summarizeConversationRolling(previousSummary, recentMessages);
        const lastMsgCreatedAt = recentMessages[recentMessages.length - 1].created_at;
        await supabase
          .from('conversations')
          .update({ summary, last_summary_created_at: lastMsgCreatedAt })
          .eq('id', convId);
        sessionStorage.setItem(`conversation_summary_${convId}`, summary);
      } catch (error) {
        // ignore summarization errors
      }
    }
    setLoadingMessages(false);
    setIsSummarizing(false);
  }, [supabase, setLoadingMessages, setIsSummarizing, setMessages, clearChessState]);

  // When a conversation is selected, fetch its messages
  const handleSelectConversation = useCallback(async (convId: string) => {
    console.log('Selecting conversation:', convId);
    await loadConversation(convId, agentId || '');
  }, [loadConversation, agentId]);

  // Create a new conversation in Supabase
  const handleNewChat = useCallback(async () => {
    if (!user || !agentId) return;
    // Always clear chess state for new chat
    if (isGamesAgent) clearChessState();
    // Reset pose to greeting for new conversation
    setPose('greeting');
    const { data, error } = await supabase
      .from('conversations')
      .insert([{ user_id: user.id, agent_id: agentId, title: 'New Conversation' }])
      .select();
    if (!error && data && data[0]) {
      setConversationId(data[0].id);
      setAgentConversations((prev: any) => ({ ...prev, [agentId]: data[0].id }));
      setMessages([]);
      setConversations((prev: any[]) => [data[0], ...prev]);
    }
  }, [user, agentId, supabase, isGamesAgent, clearChessState, setPose, setMessages]);

  // Rename conversation
  const handleRenameConversation = useCallback(async (convId: string, newTitle: string) => {
    await supabase.from('conversations').update({ title: newTitle }).eq('id', convId);
    setConversations((conversations: any[]) => conversations.map((c: any) => c.id === convId ? { ...c, title: newTitle } : c));
  }, [supabase]);

  // Delete conversation
  const handleDeleteConversation = useCallback(async (convId: string) => {
    await supabase.from('conversations').delete().eq('id', convId);
    setConversations((conversations: any[]) => conversations.filter((c: any) => c.id !== convId));
    if (conversationId === convId) {
      setConversationId('');
      setMessages([]);
    }
  }, [supabase, conversationId, setMessages]);

  // Create conversation if needed and return conversation ID
  const ensureConversation = useCallback(async (): Promise<string | null> => {
    if (conversationId) return conversationId;
    
    if (!user || !agentId) return null;
    
    const { data, error } = await supabase
      .from('conversations')
      .insert([{ user_id: user.id, agent_id: agentId, title: 'New Conversation' }])
      .select();
      
    if (!error && data && data[0]) {
      const newConvId = data[0].id;
      setConversationId(newConvId);
      setAgentConversations((prev: any) => ({ ...prev, [agentId]: newConvId }));
      setConversations((prev: any[]) => [data[0], ...prev]);
      return newConvId;
    }
    
    return null;
  }, [conversationId, user, agentId, supabase]);

  return {
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
  };
};