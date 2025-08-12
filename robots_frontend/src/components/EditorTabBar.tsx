import React from 'react';
import { FaLightbulb } from 'react-icons/fa';
import { FiX } from 'react-icons/fi';
import './EditorTabBar.css';
import type { AgentSuggestion } from './MonacoFileEditor';

interface EditorTab {
  path: string;
  content: string;
  isDirty?: boolean;
}

interface EditorTabBarProps {
  tabs: EditorTab[];
  activeTab: string | null;
  onTabClick: (path: string) => void;
  onTabClose: (path: string, e: React.MouseEvent) => void;
  agentSuggestion?: AgentSuggestion | null;
}

const EditorTabBar: React.FC<EditorTabBarProps> = ({
  tabs,
  activeTab,
  onTabClick,
  onTabClose,
  agentSuggestion,
}) => {
  return (
    <div className="editor-tab-bar">
      {tabs.map((tab) => (
        <div
          key={tab.path}
          onClick={() => onTabClick(tab.path)}
          className={`editor-tab ${activeTab === tab.path ? 'active' : ''}`}
        >
          <span className="editor-tab-text">
            {tab.isDirty && <span className="editor-tab-dirty">•</span>}
            {agentSuggestion && agentSuggestion.filePath === tab.path && (
              <FaLightbulb size={12} className="editor-tab-suggestion" title="Agent suggestion available" />
            )}
            {tab.path.split('/').pop()}
          </span>
          <span 
            onClick={(e) => onTabClose(tab.path, e)}
            className="editor-tab-close"
          >
            <FiX size={14} />
          </span>
        </div>
      ))}
    </div>
  );
};

export default EditorTabBar;
