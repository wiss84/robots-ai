import React, { useState, useRef, useEffect } from 'react';
import { useFileChangeSocket } from '../hooks/useFileChangeSocket';
import CustomFileExplorer from './CustomFileExplorer';
import type { FileNode } from './CustomFileExplorer';
import { FaChevronLeft, FaChevronRight, FaSyncAlt, FaCompressAlt, FaFolderOpen } from 'react-icons/fa';
import './FileExplorerSidebar.css';

// --- Frontend file filter (gitignore-like) ---
// Ported to TS from backend FileFilter to filter BEFORE upload.
// This avoids sending unnecessary files (node_modules, caches, logs, etc.)
const DEFAULT_EXCLUDE_PATTERNS: string[] = [
  // Dependencies
  'node_modules/**',
  'venv/**',
  'env/**',
  '.venv/**',
  '.env/**',
  '__pycache__/**',
  '*.pyc',
  '*.pyo',
  '*.pyd',
  '.Python',
  'pip-log.txt',
  'pip-delete-this-directory.txt',

  // Build outputs
  'dist/**',
  'build/**',
  '.next/**',
  'out/**',
  'target/**',
  '.output/**',
  '.nuxt/**',
  '.vuepress/dist/**',

  // Cache and temp files
  '.cache/**',
  '.tmp/**',
  'tmp/**',
  '*.tmp',
  '*.temp',
  '.sass-cache/**',
  '.parcel-cache/**',

  // IDE and editor files
  '.vscode/**',
  '.idea/**',
  '*.swp',
  '*.swo',
  '*~',
  '.project',
  '.classpath',
  '.settings/**',
  '*.sublime-project',
  '*.sublime-workspace',

  // OS files
  '.DS_Store',
  '.DS_Store?',
  '._*',
  '.Spotlight-V100',
  '.Trashes',
  'ehthumbs.db',
  'Thumbs.db',
  'desktop.ini',

  // Version control
  '.git/**',
  '.svn/**',
  '.hg/**',
  '.bzr/**',

  // Logs
  '*.log',
  'logs/**',
  'npm-debug.log*',
  'yarn-debug.log*',
  'yarn-error.log*',

  // Runtime data
  'pids/**',
  '*.pid',
  '*.seed',
  '*.pid.lock',

  // Coverage
  'coverage/**',
  '.nyc_output/**',

  // Legacy dependency dirs
  'jspm_packages/**',
  'bower_components/**',

  // Optional caches
  '.npm/**',
  '.eslintcache',

  // Very large media and archives (unlikely needed for code review)
  '*.mp4',
  '*.avi',
  '*.mov',
  '*.mkv',
  '*.iso',
  '*.dmg',

  // Archives
  '*.zip',
  '*.tar.gz',
  '*.rar',
  '*.7z',
  '*.tar',
  '*.gz',

  // Databases
  '*.db',
  '*.sqlite',
  '*.sqlite3',

  // Binaries
  '*.exe',
  '*.dll',
  '*.so',
  '*.dylib',

  // Data blobs
  '*.bin',
  '*.dat',
];

// Convert simple glob to RegExp
function globToRegExp(pattern: string): RegExp {
  // Escape regex specials except for globs
  const esc = (s: string) => s.replace(/[-/\\^$+?.()|[\]{}]/g, '\\$&');
  // Handle doublestar first
  let re = '';
  let i = 0;
  while (i < pattern.length) {
    const two = pattern.slice(i, i + 2);
    const one = pattern[i];
    if (two === '**') {
      re += '.*';
      i += 2;
    } else if (one === '*') {
      re += '[^/]*';
      i += 1;
    } else if (one === '?') {
      re += '[^/]';
      i += 1;
    } else {
      re += esc(one);
      i += 1;
    }
  }
  return new RegExp(`^${re}$`);
}

function shouldExclude(relativePath: string, patterns: string[] = DEFAULT_EXCLUDE_PATTERNS): boolean {
  const path = relativePath.replace(/\\/g, '/');

  for (const pattern of patterns) {
    if (pattern.endsWith('/**')) {
      const dir = pattern.slice(0, -3).replace(/\\/g, '/').replace(/\/+$/, '');
      if (!dir) continue;
      // Match if any path segment equals dir or path starts with dir/
      const parts = path.split('/');
      if (parts.includes(dir) || path === dir || path.startsWith(dir + '/')) {
        return true;
      }
      continue;
    }

    if (!pattern.includes('/')) {
      // Filename-only pattern
      const base = path.split('/').pop() || path;
      const re = globToRegExp(pattern);
      if (re.test(base)) return true;
    } else {
      // Full path pattern
      const re = globToRegExp(pattern);
      if (re.test(path)) return true;
    }
  }
  return false;
}

interface FileExplorerSidebarProps {
  onFileSelect: (filePath: string) => void;
  initialRoot?: string;
}

console.log('FileExplorerSidebar mounted');
const FileExplorerSidebar: React.FC<FileExplorerSidebarProps> = ({ onFileSelect }) => {
  const [filter, setFilter] = useState('');
  const [collapsed, setCollapsed] = useState(false);
  const [treeData, setTreeData] = useState<any>(null);
  const [selectedPath, setSelectedPath] = useState<string>('');
  const [uploadConfirm, setUploadConfirm] = useState<{ files: File[] } | null>(null);

  const folderInputRef = useRef<HTMLInputElement>(null);
  const [collapseAllCount, setCollapseAllCount] = useState(0);

  // WebSocket for real-time file change notifications
  const { lastMessage } = useFileChangeSocket(`${import.meta.env.VITE_WS_BACKEND_URL}/ws/file-changes`);

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage);
        console.log('File change WebSocket message received:', data);

        if (data.type === 'file_change') {
          // Automatically refresh the file explorer when files change
          console.log(`File ${data.data.event_type}: ${data.data.file_path}`);
          // Debounce the refresh to avoid too many rapid updates
          setTimeout(() => {
            fetchTree();
          }, 500);
        }
      } catch (err) {
        console.error('File changes WebSocket message parse error:', err);
      }
    }
  }, [lastMessage]);

  // Fetch project index
  const fetchTree = async () => {
  console.log('fetchTree called');
  try {
    const res = await fetch('/project/index');
    console.log('fetchTree got response:', res);
    if (res.ok) {
      const tree = await res.json();
      console.log('FileExplorerSidebar: loaded tree from /project/index:', tree);
      setTreeData(tree);
      console.log('setTreeData called');
    } else {
      const text = await res.text();
      console.error('fetchTree: response not ok', res.status, text);
    }
  } catch (err) {
    console.error('fetchTree: error', err);
    setTreeData(null);
  }
};

  React.useEffect(() => {
    fetchTree();
  }, []);

  const handleCollapseToggle = () => setCollapsed(c => !c);

  const handleBrowseClick = () => {
    folderInputRef.current?.click();
  };

  const handleFolderChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      setUploadConfirm({ files });
    }
  };

  const confirmFolderUpload = async (files: File[]) => {
    // Frontend filtering BEFORE upload
    const allowed: File[] = [];
    const excludedByPattern: { path: string; reason: string }[] = [];

    for (const file of files) {
      const rel = (file as any).webkitRelativePath || file.name;
      const normalized = String(rel).replace(/\\/g, '/');
      if (shouldExclude(normalized)) {
        excludedByPattern.push({ path: normalized, reason: 'matches exclusion pattern' });
        continue;
      }
      allowed.push(file);
    }

    if (allowed.length === 0) {
      alert('No files to upload after filtering. Make sure you did not select a build or dependency directory.');
      setUploadConfirm(null);
      return;
    }

    const formData = new FormData();
    for (const file of allowed) {
      const rel = (file as any).webkitRelativePath || file.name;
      formData.append('files', file, rel);
    }

    try {
      // POST to backend endpoint for workspace upload (backend wipes previous content)
      const res = await fetch('/project/files/upload-folder', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        // Optionally parse response for details
        // const result = await res.json();
        handleRefresh();

        // Show a brief summary of filtering to the user
        const excl = excludedByPattern.length;
        if (excl > 0) {
          const examples = excludedByPattern.slice(0, 5).map(e => e.path).join('\n - ');
          alert(`Folder uploaded.\nIncluded: ${allowed.length} files\nExcluded (by pattern): ${excl}\nExamples:\n - ${examples}`);
        }
      } else {
        const errText = await res.text();
        alert('Folder upload failed: ' + errText);
      }
    } catch (err) {
      alert('Error uploading folder: ' + (err instanceof Error ? err.message : String(err)));
    }
    setUploadConfirm(null);
  };

  // Select logic for contextual creation


  // New handlers for inline creation from CustomFileExplorer
  const handleNewFile = async (parentPath: string, name: string) => {
    if (!name) return;
    const fullPath = parentPath === '' || parentPath === '/' ? name : `${parentPath}/${name}`;
    try {
      const res = await fetch('/files/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fullPath, type: 'file' }),
      });
      if (!res.ok) throw new Error('Failed to create file');
      await fetchTree();
      // Clear pending/inline creation state if needed
      setSelectedPath(fullPath);
    } catch (err) {
      console.error('Failed to create file:', err);
    }
  };
  const handleNewFolder = async (parentPath: string, name: string) => {
    if (!name) return;
    const fullPath = parentPath === '' || parentPath === '/' ? name : `${parentPath}/${name}`;
    try {
      const res = await fetch('/files/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: fullPath, type: 'folder' }),
      });
      if (!res.ok) throw new Error('Failed to create folder');
      await fetchTree();
      setSelectedPath(fullPath);
    } catch (err) {
      console.error('Failed to create folder:', err);
    }
  };

  const handleRefresh = async () => {
    try {
      await fetch('/project/reindex', { method: 'POST' });
      await fetchTree();
    } catch (err) {
      console.error('Failed to refresh project index:', err);
    }
  };
  const handleCollapseAll = () => {
    setCollapseAllCount(count => count + 1);
  };

  const handleDelete = async (node: FileNode) => {
    try {
      const response = await fetch('/project/files/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: node.path }),
      });
      if (!response.ok) {
        const errText = await response.text();
        console.error('Delete failed:', errText);
        throw new Error('Failed to delete: ' + errText);
      }
      await handleRefresh();
    } catch (err) {
      alert('Delete failed: ' + err);
    }
  };

  const handleRename = async (oldPath: string, newName: string) => {
    if (!newName || !oldPath || newName.trim() === '') return;
    // Use the separator that exists in oldPath (handles both / and \\)
    const sep = oldPath.includes('\\') ? '\\' : '/';
    const parentDir = oldPath.substring(0, oldPath.lastIndexOf(sep));
    const baseName = newName.split(/[/\\]/).pop() || newName;
    const newPath = parentDir ? `${parentDir}${sep}${baseName}` : baseName;
    try {
      await fetch('/project/files/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
      });
      await handleRefresh();
    } catch (err) {
      alert('Rename failed: ' + err);
    }
  };

  return (
    <div className={`file-explorer-sidebar${collapsed ? ' collapsed' : ''}`}>
      {!collapsed ? (
        <>
          <div className="sidebar-header">
            <button className="collapse-btn" onClick={handleCollapseToggle} title="Collapse/Expand">
              <FaChevronLeft />
            </button>
            <div className="sidebar-actions">
              <button onClick={handleRefresh} title="Refresh"><FaSyncAlt /></button>
              <button onClick={handleCollapseAll} title="Collapse All"><FaCompressAlt /></button>
              <button onClick={handleBrowseClick} title="Browse Folder"><FaFolderOpen /></button>
              <input
                ref={folderInputRef}
                type="file"
                webkitdirectory="true"
                multiple
                style={{ display: 'none' }}
                onChange={handleFolderChange}
              />
            </div>
          </div>
          <div className="file-explorer-content">
            {treeData && (
              <CustomFileExplorer
                treeData={treeData}
                onFileSelect={node => {
                  setSelectedPath(node.path);
                  onFileSelect(node.path);
                }}
                onFolderSelect={node => {
                  setSelectedPath(node.path);
                }}
                selectedPath={selectedPath}
                filter={filter}
                onFilterChange={setFilter}
                onNewFile={handleNewFile}
                onNewFolder={handleNewFolder}
                onRename={handleRename}
                onDelete={handleDelete}
                collapseAll={collapseAllCount}
                onRefresh={handleRefresh}
              />
            )}
          </div>
        </>
      ) : (
        <div className="sidebar-header">
          <button className="collapse-btn" onClick={handleCollapseToggle} title="Expand">
            <FaChevronRight />
          </button>
        </div>
      )}
      {uploadConfirm && (
        <div className="explorer-delete-modal">
          <div className="explorer-delete-modal-content">
            <div className="explorer-delete-modal-title">Upload Folder</div>
            <div className="explorer-delete-modal-message">
              This will replace the current workspace with the selected folder. Are you sure you want to continue?
            </div>
            <div className="explorer-delete-modal-buttons">
              <button 
                className="explorer-delete-modal-btn explorer-delete-modal-yes" 
                onClick={() => confirmFolderUpload(uploadConfirm.files)}
              >
                Yes
              </button>
              <button 
                className="explorer-delete-modal-btn explorer-delete-modal-no" 
                onClick={() => setUploadConfirm(null)}
              >
                No
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileExplorerSidebar;