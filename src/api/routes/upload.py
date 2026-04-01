import os
import uuid
from pathlib import Path
from fastapi import UploadFile, File, HTTPException

from src.core.config import settings


class UploadService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.max_size = settings.MAX_UPLOAD_SIZE
        self.allowed_extensions = settings.ALLOWED_EXTENSIONS
        
    async def save_upload(self, file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed: {self.allowed_extensions}"
            )
        
        content = await file.read()
        
        if len(content) > self.max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {self.max_size / (1024*1024)}MB"
            )
        
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = self.upload_dir / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return {
            "filename": unique_filename,
            "original_filename": file.filename,
            "size": len(content),
            "path": str(file_path),
        }
    
    def delete_upload(self, file_path: str) -> bool:
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def cleanup_old_uploads(self, max_age_seconds: int = 3600):
        import time
        current_time = time.time()
        
        for file_path in self.upload_dir.glob("*"):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
