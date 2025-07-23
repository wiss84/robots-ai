import React, { useState, useRef } from 'react';
import type { DragEvent } from 'react';
import './ChatInput.css';
import { FiMic, FiSend, FiX } from 'react-icons/fi';
import FileUpload from './FileUpload';
import { agents } from '../pages/AgentSelection';
import type { Agent } from '../pages/AgentSelection';

interface ChatInputProps {
  input: string;
  setInput: (val: string) => void;
  loadingMessages: boolean;
  handleSend: (attachedFile?: any, overrideAgentId?: string) => void;
  conversationId: string;
  currentAgentId: string; // <-- Add this prop
  onAgentSwitch: (newAgentId: string, message: string, file?: any, autoSend?: boolean) => void;
}

const ChatInput: React.FC<ChatInputProps> = ({ input, setInput, loadingMessages, handleSend, conversationId, currentAgentId, onAgentSwitch }) => {
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
      if (conversationId) formData.append('conversation_id', conversationId);
      fetch('http://localhost:8000/files/upload', {
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
      handleSend(attachedFile);
      setAttachedFile(null);
      setError(null);
    } catch (err: any) {
      setError('Send error: ' + err.message);
    }
  };

  return (
    <>
      {/* Agent switch confirmation dialog */}
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
                style={{ background: '#00bcd4', color: '#fff', border: 'none', borderRadius: 6, padding: '0.5rem 1.2rem', marginRight: 8, cursor: 'pointer' }}
                onClick={() => {
                  onAgentSwitch(pendingSwitchAgent.id, '', pendingFile, false);
                  setPendingSwitchAgent(null);
                  setPendingFile(null);
                  setAttachedFile(null);
                  setError(null);
                  setInput('');
                }}
              >
                Yes, switch
              </button>
              <button
                className="agent-switch-cancel"
                style={{ background: '#00bcd4', color: '#fff', border: 'none', borderRadius: 6, padding: '0.5rem 1.2rem', marginLeft: 8, cursor: 'pointer' }}
                onClick={() => {
                  handleSend(pendingFile);
                  setPendingSwitchAgent(null);
                  setPendingFile(null);
                  setAttachedFile(null);
                  setError(null);
                }}
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
          className={`chat-input-container${dragActive ? ' drag-active' : ''}`}
          ref={inputContainerRef}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {error && <div className="chat-input-error">{error}</div>}
          {attachedFile && (
            <div className="chat-attachment-preview">
              <div className="attachment-info">
                {attachedFile.content_type && attachedFile.content_type.startsWith('image/') ? (
                  <img
                    src={`/uploaded_files/${attachedFile.filename}`}
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
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder={dragActive ? 'Drop file here...' : uploading ? 'Uploading file...' : 'Type your message...'}
            className="chat-input"
            disabled={loadingMessages || uploading}
            rows={3}
            onKeyDown={e => {
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
                  handleSend(attachedFile);
                  setAttachedFile(null);
                  setError(null);
                } catch (err: any) {
                  setError('Send error: ' + err.message);
                }
              }
            }}
          />
          <div className="chat-input-buttons">
            <FileUpload conversationId={conversationId} onUploadSuccess={fileInfo => { setUploading(false); handleFileUpload(fileInfo); }} />
            <button type="button" className="chat-mic-btn" disabled={uploading}>
              <FiMic size={24} color="#00bcd4" />
            </button>
            <button type="submit" className="chat-send-btn" disabled={uploading}>
              <FiSend size={26} color="#00bcd4" />
            </button>
            {uploading && <span className="chat-uploading-spinner">Uploading...</span>}
          </div>
        </div>
      </form>
    </>
  );
};

export default ChatInput;
