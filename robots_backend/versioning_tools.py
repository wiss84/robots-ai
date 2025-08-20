"""
Tools for file versioning: snapshot, list versions, and restore.
Stores versions under project-root 'task_management/versioning' to avoid backend restarts.
"""

import os
import hashlib
import time
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# ---------- Internals ----------

def _project_root() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_dir, os.pardir))

def _versions_root() -> str:
    root = os.path.join(_project_root(), "task_management", "versioning")
    os.makedirs(root, exist_ok=True)
    return root

def _workspace_root() -> str:
    # Match project_index.PROJECT_ROOT without importing (to avoid side effects)
    return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files", "workspace"))

def _resolve_input_path(path: str) -> str:
    # Normalize and resolve to workspace root if relative. Accept absolute paths as-is.
    p = os.path.normpath(os.path.expanduser(str(path).strip())).lstrip("\\/")
    if os.path.isabs(p):
        return os.path.abspath(p)

    # Support inputs that include '/uploaded_files/workspace' prefix
    normalized = p.replace("\\", "/")
    prefixes = [
        "uploaded_files/workspace",
        "robots_backend/uploaded_files/workspace",
        "/uploaded_files/workspace",
        "\\uploaded_files\\workspace",
    ]
    for pref in prefixes:
        if normalized.lower().startswith(pref.replace("\\", "/").lower()):
            # Strip the prefix and any remaining leading slashes
            p = normalized[len(pref):].lstrip("\\/") if len(normalized) >= len(pref) else ""
            break

    resolved = os.path.abspath(os.path.join(_workspace_root(), p))
    return resolved

def _safe_file_id(path: str) -> str:
    # Normalize to absolute path and hash
    abspath = os.path.abspath(path)
    return hashlib.sha1(abspath.encode("utf-8")).hexdigest()

def _file_bucket_dir(path: str) -> str:
    return os.path.join(_versions_root(), _safe_file_id(path))

def _metadata_path(path: str) -> str:
    return os.path.join(_file_bucket_dir(path), "metadata.json")

def _load_metadata(path: str) -> Dict:
    mp = _metadata_path(path)
    if os.path.exists(mp):
        try:
            with open(mp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Default structure
    return {
        "original_path": os.path.abspath(path),
        "versions": []  # list of dicts
    }

def _save_metadata(path: str, data: Dict) -> None:
    os.makedirs(_file_bucket_dir(path), exist_ok=True)
    with open(_metadata_path(path), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _ext(path: str) -> str:
    return os.path.splitext(path)[1]

def _new_version_id(content: bytes) -> str:
    ts = int(time.time())
    digest = hashlib.sha1(content).hexdigest()[:10]
    return f"v{ts}-{digest}"

def _version_filename(version_id: str, ext: str) -> str:
    safe_ext = ext if ext else ""
    return f"{version_id}{safe_ext}"

def _version_path(path: str, version_id: str) -> str:
    ext = _ext(path)
    return os.path.join(_file_bucket_dir(path), _version_filename(version_id, ext))

# ---------- Schemas ----------

class SnapshotInput(BaseModel):
    file_path: str = Field(..., description="Absolute or project-relative path to the file to snapshot")
    conversation_id: Optional[str] = Field(None, description="Conversation/thread id creating the snapshot")
    note: Optional[str] = Field(None, description="Optional note about the snapshot")

class ListVersionsInput(BaseModel):
    file_path: str = Field(..., description="Absolute or project-relative path to the file")

class RestoreInput(BaseModel):
    file_path: str = Field(..., description="Absolute or project-relative path to the file to restore")
    version_id: str = Field(..., description="Version id to restore to")
    create_backup_before_restore: bool = Field(True, description="If true, snapshot current file before restore")

# ---------- Tools ----------

@tool("snapshot_file", args_schema=SnapshotInput)
def snapshot_file(file_path: str, conversation_id: Optional[str] = None, note: Optional[str] = None) -> dict:
    """
    Create a point-in-time snapshot of a file that can be restored later.
    Resolves relative paths against the uploaded workspace root.
    """
    try:
        resolved_path = _resolve_input_path(file_path)

        if not os.path.exists(resolved_path):
            return {"success": False, "error": f"File not found: {file_path} (resolved: {resolved_path})"}

        with open(resolved_path, "rb") as f:
            content = f.read()

        version_id = _new_version_id(content)
        dest_path = _version_path(resolved_path, version_id)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(content)

        meta = _load_metadata(resolved_path)
        meta["versions"].append({
            "version_id": version_id,
            "timestamp": time.time(),
            "size": len(content),
            "conversation_id": conversation_id,
            "note": note,
            "path": dest_path
        })
        _save_metadata(resolved_path, meta)

        return {
            "success": True,
            "file_path": os.path.abspath(resolved_path),
            "version_id": version_id,
            "snapshot_path": dest_path,
            "total_versions": len(meta["versions"])
        }
    except Exception as e:
        return {"success": False, "error": f"Snapshot failed: {str(e)}"}

@tool("list_file_versions", args_schema=ListVersionsInput)
def list_file_versions(file_path: str) -> dict:
    """
    List available versions for a file (most recent first).
    Resolves relative paths against the uploaded workspace root.
    """
    try:
        resolved_path = _resolve_input_path(file_path)
        meta = _load_metadata(resolved_path)
        versions = list(reversed(meta.get("versions", [])))
        return {
            "success": True,
            "file_path": os.path.abspath(resolved_path),
            "versions": versions
        }
    except Exception as e:
        return {"success": False, "error": f"List versions failed: {str(e)}"}

@tool("restore_file_version", args_schema=RestoreInput)
def restore_file_version(file_path: str, version_id: str, create_backup_before_restore: bool = True) -> dict:
    """
    Restore a file to a previous version. Optionally snapshots the current file first.
    Resolves relative paths against the uploaded workspace root.
    """
    try:
        resolved_path = _resolve_input_path(file_path)

        meta = _load_metadata(resolved_path)
        match = None
        for v in meta.get("versions", []):
            if v.get("version_id") == version_id:
                match = v
                break
        if not match:
            return {"success": False, "error": f"Version not found: {version_id}"}

        if create_backup_before_restore and os.path.exists(resolved_path):
            # best effort snapshot of current state
            try:
                snapshot_file(file_path=resolved_path, conversation_id=None, note=f"Auto-backup before restore to {version_id}")
            except Exception:
                pass

        source_path = _version_path(resolved_path, version_id)
        if not os.path.exists(source_path):
            return {"success": False, "error": f"Stored version content missing: {source_path}"}

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(os.path.abspath(resolved_path)), exist_ok=True)
        # Restore
        with open(source_path, "rb") as sf, open(resolved_path, "wb") as df:
            df.write(sf.read())

        return {
            "success": True,
            "file_path": os.path.abspath(resolved_path),
            "restored_version_id": version_id
        }
    except Exception as e:
        return {"success": False, "error": f"Restore failed: {str(e)}"}