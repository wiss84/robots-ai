from fastapi import APIRouter, HTTPException, Body, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import threading
import time
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import atexit
import difflib
from datetime import datetime
import subprocess

router = APIRouter(prefix="/project", tags=["project"])

# Import WebSocket notification function
try:
    from .websocket_file_changes import notify_file_change
except ImportError:
    # Fallback if websocket_file_changes is not available
    async def notify_file_change(*args, **kwargs):
        pass

# In-memory index and lock
directory_index = None
index_lock = threading.Lock()
last_indexed_time = None
reindex_timer = None # For debouncing

# Always use uploaded workspace as project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files", "workspace"))
# If you want to support multiple workspaces, set this dynamically after upload.

class FileNode(BaseModel):
    path: str
    name: str
    type: str  # 'file' or 'folder'
    size: Optional[int] = None
    last_modified: Optional[float] = None
    children: Optional[List['FileNode']] = None

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "path": "robots_backend/agent_coding.py",
                "name": "agent_coding.py",
                "type": "file",
                "size": 12345,
                "last_modified": 1710000000.0,
                "children": None
            }
        }

FileNode.model_rebuild()

def scan_directory(path: str) -> FileNode:
    """Recursively scan directory and return FileNode tree."""
    name = os.path.basename(path)
    if os.path.isdir(path):
        children = []
        for entry in os.scandir(path):
            # Skip hidden files/folders
            if entry.name.startswith('.'):
                continue
            children.append(scan_directory(entry.path))
        return FileNode(
            path=os.path.relpath(path, PROJECT_ROOT),
            name=name,
            type='folder',
            size=None,
            last_modified=os.path.getmtime(path),
            children=children
        )
    else:
        return FileNode(
            path=os.path.relpath(path, PROJECT_ROOT),
            name=name,
            type='file',
            size=os.path.getsize(path),
            last_modified=os.path.getmtime(path),
            children=None
        )

def build_index():
    global directory_index, last_indexed_time
    with index_lock:
        directory_index = scan_directory(PROJECT_ROOT)
        last_indexed_time = time.time()

def schedule_reindex(delay: float = 1.0):
    """Schedules a debounced reindex to avoid rapid updates from file watchers."""
    global reindex_timer
    with index_lock:
        if reindex_timer and reindex_timer.is_alive():
            reindex_timer.cancel()
        print(f"[project_index] Scheduling reindex in {delay}s")
        reindex_timer = threading.Timer(delay, build_index)
        reindex_timer.daemon = True
        reindex_timer.start()

def get_index():
    global directory_index
    if directory_index is None:
        build_index()
    return directory_index

class ProjectIndexEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        # Reindex on any file/folder change, but debounced to handle bursts of events.
        print(f"[project_index] File event detected: {event.event_type} on {event.src_path}")
        schedule_reindex()
        
        # Send WebSocket notification for file changes
        try:
            # Convert absolute path to relative path
            relative_path = os.path.relpath(event.src_path, PROJECT_ROOT)
            
            # Map watchdog event types to our event types
            event_type_map = {
                'created': 'created',
                'deleted': 'deleted',
                'modified': 'modified',
                'moved': 'moved'
            }
            
            mapped_event_type = event_type_map.get(event.event_type, event.event_type)
            
            # Handle moved events specially
            old_path = None
            if hasattr(event, 'dest_path') and event.dest_path:
                old_path = os.path.relpath(event.dest_path, PROJECT_ROOT)
            
            # Schedule WebSocket notification in the event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(notify_file_change(
                        event_type=mapped_event_type,
                        file_path=relative_path,
                        is_directory=event.is_directory,
                        old_path=old_path
                    ))
                else:
                    # If no event loop is running, run in a new thread
                    def run_notification():
                        asyncio.run(notify_file_change(
                            event_type=mapped_event_type,
                            file_path=relative_path,
                            is_directory=event.is_directory,
                            old_path=old_path
                        ))
                    threading.Thread(target=run_notification, daemon=True).start()
            except RuntimeError:
                # No event loop available, run in a new thread
                def run_notification():
                    asyncio.run(notify_file_change(
                        event_type=mapped_event_type,
                        file_path=relative_path,
                        is_directory=event.is_directory,
                        old_path=old_path
                    ))
                threading.Thread(target=run_notification, daemon=True).start()
        except Exception as e:
            print(f"[project_index] Error sending WebSocket notification: {e}")

observer = None

def start_watching():
    global observer
    if observer is not None:
        return
    event_handler = ProjectIndexEventHandler()
    observer = Observer()
    observer.schedule(event_handler, PROJECT_ROOT, recursive=True)
    observer.daemon = True
    observer.start()
    atexit.register(stop_watching)

def stop_watching():
    global observer
    if observer is not None:
        observer.stop()
        observer.join()
        observer = None

# Start the file system watcher when the module is imported
start_watching()

class FileReadRequest(BaseModel):
    path: str
    start: Optional[int] = 0
    end: Optional[int] = None  # If None, read to end

class FileWriteRequest(BaseModel):
    path: str
    content: str

class FileSearchRequest(BaseModel):
    query: str
    by_content: Optional[bool] = False

class FileDeleteRequest(BaseModel):
    path: str

class FileRenameRequest(BaseModel):
    old_path: str
    new_path: str

class FilePatchRequest(BaseModel):
    path: str
    base_content: str  # The content the patch is based on
    new_content: str   # The new content to apply
    user: Optional[str] = None  # For audit logging

class CreateDirectoryRequest(BaseModel):
    path: str

class ProjectTestRequest(BaseModel):
    target: Optional[str] = None  # File or directory to test
    type: Optional[str] = None    # 'python', 'js', 'lint', etc.

class ProjectTestResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None

@router.get("/index", response_model=FileNode)
def get_project_index():
    print("[project_index] GET /project/index called")
    """Return the current project file/folder index."""
    try:
        return get_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project index: {str(e)}")

@router.post("/reindex", response_model=FileNode)
def reindex_project():
    print("[project_index] POST /project/reindex called")
    """Trigger a full reindex and return the new index."""
    try:
        build_index()
        return get_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reindex project: {str(e)}")

@router.post("/project/test", response_model=ProjectTestResult)
def run_project_test(req: ProjectTestRequest, background_tasks: BackgroundTasks):
    """Run project tests or linting and return results."""
    # Determine test command
    if req.type == 'js' or (req.target and req.target.endswith(('.js', '.ts', '.tsx'))):
        cmd = ['npm', 'test']
        if req.target:
            cmd.append('--')
            cmd.append(req.target)
    elif req.type == 'lint':
        # Try Python linting with flake8, fallback to pylint
        if req.target:
            cmd = ['flake8', req.target]
        else:
            cmd = ['flake8', PROJECT_ROOT]
    else:
        # Default: Python tests with pytest
        if req.target:
            cmd = ['pytest', req.target]
        else:
            cmd = ['pytest']
    try:
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120)
        output = proc.stdout
        error = proc.stderr if proc.returncode != 0 else None
        return ProjectTestResult(success=proc.returncode == 0, output=output, error=error)
    except Exception as e:
        return ProjectTestResult(success=False, output='', error=str(e))

#
@router.get("/files/read")
def read_file(path: str, start: int = 0, end: int = None):
    """Read a file in chunks (by line numbers), efficiently for large files."""
    # Normalize path separators and strip any leading/trailing separators or dots
    safe_path = os.path.normpath(path).replace('\\', '/').strip('/. ')
    abs_path = os.path.join(PROJECT_ROOT, safe_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        lines = []
        total_lines = 0
        s = max(0, start)
        e = end if end is not None and end > s else None
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            for i, line in enumerate(f):
                if e is not None and i >= e:
                    break
                if i >= s:
                    lines.append(line)
                total_lines += 1
        # If end is None, set e to total_lines
        if e is None:
            e = total_lines
        return {
            "path": path,
            "start": s,
            "end": e,
            "total_lines": total_lines,
            "lines": lines
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@router.post("/files/write")
def write_file(req: FileWriteRequest):
    abs_path = os.path.join(PROJECT_ROOT, req.path)
    try:
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(req.content)
        build_index()  # Reindex after write
        return {"success": True, "path": req.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {str(e)}")

@router.post("/files/search")
def search_files(req: FileSearchRequest):
    matches = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        for fname in files:
            rel_path = os.path.relpath(os.path.join(root, fname), PROJECT_ROOT)
            if req.by_content:
                try:
                    with open(os.path.join(root, fname), 'r', encoding='utf-8') as f:
                        if req.query in f.read():
                            matches.append(rel_path)
                except Exception:
                    continue
            else:
                if req.query.lower() in fname.lower():
                    matches.append(rel_path)
    return {"matches": matches}

@router.post("/files/delete")
def delete_file(req: FileDeleteRequest):
    import shutil
    abs_path = os.path.join(PROJECT_ROOT, req.path)
    # Prevent deletion of workspace root
    normalized_req_path = os.path.normpath(req.path).replace('\\', '/').strip('/. ')
    if normalized_req_path in ('', '.', '/', os.path.basename(PROJECT_ROOT).rstrip('/')):
        raise HTTPException(status_code=400, detail="Cannot delete the workspace root directory.")
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="File or folder not found")
    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
            deleted_type = "file"
        elif os.path.isdir(abs_path):
            shutil.rmtree(abs_path)
            deleted_type = "folder"
        else:
            raise HTTPException(status_code=400, detail="Path is neither file nor folder")
        build_index()  # Reindex after delete
        return {"success": True, "path": req.path, "type": deleted_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file or folder: {str(e)}")

@router.post("/files/rename")
def rename_file(req: FileRenameRequest):
    abs_old = os.path.join(PROJECT_ROOT, req.old_path)
    abs_new = os.path.join(PROJECT_ROOT, req.new_path)
    if not os.path.exists(abs_old):
        raise HTTPException(status_code=404, detail="Source file not found")
    try:
        os.rename(abs_old, abs_new)
        build_index()  # Reindex after rename
        return {"success": True, "old_path": req.old_path, "new_path": req.new_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename file: {str(e)}")

@router.post("/files/patch")
def patch_file(req: FilePatchRequest):
    abs_path = os.path.join(PROJECT_ROOT, req.path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        # Read current file content
        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            current_content = f.read()
        # Only apply patch if file unchanged since base_content
        if current_content != req.base_content:
            raise HTTPException(status_code=409, detail="File has changed since last read. Please reload and try again.")
        # Write new content
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(req.new_content)
        # Log the edit
        log_edit(req.path, req.user, req.base_content, req.new_content)
        build_index()  # Reindex after patch
        return {"success": True, "path": req.path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply patch: {str(e)}")

@router.post("/files/create-directory")
def create_directory(req: CreateDirectoryRequest):
    """Create a directory at the specified path."""
    try:
        safe_path = req.path.lstrip('/\\')
        abs_path = os.path.join(PROJECT_ROOT, safe_path)
        
        # Create the directory (and any parent directories)
        os.makedirs(abs_path, exist_ok=True)
        
        schedule_reindex()
        return {
            "success": True,
            "path": req.path,
            "message": "Directory created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {str(e)}")

def log_edit(path, user, old_content, new_content):
    log_path = os.path.join(PROJECT_ROOT, 'edit_history.log')
    timestamp = datetime.utcnow().isoformat()
    diff = ''.join(difflib.unified_diff(
        old_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile='before',
        tofile='after',
        lineterm=''
    ))
    entry = f"[{timestamp}] USER: {user or 'unknown'}\nPATH: {path}\nDIFF:\n{diff}\n{'-'*40}\n"
    with open(log_path, 'a', encoding='utf-8') as logf:
        logf.write(entry)