from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import httpx
import redis
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ankhai-super-secret-jwt-key-2024-production-ready")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Initialize Redis
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()  # Test connection
    logger.info("Redis connection established")
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

# Security
security = HTTPBearer()

app = FastAPI(
    title="AnkhAi Weather Service",
    description="Weather data service with OpenWeatherMap integration",
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
class WeatherResponse(BaseModel):
    location: str
    temperature: float
    feels_like: float
    humidity: int
    description: str
    icon: str
    wind_speed: float
    pressure: int
    visibility: int
    uv_index: Optional[float]
    sunrise: str
    sunset: str
    timestamp: datetime

class WeatherRequest(BaseModel):
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None

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

# Weather API functions
async def get_weather_by_city(city: str) -> Dict[str, Any]:
    """Get weather data by city name"""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeatherMap API key not configured")
    
    # Check cache first
    cache_key = f"weather_city_{city.lower()}"
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached weather data for {city}")
            return json.loads(cached_data)
    
    try:
        async with httpx.AsyncClient() as client:
            # Get current weather
            current_url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": city,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            }
            
            response = await client.get(current_url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            
            # Get UV index
            uv_url = f"http://api.openweathermap.org/data/2.5/uvi"
            uv_params = {
                "lat": weather_data["coord"]["lat"],
                "lon": weather_data["coord"]["lon"],
                "appid": OPENWEATHER_API_KEY
            }
            
            try:
                uv_response = await client.get(uv_url, params=uv_params)
                uv_data = uv_response.json()
                uv_index = uv_data.get("value")
            except:
                uv_index = None
            
            # Format response
            formatted_data = {
                "location": f"{weather_data['name']}, {weather_data['sys']['country']}",
                "temperature": weather_data["main"]["temp"],
                "feels_like": weather_data["main"]["feels_like"],
                "humidity": weather_data["main"]["humidity"],
                "description": weather_data["weather"][0]["description"],
                "icon": weather_data["weather"][0]["icon"],
                "wind_speed": weather_data["wind"]["speed"],
                "pressure": weather_data["main"]["pressure"],
                "visibility": weather_data.get("visibility", 0),
                "uv_index": uv_index,
                "sunrise": datetime.fromtimestamp(weather_data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(weather_data["sys"]["sunset"]).strftime("%H:%M"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache the result (15 minutes)
            if redis_client:
                redis_client.setex(cache_key, 900, json.dumps(formatted_data))
            
            return formatted_data
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"City '{city}' not found")
        else:
            logger.error(f"OpenWeatherMap API error: {e}")
            raise HTTPException(status_code=500, detail="Weather service unavailable")
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching weather data")

async def get_weather_by_coordinates(lat: float, lon: float) -> Dict[str, Any]:
    """Get weather data by coordinates"""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenWeatherMap API key not configured")
    
    # Check cache first
    cache_key = f"weather_coords_{lat}_{lon}"
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached weather data for coordinates {lat}, {lon}")
            return json.loads(cached_data)
    
    try:
        async with httpx.AsyncClient() as client:
            # Get current weather
            current_url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric"
            }
            
            response = await client.get(current_url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            
            # Get UV index
            uv_url = f"http://api.openweathermap.org/data/2.5/uvi"
            uv_params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY
            }
            
            try:
                uv_response = await client.get(uv_url, params=uv_params)
                uv_data = uv_response.json()
                uv_index = uv_data.get("value")
            except:
                uv_index = None
            
            # Format response
            formatted_data = {
                "location": f"{weather_data['name']}, {weather_data['sys']['country']}",
                "temperature": weather_data["main"]["temp"],
                "feels_like": weather_data["main"]["feels_like"],
                "humidity": weather_data["main"]["humidity"],
                "description": weather_data["weather"][0]["description"],
                "icon": weather_data["weather"][0]["icon"],
                "wind_speed": weather_data["wind"]["speed"],
                "pressure": weather_data["main"]["pressure"],
                "visibility": weather_data.get("visibility", 0),
                "uv_index": uv_index,
                "sunrise": datetime.fromtimestamp(weather_data["sys"]["sunrise"]).strftime("%H:%M"),
                "sunset": datetime.fromtimestamp(weather_data["sys"]["sunset"]).strftime("%H:%M"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cache the result (15 minutes)
            if redis_client:
                redis_client.setex(cache_key, 900, json.dumps(formatted_data))
            
            return formatted_data
    
    except httpx.HTTPStatusError as e:
        logger.error(f"OpenWeatherMap API error: {e}")
        raise HTTPException(status_code=500, detail="Weather service unavailable")
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching weather data")

def get_weather_recommendations(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate weather-based clothing recommendations"""
    temp = weather_data["temperature"]
    humidity = weather_data["humidity"]
    description = weather_data["description"].lower()
    
    recommendations = {
        "temperature_category": "",
        "clothing_suggestions": [],
        "accessories": [],
        "notes": []
    }
    
    # Temperature-based recommendations
    if temp < 0:
        recommendations["temperature_category"] = "very_cold"
        recommendations["clothing_suggestions"] = [
            "Heavy winter coat or parka",
            "Thermal underwear",
            "Wool sweaters",
            "Thick pants or jeans",
            "Winter boots"
        ]
        recommendations["accessories"] = [
            "Scarf",
            "Gloves",
            "Winter hat",
            "Thermal socks"
        ]
    elif temp < 10:
        recommendations["temperature_category"] = "cold"
        recommendations["clothing_suggestions"] = [
            "Warm jacket or coat",
            "Sweaters or cardigans",
            "Long pants",
            "Closed-toe shoes"
        ]
        recommendations["accessories"] = [
            "Scarf",
            "Light gloves",
            "Hat"
        ]
    elif temp < 20:
        recommendations["temperature_category"] = "cool"
        recommendations["clothing_suggestions"] = [
            "Light jacket or blazer",
            "Long-sleeve shirts",
            "Pants or jeans",
            "Comfortable shoes"
        ]
        recommendations["accessories"] = [
            "Light scarf (optional)",
            "Sunglasses"
        ]
    elif temp < 30:
        recommendations["temperature_category"] = "warm"
        recommendations["clothing_suggestions"] = [
            "T-shirts or short-sleeve shirts",
            "Light pants or shorts",
            "Breathable fabrics",
            "Comfortable shoes"
        ]
        recommendations["accessories"] = [
            "Sunglasses",
            "Hat for sun protection"
        ]
    else:
        recommendations["temperature_category"] = "hot"
        recommendations["clothing_suggestions"] = [
            "Light, breathable clothing",
            "Shorts or light pants",
            "Tank tops or light shirts",
            "Sandals or breathable shoes"
        ]
        recommendations["accessories"] = [
            "Sunglasses",
            "Wide-brimmed hat",
            "Sunscreen"
        ]
    
    # Weather condition adjustments
    if "rain" in description:
        recommendations["accessories"].append("Umbrella")
        recommendations["accessories"].append("Waterproof shoes")
        recommendations["notes"].append("Consider waterproof clothing")
    
    if "snow" in description:
        recommendations["accessories"].append("Waterproof boots")
        recommendations["notes"].append("Dress in layers for warmth")
    
    if "wind" in description:
        recommendations["notes"].append("Consider wind-resistant clothing")
    
    if humidity > 70:
        recommendations["notes"].append("High humidity - choose breathable fabrics")
    
    return recommendations

# Routes
@app.get("/")
async def root():
    return {"message": "AnkhAi Weather Service", "status": "running"}

@app.get("/health")
async def health_check():
    redis_status = "connected" if redis_client and redis_client.ping() else "disconnected"
    api_status = "configured" if OPENWEATHER_API_KEY else "not_configured"
    
    return {
        "status": "healthy",
        "service": "weather",
        "redis": redis_status,
        "openweather_api": api_status
    }

@app.get("/{city}")
async def get_weather_by_city_endpoint(
    city: str,
    user_id: int = Depends(verify_token)
):
    """Get weather data by city name"""
    weather_data = await get_weather_by_city(city)
    recommendations = get_weather_recommendations(weather_data)
    
    return {
        "weather": weather_data,
        "recommendations": recommendations
    }

@app.get("/coordinates/{lat}/{lon}")
async def get_weather_by_coordinates_endpoint(
    lat: float,
    lon: float,
    user_id: int = Depends(verify_token)
):
    """Get weather data by coordinates"""
    weather_data = await get_weather_by_coordinates(lat, lon)
    recommendations = get_weather_recommendations(weather_data)
    
    return {
        "weather": weather_data,
        "recommendations": recommendations
    }

@app.post("/recommendations")
async def get_weather_recommendations_endpoint(
    request: WeatherRequest,
    user_id: int = Depends(verify_token)
):
    """Get weather-based clothing recommendations"""
    if request.city:
        weather_data = await get_weather_by_city(request.city)
    elif request.lat and request.lon:
        weather_data = await get_weather_by_coordinates(request.lat, request.lon)
    else:
        raise HTTPException(status_code=400, detail="Either city or coordinates must be provided")
    
    recommendations = get_weather_recommendations(weather_data)
    
    return {
        "weather": weather_data,
        "recommendations": recommendations
    }

@app.delete("/cache/{city}")
async def clear_weather_cache(
    city: str,
    user_id: int = Depends(verify_token)
):
    """Clear cached weather data for a city"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    cache_key = f"weather_city_{city.lower()}"
    redis_client.delete(cache_key)
    
    return {"message": f"Cache cleared for {city}"}

@app.delete("/cache/coordinates/{lat}/{lon}")
async def clear_coordinates_cache(
    lat: float,
    lon: float,
    user_id: int = Depends(verify_token)
):
    """Clear cached weather data for coordinates"""
    if not redis_client:
        raise HTTPException(status_code=500, detail="Redis not available")
    
    cache_key = f"weather_coords_{lat}_{lon}"
    redis_client.delete(cache_key)
    
    return {"message": f"Cache cleared for coordinates {lat}, {lon}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
