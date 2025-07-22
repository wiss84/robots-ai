import React from 'react';
import './ChatMessages.css';
import ReactMarkdown from 'react-markdown';
import MapMessage from './MapMessage';
// import { FiDownload } from 'react-icons/fi';
import { autoWrapJsonResponse } from '../utils/mapDataParser';
import { CodeBlock, parseAgentResponse } from '../utils/code_parser';

interface Message {
  role: string;
  type?: 'text' | 'image' | 'file';
  content: string;
  fileName?: string;
  fileUrl?: string;
}

interface ChatMessagesProps {
  messages: Message[];
  loadingMessages: boolean;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  userName?: string;
  agentName?: string;
  agentId?: string;
}

// Utility to remove JSON code blocks (and optionally other code blocks) from a string
function removeMapJsonBlocks(text: string): string {
  // Remove ```json ... ``` blocks
  let cleaned = text.replace(/```json[\s\S]*?```/gi, '');
  // Optionally, remove any empty code blocks left
  cleaned = cleaned.replace(/```[\s\S]*?```/gi, '');
  // Remove extra newlines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  return cleaned.trim();
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ 
  messages, 
  loadingMessages, 
  messagesEndRef, 
  userName = 'You',
  agentName = 'Agent',
  agentId
}) => (
  <div className="chat-messages">
    {messages.map((msg, idx) => {
      // Auto-wrap unwrapped JSON responses for travel and realestate agent messages only
      const processedContent =
        msg.role === 'agent' && (agentId === 'travel' || agentId === 'realestate')
          ? autoWrapJsonResponse(msg.content)
          : msg.content;

      // Remove JSON code blocks for markdown rendering only for travel and realestate agents
      const contentWithoutJson =
        msg.role === 'agent' && (agentId === 'travel' || agentId === 'realestate')
          ? removeMapJsonBlocks(processedContent)
          : processedContent;

      return (
        <div
          key={idx}
          className={`chat-message ${msg.role === 'user' ? 'user' : 'agent'}`}
        >
          <b className="chat-message-label">{msg.role === 'user' ? userName : agentName}:</b>{' '}
          {/* Render agent message as full markdown, with special image styling for shopping agent */}
          {msg.role === 'agent' ? (
            <div className="chat-markdown">
              {agentId === 'coding' ? (
                // Custom rendering for coding agent: split into text/code parts
                parseAgentResponse(contentWithoutJson).map((part, i) =>
                  part.type === 'code' ? (
                    <CodeBlock key={i} code={part.content} language={part.language} />
                  ) : (
                    <div key={i} className="markdown-text-block">
                      <ReactMarkdown
                        components={{
                          a: ({ node, ...props }) => (
                            <a {...props} target="_blank" rel="noopener noreferrer" />
                          ),
                        }}
                      >
                        {part.content}
                      </ReactMarkdown>
                    </div>
                  )
                )
              ) : (
                <ReactMarkdown
                  components={{
                    a: ({ node, ...props }) => (
                      <a {...props} target="_blank" rel="noopener noreferrer" />
                    ),
                    img: ({ node, ...props }) => (
                      agentId === 'shopping' ? (
                        <img
                          {...props}
                          className="shopping-product-image-markdown"
                          alt={props.alt || 'product'}
                          onError={e => {
                            if (e.currentTarget.src.endsWith('image-not-found.png')) {
                              // If fallback also fails, use a transparent pixel
                              e.currentTarget.onerror = null;
                              e.currentTarget.src =
                                'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=';
                            } else {
                              e.currentTarget.onerror = null;
                              e.currentTarget.src = '/assets/image-not-found.png';
                            }
                          }}
                        />
                      ) : (
                        <img {...props} style={{ maxWidth: 500, maxHeight: 500, borderRadius: 8, margin: '8px 0' }} alt={props.alt || ''} />
                      )
                    )
                  }}
                >
                  {contentWithoutJson}
                </ReactMarkdown>
              )}
              {/* Only render map for travel and realestate agents */}
              {(agentId === 'travel' || agentId === 'realestate') && (
                <MapMessage message={processedContent} />
              )}
            </div>
          ) : (
            <span>{processedContent}</span>
          )}
          {/* Render image if type is image and fileUrl is present */}
          {msg.type === 'image' && msg.fileUrl && (
            <div className="chat-image-message">
              <img src={msg.fileUrl} alt={msg.fileName || 'uploaded'} style={{ maxWidth: 500, maxHeight: 500, borderRadius: 8, margin: '8px 0' }} />
            </div>
          )}

          {/* Render file if type is file and fileName is present */}
          {msg.type === 'file' && msg.fileName && (
            <div className="chat-file-message">
              <div className="file-info">
                <span className="file-name">{msg.fileName}</span>
                <div className="file-actions">
                  {msg.fileUrl && (
                    <a href={msg.fileUrl} target="_blank" rel="noopener noreferrer" className="file-download">
                      Download
                    </a>
                  )}
                  <span className="file-context-status">📄 Available in conversation</span>
                </div>
              </div>
              {/* Show file content preview if available */}
              {msg.content && msg.content.includes('[Uploaded File Content:') && (
                <div className="file-content-preview">
                  <details>
                    <summary>📄 View File Content</summary>
                    <pre className="file-content">
                      {msg.content.split('[Uploaded File Content:')[1]?.split(']')[0] || msg.content}
                    </pre>
                  </details>
                </div>
              )}
            </div>
          )}
        </div>
      );
    })}
    {loadingMessages && <div className="chat-message agent">{agentName} is typing...</div>}
    <div ref={messagesEndRef} />
  </div>
);

export default ChatMessages;
