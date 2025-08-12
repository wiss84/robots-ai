import React, { useState } from 'react';
import './code_parser.css';

// CodeBlock component with copy button and custom styling
export const CodeBlock: React.FC<{ code: string; language?: string }> = ({ code, language = 'text' }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      // Optionally handle error
    }
  };

  return (
    <div className="custom-code-block-container">
      <div className="custom-code-block-header">
        <span className="custom-code-block-language">{language}</span>
        <button
          onClick={copyToClipboard}
          className="custom-code-block-copy-btn"
          aria-label="Copy code to clipboard"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="custom-code-block-pre">
        <code>{code}</code>
      </pre>
    </div>
  );
};

// Function to parse agent response into text/code parts
export function parseAgentResponse(text: string): Array<{ type: 'text' | 'code'; content: string; language?: string }> {
  const parts: Array<{ type: 'text' | 'code'; content: string; language?: string }> = [];
  const lines = text.split('\n');
  let currentSection = '';
  let inCodeBlock = false;
  let codeContent = '';
  let language = 'text';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        // Starting code block
        if (currentSection.trim()) {
          parts.push({ type: 'text', content: currentSection.trim() });
          currentSection = '';
        }
        inCodeBlock = true;
        language = line.slice(3).trim() || 'text';
        codeContent = '';
      } else {
        // Ending code block
        parts.push({ type: 'code', content: codeContent.trim(), language });
        inCodeBlock = false;
        codeContent = '';
      }
    } else if (inCodeBlock) {
      codeContent += line + '\n';
    } else {
      currentSection += line + '\n';
    }
  }
  if (inCodeBlock && codeContent.trim()) {
    // Unclosed code block at end
    parts.push({ type: 'code', content: codeContent.trim(), language });
  } else if (currentSection.trim()) {
    parts.push({ type: 'text', content: currentSection.trim() });
  }
  return parts;
} 