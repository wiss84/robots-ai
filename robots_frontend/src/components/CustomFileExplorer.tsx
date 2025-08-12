import React, { useState, useMemo } from 'react';
import { FiChevronDown, FiChevronRight, FiFile, FiFolder, FiFolderPlus, FiFilePlus, FiMoreVertical } from 'react-icons/fi';
import './CustomFileExplorer.css';

// Types
export interface FileNode {
  path: string;
  name: string;
  type: 'file' | 'folder';
  children?: FileNode[];
}

interface CustomFileExplorerProps {
  treeData: FileNode;
  onFileSelect?: (file: FileNode) => void;
  onFolderSelect?: (folder: FileNode) => void;
  selectedPath?: string;
  filter?: string;
  onFilterChange?: (value: string) => void;
  // Optional: context menu actions
  onNewFile?: (parentPath: string, name: string) => void;
  onNewFolder?: (parentPath: string, name: string) => void;
  onRename?: (oldPath: string, newName: string) => void;
  onDelete?: (node: FileNode) => void;
  collapseAll?: number;
  onRefresh?: () => void;
}

const CustomFileExplorer: React.FC<CustomFileExplorerProps> = ({
  treeData,
  onFileSelect,
  onFolderSelect,
  selectedPath,
  filter = '',
  onFilterChange,
  onNewFile,
  onNewFolder,
  onRename,
  onDelete,

  collapseAll,
  onRefresh,
}) => {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // Auto-expand folders with matches when filter changes
  React.useEffect(() => {
    if (!filter || !treeData) return;
    // Walk the filtered tree and expand all folders with matches
    const expandFoldersWithMatches = (node: FileNode) => {
      if (node.type === 'folder' && node.children) {
        if (node.children.some(child => substringMatch(child.name, filter) || (child.type === 'folder' && child.children && child.children.length > 0))) {
          setExpanded(e => ({ ...e, [node.path]: true }));
        }
        node.children.forEach(expandFoldersWithMatches);
      }
    };
    expandFoldersWithMatches(treeData);
  }, [filter, treeData]);

  const [editingNode, setEditingNode] = useState<{ path: string; value: string; isNew?: boolean } | null>(null);
  const [actionMenuOpen, setActionMenuOpen] = useState<string | null>(null);

  // Close action menu on outside click
  React.useEffect(() => {
    if (!actionMenuOpen) return;
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('.explorer-action-menu-wrapper')) {
        setActionMenuOpen(null);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [actionMenuOpen]);
  const [pendingNew, setPendingNew] = useState<{ type: 'file' | 'folder'; parentPath: string } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ node: FileNode } | null>(null);

  // Auto-expand parent when starting inline creation
  React.useEffect(() => {
    if (pendingNew && pendingNew.parentPath) {
      setExpanded(prev => ({ ...prev, [pendingNew.parentPath]: true }));
    }
  }, [pendingNew]);

  // Collapse all folders when collapseAll changes
  React.useEffect(() => {
    if (collapseAll !== undefined) {
      setExpanded({});
    }
  }, [collapseAll]);

  // Helper to insert a new node in the tree for inline editing
  const insertPendingNew = (node: FileNode): FileNode => {
    if (!pendingNew || node.type !== 'folder') return node;
    if (node.path !== pendingNew.parentPath) {
      return { ...node, children: node.children?.map(insertPendingNew) };
    }
    const defaultName = pendingNew.type === 'file' ? 'New file.txt' : 'New Folder';
    const newNode: FileNode = {
      path: `${node.path}/${defaultName}`,
      name: defaultName,
      type: pendingNew.type,
      children: pendingNew.type === 'folder' ? [] : undefined,
    };
    return {
      ...node,
      children: [newNode, ...(node.children || [])],
    };
  };




  const handleToggle = (path: string) => {
    setExpanded(e => ({ ...e, [path]: !e[path] }));
  };

  const handleFileClick = (node: FileNode) => {
    if (onFileSelect) onFileSelect(node);
  };
  const handleFolderClick = (node: FileNode) => {
    handleToggle(node.path);
    if (onFolderSelect) onFolderSelect(node);
  };

  // Strict substring match (case-insensitive)
  function substringMatch(str: string, pattern: string): boolean {
    return str.toLowerCase().includes(pattern.toLowerCase());
  }


  // Highlight all substring matches (case-insensitive)
  function highlightMatch(name: string, pattern: string): React.ReactNode {
    if (!pattern) return name;
    const nameLower = name.toLowerCase();
    const patternLower = pattern.toLowerCase();
    const parts: React.ReactNode[] = [];
    let lastIdx = 0;
    let idx = nameLower.indexOf(patternLower);
    let key = 0;
    while (idx !== -1) {
      if (idx > lastIdx) parts.push(name.slice(lastIdx, idx));
      parts.push(
        <span 
          key={key++} 
          className="search-highlight"
        >
          {name.slice(idx, idx + pattern.length)}
        </span>
      );
      lastIdx = idx + pattern.length;
      idx = nameLower.indexOf(patternLower, lastIdx);
    }
    if (lastIdx < name.length) parts.push(name.slice(lastIdx));
    return parts;
  }

  const renderTree = (node: FileNode, depth = 0) => {

    if (!node) return null;
    const isFolder = node.type === 'folder';
    const isExpanded = expanded[node.path];
    const isEditing = editingNode && editingNode.path === node.path;
    return (
      <div key={node.path} className={`explorer-node depth-${depth} ${selectedPath === node.path ? 'selected' : ''}`}>
        <div className={`explorer-row ${isFolder ? 'folder' : 'file'}`} style={{ paddingLeft: depth * 16 }}>
          {isFolder ? (
            <span onClick={() => handleFolderClick(node)}>
              {isExpanded ? <FiChevronDown /> : <FiChevronRight />}
              <FiFolder className="explorer-icon" />
              {isEditing ? (
                <input
                  autoFocus
                  value={editingNode.value}
                  onChange={e => setEditingNode({ ...editingNode, value: e.target.value })}
                  onBlur={async () => {
                    const finalName = editingNode.value.trim() || 'New Folder';
                    setEditingNode(null);
                    if (editingNode.isNew && onNewFolder && pendingNew) {
                      await onNewFolder(pendingNew.parentPath, finalName);
                      if (onRefresh) onRefresh();
                    }
                    else if (onRename) {
                      let parentDir = node.path.substring(0, node.path.lastIndexOf('/'));
                      if (parentDir === '') parentDir = '';
                      const newPath = parentDir ? `${parentDir}/${finalName}` : finalName;
                      await onRename(node.path, newPath);
                    }
                  }}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  className="explorer-rename-input"
                />
              ) : (
                <span className="explorer-label">{filter ? highlightMatch(node.name, filter) : node.name}</span>
              )}
            </span>
          ) : (
            <span onClick={() => handleFileClick(node)}>
              <FiFile className="explorer-icon" />
              {isEditing ? (
                <input
                  autoFocus
                  value={editingNode.value}
                  onChange={e => setEditingNode({ ...editingNode, value: e.target.value })}
                  onBlur={async () => {
                    const finalName = editingNode.value.trim() || 'New file.txt';
                    setEditingNode(null);
                    if (editingNode.isNew && onNewFile && pendingNew) {
                      await onNewFile(pendingNew.parentPath, finalName);
                      if (onRefresh) onRefresh();
                    }
                    else if (onRename && node.name !== finalName) {
                      let parentDir = node.path.substring(0, node.path.lastIndexOf('/'));
                      if (parentDir === '') parentDir = '';
                      const newPath = parentDir ? `${parentDir}/${finalName}` : finalName;
                      await onRename(node.path, newPath);
                    }
                    setEditingNode(null);
                    if (onRefresh) onRefresh();
                  }}
                  onKeyDown={e => {
                    if (e.key === 'Enter') {
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  className="explorer-rename-input"
                />
              ) : (
                <span className="explorer-label">{filter ? highlightMatch(node.name, filter) : node.name}</span>
              )}
            </span>
          )}
          <span className="explorer-actions">
            {isFolder && onNewFile && (
              <FiFilePlus title="New File" onClick={e => { e.stopPropagation(); setPendingNew({ type: 'file', parentPath: node.path }); setEditingNode({ path: `${node.path}/New file.txt`, value: '', isNew: true }); }} />
            )}
            {isFolder && onNewFolder && (
              <FiFolderPlus title="New Folder" onClick={e => { e.stopPropagation(); setPendingNew({ type: 'folder', parentPath: node.path }); setEditingNode({ path: `${node.path}/New Folder`, value: '', isNew: true }); }} />
            )}
            {onDelete && node.path !== treeData.path && (
              <span title="Delete" onClick={e => { e.stopPropagation(); setDeleteConfirm({ node }); }} className="explorer-action-delete">
                <FiFilePlus className="hidden" /> {/* Placeholder for spacing/alignment */}
                <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-trash-2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
              </span>
            )}
            {(onRename || onDelete) && (
              <span className="explorer-action-menu-wrapper">
                <FiMoreVertical onClick={e => {
                  e.stopPropagation();
                  setActionMenuOpen(actionMenuOpen === node.path ? null : node.path);
                }} className="explorer-action-icon" />
                {actionMenuOpen === node.path && (
                  <div className="explorer-action-menu">
                    {onRename && <div className="explorer-action-menu-item" onClick={e => {
                      e.stopPropagation();
                      setEditingNode({ path: node.path, value: node.name });
                      setActionMenuOpen(null);
                    }}>Rename</div>}
                    {onDelete && <div className="explorer-action-menu-item delete" onClick={e => {
                      e.stopPropagation();
                      setDeleteConfirm({ node });
                      setActionMenuOpen(null);
                    }}>Delete</div>}
                  </div>
                )}
              </span>
            )}
          </span>
        </div>
        {isFolder && isExpanded && node.children && node.children.length > 0 && (
          <div className="explorer-children">
            {node.children
              .slice()
              .sort((a, b) => {
                // Folders first, then files, then alphabetically
                if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
                return a.name.localeCompare(b.name);
              })
              .map(child => renderTree(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };
  // Insert pending new node for inline editing
  const treeWithPending = useMemo(() => {
    // Only show the pending node if editingNode is active (inline creation)
    if (pendingNew && editingNode && editingNode.isNew) return insertPendingNew(treeData);
    return treeData;
  }, [treeData, pendingNew, editingNode]);

  return (
    <div className="custom-file-explorer explorer-container">
      <div className="explorer-search">
        <input
          type="text"
          placeholder="Search files/folders..."
          value={filter}
          onChange={e => onFilterChange?.(e.target.value)}
        />
      </div>
      <div className="explorer-tree">
        {treeWithPending ? renderTree(treeWithPending) : <div className="explorer-empty">No files or folders found.</div>}
      </div>

      <div className="explorer-divider" />
      {deleteConfirm && (
        <div className="explorer-delete-modal">
          {(() => { console.log('Rendering delete modal for', deleteConfirm.node); return null; })()}
          <div className="explorer-delete-modal-content">
            <div className="explorer-delete-modal-title">Delete File or Folder</div>
            <div className="explorer-delete-modal-message">Are you sure you want to delete this file or folder?</div>
            <div className="explorer-delete-modal-buttons">
              <button className="explorer-delete-modal-btn explorer-delete-modal-yes" onClick={async () => {
                if (onDelete) await onDelete(deleteConfirm.node);
                setDeleteConfirm(null);
              }}>Yes</button>
              <button className="explorer-delete-modal-btn explorer-delete-modal-no" onClick={() => setDeleteConfirm(null)}>No</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomFileExplorer;
