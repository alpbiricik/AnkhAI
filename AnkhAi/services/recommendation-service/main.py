from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import httpx
import openai
import google.generativeai as genai
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Service URLs
OUTFIT_SERVICE_URL = os.getenv("OUTFIT_SERVICE_URL", "http://outfit-service:8002")
CELEBRITY_SERVICE_URL = os.getenv("CELEBRITY_SERVICE_URL", "http://celebrity-style-service:8003")
WEATHER_SERVICE_URL = os.getenv("WEATHER_SERVICE_URL", "http://weather-service:8004")

# Initialize AI clients
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Security
security = HTTPBearer()

app = FastAPI(
    title="AnkhAi Recommendation Service",
    description="AI-powered outfit recommendations combining user wardrobe, celebrity styles, and weather",
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
class RecommendationRequest(BaseModel):
    user_id: int
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    occasion: Optional[str] = None
    celebrity_id: Optional[int] = None
    style_preferences: Optional[List[str]] = []

class RecommendationResponse(BaseModel):
    id: str
    user_id: int
    recommendation_text: str
    suggested_outfit: Dict[str, Any]
    weather_considerations: Dict[str, Any]
    celebrity_inspiration: Optional[Dict[str, Any]]
    confidence_score: float
    created_at: datetime

class OutfitAnalysis(BaseModel):
    id: int
    user_id: int
    image_url: str
    analysis_result: Dict[str, Any]
    clothing_items: List[Dict[str, Any]]

class WeatherData(BaseModel):
    location: str
    temperature: float
    description: str
    recommendations: Dict[str, Any]

class CelebrityStyle(BaseModel):
    id: int
    name: str
    style_tags: List[str]
    outfits: List[Dict[str, Any]]

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

# Service integration functions
async def get_user_outfits(user_id: int, auth_token: str) -> List[OutfitAnalysis]:
    """Get user's analyzed outfits from outfit service"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await client.get(
                f"{OUTFIT_SERVICE_URL}/{user_id}",
                headers=headers
            )
            response.raise_for_status()
            outfits_data = response.json()
            
            return [OutfitAnalysis(**outfit) for outfit in outfits_data]
    except Exception as e:
        logger.error(f"Error fetching user outfits: {e}")
        return []

async def get_weather_data(city: str = None, lat: float = None, lon: float = None, auth_token: str = None) -> Optional[WeatherData]:
    """Get weather data from weather service"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            
            if city:
                response = await client.get(f"{WEATHER_SERVICE_URL}/{city}", headers=headers)
            elif lat and lon:
                response = await client.get(f"{WEATHER_SERVICE_URL}/coordinates/{lat}/{lon}", headers=headers)
            else:
                return None
            
            response.raise_for_status()
            weather_response = response.json()
            
            return WeatherData(
                location=weather_response["weather"]["location"],
                temperature=weather_response["weather"]["temperature"],
                description=weather_response["weather"]["description"],
                recommendations=weather_response["recommendations"]
            )
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

async def get_celebrity_style(celebrity_id: int, auth_token: str = None) -> Optional[CelebrityStyle]:
    """Get celebrity style data from celebrity service"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            
            # Get celebrity info
            celeb_response = await client.get(f"{CELEBRITY_SERVICE_URL}/celebrities/{celebrity_id}", headers=headers)
            celeb_response.raise_for_status()
            celebrity_data = celeb_response.json()
            
            # Get celebrity outfits
            outfits_response = await client.get(f"{CELEBRITY_SERVICE_URL}/celebrities/{celebrity_id}/outfits", headers=headers)
            outfits_response.raise_for_status()
            outfits_data = outfits_response.json()
            
            return CelebrityStyle(
                id=celebrity_data["id"],
                name=celebrity_data["name"],
                style_tags=celebrity_data["style_tags"],
                outfits=outfits_data
            )
    except Exception as e:
        logger.error(f"Error fetching celebrity style: {e}")
        return None

async def get_all_celebrities(auth_token: str = None) -> List[Dict[str, Any]]:
    """Get all celebrities for inspiration"""
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            response = await client.get(f"{CELEBRITY_SERVICE_URL}/celebrities", headers=headers)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching celebrities: {e}")
        return []

# AI-powered recommendation generation
async def generate_recommendation_with_openai(
    user_outfits: List[OutfitAnalysis],
    weather_data: Optional[WeatherData],
    celebrity_style: Optional[CelebrityStyle],
    occasion: str = None,
    style_preferences: List[str] = []
) -> str:
    """Generate outfit recommendation using OpenAI GPT"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        # Prepare context data
        outfit_summary = ""
        if user_outfits:
            outfit_summary = "User's wardrobe includes:\n"
            for outfit in user_outfits[:3]:  # Limit to recent outfits
                items = outfit.analysis_result.get("items_by_type", {})
                outfit_summary += f"- {len(items.get('top', []))} tops, {len(items.get('bottom', []))} bottoms, {len(items.get('accessory', []))} accessories\n"
        
        weather_context = ""
        if weather_data:
            weather_context = f"""
Weather conditions: {weather_data.temperature}°C, {weather_data.description}
Location: {weather_data.location}
Weather recommendations: {', '.join(weather_data.recommendations.get('clothing_suggestions', [])[:3])}
"""
        
        celebrity_context = ""
        if celebrity_style:
            celebrity_context = f"""
Celebrity inspiration: {celebrity_style.name}
Style tags: {', '.join(celebrity_style.style_tags)}
Available outfits: {len(celebrity_style.outfits)} looks
"""
        
        prompt = f"""
You are a personal fashion stylist for AnkhAi. Create a personalized outfit recommendation based on the following information:

{outfit_summary}

{weather_context}

{celebrity_context}

Occasion: {occasion or 'casual daily wear'}
Style preferences: {', '.join(style_preferences) if style_preferences else 'not specified'}

Please provide:
1. A detailed outfit recommendation that combines the user's existing wardrobe with weather-appropriate choices
2. Specific suggestions for tops, bottoms, shoes, and accessories
3. How to incorporate the celebrity's style elements
4. Weather-appropriate considerations
5. Confidence level (1-10) for this recommendation

Write in a friendly, encouraging tone as if you're a personal stylist speaking directly to the user.
"""
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert fashion stylist with deep knowledge of personal styling, weather-appropriate dressing, and celebrity fashion trends."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Error generating recommendation with OpenAI: {e}")
        raise HTTPException(status_code=500, detail="Error generating recommendation")

async def generate_recommendation_with_gemini(
    user_outfits: List[OutfitAnalysis],
    weather_data: Optional[WeatherData],
    celebrity_style: Optional[CelebrityStyle],
    occasion: str = None,
    style_preferences: List[str] = []
) -> str:
    """Generate outfit recommendation using Google Gemini"""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Prepare context data (similar to OpenAI version)
        outfit_summary = ""
        if user_outfits:
            outfit_summary = "User's wardrobe includes:\n"
            for outfit in user_outfits[:3]:
                items = outfit.analysis_result.get("items_by_type", {})
                outfit_summary += f"- {len(items.get('top', []))} tops, {len(items.get('bottom', []))} bottoms, {len(items.get('accessory', []))} accessories\n"
        
        weather_context = ""
        if weather_data:
            weather_context = f"""
Weather conditions: {weather_data.temperature}°C, {weather_data.description}
Location: {weather_data.location}
Weather recommendations: {', '.join(weather_data.recommendations.get('clothing_suggestions', [])[:3])}
"""
        
        celebrity_context = ""
        if celebrity_style:
            celebrity_context = f"""
Celebrity inspiration: {celebrity_style.name}
Style tags: {', '.join(celebrity_style.style_tags)}
Available outfits: {len(celebrity_style.outfits)} looks
"""
        
        prompt = f"""
You are a personal fashion stylist for AnkhAi. Create a personalized outfit recommendation based on the following information:

{outfit_summary}

{weather_context}

{celebrity_context}

Occasion: {occasion or 'casual daily wear'}
Style preferences: {', '.join(style_preferences) if style_preferences else 'not specified'}

Please provide:
1. A detailed outfit recommendation that combines the user's existing wardrobe with weather-appropriate choices
2. Specific suggestions for tops, bottoms, shoes, and accessories
3. How to incorporate the celebrity's style elements
4. Weather-appropriate considerations
5. Confidence level (1-10) for this recommendation

Write in a friendly, encouraging tone as if you're a personal stylist speaking directly to the user.
"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    
    except Exception as e:
        logger.error(f"Error generating recommendation with Gemini: {e}")
        raise HTTPException(status_code=500, detail="Error generating recommendation")

async def generate_recommendation(
    user_outfits: List[OutfitAnalysis],
    weather_data: Optional[WeatherData],
    celebrity_style: Optional[CelebrityStyle],
    occasion: str = None,
    style_preferences: List[str] = []
) -> str:
    """Generate recommendation using available AI service"""
    try:
        if OPENAI_API_KEY:
            return await generate_recommendation_with_openai(
                user_outfits, weather_data, celebrity_style, occasion, style_preferences
            )
        elif GEMINI_API_KEY:
            return await generate_recommendation_with_gemini(
                user_outfits, weather_data, celebrity_style, occasion, style_preferences
            )
        else:
            # Fallback recommendation
            return f"""
Based on your wardrobe and current conditions, here's a personalized outfit suggestion:

{weather_data.location if weather_data else 'Your location'}: {weather_data.temperature}°C, {weather_data.description if weather_data else 'unknown weather'}

Recommendation: Consider wearing weather-appropriate clothing that matches your personal style. 
{celebrity_style.name if celebrity_style else 'A celebrity'} could be great inspiration for this look!

Confidence: 7/10
"""
    except Exception as e:
        logger.error(f"Error in recommendation generation: {e}")
        return "Unable to generate recommendation at this time. Please try again later."

# Routes
@app.get("/")
async def root():
    return {"message": "AnkhAi Recommendation Service", "status": "running"}

@app.get("/health")
async def health_check():
    ai_status = "configured" if (OPENAI_API_KEY or GEMINI_API_KEY) else "not_configured"
    return {
        "status": "healthy",
        "service": "recommendation",
        "ai_services": ai_status
    }

@app.post("/generate")
async def generate_outfit_recommendation(
    request: RecommendationRequest,
    user_id: int = Depends(verify_token),
    auth_token: str = Depends(security)
):
    """Generate personalized outfit recommendation"""
    if user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to generate recommendations for this user")
    
    try:
        # Get user's wardrobe
        user_outfits = await get_user_outfits(request.user_id, auth_token.credentials)
        
        # Get weather data
        weather_data = None
        if request.city or (request.lat and request.lon):
            weather_data = await get_weather_data(
                city=request.city,
                lat=request.lat,
                lon=request.lon,
                auth_token=auth_token.credentials
            )
        
        # Get celebrity style inspiration
        celebrity_style = None
        if request.celebrity_id:
            celebrity_style = await get_celebrity_style(request.celebrity_id, auth_token.credentials)
        
        # Generate recommendation
        recommendation_text = await generate_recommendation(
            user_outfits=user_outfits,
            weather_data=weather_data,
            celebrity_style=celebrity_style,
            occasion=request.occasion,
            style_preferences=request.style_preferences
        )
        
        # Calculate confidence score (simplified)
        confidence_score = 0.8  # Base confidence
        if weather_data:
            confidence_score += 0.1
        if celebrity_style:
            confidence_score += 0.1
        if user_outfits:
            confidence_score += 0.1
        
        # Create response
        recommendation_id = f"rec_{request.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        return RecommendationResponse(
            id=recommendation_id,
            user_id=request.user_id,
            recommendation_text=recommendation_text,
            suggested_outfit={
                "tops": len([o for o in user_outfits for items in o.analysis_result.get("items_by_type", {}).get("top", [])]),
                "bottoms": len([o for o in user_outfits for items in o.analysis_result.get("items_by_type", {}).get("bottom", [])]),
                "accessories": len([o for o in user_outfits for items in o.analysis_result.get("items_by_type", {}).get("accessory", [])])
            },
            weather_considerations=weather_data.recommendations if weather_data else {},
            celebrity_inspiration={
                "name": celebrity_style.name,
                "style_tags": celebrity_style.style_tags
            } if celebrity_style else None,
            confidence_score=min(confidence_score, 1.0),
            created_at=datetime.utcnow()
        )
    
    except Exception as e:
        logger.error(f"Error generating recommendation: {e}")
        raise HTTPException(status_code=500, detail="Error generating recommendation")

@app.get("/{user_id}")
async def get_user_recommendations(
    user_id: int,
    current_user_id: int = Depends(verify_token)
):
    """Get recommendation history for a user (placeholder)"""
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user's recommendations")
    
    # This would typically fetch from a database
    return {
        "user_id": user_id,
        "recommendations": [],
        "message": "Recommendation history feature coming soon"
    }

@app.get("/celebrities/inspiration")
async def get_celebrities_for_inspiration(
    auth_token: str = Depends(security)
):
    """Get all celebrities for inspiration"""
    celebrities = await get_all_celebrities(auth_token.credentials)
    return {
        "celebrities": celebrities,
        "message": "Available celebrities for style inspiration"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
