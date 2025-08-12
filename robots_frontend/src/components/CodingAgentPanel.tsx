import React, { useState, useRef, useCallback, useEffect } from 'react';
import ChatSidebar from './ChatSidebar';
import FileExplorerSidebar from './FileExplorerSidebar';
import MonacoFileEditor from './MonacoFileEditor';
import { getMonacoLanguage } from '../utils/monacoLanguageFromFilename';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import EditorTabBar from './EditorTabBar';
import type { AgentSuggestion } from './MonacoFileEditor';
import './CodingAgentPanel.css';

interface EditorTab {
  path: string;
  content: string;
  isDirty?: boolean;
}

interface CodingAgentPanelProps {
  setMessages: (messages: any[]) => void;
  messagesEndRef: React.RefObject<HTMLDivElement>;
  userName: string;
  agentName: string;
  isSummarizing: boolean;
  agentId: string;
  user: any;
  conversations: any[];
  messages: any[];

  loadingMessages: boolean;
  handleSend: (message: string, fileInfo?: any) => void;
  handleCancel?: () => void;
  conversationId: string;
  onAgentSwitch: (newAgentId: string, message: string, file?: any, autoSend?: boolean) => void;
  showAllConversations: boolean;
  sidebarOpen: boolean;
  renamingId: string | null;
  renameValue: string;
  dropdownOpen: string | null;
  handleNewChat: () => void;
  handleSelectConversation: (convId: string) => void;
  handleRenameConversation: (convId: string, newTitle: string) => void;
  handleDeleteConversation: (convId: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setDropdownOpen: (id: string | null) => void;
  setRenamingId: (id: string | null) => void;
  setRenameValue: (val: string) => void;
  setShowAllConversations: (show: boolean) => void;
  agentSuggestion?: AgentSuggestion | null;
  onAcceptSuggestion: (suggestion: AgentSuggestion, successCallback: (newContent: string) => void) => void;
  onRejectSuggestion: (suggestion: AgentSuggestion) => void;
  onToggleAgentMode?: () => void;
  fileChangeMessage?: string | null;

  // New optional continue handler for fallback banner
  onContinue?: (convId: string) => void;
}

const CodingAgentPanel: React.FC<CodingAgentPanelProps> = ({ fileChangeMessage, ...props }) => {
  const [tabs, setTabs] = useState<EditorTab[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [fileLanguage, setFileLanguage] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [fileExplorerKey, setFileExplorerKey] = useState<number>(0);
  
  // Resizable panel state
  const [fileExplorerWidth, setFileExplorerWidth] = useState<number>(300);
  const [chatWidth, setChatWidth] = useState<number>(400);
  const [isDraggingLeft, setIsDraggingLeft] = useState<boolean>(false);
  const [isDraggingRight, setIsDraggingRight] = useState<boolean>(false);
  
  // Handle width kept slim to reduce visual footprint
  const HANDLE_WIDTH = 8;
  const HANDLES_TOTAL = HANDLE_WIDTH * 2;
  const EDITOR_MIN = 300;
  const FILE_EXPLORER_MIN = 200;
  const FILE_EXPLORER_MAX = 600;
  const CHAT_MIN = 300;
  const CHAT_MAX = 800;
  
  const containerRef = useRef<HTMLDivElement>(null);
  
  
  
  // Resizing logic
  const handleMouseDown = useCallback((side: 'left' | 'right') => (e: React.MouseEvent) => {
    e.preventDefault();
    if (side === 'left') {
      setIsDraggingLeft(true);
    } else {
      setIsDraggingRight(true);
    }
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const containerWidth = rect.width;

    if (isDraggingLeft) {
      const desired = e.clientX - rect.left;
      // Maximum left panel width allowed while keeping editor >= EDITOR_MIN and right panel fixed
      const maxAllowed = containerWidth - chatWidth - EDITOR_MIN - HANDLES_TOTAL;
      // If there's no room to expand (invalid range), do nothing
      if (maxAllowed < FILE_EXPLORER_MIN) {
        return;
      }
      const clampedDesired = Math.max(FILE_EXPLORER_MIN, Math.min(desired, Math.min(FILE_EXPLORER_MAX, maxAllowed)));
      setFileExplorerWidth(clampedDesired);
    }

    if (isDraggingRight) {
      const desiredChat = rect.right - e.clientX;
      // Maximum right panel width allowed while keeping editor >= EDITOR_MIN and left panel fixed
      const maxAllowedChat = containerWidth - fileExplorerWidth - EDITOR_MIN - HANDLES_TOTAL;
      if (maxAllowedChat < CHAT_MIN) {
        return;
      }
      const clampedDesiredChat = Math.max(CHAT_MIN, Math.min(desiredChat, Math.min(CHAT_MAX, maxAllowedChat)));
      setChatWidth(clampedDesiredChat);
    }
  }, [isDraggingLeft, isDraggingRight, chatWidth, fileExplorerWidth]);

  const handleMouseUp = useCallback(() => {
    setIsDraggingLeft(false);
    setIsDraggingRight(false);
  }, []);

  // Mouse event listeners
  useEffect(() => {
    if (isDraggingLeft || isDraggingRight) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isDraggingLeft, isDraggingRight, handleMouseMove, handleMouseUp]);

  // Clamp widths on window resize to avoid layout breakage
  useEffect(() => {
    const onResize = () => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const containerWidth = rect.width;

      // Ensure total fits: file + chat + handles + editor_min <= container
      let fe = fileExplorerWidth;
      let ch = chatWidth;

      const maxFeAllowed = Math.min(FILE_EXPLORER_MAX, Math.max(FILE_EXPLORER_MIN, containerWidth - EDITOR_MIN - HANDLES_TOTAL - ch));
      if (fe > maxFeAllowed) fe = maxFeAllowed;

      const maxChAllowed = Math.min(CHAT_MAX, Math.max(CHAT_MIN, containerWidth - EDITOR_MIN - HANDLES_TOTAL - fe));
      if (ch > maxChAllowed) ch = maxChAllowed;

      // If still overflowing, reduce both proportionally
      let overflow = fe + ch + HANDLES_TOTAL + EDITOR_MIN - containerWidth;
      if (overflow > 0) {
        const feRoom = fe - FILE_EXPLORER_MIN;
        const chRoom = ch - CHAT_MIN;
        const totalRoom = feRoom + chRoom;
        if (totalRoom > 0) {
          const feCut = Math.min(feRoom, Math.round((feRoom / totalRoom) * overflow));
          const chCut = Math.min(chRoom, overflow - feCut);
          fe -= feCut;
          ch -= chCut;
        } else {
          // As last resort, pin to mins
          fe = FILE_EXPLORER_MIN;
          ch = CHAT_MIN;
        }
      }

      if (fe !== fileExplorerWidth) setFileExplorerWidth(fe);
      if (ch !== chatWidth) setChatWidth(ch);
    };

    window.addEventListener('resize', onResize);
    onResize();
    return () => window.removeEventListener('resize', onResize);
  }, [fileExplorerWidth, chatWidth]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [props.messages]);

  // Function to refresh file explorer
  const refreshFileExplorer = useCallback(() => {
    setFileExplorerKey(prev => prev + 1);
  }, []);

  const handleFileSelect = useCallback(async (filePath: string, forceRefresh = false) => {
    try {
      const normalizedPath = filePath.replace(/\\/g, '/');
      
      let isTabOpen = false;
      setTabs(prevTabs => {
        const existingTab = prevTabs.find(tab => tab.path === normalizedPath);
        isTabOpen = !!existingTab;
        if (existingTab && !forceRefresh) {
          setActiveTab(normalizedPath);
          setFileContent(existingTab.content);
          setFileLanguage(getMonacoLanguage(normalizedPath));
        }
        return prevTabs;
      });

      if (isTabOpen && !forceRefresh) {
        return;
      }

      // Fetch file content
      const res = await fetch(`/project/files/read?path=${encodeURIComponent(normalizedPath)}`);
      if (!res.ok) throw new Error('Failed to fetch file');
      const data = await res.json();
      const content = Array.isArray(data.lines) ? data.lines.join('') : '';
      
      // Add new tab
      const newTab = {
        path: normalizedPath,
        content,
        isDirty: false
      };
      
      setTabs(prevTabs => {
        const tabExists = prevTabs.some(tab => tab.path === newTab.path);
        if (tabExists) {
          return prevTabs.map(tab => tab.path === newTab.path ? newTab : tab);
        }
        return [...prevTabs, newTab];
      });
      setActiveTab(normalizedPath);
      setFileContent(content);
      setFileLanguage(getMonacoLanguage(normalizedPath));
    } catch (err) {
      console.error('Error loading file:', err);
      // Show error to user
    }
  }, []);

  // Auto-open file when a suggestion is received
  useEffect(() => {
    if (props.agentSuggestion && props.agentSuggestion.filePath) {
      handleFileSelect(props.agentSuggestion.filePath);
    }
  }, [props.agentSuggestion, handleFileSelect]);

    // Handle WebSocket messages for file changes
  useEffect(() => {
    if (fileChangeMessage) {
      try {
        const data = JSON.parse(fileChangeMessage);
        
        if (data.type === 'file_change') {
          console.log('File change detected via WebSocket:', data);
          
          // Refresh file explorer for any file system changes
          refreshFileExplorer();
          
          // If the changed file is open in a tab, refresh its content
          const changedFilePath = data.data.file_path.replace(/\\/g, '/');
          const isOpen = tabs.some(tab => tab.path === changedFilePath);

          if (isOpen) {
            // Refetch content for the open tab
            handleFileSelect(changedFilePath, true /* force refresh */);
          } else if (data.data.event_type === 'created' || data.data.event_type === 'modified') {
            // If not open, and it's a create/modify event, open it
            setTimeout(() => {
              handleFileSelect(changedFilePath);
            }, 100);
          }
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    }
  }, [fileChangeMessage, refreshFileExplorer, handleFileSelect]);



  const handleTabClick = (path: string) => {
    const tab = tabs.find(t => t.path === path);
    if (tab) {
      setActiveTab(path);
      setFileContent(tab.content);
      setFileLanguage(getMonacoLanguage(path));
    }
  };

  const handleTabClose = (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    
    setTabs(prevTabs => {
      const newTabs = prevTabs.filter(tab => tab.path !== path);
      
      // If closing the active tab, activate another tab if available
      if (path === activeTab) {
        const currentIndex = prevTabs.findIndex(tab => tab.path === path);
        const newActiveTab = newTabs[currentIndex] || newTabs[newTabs.length - 1];
        setActiveTab(newActiveTab?.path || null);
        setFileContent(newActiveTab?.content || '');
        setFileLanguage(newActiveTab ? getMonacoLanguage(newActiveTab.path) : undefined);
      }
      
      return newTabs;
    });
  };

  const handleEditorChange = (value: string | undefined) => {
    if (!activeTab || value === undefined) return;
    
    setTabs(prevTabs => 
      prevTabs.map(tab => 
        tab.path === activeTab 
          ? { ...tab, content: value, isDirty: tab.content !== value }
          : tab
      )
    );
    
    setFileContent(value);
  };


  return (
    <div className="coding-agent-root">
      {/* Sidebar */}
      <ChatSidebar
        sidebarOpen={props.sidebarOpen}
        conversations={props.conversations}
        showAllConversations={props.showAllConversations}
        renamingId={props.renamingId}
        renameValue={props.renameValue}
        dropdownOpen={props.dropdownOpen}
        handleNewChat={props.handleNewChat}
        handleSelectConversation={props.handleSelectConversation}
        handleRenameConversation={props.handleRenameConversation}
        handleDeleteConversation={props.handleDeleteConversation}
        setSidebarOpen={props.setSidebarOpen}
        setDropdownOpen={props.setDropdownOpen}
        setRenamingId={props.setRenamingId}
        setRenameValue={props.setRenameValue}
        setShowAllConversations={props.setShowAllConversations}
      />
      
      {/* Main content area with resizable panels */}
      <div className="coding-agent-main" ref={containerRef}>
        <EditorTabBar
          tabs={tabs}
          activeTab={activeTab}
          onTabClick={handleTabClick}
          onTabClose={handleTabClose}
          agentSuggestion={props.agentSuggestion}
        />
        <div className="coding-agent-content" style={{ display: 'flex', height: '100%' }}>
          {/* File Explorer Panel */}
          <div
            style={{
              width: `${fileExplorerWidth}px`,
              minWidth: '200px',
              maxWidth: '600px',
              height: '100%',
              overflow: 'hidden',
              flex: '0 0 auto',
              boxSizing: 'border-box'
            }}
          >
            <FileExplorerSidebar key={fileExplorerKey} onFileSelect={handleFileSelect} />
          </div>
          
          {/* Left Drag Handle (single visual border handled via CSS) */}
          <div
            className={`drag-handle ${isDraggingLeft ? 'dragging' : ''}`}
            style={{ width: `${HANDLE_WIDTH}px`, height: '100%', cursor: 'col-resize', flex: `0 0 ${HANDLE_WIDTH}px`, zIndex: 10 }}
            onMouseDown={handleMouseDown('left')}
          />
          
          {/* Monaco Editor Panel */}
          <div style={{
            flex: '1 1 0%',
            minWidth: `${EDITOR_MIN}px`,
            height: '100%',
            overflow: 'hidden',
            boxSizing: 'border-box'
          }}>
            {activeTab ? (
              <MonacoFileEditor
                filePath={activeTab}
                value={fileContent}
                language={fileLanguage}
                onChange={handleEditorChange}
                agentSuggestion={props.agentSuggestion}
                onAcceptSuggestion={(suggestion, successCallback) =>
                  props.onAcceptSuggestion(suggestion, (newContent) => {
                    handleEditorChange(newContent);
                    successCallback(newContent);
                  })
                }
                onRejectSuggestion={props.onRejectSuggestion}
              />
            ) : (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: 'var(--main-color, #888)',
                backgroundColor: 'var(--main-bg)',
                fontSize: '16px',
                fontWeight: '500'
              }}>
                Select a file to edit
              </div>
            )}
          </div>
          
          {/* Right Drag Handle (single visual border handled via CSS) */}
          <div
            className={`drag-handle ${isDraggingRight ? 'dragging' : ''}`}
            style={{ width: `${HANDLE_WIDTH}px`, height: '100%', cursor: 'col-resize', flex: `0 0 ${HANDLE_WIDTH}px`, zIndex: 10 }}
            onMouseDown={handleMouseDown('right')}
          />
          
          {/* Chat Panel */}
          <div
            style={{
              width: `${chatWidth}px`,
              minWidth: '300px',
              maxWidth: '800px',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              flex: '0 0 auto',
              boxSizing: 'border-box'
            }}
          >
            <div className="coding-agent-messages" ref={messagesContainerRef} style={{ flex: 1, overflow: 'auto' }}>
              <ChatMessages
                messages={props.messages}
                loadingMessages={props.loadingMessages}
                messagesEndRef={messagesEndRef}
                userName={props.user?.user_metadata?.first_name || 'You'}
                agentName={props.agentId}
                agentId={props.agentId}
                isSummarizing={false}
                conversationId={props.conversationId}
                onContinue={props.onContinue}
              />
              <div ref={messagesEndRef} />
            </div>
            <div className="coding-agent-input" style={{ flexShrink: 0 }}>
              <ChatInput
                loadingMessages={props.loadingMessages}
                handleSend={props.handleSend}
                conversationId={props.conversationId}
                currentAgentId={props.agentId}
                onAgentSwitch={props.onAgentSwitch}
                isCodingAgent={true}
                isAgentMode={true}
                onToggleAgentMode={props.onToggleAgentMode}
                onCancel={props.handleCancel}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default React.memo(CodingAgentPanel);