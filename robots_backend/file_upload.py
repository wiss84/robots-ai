from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import logging
from typing import Optional
from file_processor import file_processor
from file_filter import FileFilter

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project/files", tags=["files"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploaded_files")
WORKSPACE_DIR = os.path.join(UPLOAD_DIR, "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure main upload directory exists

@router.get("/content/{file_path:path}")
async def get_file_content(file_path: str, workspace: bool = False):
    """
    Get the content of a file from either the workspace directory (coding agent)
    or the main uploads directory (all other agents).
    """
    try:
        # Use workspace directory only if explicitly requested (coding agent)
        target_dir = WORKSPACE_DIR if workspace else UPLOAD_DIR
        full_path = os.path.join(target_dir, file_path)
        
        if not os.path.exists(full_path):
            return JSONResponse({
                "error": "File not found"
            }, status_code=404)
        
        return FileResponse(full_path)
    except Exception as e:
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

# Initialize file filter (pattern-only; no backend size limit)
file_filter = FileFilter()



# Single file upload endpoint
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    workspace_upload: bool = Form(False)
):
    """
    Handle single file upload.
    If workspace_upload is True (coding agent only), save to /uploaded_files/workspace/
    If workspace_upload is False (all other agents), save to /uploaded_files/
    """
    try:
        # Clean filename
        filename = os.path.basename(file.filename)
        content_type = file.content_type or "application/octet-stream"
        is_image = content_type.startswith("image/")
        
        # If not workspace_upload (regular agents), force using UPLOAD_DIR
        # Only allow WORKSPACE_DIR for coding agent (workspace_upload=True)
        target_dir = WORKSPACE_DIR if workspace_upload else UPLOAD_DIR
        if not workspace_upload and 'workspace' in filename:
            # Regular agents should not access workspace files
            return JSONResponse({
                "success": False,
                "error": "Access to workspace directory not allowed"
            }, status_code=403)
            
        # Create unique filename
        unique_filename = filename
        counter = 1
        while os.path.exists(os.path.join(target_dir, unique_filename)):
            name, ext = os.path.splitext(filename)
            unique_filename = f"{name}_{counter}{ext}"
            counter += 1
        
        # Read file contents
        contents = await file.read()
        
        # If it's a webp image, convert to PNG first
        if content_type == "image/webp":
            try:
                from PIL import Image
                import io
                
                # Log original file info
                logger.info(f"Processing WEBP image: {filename}, size: {len(contents)} bytes")
                
                # First verify the WEBP data is valid
                img_buffer = io.BytesIO(contents)
                # Force loading the image to validate it
                img = Image.open(img_buffer)
                img.load()  # This will verify the image data is valid
                
                # Log image details
                logger.info(f"WEBP image details - Mode: {img.mode}, Size: {img.size}")
                
                # If image is in RGBA mode and has transparency, preserve it
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    converted_img = img.convert('RGBA')
                else:
                    converted_img = img.convert('RGB')
                
                # Change extension to .png
                name, _ = os.path.splitext(unique_filename)
                unique_filename = f"{name}.png"
                
                # Create a bytes buffer for the PNG
                png_buffer = io.BytesIO()
                # Save as PNG with maximum compatibility
                converted_img.save(png_buffer, format='PNG', optimize=True)
                contents = png_buffer.getvalue()
                content_type = "image/png"
                
                logger.info(f"Successfully converted to PNG, new size: {len(contents)} bytes")
                
            except Image.DecompressionBombError as e:
                logger.error(f"Image too large: {str(e)}")
                return JSONResponse({
                    "success": False,
                    "error": "Image file is too large to process"
                }, status_code=413)
                
            except Image.UnidentifiedImageError as e:
                logger.error(f"Invalid WEBP format: {str(e)}")
                return JSONResponse({
                    "success": False,
                    "error": "Invalid or corrupted WEBP image file"
                }, status_code=400)
                
            except Exception as e:
                logger.error(f"Failed to convert WEBP to PNG: {str(e)}")
                return JSONResponse({
                    "success": False,
                    "error": f"Failed to process WEBP image: {str(e)}"
                }, status_code=400)
        
        # Save file
        file_path = os.path.join(target_dir, unique_filename)
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Process file contents if it's not an image and not in workspace
        extracted_content = None
        if not is_image and not workspace_upload:
            result = file_processor.extract_content(file_path)
            extracted_content = result.get('content', '')
        
        return JSONResponse({
            "success": True,
            "filename": unique_filename,
            "filepath": file_path,
            "content_type": content_type,
            "is_image": is_image,
            "extracted_content": extracted_content,
            "file_url": f"/uploaded_files/workspace/{unique_filename}" if workspace_upload else f"/uploaded_files/{unique_filename}"
        })
    except Exception as e:
        logger.error(f"Upload failed - Error type: {type(e)}, Error: {str(e)}")
        return JSONResponse({
            "success": False,
            "error": f"File upload error: {str(e)}"
        }, status_code=500)

@router.post("/upload-folder")
async def upload_folder(files: list[UploadFile] = File(...)):
    """
    Accepts multiple files (with webkitRelativePath) and recreates the folder structure in the workspace root.
    Filters out common unwanted files (node_modules, cache, etc.) before processing.
    Wipes all previous contents of /uploaded_files/workspace before saving.
    All uploaded files are saved under /uploaded_files/workspace/...
    """
    try:
        logger.info(f"Starting folder upload with {len(files)} files")
        
        # First pass: collect file information and filter by patterns
        file_info_list = []
        pattern_excluded = []
        
        for file in files:
            rel_path = file.filename
            if not rel_path:
                continue
            
            # Normalize path separators
            rel_path = rel_path.replace('\\', '/')
            
            # Check if file should be excluded by pattern
            if file_filter.should_exclude(rel_path):
                pattern_excluded.append(rel_path)
                continue
            
            file_info_list.append({
                'file': file,
                'rel_path': rel_path,
                'size': 0  # Will be updated when we read the file
            })
        
        logger.info(f"After pattern filtering: {len(file_info_list)} files allowed, {len(pattern_excluded)} excluded by patterns")
        
        # Wipe workspace directory
        if os.path.exists(WORKSPACE_DIR):
            for entry in os.listdir(WORKSPACE_DIR):
                entry_path = os.path.join(WORKSPACE_DIR, entry)
                if os.path.isdir(entry_path):
                    shutil.rmtree(entry_path)
                else:
                    os.remove(entry_path)
        
        # Second pass: save files (no backend size limits; filtering handled in frontend)
        saved_files = []
        total_size = 0
        
        for file_info in file_info_list:
            file = file_info['file']
            rel_path = file_info['rel_path']
            
            # Ensure path is safe
            rel_path = os.path.normpath(rel_path)
            if rel_path.startswith(".."):
                logger.warning(f"Skipping unsafe path: {rel_path}")
                continue
            
            # Read file content
            try:
                content = await file.read()
                file_size = len(content)
                file_info['size'] = file_size
                
                # Size limit check removed; frontend performs filtering
                # (allow all sizes here, subject to overall server constraints)
                
                # Save file
                dest_path = os.path.join(WORKSPACE_DIR, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                with open(dest_path, "wb") as f:
                    f.write(content)
                
                saved_files.append(dest_path)
                total_size += file_size
                
            except Exception as e:
                logger.error(f"Error processing file {rel_path}: {str(e)}")
                continue
        
        # Prepare response with detailed information
        total_excluded = len(pattern_excluded)
        excluded_examples = pattern_excluded[:5]
        
        logger.info(f"Upload completed: {len(saved_files)} files saved, {total_excluded} excluded, total size: {total_size / (1024 * 1024):.1f}MB")
        
        return JSONResponse({
            "success": True,
            "uploaded": [os.path.relpath(p, WORKSPACE_DIR) for p in saved_files],
            "excluded_count": total_excluded,
            "excluded_by_pattern": len(pattern_excluded),
            "excluded_examples": excluded_examples,
            "total_processed": len(saved_files),
            "total_excluded": total_excluded,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "filtering_details": {
                "pattern_exclusions": len(pattern_excluded)
            }
        })
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        return JSONResponse({
            "error": f"Upload failed: {str(e)}",
            "success": False
        }, status_code=500)
