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
  setShowAllConversations: (val: (v: boolean) => boolean) => void;
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
      {sidebarOpen && (
        <>
          <button className="new-chat-btn" onClick={handleNewChat}>
            + New Chat
          </button>
          <div className="conversations-list">
            <div className="conversations-title">Conversations</div>
            <ul>
              {(showAllConversations ? conversations : conversations.slice(0, 4)).map((conv) => (
                <li key={conv.id} className="conversation-item" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span onClick={() => handleSelectConversation(conv.id)} style={{ flex: 1, cursor: 'pointer', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {renamingId === conv.id ? (
                      <form onSubmit={e => { e.preventDefault(); handleRenameConversation(conv.id, renameValue); setRenamingId(null); }} style={{ display: 'inline' }}>
                        <input value={renameValue} onChange={e => setRenameValue(e.target.value)} onBlur={() => setRenamingId(null)} autoFocus style={{ width: 120 }} />
                      </form>
                    ) : (
                      conv.title || 'New Conversation'
                    )}
                  </span>
                  <div style={{ position: 'relative' }}>
                    <button className="conversation-menu-btn" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }} onClick={() => setDropdownOpen(dropdownOpen === conv.id ? null : conv.id)}>
                      <FiMoreVertical size={18} color="#fff" />
                    </button>
                    {dropdownOpen === conv.id && (
                      <div className="conversation-dropdown" style={{ position: 'absolute', right: 0, top: 24, background: '#fff', border: '1px solid #eee', borderRadius: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.08)', zIndex: 10 }}>
                        <button style={{ display: 'block', width: '100%', padding: '6px 16px', border: 'none', background: 'none', textAlign: 'left', cursor: 'pointer' }} onClick={() => { setRenamingId(conv.id); setRenameValue(conv.title); setDropdownOpen(null); }}>Rename</button>
                        <button style={{ display: 'block', width: '100%', padding: '6px 16px', border: 'none', background: 'none', textAlign: 'left', color: 'red', cursor: 'pointer' }} onClick={() => { handleDeleteConversation(conv.id); setDropdownOpen(null); }}>Delete</button>
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
            {conversations.length >= 5 && (
              <div style={{ textAlign: 'center', marginTop: 8 }}>
                <button style={{ background: 'none', border: 'none', color: '#00bcd4', cursor: 'pointer', fontSize: 14, textDecoration: 'underline' }} onClick={() => setShowAllConversations(v => !v)}>
                  {showAllConversations ? 'Show less' : 'Show more'}
                </button>
              </div>
            )}
          </div>
          <div style={{ flex: 1 }} />
        </>
      )}
    </div>
  );
};

export default ChatSidebar;
