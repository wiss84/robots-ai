import { useCallback, useRef } from 'react';
// import DeepSearchContainer from '../components/DeepSearchContainer';

interface ChatMessage {
  role: string;
  type?: 'text' | 'image' | 'video' | 'file';
  content: string;
  fileUrl?: string;
  fileName?: string;
}

interface UseMessageHandlerProps {
  user: any;
  agentId: string | undefined;
  supabase: any;
  messages: ChatMessage[];
  setMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  setLoadingMessages: (loading: boolean) => void;
  setPose: (pose: 'greeting'|'typing'|'thinking'|'arms_crossing'|'wondering'|'painting') => void;
  handleRenameConversation: (convId: string, newTitle: string) => Promise<void>;
  setConversationId: (id: string) => void;
  isGamesAgent: boolean;
  userName: string;
  onChessResponse?: (response: string, convId: string) => Promise<void>; // Callback for chess response handling
}


export const useMessageHandler = ({
  user,
  agentId,
  supabase,
  messages,
  setMessages,
  setLoadingMessages,
  setPose,
  handleRenameConversation,
  setConversationId,
  isGamesAgent,
  userName,
  onChessResponse
}: UseMessageHandlerProps) => {

  // Abort/cancel support
  const abortRef = useRef<AbortController | null>(null);
  const lastConvRef = useRef<string>('');
  const lastAgentRef = useRef<string | undefined>(agentId);

  const handleSend = useCallback(async (userMessage: string, fileInfo: any, convId: string) => {
    // keep latest refs for possible cancel
    lastAgentRef.current = agentId;
    lastConvRef.current = convId;
    // create abort controller for this request
    const controller = new AbortController();
    abortRef.current = controller;
    if (!userMessage.trim() || !user || !agentId) return;

    setLoadingMessages(true);
    setPose('typing');

    // Special handling for games agent
    if (isGamesAgent && userMessage.toLowerCase().includes('chess')) {
      // This would trigger chess game initialization
      // The actual chess handling is done in useChessGame hook
      console.log('useMessageHandler: Detected chess-related message', { userMessage });
    }
    
    console.log('useMessageHandler: Processing message', { 
      userMessage, 
      agentId, 
      convId, 
      isGamesAgent 
    });
    

    
    // Compose message content for agent with file content
    let agentMessage = userMessage;
    let fileContent = null;
    let chatMessage: ChatMessage = {
      role: 'user',
      content: userMessage
    };
    
    // Check if this is a chess move message that shouldn't be displayed in UI
    const isHiddenChessMessage = userMessage.includes('I just made the move') && 
                                userMessage.includes('The current position is') && 
                                userMessage.includes('Available legal moves are');
    
    // Check if this is a chess start message that shouldn't be displayed in UI
    const isHiddenChessStartMessage = userMessage.includes('just started a chess game') && 
                                     userMessage.includes('Please respond with your excitement');
    
    // Check if this is a new game message that shouldn't be displayed in UI
    const isHiddenNewGameMessage = userMessage.includes('decided to start a new game') && 
                                  userMessage.includes('please acknowledge it');
    
    // Check if this is a close game message that shouldn't be displayed in UI
    const isHiddenCloseGameMessage = userMessage.includes('decided to close the current chess game') && 
                                    userMessage.includes('please acknowledge it');
    
    // Check if this is a game over message that shouldn't be displayed in UI
    const isHiddenGameOverMessage = userMessage.includes('I just made the move') && 
                                   userMessage.includes('The current position is') && 
                                   userMessage.includes('There are no legal moves available') &&
                                   userMessage.includes('game may be over');
    
    // Handle file attachments
    if (fileInfo) {
      const isImage = fileInfo.content_type?.startsWith('image/');
      fileContent = fileInfo.extracted_content || '';
      
      // Add file info to the chat message
      chatMessage = {
        role: 'user',
        type: isImage ? 'image' : 'file',
        content: userMessage,
        fileUrl: fileInfo.file_url,
        fileName: fileInfo.filename
      };

      // For images, include base64 data in the message
      if (isImage) {
        // Remove the '/uploaded_files/' prefix and fetch the image
        const imgPath = fileInfo.file_url.replace('/uploaded_files/', '');
        try {
          const response = await fetch(`http://localhost:8000/project/files/content/${imgPath}`);
          if (response.ok) {
            const blob = await response.blob();
            const reader = new FileReader();
            const base64 = await new Promise<string>((resolve) => {
              reader.onloadend = () => resolve(reader.result as string);
              reader.readAsDataURL(blob);
            });
            fileContent = base64;
            agentMessage = `${userMessage}\n\n[Image: ${base64}]`;
          }
        } catch (err) {
          console.error('Error loading image:', err);
        }
      } else if (fileContent) {
        // For other files, include the extracted content
        agentMessage = `${userMessage}\n\nFile Content from ${fileInfo.filename}:\n${fileContent}`;
      }
    }
    
    // Add user message to UI immediately (unless it's a hidden chess message)
    if (!isHiddenChessMessage && !isHiddenChessStartMessage && !isHiddenNewGameMessage && !isHiddenCloseGameMessage && !isHiddenGameOverMessage) {
      setMessages((prev: ChatMessage[]) => [...prev, chatMessage]);
    } else {
      console.log('Skipping UI display for hidden chess message');
    }
    
    // Save user message to database (including hidden chess messages)
    if (convId && user) {
      try {
        const { error } = await supabase
          .from('messages')
          .insert([{
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'user',
            content: userMessage,
            type: chatMessage.type || null,
            file_url: chatMessage.fileUrl || null
          }])
          .select();
          
        if (error) {
          console.error('Error saving message to Supabase:', error);
        }
      } catch (err) {
        console.error('Failed to save message to database:', err);
      }
    }
    
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
      
// If coding, finance, or news agent, use streaming endpoint
if (agentId === 'coding' || agentId === 'finance' || agentId === 'news') {
  try {
    setPose('typing');

    const streamRes = await fetch(`http://localhost:8000/${agentId}/ask/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: JSON.stringify({
        message: agentMessage,
        conversation_id: convId,
        conversation_summary: conversationSummary
      }),
      signal: controller.signal
    });

    if (!streamRes.ok || !streamRes.body) {
      const errorText = await streamRes.text().catch(() => '');
      console.error('Stream HTTP Error:', streamRes.status, errorText);
      throw new Error(`HTTP ${streamRes.status}: ${streamRes.statusText} - ${errorText}`);
    }

    // Append placeholder agent message to update progressively
    setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: '' }]);

    const reader = streamRes.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let assembled = '';

    const flushChunk = (raw: string) => {
      // Expect SSE-style: lines like "data: {...}\n\n"
      const line = raw.trim();
      if (!line.startsWith('data:')) return;
      const jsonStr = line.slice(5).trim();
      if (!jsonStr) return;

      try {
        const evt = JSON.parse(jsonStr);
        if (evt.type === 'token' && typeof evt.content === 'string') {
          assembled += evt.content;
          // Update last agent message with current assembled content
          setMessages((prev: ChatMessage[]) => {
            const updated = [...prev];
            // Update last message which we just pushed as agent
            for (let i = updated.length - 1; i >= 0; i--) {
              if (updated[i].role === 'agent') {
                updated[i] = { ...updated[i], content: assembled };
                break;
              }
            }
            return updated;
          });
        } else if (evt.type === 'done') {
          if (evt.conversation_id) {
            setConversationId(evt.conversation_id);
          }
        } else if (evt.type === 'error') {
          throw new Error(evt.message || 'Streaming error');
        }
      } catch (e) {
        console.error('Failed to parse stream event:', e, raw);
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Split on SSE event separators
      let idx;
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        flushChunk(rawEvent);
      }
    }

    // Finalize assembly if there's trailing buffer (no \n\n at end)
    if (buffer.trim().length > 0) {
      flushChunk(buffer);
      buffer = '';
    }

    // If streaming produced no content, show continue prompt and stop
    if (!assembled || assembled.trim() === '') {
      const fallbackText = '[[CONTINUE]] Something went wrong with the previous response. Click Continue to resume the previous task.';
      setMessages((prev: ChatMessage[]) => {
        const updated = [...prev];
        for (let i = updated.length - 1; i >= 0; i--) {
          if (updated[i].role === 'agent') {
            updated[i] = { ...updated[i], content: fallbackText };
            break;
          }
        }
        return updated;
      });
      setPose('wondering');
      setLoadingMessages(false);
      abortRef.current = null;
      return;
    }



    // Save agent streamed message to database
    if (convId && user && assembled) {
      try {
        const { error } = await supabase
          .from('messages')
          .insert([{
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'agent',
            content: assembled
          }])
          .select();
        if (error) {
          console.error('Error saving streamed agent response to Supabase:', error);
        }
      } catch (err) {
        console.error('Failed to save streamed agent response to database:', err);
      }
    }

    // Update usage stats
    if ((window as any).updateUsage) {
      (window as any).updateUsage();
    }

    setPose('arms_crossing');
    // Rename conversation if it's the first user message (streaming path)
    try {
      const isFirstUserMessage = messages.filter(m => m.role === 'user').length === 0;
      if (isFirstUserMessage && convId) {
        await supabase.from('conversations')
          .update({ title: userMessage.slice(0, 30) })
          .eq('id', convId);
        await handleRenameConversation(convId, userMessage.slice(0, 30));
      }
    } catch (e) {
      console.error('Failed to rename conversation (streaming):', e);
    }
    setLoadingMessages(false);
    // For coding agent streaming, we return here to avoid the non-stream flow
    abortRef.current = null;
    return;
  } catch (err: any) {
    // If aborted by user, stop gracefully without fallback
    if ((err && err.name === 'AbortError') || controller.signal.aborted) {
      // Remove the placeholder empty agent message if present
      setMessages((prev: ChatMessage[]) => {
        const updated = [...prev];
        if (
          updated.length > 0 &&
          updated[updated.length - 1].role === 'agent' &&
          (updated[updated.length - 1].content ?? '') === ''
        ) {
          updated.pop();
        }
        return updated;
      });
      setPose('arms_crossing');
      setLoadingMessages(false);
      abortRef.current = null;
      return;
    }
    console.error('Streaming chat error:', err);
    setPose('wondering');
    const errorMessage = '⚠️ Streaming Error\n\nUnable to stream response. Falling back to non-streaming.';
    setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: errorMessage }]);

    try {
      const { error } = await supabase
        .from('messages')
        .insert([{
          conversation_id: convId,
          user_id: user.id,
          agent_id: agentId,
          role: 'agent',
          content: errorMessage
        }])
        .select();
      if (error) {
        console.error('Error saving streaming error message to Supabase:', error);
      }
    } catch (dbError) {
      console.error('Failed to save streaming error message to database:', dbError);
    }

    // Do not early return; continue to the regular /chat flow as a fallback
  }
}
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer test-token'
        },
        body: JSON.stringify(requestBody),
        signal: controller.signal
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

      // If server returned an empty/whitespace response, show Continue fallback banner
      {
        const respStr = typeof data.response === 'string' ? data.response : String(data.response ?? '');
        if (!respStr || respStr.trim() === '' || (typeof data.response === 'object' && Object.keys(data.response).length === 0)) {
          setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: '[[CONTINUE]] Something went wrong with the previous response. Click Continue to resume the previous task.' }]);
          setPose('wondering');
          setLoadingMessages(false);
          abortRef.current = null;
          return;
        }
      }

      // Handle planned delay (backend indicates countdown and expects client-side auto-retry)
      if (data.response && typeof data.response === 'string' && data.response.startsWith('⏳ Waiting')) {
        const match = data.response.match(/Waiting\s+(\d+)\s+seconds/i);
        let remaining = match ? parseInt(match[1], 10) : 0;

        // Append delay status message (ephemeral)
        setMessages((prev: ChatMessage[]) => [
          ...prev,
          { role: 'agent', content: `[[DELAY:${remaining}]] ⏳ Waiting ${remaining} seconds to avoid rate limits...` }
        ]);

        // Countdown that updates the last agent message
        await new Promise<void>((resolve) => {
          const interval = setInterval(() => {
            remaining = Math.max(remaining - 1, 0);
            setMessages((prev: ChatMessage[]) => {
              const updated = [...prev];
              for (let i = updated.length - 1; i >= 0; i--) {
                const c = updated[i].content as string;
                if (updated[i].role === 'agent' && typeof c === 'string' && c.startsWith('[[DELAY:')) {
                  updated[i] = {
                    ...updated[i],
                    content: `[[DELAY:${remaining}]] ⏳ Waiting ${remaining} seconds to avoid rate limits...`
                  };
                  break;
                }
              }
              return updated;
            });
            if (remaining <= 0) {
              clearInterval(interval);
              resolve();
            }
          }, 1000);
        });

        // Remove delay message after countdown
        setMessages((prev: ChatMessage[]) => {
          const updated = [...prev];
          if (
            updated.length > 0 &&
            updated[updated.length - 1].role === 'agent' &&
            typeof updated[updated.length - 1].content === 'string' &&
            (updated[updated.length - 1].content as string).startsWith('[[DELAY:')
          ) {
            updated.pop();
          }
          return updated;
        });

        // Auto-retry same request without adding another user message
        const controller2 = new AbortController();
        abortRef.current = controller2;
        setLoadingMessages(true);
        try {
          const res2 = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer test-token'
            },
            body: JSON.stringify(requestBody),
            signal: controller2.signal
          });

          if (!res2.ok) {
            const errorText = await res2.text();
            throw new Error(`HTTP ${res2.status}: ${res2.statusText} - ${errorText}`);
          }

          const data2 = await res2.json();

          // Update conversationId if present
          if (data2.conversation_id) {
            setConversationId(data2.conversation_id);
          }

          // API quota style errors
          if (data2.response && (
              data2.response.includes('API Quota Exceeded') ||
              data2.response.includes('Rate Limit Reached') ||
              data2.response.includes('ResourceExhausted')
            )) {
            setPose('wondering');
            setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: data2.response }]);
            await supabase.from('messages').insert([{
              conversation_id: convId,
              user_id: user.id,
              agent_id: agentId,
              role: 'agent',
              content: data2.response
            }]);
            setLoadingMessages(false);
            abortRef.current = null;
            return;
          }

          // Games agent JSON handling (minimal parity)
          let parsed2: any = null;
          try { parsed2 = JSON.parse(data2.response); } catch {}

          if (isGamesAgent && parsed2 && parsed2.fen) {
            // Use callback for chess response handling if provided
            if (onChessResponse) {
              await onChessResponse(data2.response, convId);
            } else {
              // Fallback to default behavior
              setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: data2.response }]);
              if (convId && user) {
                try {
                  await supabase.from('messages').insert([{
                    conversation_id: convId,
                    user_id: user.id,
                    agent_id: agentId,
                    role: 'agent',
                    content: data2.response
                  }]).select();
                } catch (e) {
                  console.error('Error saving chess response (retry):', e);
                }
              }
            }
          } else {
            setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: data2.response }]);
            if (convId && user) {
              try {
                await supabase.from('messages').insert([{
                  conversation_id: convId,
                  user_id: user.id,
                  agent_id: agentId,
                  role: 'agent',
                  content: data2.response
                }]).select();
              } catch (e) {
                console.error('Error saving agent response (retry):', e);
              }
            }
          }

          setPose('arms_crossing');
          setLoadingMessages(false);
          abortRef.current = null;
          return;
        } catch (e) {
          console.error('Retry after delay failed:', e);
          setPose('wondering');
          setLoadingMessages(false);
          abortRef.current = null;
          return;
        }
      }

      // Check if response contains image path
      if (data.response && typeof data.response === 'string' && data.response.includes('{image_path:')) {
        // Extract image path from response
        const imageMatch = data.response.match(/{image_path: ['"]([^'"]+)['"]}/);
        if (imageMatch) {
          const filename = imageMatch[1];

          // Remove the image_path part from the displayed text
          const displayText = data.response.replace(/\n?\n?{image_path: ['"][^'"]+['"]}/g, '').trim();

          setMessages((prev: ChatMessage[]) => [...prev, {
            role: 'agent',
            type: 'image',
            content: displayText || `Here's your generated image: ${filename}`,
            fileUrl: `/uploaded_files/${filename}`,
            fileName: filename
          }]);
        }
      }
      // Check if response contains video path
      else if (data.response && typeof data.response === 'string' && data.response.includes('{video_path:')) {
        // Extract video path from response
        const videoMatch = data.response.match(/{video_path: ['"]([^'"]+)['"]}/);
        if (videoMatch) {
          const filename = videoMatch[1];

          // Remove the video_path part from the displayed text
          const displayText = data.response.replace(/\n?\n?{video_path: ['"][^'"]+['"]}/g, '').trim();

          setMessages((prev: ChatMessage[]) => [...prev, {
            role: 'agent',
            type: 'video',
            content: displayText || `Here's your generated video: ${filename}`,
            fileUrl: `/uploaded_files/${filename}`,
            fileName: filename
          }]);

          // Save to database
          if (convId && user) {
            try {
              await supabase.from('messages').insert([{
                conversation_id: convId,
                user_id: user.id,
                agent_id: agentId,
                role: 'agent',
                content: displayText || `Here's your generated image: ${filename}`,
                type: 'image',
                file_url: `/uploaded_files/${filename}`
              }]);
            } catch (e) {
              console.error('Error saving image response to Supabase:', e);
            }
          }

          setPose('arms_crossing');
          setLoadingMessages(false);
          abortRef.current = null;
          return;
        }
      }

      // Check for API quota errors in the response (only for string responses)
      if (data.response && typeof data.response === 'string' && (
        data.response.includes('API Quota Exceeded') ||
        data.response.includes('Rate Limit Reached') ||
        data.response.includes('ResourceExhausted')
      )) {
        // Set error pose and show quota error message
        setPose('wondering');
        setMessages((prev: ChatMessage[]) => [...prev, {
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
      console.log('Chess response handling:', { isGamesAgent, onChessResponse: !!onChessResponse, response: data.response });
      if (isGamesAgent) {
        console.log('Processing games agent response:', { response: data.response, onChessResponse: !!onChessResponse });
        // Use callback for chess response handling if provided
        if (onChessResponse) {
          await onChessResponse(data.response, convId);
        } else {
          // Fallback to default behavior if no callback
          setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: data.response }]);
          
          // Save agent response to database
          if (convId && user) {
            try {
              const { error } = await supabase
                .from('messages')
                .insert([{
                  conversation_id: convId,
                  user_id: user.id,
                  agent_id: agentId,
                  role: 'agent',
                  content: data.response
                }])
                .select();
                
              if (error) {
                console.error('Error saving chess response to Supabase:', error);
              }
            } catch (err) {
              console.error('Failed to save chess response to database:', err);
            }
          }
        }
      } else {
        // Handle regular text response
        const responseText = typeof data.response === 'string' ? data.response : JSON.stringify(data.response);
        setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: responseText }]);

        // Save agent response to database
        if (convId && user) {
          try {
            const { error } = await supabase
              .from('messages')
              .insert([{
                conversation_id: convId,
                user_id: user.id,
                agent_id: agentId,
                role: 'agent',
                content: responseText
              }])
              .select();

            if (error) {
              console.error('Error saving agent response to Supabase:', error);
            }
          } catch (err) {
            console.error('Failed to save agent response to database:', err);
          }
        }
      }
      abortRef.current = null;
    } catch (err: any) {
      // Graceful handling of user-initiated cancel
      if ((err && err.name === 'AbortError')) {
        setPose('wondering');
        setLoadingMessages(false);
        abortRef.current = null;
        return;
      }

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
      setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: errorMessage }]);
      
      // Save error message to database
      try {
        const { error } = await supabase
          .from('messages')
          .insert([{
            conversation_id: convId,
            user_id: user.id,
            agent_id: agentId,
            role: 'agent',
            content: errorMessage
          }])
          .select();
          
        if (error) {
          console.error('Error saving error message to Supabase:', error);
        }
      } catch (dbError) {
        console.error('Failed to save error message to database:', dbError);
      }
    }
    setLoadingMessages(false);
    
    // Rename conversation if it's the first user message (for chess games, this might be the first move)
    const isFirstUserMessage = messages.filter(m => m.role === 'user').length === 0;
    if (isFirstUserMessage && convId) {
      await supabase.from('conversations').update({ title: userMessage.slice(0, 30) }).eq('id', convId);
      await handleRenameConversation(convId, userMessage.slice(0, 30));
    }
  }, [
    user,
    agentId,
    supabase,
    messages,
    setMessages,
    setLoadingMessages,
    setPose,
    handleRenameConversation,
    setConversationId,
    isGamesAgent,
    userName,
    onChessResponse
  ]);

  const handleCancel = useCallback(async () => {
    try {
      const ctrl = abortRef.current;
      if (ctrl && !ctrl.signal.aborted) {
        ctrl.abort();
      }
      // best-effort server-side interrupt for coding, finance, or news stream
      if ((lastAgentRef.current === 'coding' || lastAgentRef.current === 'finance' || lastAgentRef.current === 'news') && lastConvRef.current) {
        try {
          await fetch(`http://localhost:8000/${lastAgentRef.current}/ask/interrupt`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conversation_id: lastConvRef.current })
          });
        } catch {
          // ignore network/interrupt errors
        }
      }
    } finally {
      setPose('arms_crossing');
      setLoadingMessages(false);
      abortRef.current = null;
    }
  }, [setLoadingMessages, setPose]);

  const handleHiddenContinue = useCallback(async (convId: string) => {
    if (!convId || !agentId || !user) return;
    setLoadingMessages(true);
    setPose('thinking');

    const continueMessage =
      "Something went wrong with your previous response. Please check the last task you were working on and continue to complete it.";

    try {
      if (agentId === 'coding' || agentId === 'finance' || agentId === 'news') {
        // Stream silently to continue the task
        const controller = new AbortController();
        abortRef.current = controller;

        const streamRes = await fetch(`http://localhost:8000/${agentId}/ask/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
          },
          body: JSON.stringify({
            message: continueMessage,
            conversation_id: convId
          }),
          signal: controller.signal
        });

        if (!streamRes.ok || !streamRes.body) {
          const t = await streamRes.text().catch(() => '');
          throw new Error(`HTTP ${streamRes.status}: ${streamRes.statusText} - ${t}`);
        }

        // Insert placeholder agent message
        setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: '' }]);

        const reader = streamRes.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let assembled = '';

        const flushChunk = (raw: string) => {
          const line = raw.trim();
          if (!line.startsWith('data:')) return;
          const jsonStr = line.slice(5).trim();
          if (!jsonStr) return;

          try {
            const evt = JSON.parse(jsonStr);
            if (evt.type === 'token' && typeof evt.content === 'string') {
              assembled += evt.content;
              setMessages((prev: ChatMessage[]) => {
                const updated = [...prev];
                for (let i = updated.length - 1; i >= 0; i--) {
                  if (updated[i].role === 'agent') {
                    updated[i] = { ...updated[i], content: assembled };
                    break;
                  }
                }
                return updated;
              });
            }
          } catch (e) {
            console.error('Failed to parse stream event (continue):', e, raw);
          }
        };

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            flushChunk(rawEvent);
          }
        }
        if (buffer.trim().length > 0) {
          flushChunk(buffer);
          buffer = '';
        }

        // Save agent streamed continue response if any
        // (optional, safe to skip saving empty)
        if (convId && user && assembled) {
          try {
            await supabase.from('messages').insert([{
              conversation_id: convId,
              user_id: user.id,
              agent_id: agentId,
              role: 'agent',
              content: assembled
            }]).select();
          } catch (e) {
            console.error('Error saving continued agent response:', e);
          }
        }

        setPose('arms_crossing');
        setLoadingMessages(false);
        abortRef.current = null;
        return;
      } else {
        // Non-coding: silent /chat call without adding a user message
        const controller = new AbortController();
        abortRef.current = controller;

        const requestBody: any = {
          agent_id: agentId,
          message: continueMessage,
          conversation_id: convId,
          file_content: null,
          user_name: userName
        };

        const res = await fetch('http://localhost:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
          },
          body: JSON.stringify(requestBody),
          signal: controller.signal
        });

        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(`HTTP ${res.status}: ${res.statusText} - ${errorText}`);
        }

        const data = await res.json();

        if (data.conversation_id) {
          setConversationId(data.conversation_id);
        }

        setMessages((prev: ChatMessage[]) => [...prev, { role: 'agent', content: data.response }]);

        if (convId && user) {
          try {
            await supabase.from('messages').insert([{
              conversation_id: convId,
              user_id: user.id,
              agent_id: agentId,
              role: 'agent',
              content: data.response
            }]).select();
          } catch (e) {
            console.error('Error saving continued agent response (non-coding):', e);
          }
        }

        setPose('arms_crossing');
        setLoadingMessages(false);
        abortRef.current = null;
        return;
      }
    } catch (e) {
      console.error('Hidden continue failed:', e);
      setPose('wondering');
      setLoadingMessages(false);
      abortRef.current = null;
    }
  }, [agentId, setConversationId, setLoadingMessages, setMessages, setPose, supabase, user, userName]);

  return {
    handleSend,
    handleCancel,
    handleHiddenContinue
  };
};