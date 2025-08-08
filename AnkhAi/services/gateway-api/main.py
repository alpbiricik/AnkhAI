from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx
import os
from typing import Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AnkhAi API Gateway",
    description="API Gateway for AnkhAi Fashion Assistant",
    version="1.0.0"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Service URLs from environment variables
SERVICE_URLS = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001"),
    "outfit": os.getenv("OUTFIT_SERVICE_URL", "http://outfit-service:8002"),
    "celebrity": os.getenv("CELEBRITY_SERVICE_URL", "http://celebrity-style-service:8003"),
    "weather": os.getenv("WEATHER_SERVICE_URL", "http://weather-service:8004"),
    "recommendation": os.getenv("RECOMMENDATION_SERVICE_URL", "http://recommendation-service:8005"),
    "media": os.getenv("MEDIA_SERVICE_URL", "http://media-service:8006"),
}

async def forward_request(
    service_name: str,
    path: str,
    method: str = "GET",
    data: Optional[dict] = None,
    headers: Optional[dict] = None
):
    """Forward request to appropriate microservice"""
    if service_name not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    service_url = SERVICE_URLS[service_name]
    target_url = f"{service_url}{path}"
    
    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(target_url, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(target_url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = await client.put(target_url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = await client.delete(target_url, headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            return response.json(), response.status_code
            
    except httpx.RequestError as e:
        logger.error(f"Error forwarding request to {service_name}: {e}")
        raise HTTPException(status_code=503, detail=f"Service {service_name} unavailable")

@app.get("/")
async def root():
    return {"message": "AnkhAi API Gateway", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = {"gateway": "healthy", "services": {}}
    
    for service_name, service_url in SERVICE_URLS.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=5.0)
                health_status["services"][service_name] = "healthy" if response.status_code == 200 else "unhealthy"
        except:
            health_status["services"][service_name] = "unhealthy"
    
    return health_status

# Authentication routes
@app.post("/auth/register")
async def register_user(request: Request):
    body = await request.json()
    return await forward_request("auth", "/register", "POST", body)

@app.post("/auth/login")
async def login_user(request: Request):
    body = await request.json()
    return await forward_request("auth", "/login", "POST", body)

@app.post("/auth/refresh")
async def refresh_token(request: Request):
    body = await request.json()
    return await forward_request("auth", "/refresh", "POST", body)

@app.get("/auth/me")
async def get_current_user(request: Request):
    headers = dict(request.headers)
    return await forward_request("auth", "/me", "GET", headers=headers)

# Outfit analysis routes
@app.post("/outfits/analyze")
async def analyze_outfit(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    return await forward_request("outfit", "/analyze", "POST", body, headers)

@app.get("/outfits/{user_id}")
async def get_user_outfits(user_id: int, request: Request):
    headers = dict(request.headers)
    return await forward_request("outfit", f"/{user_id}", "GET", headers=headers)

# Celebrity style routes
@app.get("/celebrities")
async def get_celebrities():
    return await forward_request("celebrity", "/")

@app.get("/celebrities/{celebrity_id}")
async def get_celebrity(celebrity_id: int):
    return await forward_request("celebrity", f"/{celebrity_id}")

@app.get("/celebrities/{celebrity_id}/outfits")
async def get_celebrity_outfits(celebrity_id: int):
    return await forward_request("celebrity", f"/{celebrity_id}/outfits")

# Weather routes
@app.get("/weather/{city}")
async def get_weather(city: str):
    return await forward_request("weather", f"/{city}")

@app.get("/weather/coordinates/{lat}/{lon}")
async def get_weather_by_coordinates(lat: float, lon: float):
    return await forward_request("weather", f"/coordinates/{lat}/{lon}")

# Recommendation routes
@app.post("/recommendations/generate")
async def generate_recommendation(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    return await forward_request("recommendation", "/generate", "POST", body, headers)

@app.get("/recommendations/{user_id}")
async def get_user_recommendations(user_id: int, request: Request):
    headers = dict(request.headers)
    return await forward_request("recommendation", f"/{user_id}", "GET", headers=headers)

# Media routes
@app.post("/media/upload")
async def upload_media(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    return await forward_request("media", "/upload", "POST", body, headers)

@app.get("/media/{file_id}")
async def get_media(file_id: str):
    return await forward_request("media", f"/{file_id}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
