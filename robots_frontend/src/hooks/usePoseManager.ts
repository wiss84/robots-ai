import { useState, useEffect, useRef, useCallback } from 'react';

interface ChatMessage {
  role: string;
  type?: 'text' | 'image' | 'file';
  content: string;
  fileName?: string;
  fileUrl?: string;
}

type PoseType = 'greeting' | 'typing' | 'thinking' | 'arms_crossing' | 'wondering' | 'painting';

interface UsePoseManagerProps {
  agentId: string | undefined;
  messages: ChatMessage[];
  loadingMessages: boolean;
  gameState: any;
  isGamesAgent: boolean;
}

export const usePoseManager = ({
  agentId,
  messages,
  loadingMessages,
  gameState,
  isGamesAgent
}: UsePoseManagerProps) => {
  const [pose, setPose] = useState<PoseType>('greeting');
  const [isAgentMode, setIsAgentMode] = useState(false);
  const idleTimer = useRef<NodeJS.Timeout | null>(null);

  // Set pose for greeting on initial load/new chat
  useEffect(() => {
    setPose('greeting');
  }, [agentId]);

  // Reset agent mode when switching agents
  useEffect(() => {
    setIsAgentMode(false);
  }, [agentId]);



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
  }, [messages, loadingMessages]);

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

  const toggleAgentMode = useCallback(() => {
    setIsAgentMode((prev: boolean) => !prev);
  }, []);

  return {
    pose,
    setPose,
    isAgentMode,
    setIsAgentMode,
    toggleAgentMode
  };
};