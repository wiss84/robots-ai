import React, { useEffect, useRef, useState } from 'react';
import Editor, { DiffEditor } from '@monaco-editor/react';
import './MonacoFileEditor.css';

export interface AgentSuggestion {
  filePath: string;
  originalContent: string;
  proposedContent: string;
  description: string;
}

interface MonacoFileEditorProps {
  filePath: string;
  value: string;
  language?: string;
  onChange?: (value: string | undefined) => void;
  agentSuggestion?: AgentSuggestion | null;
  onAcceptSuggestion?: (suggestion: AgentSuggestion, successCallback: (newContent: string) => void) => void;
  onRejectSuggestion?: (suggestion: AgentSuggestion) => void;
}

const MonacoFileEditor: React.FC<MonacoFileEditorProps> = ({
  filePath,
  value,
  language,
  onChange,
  agentSuggestion,
  onAcceptSuggestion,
  onRejectSuggestion,
}) => {
  const editorRef = useRef<any>(null);
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  useEffect(() => {
    const handleThemeChange = () => {
      const currentTheme = localStorage.getItem('theme') || 'dark';
      setTheme(currentTheme);
    };

    // Listen for theme changes
    window.addEventListener('storage', handleThemeChange);
    
    // Also check for theme changes via mutation observer on body class
    const observer = new MutationObserver(() => {
      const currentTheme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
      setTheme(currentTheme);
    });
    
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    return () => {
      window.removeEventListener('storage', handleThemeChange);
      observer.disconnect();
    };
  }, []);
  const monacoRef = useRef<any>(null);
  const [showDiff, setShowDiff] = useState<boolean>(false);

  const shouldShowSuggestion =
    agentSuggestion &&
    filePath &&
    agentSuggestion.filePath.replace(/\\/g, '/') === filePath.replace(/\\/g, '/');
  const [decorations, setDecorations] = useState<string[]>([]);

  const handleEditorDidMount = (editor: any, monaco: any) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
  };

  // Update editor content when value prop changes
  useEffect(() => {
    if (editorRef.current && value !== editorRef.current.getValue()) {
      editorRef.current.setValue(value);
    }
  }, [value, filePath]);

  // Handle editor content changes
  const handleChange = (value: string | undefined) => {
    if (onChange) {
      onChange(value);
    }
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        // Handle save if needed
      }
      
      // Add keyboard shortcuts for accepting/rejecting suggestions
      if (agentSuggestion && onAcceptSuggestion && onRejectSuggestion) {
        // Alt+Enter to accept suggestion
        if (e.altKey && e.key === 'Enter') {
          e.preventDefault();
          handleAccept();
        }
        // Alt+Escape to reject suggestion
        if (e.altKey && e.key === 'Escape') {
          e.preventDefault();
          handleReject();
        }
        // Alt+D to toggle diff view
        if (e.altKey && e.key === 'd') {
          e.preventDefault();
          setShowDiff(prev => !prev);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [agentSuggestion, onAcceptSuggestion, onRejectSuggestion]);
  
  // Add decorations to highlight suggested changes when a suggestion is available
  useEffect(() => {
    if (editorRef.current && monacoRef.current && shouldShowSuggestion && !showDiff) {
      // Clear existing decorations
      if (decorations.length > 0) {
        editorRef.current.deltaDecorations(decorations, []);
      }
      
      // Simple line-based diff to highlight changes
      const originalLines = agentSuggestion.originalContent.split('\n');
      const proposedLines = agentSuggestion.proposedContent.split('\n');
      
      const newDecorations = [];
      
      // Find changed lines (very basic implementation)
      for (let i = 0; i < Math.max(originalLines.length, proposedLines.length); i++) {
        if (i < originalLines.length && i < proposedLines.length && originalLines[i] !== proposedLines[i]) {
          // Line was changed
          newDecorations.push({
            range: new monacoRef.current.Range(i+1, 1, i+1, 1),
            options: {
              isWholeLine: true,
              className: 'suggestionLineChanged',
              linesDecorationsClassName: 'suggestionGlyphChanged',
              minimap: { color: '#ffcc00', position: 1 },
              overviewRuler: { color: '#ffcc00', position: 7 }
            }
          });
        } else if (i >= originalLines.length && i < proposedLines.length) {
          // Line was added
          newDecorations.push({
            range: new monacoRef.current.Range(i+1, 1, i+1, 1),
            options: {
              isWholeLine: true,
              className: 'suggestionLineAdded',
              linesDecorationsClassName: 'suggestionGlyphAdded',
              minimap: { color: '#00cc66', position: 1 },
              overviewRuler: { color: '#00cc66', position: 7 }
            }
          });
        } else if (i < originalLines.length && i >= proposedLines.length) {
          // Line was removed (can't show in current view)
          // We could potentially add a decoration to the previous line
          if (i > 0) {
            newDecorations.push({
              range: new monacoRef.current.Range(i, 1, i, 1),
              options: {
                isWholeLine: true,
                className: 'suggestionLineRemoved',
                linesDecorationsClassName: 'suggestionGlyphRemoved',
                minimap: { color: '#ff6666', position: 1 },
                overviewRuler: { color: '#ff6666', position: 7 }
              }
            });
          }
        }
      }
      
      // Apply the decorations
      const newDecorationsIds = editorRef.current.deltaDecorations([], newDecorations);
      setDecorations(newDecorationsIds);
    }
    
    return () => {
      // Clear decorations when component unmounts or suggestion changes
      if (editorRef.current && decorations.length > 0) {
        editorRef.current.deltaDecorations(decorations, []);
        setDecorations([]);
      }
    };
  }, [agentSuggestion, showDiff]);

  const handleAccept = () => {
    if (agentSuggestion && onAcceptSuggestion) {
      onAcceptSuggestion(agentSuggestion, (newContent) => {
        if (onChange) {
          onChange(newContent);
        }
        if (editorRef.current) {
          editorRef.current.setValue(newContent);
        }
      });
      // Clean up diff models after accepting
      cleanupDiffModels();
    }
  };

  const handleReject = () => {
    if (agentSuggestion) {
      onRejectSuggestion?.(agentSuggestion);
      // Clean up diff models after rejecting
      cleanupDiffModels();
    }
  };

  const cleanupDiffModels = () => {
    if (diffModelsRef.current.original) {
      try {
        diffModelsRef.current.original.dispose();
      } catch (err) {
        console.debug('Error disposing original model:', err);
      }
    }
    if (diffModelsRef.current.modified) {
      try {
        diffModelsRef.current.modified.dispose();
      } catch (err) {
        console.debug('Error disposing modified model:', err);
      }
    }
    diffModelsRef.current = {};
  };

  const diffEditorRef = useRef<any>(null);
  const diffModelsRef = useRef<{ original?: any; modified?: any }>({});

  // Clean up diff editor models only when component unmounts or suggestion changes
  useEffect(() => {
    return () => {
      // Only dispose models when component unmounts or suggestion changes, not when showDiff toggles
      if (diffModelsRef.current.original) {
        try {
          diffModelsRef.current.original.dispose();
        } catch (err) {
          console.debug('Error disposing original model:', err);
        }
      }
      if (diffModelsRef.current.modified) {
        try {
          diffModelsRef.current.modified.dispose();
        } catch (err) {
          console.debug('Error disposing modified model:', err);
        }
      }
      diffModelsRef.current = {};
    };
  }, [agentSuggestion?.filePath]); // Only cleanup when suggestion changes or component unmounts

  const renderDiffEditor = (suggestion: AgentSuggestion) => (
    <>
      <div className="diff-view-controls">
        <button
          onClick={() => setShowDiff(false)}
          className="diff-view-exit-btn"
        >
          Exit Diff View
        </button>
        <span>Alt+D to toggle diff view</span>
      </div>
      <DiffEditor
        height="100%"
        language={language || 'plaintext'}
        original={suggestion.originalContent}
        modified={suggestion.proposedContent}
        theme={theme === 'light' ? 'light' : 'vs-dark'}
        onMount={(editor) => {
          diffEditorRef.current = editor;
          // Store model references for proper cleanup
          const model = editor.getModel();
          if (model) {
            diffModelsRef.current.original = model.original;
            diffModelsRef.current.modified = model.modified;
          }
        }}
        options={{
          renderSideBySide: true,
          readOnly: true,
          minimap: { enabled: true },
          scrollBeyondLastLine: false,
          fontSize: 14,
          wordWrap: 'on',
          automaticLayout: true
        }}
      />
    </>
  );

  return (
    <div className="monaco-editor-container">
      {shouldShowSuggestion && (
        <div className="suggestion-controls">
          <div className="suggestion-description">{agentSuggestion.description}</div>
          <div className="suggestion-buttons">
            <button onClick={handleAccept}>Accept</button>
            <button onClick={handleReject}>Reject</button>
            <button onClick={() => setShowDiff(prev => !prev)}>{showDiff ? 'Hide Diff' : 'Show Diff'}</button>
          </div>
        </div>
      )}
      {shouldShowSuggestion && showDiff && agentSuggestion && renderDiffEditor(agentSuggestion)}

      {(!shouldShowSuggestion || !showDiff) && (
        <Editor
          height="100%"
          defaultLanguage={language || 'plaintext'}
          defaultValue={value}
          onChange={handleChange}
          onMount={handleEditorDidMount}
          theme={theme === 'light' ? 'light' : 'vs-dark'}
          options={{
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            fontSize: 14,
            wordWrap: 'on',
            automaticLayout: true,
            tabSize: 2,
          }}
        />
      )}
    </div>
  );
};

export default MonacoFileEditor;