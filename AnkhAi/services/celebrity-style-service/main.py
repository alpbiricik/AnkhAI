from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
import openai
import google.generativeai as genai
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ankhai_user:ankhai_password@postgres:5432/ankhai_celebrity")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# JWT configuration (for user verification)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# AI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize AI clients
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Security
security = HTTPBearer()

app = FastAPI(
    title="AnkhAi Celebrity Style Service",
    description="Celebrity style data and LLM-powered descriptions",
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
class Celebrity(Base):
    __tablename__ = "celebrities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    style_tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CelebrityOutfit(Base):
    __tablename__ = "celebrity_outfits"
    
    id = Column(Integer, primary_key=True, index=True)
    celebrity_id = Column(Integer)
    image_url = Column(String)
    style_description = Column(Text)
    occasion = Column(String)
    season = Column(String)
    tags = Column(ARRAY(String))
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# Pydantic models
class CelebrityResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    style_tags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CelebrityOutfitResponse(BaseModel):
    id: int
    celebrity_id: int
    image_url: str
    style_description: str
    occasion: Optional[str]
    season: Optional[str]
    tags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

class CelebrityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    style_tags: List[str] = []

class CelebrityOutfitCreate(BaseModel):
    celebrity_id: int
    image_url: str
    style_description: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    tags: List[str] = []

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

# AI-powered style description generation
async def generate_style_description_with_openai(celebrity_name: str, image_url: str, occasion: str = None) -> str:
    """Generate style description using OpenAI GPT"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        prompt = f"""
        Analyze the fashion style of {celebrity_name} in this outfit image: {image_url}
        
        Please provide a detailed style description including:
        - Key clothing pieces and their characteristics
        - Color palette and patterns
        - Overall aesthetic and vibe
        - Style elements that make this outfit distinctive
        - How it reflects the celebrity's signature style
        
        {f"Occasion: {occasion}" if occasion else ""}
        
        Write a compelling, fashion-forward description that captures the essence of this look.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a fashion expert and style analyst. Provide detailed, engaging descriptions of celebrity fashion looks."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Error generating style description with OpenAI: {e}")
        raise HTTPException(status_code=500, detail="Error generating style description")

async def generate_style_description_with_gemini(celebrity_name: str, image_url: str, occasion: str = None) -> str:
    """Generate style description using Google Gemini"""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Analyze the fashion style of {celebrity_name} in this outfit image: {image_url}
        
        Please provide a detailed style description including:
        - Key clothing pieces and their characteristics
        - Color palette and patterns
        - Overall aesthetic and vibe
        - Style elements that make this outfit distinctive
        - How it reflects the celebrity's signature style
        
        {f"Occasion: {occasion}" if occasion else ""}
        
        Write a compelling, fashion-forward description that captures the essence of this look.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        logger.error(f"Error generating style description with Gemini: {e}")
        raise HTTPException(status_code=500, detail="Error generating style description")

async def generate_style_description(celebrity_name: str, image_url: str, occasion: str = None) -> str:
    """Generate style description using available AI service"""
    try:
        if OPENAI_API_KEY:
            return await generate_style_description_with_openai(celebrity_name, image_url, occasion)
        elif GEMINI_API_KEY:
            return await generate_style_description_with_gemini(celebrity_name, image_url, occasion)
        else:
            # Fallback to a basic description
            return f"A stylish outfit worn by {celebrity_name} featuring contemporary fashion elements and a distinctive personal style."
    except Exception as e:
        logger.error(f"Error in style description generation: {e}")
        return f"A fashionable look by {celebrity_name} showcasing their unique style."

# Routes
@app.get("/")
async def root():
    return {"message": "AnkhAi Celebrity Style Service", "status": "running"}

@app.get("/health")
async def health_check():
    ai_status = "configured" if (OPENAI_API_KEY or GEMINI_API_KEY) else "not_configured"
    return {
        "status": "healthy",
        "service": "celebrity_style",
        "ai_services": ai_status
    }

@app.get("/celebrities", response_model=List[CelebrityResponse])
async def get_celebrities(db: Session = Depends(get_db)):
    """Get all celebrities"""
    celebrities = db.query(Celebrity).all()
    return [CelebrityResponse.from_orm(celebrity) for celebrity in celebrities]

@app.get("/celebrities/{celebrity_id}", response_model=CelebrityResponse)
async def get_celebrity(celebrity_id: int, db: Session = Depends(get_db)):
    """Get a specific celebrity by ID"""
    celebrity = db.query(Celebrity).filter(Celebrity.id == celebrity_id).first()
    if not celebrity:
        raise HTTPException(status_code=404, detail="Celebrity not found")
    return CelebrityResponse.from_orm(celebrity)

@app.post("/celebrities", response_model=CelebrityResponse)
async def create_celebrity(
    celebrity: CelebrityCreate,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create a new celebrity"""
    db_celebrity = Celebrity(
        name=celebrity.name,
        description=celebrity.description,
        style_tags=celebrity.style_tags
    )
    db.add(db_celebrity)
    db.commit()
    db.refresh(db_celebrity)
    return CelebrityResponse.from_orm(db_celebrity)

@app.get("/celebrities/{celebrity_id}/outfits", response_model=List[CelebrityOutfitResponse])
async def get_celebrity_outfits(celebrity_id: int, db: Session = Depends(get_db)):
    """Get all outfits for a specific celebrity"""
    outfits = db.query(CelebrityOutfit).filter(CelebrityOutfit.celebrity_id == celebrity_id).all()
    return [CelebrityOutfitResponse.from_orm(outfit) for outfit in outfits]

@app.post("/celebrities/{celebrity_id}/outfits", response_model=CelebrityOutfitResponse)
async def create_celebrity_outfit(
    celebrity_id: int,
    outfit: CelebrityOutfitCreate,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Create a new celebrity outfit with AI-generated description"""
    # Verify celebrity exists
    celebrity = db.query(Celebrity).filter(Celebrity.id == celebrity_id).first()
    if not celebrity:
        raise HTTPException(status_code=404, detail="Celebrity not found")
    
    # Generate style description if not provided
    style_description = outfit.style_description
    if not style_description:
        style_description = await generate_style_description(
            celebrity.name, 
            outfit.image_url, 
            outfit.occasion
        )
    
    db_outfit = CelebrityOutfit(
        celebrity_id=celebrity_id,
        image_url=outfit.image_url,
        style_description=style_description,
        occasion=outfit.occasion,
        season=outfit.season,
        tags=outfit.tags
    )
    db.add(db_outfit)
    db.commit()
    db.refresh(db_outfit)
    return CelebrityOutfitResponse.from_orm(db_outfit)

@app.get("/outfits", response_model=List[CelebrityOutfitResponse])
async def get_all_outfits(
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all celebrity outfits with optional filtering"""
    query = db.query(CelebrityOutfit)
    
    if occasion:
        query = query.filter(CelebrityOutfit.occasion == occasion)
    if season:
        query = query.filter(CelebrityOutfit.season == season)
    
    outfits = query.all()
    return [CelebrityOutfitResponse.from_orm(outfit) for outfit in outfits]

@app.get("/outfits/{outfit_id}", response_model=CelebrityOutfitResponse)
async def get_outfit(outfit_id: int, db: Session = Depends(get_db)):
    """Get a specific outfit by ID"""
    outfit = db.query(CelebrityOutfit).filter(CelebrityOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return CelebrityOutfitResponse.from_orm(outfit)

@app.post("/outfits/{outfit_id}/regenerate-description")
async def regenerate_outfit_description(
    outfit_id: int,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Regenerate the style description for an outfit using AI"""
    outfit = db.query(CelebrityOutfit).filter(CelebrityOutfit.id == outfit_id).first()
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    
    celebrity = db.query(Celebrity).filter(Celebrity.id == outfit.celebrity_id).first()
    if not celebrity:
        raise HTTPException(status_code=404, detail="Celebrity not found")
    
    # Generate new description
    new_description = await generate_style_description(
        celebrity.name,
        outfit.image_url,
        outfit.occasion
    )
    
    # Update outfit
    outfit.style_description = new_description
    outfit.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(outfit)
    
    return {
        "id": outfit.id,
        "style_description": outfit.style_description,
        "updated_at": outfit.updated_at
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
