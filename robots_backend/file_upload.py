from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
from typing import Optional
from file_processor import file_processor

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = os.path.join(os.getcwd(), "uploaded_files")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
def upload_file(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None)
):
    """
    Accepts a file upload and automatically extracts its content.
    Supports: PDF, images, spreadsheets, text files, Word documents, JSON, XML
    Returns the file path, metadata, and extracted content.
    """
    try:
        # Ensure filename is not None
        if not file.filename:
            return JSONResponse({
                "error": "No filename provided",
                "success": False
            }, status_code=400)
        
        # Save file to disk
        file_location = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_location, "wb") as f:
            f.write(file.file.read())
        
        # Extract content from the file
        extraction_result = file_processor.extract_content(file_location)
        
        return JSONResponse({
            "filename": file.filename,
            "content_type": file.content_type,
            "file_path": file_location,
            "conversation_id": conversation_id,
            "extracted_content": extraction_result.get("content", ""),
            "metadata": extraction_result.get("metadata", {}),
            "error": extraction_result.get("error"),
            "success": "error" not in extraction_result
        })
        
    except Exception as e:
        return JSONResponse({
            "error": f"Upload failed: {str(e)}",
            "filename": file.filename,
            "content_type": file.content_type,
            "success": False
        }, status_code=500)
