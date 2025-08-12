from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import os

router = APIRouter(prefix="/files", tags=["files"])

class CreateRequest(BaseModel):
    path: str
    type: str  # 'file' or 'folder'

@router.post("/create")
def create_file_or_folder(req: CreateRequest):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files", "workspace"))
    target_path = os.path.abspath(os.path.join(base_dir, req.path))

    # Prevent path traversal
    if not target_path.startswith(base_dir):
        raise HTTPException(status_code=400, detail="Invalid path.")

    if os.path.exists(target_path):
        raise HTTPException(status_code=409, detail="File or folder already exists.")

    if req.type == "file":
        # Create parent directories if needed
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            pass
        return {"status": "file created", "path": req.path}
    elif req.type == "folder":
        os.makedirs(target_path, exist_ok=False)
        return {"status": "folder created", "path": req.path}
    else:
        raise HTTPException(status_code=400, detail="Invalid type. Must be 'file' or 'folder'.")
