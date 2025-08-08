from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import cloudinary
import cloudinary.uploader
import cloudinary.api
import firebase_admin
from firebase_admin import credentials, storage
import os
import base64
from datetime import datetime
from typing import Optional, Dict, Any
import logging
from io import BytesIO
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "/app/firebase-credentials.json")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Initialize Cloudinary
if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )
    logger.info("Cloudinary configured successfully")
else:
    logger.warning("Cloudinary not configured")

# Initialize Firebase
firebase_bucket = None
if FIREBASE_STORAGE_BUCKET and os.path.exists(FIREBASE_CREDENTIALS_PATH):
    try:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred, {
            'storageBucket': FIREBASE_STORAGE_BUCKET
        })
        firebase_bucket = storage.bucket()
        logger.info("Firebase configured successfully")
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
else:
    logger.warning("Firebase not configured")

# Security
security = HTTPBearer()

app = FastAPI(
    title="AnkhAi Media Service",
    description="Image upload and storage service with Cloudinary and Firebase integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class UploadResponse(BaseModel):
    file_id: str
    url: str
    provider: str
    filename: str
    size: int
    content_type: str
    created_at: datetime

class UploadRequest(BaseModel):
    image_data: str  # Base64 encoded image
    filename: str
    content_type: str = "image/jpeg"

class FileInfo(BaseModel):
    file_id: str
    url: str
    provider: str
    filename: str
    size: int
    content_type: str
    created_at: datetime

# JWT verification
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Upload functions
async def upload_to_cloudinary(image_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """Upload image to Cloudinary"""
    if not CLOUDINARY_CLOUD_NAME:
        raise HTTPException(status_code=500, detail="Cloudinary not configured")
    
    try:
        # Create a unique public ID
        public_id = f"ankhai/{uuid.uuid4()}"
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            image_data,
            public_id=public_id,
            resource_type="image",
            folder="ankhai"
        )
        
        return {
            "file_id": result["public_id"],
            "url": result["secure_url"],
            "provider": "cloudinary",
            "filename": filename,
            "size": len(image_data),
            "content_type": content_type,
            "created_at": datetime.utcnow()
        }
    
    except Exception as e:
        logger.error(f"Cloudinary upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload to Cloudinary")

async def upload_to_firebase(image_data: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    """Upload image to Firebase Storage"""
    if not firebase_bucket:
        raise HTTPException(status_code=500, detail="Firebase not configured")
    
    try:
        # Create a unique blob name
        blob_name = f"ankhai/{uuid.uuid4()}/{filename}"
        blob = firebase_bucket.blob(blob_name)
        
        # Set content type
        blob.content_type = content_type
        
        # Upload the file
        blob.upload_from_string(image_data)
        
        # Make the blob publicly accessible
        blob.make_public()
        
        return {
            "file_id": blob_name,
            "url": blob.public_url,
            "provider": "firebase",
            "filename": filename,
            "size": len(image_data),
            "content_type": content_type,
            "created_at": datetime.utcnow()
        }
    
    except Exception as e:
        logger.error(f"Firebase upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload to Firebase")

async def upload_image(image_data: bytes, filename: str, content_type: str, provider: str = "auto") -> Dict[str, Any]:
    """Upload image to the specified provider or auto-select"""
    if provider == "cloudinary" or (provider == "auto" and CLOUDINARY_CLOUD_NAME):
        try:
            return await upload_to_cloudinary(image_data, filename, content_type)
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}")
            if provider == "cloudinary":
                raise
            # Fall back to Firebase if auto mode
    
    if provider == "firebase" or (provider == "auto" and firebase_bucket):
        try:
            return await upload_to_firebase(image_data, filename, content_type)
        except Exception as e:
            logger.error(f"Firebase upload failed: {e}")
            if provider == "firebase":
                raise
    
    raise HTTPException(status_code=500, detail="No storage provider available")

# Routes
@app.get("/")
async def root():
    return {"message": "AnkhAi Media Service", "status": "running"}

@app.get("/health")
async def health_check():
    cloudinary_status = "configured" if CLOUDINARY_CLOUD_NAME else "not_configured"
    firebase_status = "configured" if firebase_bucket else "not_configured"
    
    return {
        "status": "healthy",
        "service": "media",
        "cloudinary": cloudinary_status,
        "firebase": firebase_status
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    image_data: str = Form(...),
    filename: str = Form(...),
    content_type: str = Form("image/jpeg"),
    provider: str = Form("auto"),
    user_id: int = Depends(verify_token)
):
    """Upload an image file"""
    try:
        # Decode base64 image data
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Validate file size (max 10MB)
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Upload the image
        result = await upload_image(image_bytes, filename, content_type, provider)
        
        return UploadResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@app.post("/upload/json", response_model=UploadResponse)
async def upload_file_json(
    request: UploadRequest,
    provider: str = "auto",
    user_id: int = Depends(verify_token)
):
    """Upload an image file using JSON request"""
    try:
        # Decode base64 image data
        try:
            image_bytes = base64.b64decode(request.image_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")
        
        # Validate file size (max 10MB)
        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
        
        # Upload the image
        result = await upload_image(image_bytes, request.filename, request.content_type, provider)
        
        return UploadResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@app.get("/{file_id}")
async def get_file_info(
    file_id: str,
    user_id: int = Depends(verify_token)
):
    """Get file information by ID"""
    try:
        # Try to get info from Cloudinary
        if CLOUDINARY_CLOUD_NAME:
            try:
                result = cloudinary.api.resource(file_id)
                return FileInfo(
                    file_id=result["public_id"],
                    url=result["secure_url"],
                    provider="cloudinary",
                    filename=file_id.split("/")[-1],
                    size=result.get("bytes", 0),
                    content_type="image/jpeg",
                    created_at=datetime.fromtimestamp(result["created_at"])
                )
            except:
                pass
        
        # Try to get info from Firebase
        if firebase_bucket:
            try:
                blob = firebase_bucket.blob(file_id)
                blob.reload()
                
                return FileInfo(
                    file_id=file_id,
                    url=blob.public_url,
                    provider="firebase",
                    filename=file_id.split("/")[-1],
                    size=blob.size,
                    content_type=blob.content_type,
                    created_at=datetime.utcnow()  # Firebase doesn't provide creation time
                )
            except:
                pass
        
        raise HTTPException(status_code=404, detail="File not found")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving file information")

@app.delete("/{file_id}")
async def delete_file(
    file_id: str,
    user_id: int = Depends(verify_token)
):
    """Delete a file by ID"""
    try:
        deleted = False
        
        # Try to delete from Cloudinary
        if CLOUDINARY_CLOUD_NAME:
            try:
                cloudinary.uploader.destroy(file_id)
                deleted = True
                logger.info(f"Deleted file {file_id} from Cloudinary")
            except Exception as e:
                logger.warning(f"Failed to delete {file_id} from Cloudinary: {e}")
        
        # Try to delete from Firebase
        if firebase_bucket:
            try:
                blob = firebase_bucket.blob(file_id)
                blob.delete()
                deleted = True
                logger.info(f"Deleted file {file_id} from Firebase")
            except Exception as e:
                logger.warning(f"Failed to delete {file_id} from Firebase: {e}")
        
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found or could not be deleted")
        
        return {"message": f"File {file_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail="Error deleting file")

@app.get("/providers/status")
async def get_providers_status():
    """Get status of storage providers"""
    return {
        "cloudinary": {
            "configured": bool(CLOUDINARY_CLOUD_NAME),
            "cloud_name": CLOUDINARY_CLOUD_NAME
        },
        "firebase": {
            "configured": bool(firebase_bucket),
            "bucket": FIREBASE_STORAGE_BUCKET
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
