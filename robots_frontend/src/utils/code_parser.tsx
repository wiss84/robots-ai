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

// Function to clean and fix malformed markdown before parsing
function cleanMarkdown(text: string): string {
  const lines = text.split('\n');
  const cleanedLines: string[] = [];
  const openCodeBlocks: number[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Detect code block markers
    if (line.trim().startsWith('```')) {
      const backtickCount = line.match(/^`+/);
      if (backtickCount) {
        const count = backtickCount[0].length;

        // If we have nested code blocks (more than 3 backticks), fix them
        if (count > 3 && openCodeBlocks.length > 0) {
          // Close the previous code block and start a new one
          const lastIndex = openCodeBlocks[openCodeBlocks.length - 1];
          if (lastIndex >= 0) {
            cleanedLines[lastIndex] = '```';
            cleanedLines.splice(i, 0, '```');
            openCodeBlocks.push(i);
            continue;
          }
        }

        // Check if this should close an open code block
        if (openCodeBlocks.length > 0) {
          const lastBacktickCount = openCodeBlocks[openCodeBlocks.length - 1];
          if (count === lastBacktickCount) {
            // Matching backticks - close the code block
            openCodeBlocks.pop();
            cleanedLines.push('```');
          } else {
            // Different backtick count - start new code block
            openCodeBlocks.push(count);
            cleanedLines.push(line);
          }
        } else {
          // No open code blocks - start new one
          openCodeBlocks.push(count);
          cleanedLines.push(line);
        }
      } else {
        cleanedLines.push(line);
      }
    } else {
      cleanedLines.push(line);
    }
  }

  // Close any unclosed code blocks at the end
  while (openCodeBlocks.length > 0) {
    cleanedLines.push('```');
    openCodeBlocks.pop();
  }

  return cleanedLines.join('\n');
}

// Function to parse agent response into text/code parts
export function parseAgentResponse(text: string): Array<{ type: 'text' | 'code'; content: string; language?: string }> {
  // First, clean and fix any malformed markdown
  const cleanedText = cleanMarkdown(text);

  const parts: Array<{ type: 'text' | 'code'; content: string; language?: string }> = [];
  const lines = cleanedText.split('\n');
  let currentSection = '';
  let inCodeBlock = false;
  let codeContent = '';
  let language = 'text';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code block markers (now cleaned)
    if (line.trim() === '```') {
      if (!inCodeBlock) {
        // Starting code block
        if (currentSection.trim()) {
          parts.push({ type: 'text', content: currentSection.trim() });
          currentSection = '';
        }
        inCodeBlock = true;
        // Try to detect language from previous non-empty line that might contain it
        for (let j = i - 1; j >= 0; j--) {
          if (lines[j].trim() && !lines[j].trim().startsWith('```')) {
            language = lines[j].trim();
            break;
          }
        }
        codeContent = '';
      } else {
        // Ending code block
        parts.push({ type: 'code', content: codeContent.trim(), language });
        inCodeBlock = false;
        codeContent = '';
        language = 'text';
      }
    } else if (inCodeBlock) {
      codeContent += line + '\n';
    } else {
      currentSection += line + '\n';
    }
  }

  // Handle unclosed code blocks or remaining content
  if (inCodeBlock && codeContent.trim()) {
    parts.push({ type: 'code', content: codeContent.trim(), language });
  } else if (currentSection.trim()) {
    parts.push({ type: 'text', content: currentSection.trim() });
  }

  return parts;
}