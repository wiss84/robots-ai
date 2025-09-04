import React from 'react';
import './ChatMessages.css';
import ReactMarkdown from 'react-markdown';
import MapMessage from './MapMessage';
import DeepSearchContainer from './DeepSearchContainer';
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
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  userName?: string;
  agentName?: string;
  agentId?: string;
  isSummarizing?: boolean;

  // New: support fallback controls
  conversationId?: string;
  onContinue?: (convId: string) => void;
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

// Utility to process citation tags into numbered links with hover tooltips
function processCitations(text: string): string {
  const sources: string[] = [];

  // Collect all unique sources
  const citationRegex = /<cite>\[(Source|Sources): ([^\]]+)\]\<\/cite\>/g;
  let match;
  while ((match = citationRegex.exec(text)) !== null) {
    const content = match[2];
    
    // For both 'Source' and 'Sources', treat as comma-separated URLs
    const urls = content.split(', ');
    urls.forEach((url: string) => {
      const trimmed = url.trim();
      if (!sources.includes(trimmed)) sources.push(trimmed);
    });
  }

  // Create mapping of URL to number
  const sourceMap: { [url: string]: number } = {};
  sources.forEach((url, idx) => {
    sourceMap[url] = idx + 1;
  });

  // Replace citations with numbered links
  let processed = text;
  processed = processed.replace(citationRegex, (_match, _type, content) => {
    const urls = content.split(', ');
    return urls
      .map((url: string) => {
        const trimmed = url.trim();
        const num = sourceMap[trimmed];
        return `[${num}](${trimmed} "Source: ${trimmed}")`;
      })
      .join(' ');
  });

  return processed;
}

const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  loadingMessages,
  messagesEndRef,
  userName = 'You',
  agentName = 'Agent',
  agentId,
  isSummarizing = false,
  conversationId,
  onContinue,
}) => {
  const isFinanceAgent = agentId === 'finance';
  
  // Find the index of the last user message in the finance agent conversation (calculate once)
  const lastUserMessageIndex = messages.map((msg, index) => ({ msg, index }))
    .filter(({ msg }) => msg.role === 'user')
    .pop()?.index;

  return (
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
      
      // Show deep search container for all user messages to finance agent
      // Only the latest user message container should actively listen to SSE
      const shouldShowDeepSearchContainer = isFinanceAgent && msg.role === 'user';
      const isLatestUserMessage = idx === lastUserMessageIndex;

      return (
        <div key={`${msg.fileUrl || msg.content}-${idx}`}>
          <div
            className={`chat-message ${msg.role === 'user' ? 'user' : 'agent'}`}
          >
            <b className="chat-message-label">
              {msg.role === 'user' ? userName : agentName}:
            </b>{' '}
            {/* Render agent message as full markdown, with special image styling for shopping agent */}
            {msg.role === 'agent' ? (
              typeof contentWithoutJson === 'string' &&
              contentWithoutJson.startsWith('[[DELAY:') ? (
                <div className="chat-fallback chat-delay-banner">
                  {contentWithoutJson.replace(/^\[\[DELAY:\d+\]\]\s*/, '')}
                </div>
              ) : typeof contentWithoutJson === 'string' &&
                contentWithoutJson.startsWith('[[CONTINUE]]') ? (
                <div className="chat-fallback chat-continue-banner">
                  <div className="chat-continue-text">
                    {contentWithoutJson.replace('[[CONTINUE]]', '').trim() ||
                      'Something went wrong. Click Continue to resume the previous task.'}
                  </div>
                  {conversationId && onContinue && (
                    <button
                      className="chat-continue-button"
                      onClick={() => onContinue(conversationId)}
                    >
                      Continue
                    </button>
                  )}
                </div>
              ) : (
                <div className="chat-markdown">
                  {agentId === 'coding' ? (
                    parseAgentResponse(processCitations(contentWithoutJson)).map(
                      (part, i) =>
                        part.type === 'code' ? (
                          <CodeBlock
                            key={i}
                            code={part.content}
                            language={part.language}
                          />
                        ) : (
                          <div key={i} className="markdown-text-block">
                            <ReactMarkdown
                              components={{
                                a: ({ node, ...props }) => (
                                  <a
                                    {...props}
                                    className="citation-link"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                  />
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
                          <a
                            {...props}
                            className="citation-link"
                            target="_blank"
                            rel="noopener noreferrer"
                          />
                        ),
                        img: ({ node, ...props }) =>
                          agentId === 'shopping' ? (
                            <img
                              {...props}
                              className="shopping-product-image-markdown"
                              alt={props.alt || 'product'}
                              onError={(e) => {
                                if (
                                  e.currentTarget.src.endsWith(
                                    'image-not-found.png'
                                  )
                                ) {
                                  e.currentTarget.onerror = null;
                                  e.currentTarget.src =
                                    'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=';
                                } else {
                                  e.currentTarget.onerror = null;
                                  e.currentTarget.src =
                                    '/assets/image-not-found.png';
                                }
                              }}
                            />
                          ) : (
                            <img
                              {...props}
                              style={{
                                maxWidth: 500,
                                maxHeight: 500,
                                borderRadius: 8,
                                margin: '8px 0',
                              }}
                              alt={props.alt || ''}
                            />
                          ),
                        p: ({ node, children, ...props }) => (
                          <p {...props}>{children}</p>
                        ),
                        li: ({ node, children, ...props }) => (
                          <li {...props}>{children}</li>
                        ),
                        h1: ({ node, children, ...props }) => (
                          <h1 {...props}>{children}</h1>
                        ),
                        h2: ({ node, children, ...props }) => (
                          <h2 {...props}>{children}</h2>
                        ),
                        h3: ({ node, children, ...props }) => (
                          <h3 {...props}>{children}</h3>
                        ),
                        h4: ({ node, children, ...props }) => (
                          <h4 {...props}>{children}</h4>
                        ),
                        h5: ({ node, children, ...props }) => (
                          <h5 {...props}>{children}</h5>
                        ),
                        h6: ({ node, children, ...props }) => (
                          <h6 {...props}>{children}</h6>
                        ),
                        blockquote: ({ node, children, ...props }) => (
                          <blockquote {...props}>{children}</blockquote>
                        ),
                        td: ({ node, children, ...props }) => (
                          <td {...props}>{children}</td>
                        ),
                        th: ({ node, children, ...props }) => (
                          <th {...props}>{children}</th>
                        ),
                      }}
                    >
                      {processCitations(contentWithoutJson)}
                    </ReactMarkdown>
                  )}
                  {(agentId === 'travel' || agentId === 'realestate') && (
                    <MapMessage message={processedContent} />
                  )}
                </div>
              )
            ) : (
              <span>{processedContent}</span>
            )}
            {msg.type === 'image' && msg.fileUrl && (
              <div className="chat-image-message">
                <img
                  src={`http://localhost:8000/project/files/content/${
                    msg.fileUrl.split('/uploaded_files/')[1]
                  }`}
                  alt={msg.fileName || 'uploaded'}
                  style={{
                    maxWidth: 500,
                    maxHeight: 500,
                    borderRadius: 8,
                    margin: '8px 0',
                  }}
                />
              </div>
            )}
            {msg.type === 'file' && msg.fileName && (
              <div className="chat-file-message">
                <div className="file-info">
                  <span className="file-name">{msg.fileName}</span>
                  <div className="file-actions">
                    {msg.fileUrl && (
                      <a
                        href={`http://localhost:8000/project/files/content/${
                          msg.fileUrl.split('/uploaded_files/')[1]
                        }`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="file-download"
                      >
                        Download
                      </a>
                    )}
                    <span className="file-context-status">
                      📄 Available in conversation
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Show Deep Search container for user messages to finance agent */}
          {/* Container will only render when deep search tool is actually triggered */}
          {shouldShowDeepSearchContainer && (
            <DeepSearchContainer 
              messageId={`finance-search-${idx}`} 
              isLatestUserMessage={isLatestUserMessage}
              debugInfo={`Message ${idx}: "${msg.content.substring(0, 20)}..." (isLatest: ${isLatestUserMessage})`}
            />
          )}
        </div>
      );
    })}
    {loadingMessages && (
      <div className="chat-message agent">
        {isSummarizing
          ? `${agentName} is summarizing the conversation for context...`
          : `${agentName} is typing...`}
      </div>
    )}
    <div ref={messagesEndRef} />
  </div>
);
};

export default ChatMessages;
