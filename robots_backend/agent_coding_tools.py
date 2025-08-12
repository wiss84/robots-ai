from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Dict
import httpx
import os

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# --- 1. File Read Tool ---
class FileReadInput(BaseModel):
    path: str = Field(..., description="Path to the file to read (relative to project root)")
    start: int = Field(0, description="Start line number (0-based)")
    end: int = Field(None, description="End line number (exclusive); if None, read to end")

@tool("file_read", args_schema=FileReadInput, return_direct=False)
def file_read_tool(path: str, start: int = 0, end: int = None) -> dict:
    """Read a file in chunks by line numbers. Efficient for large files - read specific sections instead of entire file.
    
    Use this to examine specific parts of files, debug code sections, or read large files incrementally.
    Line numbers are 0-based. If end is omitted, reads from start to end of file.
    """
    try:
        params = {"path": path, "start": start}
        if end is not None:
            params["end"] = end

        with httpx.Client() as client:
            resp = client.get(f"{API_BASE_URL}/project/files/read", params=params)
            resp.raise_for_status()
            data = resp.json()

        if not data or "lines" not in data:
            return {"error": f"No content found in file {path}"}

        return {
            "path": data["path"],
            "start": data["start"],
            "end": data["end"],
            "total_lines": data["total_lines"],
            "lines": data["lines"],  # keep lines for editing logic
        }
    except Exception as e:
        return {"error": str(e)}



# --- 2. Create Directory Tool ---
class CreateDirectoryInput(BaseModel):
    path: str = Field(..., description="Path to the directory to create (relative to project root)")

@tool("create_directory", args_schema=CreateDirectoryInput, return_direct=True)
def create_directory_tool(path: str) -> dict:
    """Create a single empty directory/folder at the specified path. Use this tool when you need to create a new folder structure. The path should be relative to the project root."""
    payload = {"path": path}
    
    with httpx.Client() as client:
        resp = client.post(f"{API_BASE_URL}/project/files/create-directory", json=payload)
        resp.raise_for_status()
        return resp.json()

# --- 3. Create File Tool ---
class CreateFileInput(BaseModel):
    path: str = Field(..., description="Path to the file to create (relative to project root)")
    content: str = Field("", description="Content to write to the file")

@tool("create_file", args_schema=CreateFileInput, return_direct=True)
def create_file_tool(path: str, content: str = "") -> dict:
    """Create a new file at the specified path with the given content. Use this tool when you need to create a new file and write content to it. The path should be relative to the project root and include the filename with extension. If content is not provided, an empty file will be created."""
    payload = {"path": path, "content": content}
    
    with httpx.Client() as client:
        resp = client.post(f"{API_BASE_URL}/project/files/write", json=payload)
        resp.raise_for_status()
        return resp.json()

# --- 4. File Search Tool ---
class FileSearchInput(BaseModel):
    query: str = Field(..., description="Search query (filename or content)")
    by_content: bool = Field(False, description="If true, search file content; else, search by filename")

@tool("file_search", args_schema=FileSearchInput, return_direct=True)
def file_search_tool(query: str, by_content: bool = False) -> dict:
    """Search for files by filename or content. Use filename search to locate files, content search to find code patterns or text.
    
    Filename search is faster and good for finding specific files. Content search looks inside files 
    and is useful for finding functions, classes, or specific text across the project.
    """
    payload = {"query": query, "by_content": by_content}
    with httpx.Client() as client:
        resp = client.post(f"{API_BASE_URL}/project/files/search", json=payload)
        resp.raise_for_status()
        return resp.json()

# --- 5. File Delete Tool ---
class FileDeleteInput(BaseModel):
    path: str = Field(..., description="Path to the file or folder to delete (relative to project root)")

@tool("file_delete", args_schema=FileDeleteInput, return_direct=True)
def file_delete_tool(path: str) -> dict:
    """Delete a file or folder permanently. Use with caution as this operation cannot be undone.
    
    Good for removing temporary files or folders, outdated directories, or cleaning up generated files.
    Always verify the path is correct before deletion.
    """
    payload = {"path": path}
    with httpx.Client() as client:
        resp = client.post(f"{API_BASE_URL}/project/files/delete", json=payload)
        resp.raise_for_status()
        return resp.json()

# --- 6. File Rename Tool ---
class FileRenameInput(BaseModel):
    old_path: str = Field(..., description="Current file path (relative to project root)")
    new_path: str = Field(..., description="New file path (relative to project root)")

@tool("file_rename", args_schema=FileRenameInput, return_direct=True)
def file_rename_tool(old_path: str, new_path: str) -> dict:
    """Rename or move a file to a new location. Can change filename, move to different folder, or both.
    
    Use for refactoring (renaming components), organizing files into proper folders, or fixing naming conventions.
    The destination folder must exist.
    """
    payload = {"old_path": old_path, "new_path": new_path}
    with httpx.Client() as client:
        resp = client.post(f"{API_BASE_URL}/project/files/rename", json=payload)
        resp.raise_for_status()
        return resp.json()

# --- 7. Project Index Tool ---
class ProjectIndexInput(BaseModel):
    pass  # No input needed

@tool("project_index", args_schema=ProjectIndexInput, return_direct=True)
def project_index_tool() -> dict:
    """Get the complete project structure - all files and folders in a tree view from the workspace.
    
    Use this to understand project organization, find files when you're unsure of structure,
    or get an overview before making changes. Essential for new projects or complex codebases.
    """
    with httpx.Client() as client:
        resp = client.get(f"{API_BASE_URL}/project/index")
        resp.raise_for_status()
        return resp.json()

# --- 8. Project Test Tool ---
class ProjectTestInput(BaseModel):
    target: str = Field(None, description="File or directory to test (optional)")
    type: str = Field(None, description="Test type: 'python', 'js', 'lint', etc. (optional)")

@tool("project_test", args_schema=ProjectTestInput, return_direct=True)
def project_test_tool(target: str = None, type: str = None) -> dict:
    """Run tests or linting on project files. Can run all tests, specific files, or by test type.
    
    Use to verify code quality, check for errors before deployment, or validate specific changes.
    Without parameters, runs all available tests. Specify target for focused testing.
    """
    payload = {"target": target, "type": type}
    with httpx.Client() as client:
        resp = client.post(f"{API_BASE_URL}/project/test", json=payload)
        resp.raise_for_status()
        return resp.json()

# --- 9. Code Interpreter Tools ---
class CodeInterpreterCreateSandboxInput(BaseModel):
    sandbox_name: str = Field(..., description="Name of the sandbox to create")

@tool("CODEINTERPRETER_CREATE_SANDBOX", args_schema=CodeInterpreterCreateSandboxInput, return_direct=True)
def codeinterpreter_create_sandbox_tool(sandbox_name: str) -> dict:
    """Create a code interpreter sandbox."""
    # Stub: Replace with backend call
    return {"sandbox_id": f"sandbox_{sandbox_name}"}

class CodeInterpreterExecuteCodeInput(BaseModel):
    code: str = Field(..., description="Code to execute")
    sandbox_id: str = Field(..., description="Sandbox ID to execute code in")

@tool("CODEINTERPRETER_EXECUTE_CODE", args_schema=CodeInterpreterExecuteCodeInput, return_direct=True)
def codeinterpreter_execute_code_tool(code: str, sandbox_id: str) -> dict:
    """Execute code in a sandbox."""
    # Stub: Replace with backend call
    return {"execution_result": f"Executed code in {sandbox_id}"}

class CodeInterpreterGetFileCmdInput(BaseModel):
    file_path: str = Field(..., description="Path to file to retrieve from sandbox")
    sandbox_id: str = Field(..., description="Sandbox ID")

@tool("CODEINTERPRETER_GET_FILE_CMD", args_schema=CodeInterpreterGetFileCmdInput, return_direct=True)
def codeinterpreter_get_file_cmd_tool(file_path: str, sandbox_id: str) -> dict:
    """Get file contents from a sandbox."""
    # Stub: Replace with backend call
    return {"file_content": f"Contents of {file_path} in {sandbox_id}"}

class CodeInterpreterRunTerminalCmdInput(BaseModel):
    command: str = Field(..., description="Terminal command to run")
    sandbox_id: str = Field(..., description="Sandbox ID to run command in")

@tool("CODEINTERPRETER_RUN_TERMINAL_CMD", args_schema=CodeInterpreterRunTerminalCmdInput, return_direct=True)
def codeinterpreter_run_terminal_cmd_tool(command: str, sandbox_id: str) -> dict:
    """Run a terminal command in a sandbox."""
    # Stub: Replace with backend call
    return {"execution_result": f"Ran '{command}' in {sandbox_id}"}

class CodeInterpreterUploadFileCmdInput(BaseModel):
    file_path: str = Field(..., description="Path to file to upload to sandbox")
    sandbox_id: str = Field(..., description="Sandbox ID")

@tool("CODEINTERPRETER_UPLOAD_FILE_CMD", args_schema=CodeInterpreterUploadFileCmdInput, return_direct=True)
def codeinterpreter_upload_file_cmd_tool(file_path: str, sandbox_id: str) -> dict:
    """Upload a file to a sandbox."""
    # Stub: Replace with backend call
    return {"success": True, "uploaded": file_path, "sandbox_id": sandbox_id}
