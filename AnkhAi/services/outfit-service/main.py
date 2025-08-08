from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
import httpx
import os
import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import json
import base64
from io import BytesIO
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ankhai_user:ankhai_password@postgres:5432/ankhai_outfits")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT configuration (for user verification)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# YOLO model configuration
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "/app/models/yolov8n.pt")
MEDIA_SERVICE_URL = os.getenv("MEDIA_SERVICE_URL", "http://media-service:8006")

# Security
security = HTTPBearer()

app = FastAPI(
    title="AnkhAi Outfit Analysis Service",
    description="AI-powered outfit analysis using YOLOv8",
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

# Database Models
class Outfit(Base):
    __tablename__ = "outfits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    image_url = Column(String)
    analysis_result = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClothingItem(Base):
    __tablename__ = "clothing_items"
    
    id = Column(Integer, primary_key=True, index=True)
    outfit_id = Column(Integer)
    item_type = Column(String)  # 'top', 'bottom', 'shoes', 'accessory'
    confidence_score = Column(Float)
    bounding_box = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class ClothingItemResponse(BaseModel):
    id: int
    item_type: str
    confidence_score: float
    bounding_box: Dict[str, Any]

    class Config:
        from_attributes = True

class OutfitAnalysisResponse(BaseModel):
    id: int
    user_id: int
    image_url: str
    analysis_result: Dict[str, Any]
    clothing_items: List[ClothingItemResponse]
    created_at: datetime

    class Config:
        from_attributes = True

class AnalysisRequest(BaseModel):
    image_url: str
    user_id: int

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# YOLO model initialization
def load_yolo_model():
    try:
        model = YOLO(YOLO_MODEL_PATH)
        logger.info("YOLO model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Error loading YOLO model: {e}")
        return None

# Initialize YOLO model
yolo_model = load_yolo_model()

# Clothing class mapping (COCO dataset classes)
CLOTHING_CLASSES = {
    0: 'person',  # We'll filter this out
    1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane', 5: 'bus',
    6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light', 10: 'fire hydrant',
    11: 'stop sign', 12: 'parking meter', 13: 'bench', 14: 'bird', 15: 'cat',
    16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow', 20: 'elephant',
    21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack', 25: 'umbrella',
    26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee', 30: 'skis',
    31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat', 35: 'baseball glove',
    36: 'skateboard', 37: 'surfboard', 38: 'tennis racket', 39: 'bottle', 40: 'wine glass',
    41: 'cup', 42: 'fork', 43: 'knife', 44: 'spoon', 45: 'bowl',
    46: 'banana', 47: 'apple', 48: 'sandwich', 49: 'orange', 50: 'broccoli',
    51: 'carrot', 52: 'hot dog', 53: 'pizza', 54: 'donut', 55: 'cake',
    56: 'chair', 57: 'couch', 58: 'potted plant', 59: 'bed', 60: 'dining table',
    61: 'toilet', 62: 'tv', 63: 'laptop', 64: 'mouse', 65: 'remote',
    66: 'keyboard', 67: 'cell phone', 68: 'microwave', 69: 'oven', 70: 'toaster',
    71: 'sink', 72: 'refrigerator', 73: 'book', 74: 'clock', 75: 'vase',
    76: 'scissors', 77: 'teddy bear', 78: 'hair drier', 79: 'toothbrush'
}

# Clothing-related classes (simplified mapping)
CLOTHING_TYPES = {
    24: 'accessory',  # backpack
    25: 'accessory',  # umbrella
    26: 'accessory',  # handbag
    27: 'top',        # tie
    28: 'accessory',  # suitcase
    32: 'accessory',  # sports ball
    33: 'accessory',  # kite
    35: 'accessory',  # baseball glove
    39: 'accessory',  # bottle
    40: 'accessory',  # wine glass
    41: 'accessory',  # cup
    42: 'accessory',  # fork
    43: 'accessory',  # knife
    44: 'accessory',  # spoon
    45: 'accessory',  # bowl
    67: 'accessory',  # cell phone
    73: 'accessory',  # book
    74: 'accessory',  # clock
    75: 'accessory',  # vase
    76: 'accessory',  # scissors
    77: 'accessory',  # teddy bear
    78: 'accessory',  # hair drier
    79: 'accessory',  # toothbrush
}

async def download_image(image_url: str) -> np.ndarray:
    """Download image from URL and convert to numpy array"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            
            # Convert to PIL Image
            image = Image.open(BytesIO(response.content))
            # Convert to numpy array
            image_array = np.array(image)
            return image_array
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        raise HTTPException(status_code=400, detail="Failed to download image")

def analyze_outfit_with_yolo(image: np.ndarray) -> List[Dict[str, Any]]:
    """Analyze outfit using YOLOv8 model"""
    if yolo_model is None:
        raise HTTPException(status_code=500, detail="YOLO model not available")
    
    try:
        # Run YOLO inference
        results = yolo_model(image)
        
        detected_items = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    # Filter for clothing-related items
                    if class_id in CLOTHING_TYPES and confidence > 0.5:
                        item_type = CLOTHING_TYPES[class_id]
                        class_name = CLOTHING_CLASSES.get(class_id, f"class_{class_id}")
                        
                        detected_items.append({
                            "item_type": item_type,
                            "class_name": class_name,
                            "confidence_score": confidence,
                            "bounding_box": {
                                "x1": float(x1),
                                "y1": float(y1),
                                "x2": float(x2),
                                "y2": float(y2)
                            }
                        })
        
        return detected_items
    
    except Exception as e:
        logger.error(f"Error in YOLO analysis: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing outfit")

async def upload_image_to_media_service(image_data: bytes, filename: str) -> str:
    """Upload image to media service and return URL"""
    try:
        # Encode image as base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEDIA_SERVICE_URL}/upload",
                json={
                    "image_data": image_base64,
                    "filename": filename,
                    "content_type": "image/jpeg"
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("url")
    except Exception as e:
        logger.error(f"Error uploading to media service: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")

# Routes
@app.get("/")
async def root():
    return {"message": "AnkhAi Outfit Analysis Service", "status": "running"}

@app.get("/health")
async def health_check():
    model_status = "loaded" if yolo_model is not None else "not_loaded"
    return {
        "status": "healthy",
        "service": "outfit",
        "yolo_model": model_status
    }

@app.post("/analyze", response_model=OutfitAnalysisResponse)
async def analyze_outfit(
    image_url: str = Form(...),
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Analyze outfit from image URL"""
    try:
        # Download image
        image_array = await download_image(image_url)
        
        # Analyze with YOLO
        detected_items = analyze_outfit_with_yolo(image_array)
        
        # Create analysis result
        analysis_result = {
            "total_items": len(detected_items),
            "items_by_type": {},
            "confidence_scores": []
        }
        
        # Group items by type
        for item in detected_items:
            item_type = item["item_type"]
            if item_type not in analysis_result["items_by_type"]:
                analysis_result["items_by_type"][item_type] = []
            analysis_result["items_by_type"][item_type].append(item)
            analysis_result["confidence_scores"].append(item["confidence_score"])
        
        # Calculate average confidence
        if analysis_result["confidence_scores"]:
            analysis_result["average_confidence"] = sum(analysis_result["confidence_scores"]) / len(analysis_result["confidence_scores"])
        else:
            analysis_result["average_confidence"] = 0.0
        
        # Save to database
        db_outfit = Outfit(
            user_id=user_id,
            image_url=image_url,
            analysis_result=analysis_result
        )
        db.add(db_outfit)
        db.commit()
        db.refresh(db_outfit)
        
        # Save clothing items
        clothing_items = []
        for item in detected_items:
            db_item = ClothingItem(
                outfit_id=db_outfit.id,
                item_type=item["item_type"],
                confidence_score=item["confidence_score"],
                bounding_box=item["bounding_box"]
            )
            db.add(db_item)
            clothing_items.append(db_item)
        
        db.commit()
        
        # Prepare response
        clothing_items_response = [
            ClothingItemResponse(
                id=item.id,
                item_type=item.item_type,
                confidence_score=item.confidence_score,
                bounding_box=item.bounding_box
            ) for item in clothing_items
        ]
        
        return OutfitAnalysisResponse(
            id=db_outfit.id,
            user_id=db_outfit.user_id,
            image_url=db_outfit.image_url,
            analysis_result=db_outfit.analysis_result,
            clothing_items=clothing_items_response,
            created_at=db_outfit.created_at
        )
    
    except Exception as e:
        logger.error(f"Error in outfit analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{user_id}", response_model=List[OutfitAnalysisResponse])
async def get_user_outfits(
    user_id: int,
    current_user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get all outfits for a user"""
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's outfits")
    
    outfits = db.query(Outfit).filter(Outfit.user_id == user_id).all()
    
    result = []
    for outfit in outfits:
        clothing_items = db.query(ClothingItem).filter(ClothingItem.outfit_id == outfit.id).all()
        clothing_items_response = [
            ClothingItemResponse(
                id=item.id,
                item_type=item.item_type,
                confidence_score=item.confidence_score,
                bounding_box=item.bounding_box
            ) for item in clothing_items
        ]
        
        result.append(OutfitAnalysisResponse(
            id=outfit.id,
            user_id=outfit.user_id,
            image_url=outfit.image_url,
            analysis_result=outfit.analysis_result,
            clothing_items=clothing_items_response,
            created_at=outfit.created_at
        ))
    
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
