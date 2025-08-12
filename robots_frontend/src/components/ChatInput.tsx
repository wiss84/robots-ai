import React, { useState, useRef } from 'react';
import type { DragEvent } from 'react';
import './ChatInput.css';
import { FiMic, FiSend, FiX, FiStopCircle } from 'react-icons/fi';
import { FaRobot } from 'react-icons/fa';
import FileUpload from './FileUpload';
import { agents } from '../pages/AgentSelection';
import type { Agent } from '../pages/AgentSelection';

interface ChatInputProps {
  loadingMessages: boolean;
  handleSend: (message: string, attachedFile?: any, overrideAgentId?: string) => void;
  conversationId: string;
  currentAgentId: string;
  onAgentSwitch: (newAgentId: string, message: string, file?: any, autoSend?: boolean) => void;
  isCodingAgent?: boolean;
  isAgentMode?: boolean;
  onToggleAgentMode?: () => void;
  onCancel?: () => void;
}

const ChatInput: React.FC<ChatInputProps> = ({

  loadingMessages,
  handleSend,
  conversationId,
  currentAgentId,
  onAgentSwitch,
  isCodingAgent = false,
  isAgentMode = false,
  onToggleAgentMode,
  onCancel,
}) => {
  const [input, setInput] = useState('');
  const [attachedFile, setAttachedFile] = useState<any>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false); // Track file upload state
  const inputContainerRef = useRef<HTMLDivElement>(null);

  // --- Agent switch confirmation state ---
  const [pendingSwitchAgent, setPendingSwitchAgent] = useState<Agent | null>(null);
  const [pendingFile, setPendingFile] = useState<any>(null);

  // Word-boundary keyword matching
  function matchesAgentKeyword(userMessage: string, keywords: string[]): boolean {
    return keywords.some(keyword => {
      const regex = new RegExp(`\\b${keyword.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\b`, 'i');
      return regex.test(userMessage);
    });
  }

  // Called after file is uploaded to backend
  const handleFileUpload = (fileInfo: any) => {
    setAttachedFile(fileInfo);
    setUploading(false);
    setError(null);
  };

  // Drag and drop handlers
  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };
  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      setUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('workspace_upload', (isCodingAgent && isAgentMode).toString());
      if (conversationId) formData.append('conversation_id', conversationId);
      
      fetch('http://localhost:8000/project/files/upload', {
        method: 'POST',
        body: formData,
      })
        .then(res => {
          if (!res.ok) throw new Error('File upload failed');
          return res.json();
        })
        .then(data => {
          // Check if file processing was successful
          if (data.success === false) {
            setError(data.error || 'File processing failed');
            setUploading(false);
            return;
          }
          setAttachedFile(data);
          setUploading(false);
          setError(null);
        })
        .catch(err => {
          setError('File upload error: ' + err.message);
          setUploading(false);
        });
    }
  };

  const handleRemoveAttachment = () => setAttachedFile(null);

  // Enhanced handleSend to log errors
  const onSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (uploading) return; // Prevent send while uploading
    try {
      // --- Smarter agent switch confirmation logic ---
      const currentAgent = agents.find(agent => agent.id === currentAgentId);
      const matchesCurrent = currentAgent && currentAgent.keywords && matchesAgentKeyword(input, currentAgent.keywords);
      const matchedAgent = agents.find(agent =>
        agent.id !== currentAgentId &&
        agent.keywords &&
        matchesAgentKeyword(input, agent.keywords)
      );
      if (matchedAgent && !matchesCurrent) {
        setPendingSwitchAgent(matchedAgent);
        setPendingFile(attachedFile);
        return;
      }
      handleSend(input, attachedFile);
      setInput('');
      setAttachedFile(null);
      setError(null);
    } catch (err: any) {
      setError('Send error: ' + err.message);
    }
  };

  const confirmAgentSwitch = () => {
    if (pendingSwitchAgent) {
      onAgentSwitch(pendingSwitchAgent.id, '', pendingFile, false);
    }
    setPendingSwitchAgent(null);
    setPendingFile(null);
    setAttachedFile(null);
    setError(null);
    setInput('');
  };

  const cancelAgentSwitch = () => {
    handleSend(input, pendingFile);
    setInput('');
    setPendingSwitchAgent(null);
    setPendingFile(null);
    setAttachedFile(null);
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (uploading) return; // Prevent send while uploading
      try {
        // --- Smarter agent switch confirmation logic (same as onSend) ---
        const currentAgent = agents.find(agent => agent.id === currentAgentId);
        const matchesCurrent = currentAgent && currentAgent.keywords && matchesAgentKeyword(input, currentAgent.keywords);
        const matchedAgent = agents.find(agent =>
          agent.id !== currentAgentId &&
          agent.keywords &&
          matchesAgentKeyword(input, agent.keywords)
        );
        if (matchedAgent && !matchesCurrent) {
          setPendingSwitchAgent(matchedAgent);
          setPendingFile(attachedFile);
          return;
        }
        handleSend(input, attachedFile);
        setInput('');
        setAttachedFile(null);
        setError(null);
      } catch (err: any) {
        setError('Send error: ' + err.message);
      }
    }
  };

  return (
    <div className="chat-input-container" ref={inputContainerRef}>
      {error && <div className="chat-input-error">{error}</div>}
      {pendingSwitchAgent && (
        <div className="agent-switch-modal">
          <div className="agent-switch-modal-content">
            <p>
              It looks like your question is about <b>{pendingSwitchAgent.name}</b>.<br />
              Would you like to switch to the <b>{pendingSwitchAgent.name}</b> agent?
            </p>
            <div className="agent-switch-modal-buttons">
              <button
                className="agent-switch-confirm"
                onClick={confirmAgentSwitch}
              >
                Yes, switch
              </button>
              <button
                className="agent-switch-cancel"
                onClick={cancelAgentSwitch}
              >
                No, stay here
              </button>
            </div>
          </div>
        </div>
      )}
      <form
        className="chat-input-form"
        onSubmit={onSend}
      >
        <div
          className={`chat-input-wrapper${dragActive ? ' drag-active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {attachedFile && (
            <div className="chat-attachment-preview">
              <div className="attachment-info">
                {attachedFile.content_type && attachedFile.content_type.startsWith('image/') ? (
                  <img
                    src={attachedFile.file_url || `/uploaded_files/${attachedFile.filename}`}
                    alt="preview"
                    className="attachment-thumbnail"
                  />
                ) : (
                  <div className="file-attachment-info">
                    <span className="file-icon">📄</span>
                    <span className="file-type">{attachedFile.content_type?.split('/')[1]?.toUpperCase() || 'FILE'}</span>
                  </div>
                )}
                <div className="attachment-success">
                  <span className="success-icon">✓</span>
                  <span className="success-text">Ready to send</span>
                </div>
              </div>
              <button type="button" className="chat-attachment-remove" onClick={handleRemoveAttachment}>
                <FiX size={18} />
              </button>
            </div>
          )}
          <div className="chat-input-row">
            <textarea
              className="chat-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isCodingAgent ? 
                `Message in ${isAgentMode ? 'Agent' : 'Ask'} Mode...` : 
                'Type your message...'
              }
              disabled={loadingMessages || uploading}
              rows={3}
            />
            <div className="chat-input-buttons">
              <FileUpload 
                conversationId={conversationId}
                workspaceUpload={isCodingAgent && isAgentMode}
                onUploadSuccess={(fileInfo) => {
                  setUploading(false);
                  handleFileUpload(fileInfo);
                }}
              />
              <button 
                type="button" 
                className="chat-mic-btn" 
                disabled={uploading}
                title="Voice input (coming soon)"
              >
                <FiMic size={24} color="#00bcd4" />
              </button>
              {loadingMessages ? (
                <button
                  type="button"
                  className="chat-send-btn"
                  onClick={onCancel}
                  disabled={uploading || !onCancel}
                  title="Stop"
                >
                  <FiStopCircle size={24} color="#e53935" />
                </button>
              ) : (
                <button
                  type="submit"
                  className="chat-send-btn"
                  disabled={uploading || (!input.trim() && !attachedFile)}
                >
                  <FiSend size={24} color="#00bcd4" />
                </button>
              )}
              {isCodingAgent && (
                <button
                  type="button"
                  className={`agent-mode-toggle ${isAgentMode ? 'active' : ''}`}
                  onClick={onToggleAgentMode}
                  title={isAgentMode ? 'Switch to Ask Mode' : 'Switch to Agent Mode'}
                  disabled={loadingMessages || uploading}
                >
                  <FaRobot size={24} color="#00bcd4" />
                </button>
              )}
            </div>
          </div>
        </div>
        {uploading && <div className="chat-uploading-spinner">Uploading...</div>}
      </form>
    </div>
  );
};

export default ChatInput;