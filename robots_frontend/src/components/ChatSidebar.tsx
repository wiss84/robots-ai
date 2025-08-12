import React from 'react';
import './ChatSidebar.css';
import { FiChevronLeft, FiChevronRight, FiMoreVertical } from 'react-icons/fi';

interface ChatSidebarProps {
  sidebarOpen: boolean;
  conversations: any[];
  showAllConversations: boolean;
  renamingId: string | null;
  renameValue: string;
  dropdownOpen: string | null;
  handleNewChat: () => void;
  handleSelectConversation: (id: string) => void;
  handleRenameConversation: (id: string, title: string) => void;
  handleDeleteConversation: (id: string) => void;
  setSidebarOpen: (open: boolean) => void;
  setDropdownOpen: (id: string | null) => void;
  setRenamingId: (id: string | null) => void;
  setRenameValue: (val: string) => void;
  setShowAllConversations: (show: boolean) => void;
}

const ChatSidebar: React.FC<ChatSidebarProps> = ({
  sidebarOpen,
  conversations,
  showAllConversations,
  renamingId,
  renameValue,
  dropdownOpen,
  handleNewChat,
  handleSelectConversation,
  handleRenameConversation,
  handleDeleteConversation,
  setSidebarOpen,
  setDropdownOpen,
  setRenamingId,
  setRenameValue,
  setShowAllConversations
}) => {
  return (
    <div className={`chat-sidebar${sidebarOpen ? '' : ' closed'}`}>
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? <FiChevronLeft color="#00bcd4" /> : <FiChevronRight color="#00bcd4" />}
      </button>
      <button className="new-chat-btn" onClick={handleNewChat}>
        + New Chat
      </button>
      <div className="conversations-list">
        <div className="conversations-title">Conversations</div>
        <ul>
          {(showAllConversations ? conversations : conversations.slice(0, 4)).map((conv) => (
            <li key={conv.id} className="conversation-item conversation-item-container">
              <span onClick={() => handleSelectConversation(conv.id)} className="conversation-item-text">
                {renamingId === conv.id ? (
                  <form onSubmit={e => { e.preventDefault(); handleRenameConversation(conv.id, renameValue); setRenamingId(null); }} className="conversation-rename-form">
                    <input value={renameValue} onChange={e => setRenameValue(e.target.value)} onBlur={() => setRenamingId(null)} autoFocus className="conversation-rename-input" />
                  </form>
                ) : (
                  conv.title || 'New Conversation'
                )}
              </span>
              <div className="conversation-menu-container">
                <button className="conversation-menu-btn" onClick={() => setDropdownOpen(dropdownOpen === conv.id ? null : conv.id)}>
                  <FiMoreVertical size={18} />
                </button>
                {dropdownOpen === conv.id && (
                  <div className="conversation-dropdown">
                    <button className="conversation-dropdown-button" onClick={() => { setRenamingId(conv.id); setRenameValue(conv.title); setDropdownOpen(null); }}>Rename</button>
                    <button className="conversation-dropdown-button delete" onClick={() => { handleDeleteConversation(conv.id); setDropdownOpen(null); }}>Delete</button>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
        {conversations.length >= 5 && (
          <div className="show-more-container">
            <button className="show-more-button" onClick={() => setShowAllConversations(!showAllConversations)}>
              {showAllConversations ? 'Show less' : 'Show more'}
            </button>
          </div>
        )}
      </div>
      <div className="sidebar-spacer" />
    </div>
  );
};

export default ChatSidebar;
