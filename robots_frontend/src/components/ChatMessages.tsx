import React from 'react';
import './ChatMessages.css';
import ReactMarkdown from 'react-markdown';
import MapMessage from './MapMessage';
// import { FiDownload } from 'react-icons/fi';
import { autoWrapJsonResponse } from '../utils/mapDataParser';
import { CodeBlock, parseAgentResponse } from '../utils/code_parser';

// Utility function to safely extract text content from React children
const extractTextContent = (children: React.ReactNode): string => {
  try {
    if (typeof children === 'string') {
      return children;
    }
    if (Array.isArray(children)) {
      return children.map(child => extractTextContent(child)).join('');
    }
    if (React.isValidElement(children) && (children.props as any)?.children) {
      return extractTextContent((children.props as any).children);
    }
    return '';
  } catch (error) {
    console.error('Error extracting text content:', error);
    return '';
  }
};

// Citation parsing utilities (moved outside component for reuse)
const parseCitations = (text: string) => {
  try {
    const citationRegex = new RegExp('<cite>\\[Source:\\s*([^\\]]+)\\]</cite>', 'g');
    const parts: Array<{type: string, content: string, index?: number, key: string}> = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    let citationIndex = 1;

    while ((match = citationRegex.exec(text)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: text.slice(lastIndex, match.index),
          key: `text-${parts.length}`
        });
      }

      // Add citation
      const url = match[1]?.trim();
      if (url) {
        parts.push({
          type: 'citation',
          content: url,
          index: citationIndex++,
          key: `citation-${parts.length}`
        });
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push({
        type: 'text',
        content: text.slice(lastIndex),
        key: `text-${parts.length}`
      });
    }

    return parts;
  } catch (error) {
    console.error('Error parsing citations:', error);
    // Fallback: return the original text as a single text part
    return [{
      type: 'text',
      content: text,
      key: 'fallback-text'
    }];
  }
};

const parseMultipleCitations = (text: string) => {
  try {
    const multipleCitationRegex = new RegExp('<cite>\\[Sources:\\s*([^\\]]+)\\]</cite>', 'g');
    let processedText = text;

    processedText = processedText.replace(multipleCitationRegex, (_match, urls) => {
      try {
        const urlList = urls.split(',').map((url: string, _index: number) =>
          `<cite>[Source: ${url.trim()}]</cite>`
        );
        return urlList.join(' ');
      } catch (error) {
        console.error('Error processing multiple citations:', error);
        return _match; // Return original match if processing fails
      }
    });

    return parseCitations(processedText);
  } catch (error) {
    console.error('Error parsing multiple citations:', error);
    // Fallback: return the original text as a single text part
    return [{
      type: 'text',
      content: text,
      key: 'fallback-text'
    }];
  }
};

const renderCitationParts = (parts: Array<{type: string, content: string, index?: number, key: string}>) => {
  try {
    return parts.map((part) => {
      try {
        if (part.type === 'text') {
          return <span key={part.key}>{part.content || ''}</span>;
        } else if (part.type === 'citation') {
          const url = part.content || '';
          const href = url.startsWith('http') ? url : `https://${url}`;
          return (
            <sup key={part.key} className="citation">
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="citation-link"
                title={`Source: ${url}`}
              >
                [{part.index || '?'}]
              </a>
            </sup>
          );
        }
        return null;
      } catch (error) {
        console.error('Error rendering citation part:', error, part);
        return <span key={part.key || 'error'}>{part.content || '[Error rendering citation]'}</span>;
      }
    });
  } catch (error) {
    console.error('Error rendering citation parts:', error);
    return [<span key="error">Error rendering citations</span>];
  }
};

// Citation parsing utility component
const CitationText: React.FC<{ text: string }> = ({ text }) => {
  try {
    const parts = parseMultipleCitations(text);

    return (
      <div className="citation-content">
        {renderCitationParts(parts)}
      </div>
    );
  } catch (error) {
    console.error('Error in CitationText component:', error);
    return (
      <div className="citation-content">
        <span>{text}</span>
      </div>
    );
  }
};

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

const ChatMessages: React.FC<ChatMessagesProps> = ({
  messages,
  loadingMessages,
  messagesEndRef,
  userName = 'You',
  agentName = 'Agent',
  agentId,
  isSummarizing = false,
  conversationId,
  onContinue
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
          key={`${msg.fileUrl || msg.content}-${idx}`}
          className={`chat-message ${msg.role === 'user' ? 'user' : 'agent'}`}
        >
          <b className="chat-message-label">{msg.role === 'user' ? userName : agentName}:</b>{' '}
          {/* Render agent message as full markdown, with special image styling for shopping agent */}
          {msg.role === 'agent' ? (
            // Special system-like inline banners
            typeof contentWithoutJson === 'string' && contentWithoutJson.startsWith('[[DELAY:') ? (
              <div className="chat-fallback chat-delay-banner">
                {contentWithoutJson.replace(/^\[\[DELAY:\d+\]\]\s*/, '')}
              </div>
            ) : typeof contentWithoutJson === 'string' && contentWithoutJson.startsWith('[[CONTINUE]]') ? (
              <div className="chat-fallback chat-continue-banner">
                <div className="chat-continue-text">
                  {contentWithoutJson.replace('[[CONTINUE]]', '').trim() || 'Something went wrong. Click Continue to resume the previous task.'}
                </div>
                {conversationId && onContinue && (
                  <button className="chat-continue-button" onClick={() => onContinue(conversationId)}>
                    Continue
                  </button>
                )}
              </div>
            ) : (
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
                      ),
                      // Custom components to handle citations in various markdown elements
                      p: ({ node, children, ...props }) => {
                        // Extract text content safely to check for citations
                        const content = extractTextContent(children);
                        // Check if content contains citation tags and has actual citation content
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          return <CitationText text={content} />;
                        }
                        return <p {...props}>{children}</p>;
                      },
                      // Handle citations in list items
                      li: ({ node, children, ...props }) => {
                        // Extract text content safely to check for citations
                        const content = extractTextContent(children);
                        // Check if content contains citation tags and has actual citation content
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          // Parse citations and render parts directly without wrapper div
                          const parts = parseMultipleCitations(content);
                          return (
                            <li {...props}>
                              {renderCitationParts(parts)}
                            </li>
                          );
                        }
                        return <li {...props}>{children}</li>;
                      },
                      // Handle citations in headings
                      h1: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <h1 {...props}>{renderCitationParts(parts)}</h1>;
                        }
                        return <h1 {...props}>{children}</h1>;
                      },
                      h2: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <h2 {...props}>{renderCitationParts(parts)}</h2>;
                        }
                        return <h2 {...props}>{children}</h2>;
                      },
                      h3: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <h3 {...props}>{renderCitationParts(parts)}</h3>;
                        }
                        return <h3 {...props}>{children}</h3>;
                      },
                      h4: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <h4 {...props}>{renderCitationParts(parts)}</h4>;
                        }
                        return <h4 {...props}>{children}</h4>;
                      },
                      h5: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <h5 {...props}>{renderCitationParts(parts)}</h5>;
                        }
                        return <h5 {...props}>{children}</h5>;
                      },
                      h6: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <h6 {...props}>{renderCitationParts(parts)}</h6>;
                        }
                        return <h6 {...props}>{children}</h6>;
                      },
                      // Handle citations in blockquotes
                      blockquote: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <blockquote {...props}>{renderCitationParts(parts)}</blockquote>;
                        }
                        return <blockquote {...props}>{children}</blockquote>;
                      },
                      // Handle citations in table cells
                      td: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <td {...props}>{renderCitationParts(parts)}</td>;
                        }
                        return <td {...props}>{children}</td>;
                      },
                      th: ({ node, children, ...props }) => {
                        const content = extractTextContent(children);
                        if (content.includes('<cite>[') && content.includes('</cite>')) {
                          const parts = parseMultipleCitations(content);
                          return <th {...props}>{renderCitationParts(parts)}</th>;
                        }
                        return <th {...props}>{children}</th>;
                      }
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
            )
          ) : (
            <span>{processedContent}</span>
          )}
          {/* Render image if type is image and fileUrl is present */}
          {msg.type === 'image' && msg.fileUrl && (
            <div className="chat-image-message">
              <img 
                src={`http://localhost:8000/project/files/content/${msg.fileUrl.split('/uploaded_files/')[1]}`}
                alt={msg.fileName || 'uploaded'} 
                style={{ maxWidth: 500, maxHeight: 500, borderRadius: 8, margin: '8px 0' }} 
              />
            </div>
          )}

          {/* Render file if type is file and fileName is present */}
          {msg.type === 'file' && msg.fileName && (
            <div className="chat-file-message">
              <div className="file-info">
                <span className="file-name">{msg.fileName}</span>
                <div className="file-actions">
                  {msg.fileUrl && (
                    <a 
                      href={`http://localhost:8000/project/files/content/${msg.fileUrl.split('/uploaded_files/')[1]}`} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="file-download"
                    >
                      Download
                    </a>
                  )}
                  <span className="file-context-status">📄 Available in conversation</span>
                </div>
              </div>
            </div>
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

export default ChatMessages;
