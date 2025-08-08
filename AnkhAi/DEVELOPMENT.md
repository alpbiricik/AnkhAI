# AnkhAi Development Guide

This guide provides comprehensive information for developing and contributing to the AnkhAi fashion assistant project.

## 🏗️ Architecture Overview

AnkhAi is built using a microservices architecture with the following components:

### Backend Services

1. **API Gateway** (`gateway-api`)
   - Single entry point for all frontend requests
   - Routes requests to appropriate microservices
   - Handles CORS and request forwarding
   - Port: 8000

2. **Authentication Service** (`auth-service`)
   - User registration and login
   - JWT token management
   - Password hashing and verification
   - Port: 8001

3. **Outfit Analysis Service** (`outfit-service`)
   - AI-powered outfit analysis using YOLOv8
   - Clothing item detection and classification
   - Integration with media service for image storage
   - Port: 8002

4. **Celebrity Style Service** (`celebrity-style-service`)
   - Celebrity fashion data management
   - LLM-powered style descriptions
   - Style tag classification
   - Port: 8003

5. **Weather Service** (`weather-service`)
   - OpenWeatherMap API integration
   - Weather-based clothing recommendations
   - Redis caching for performance
   - Port: 8004

6. **Recommendation Service** (`recommendation-service`)
   - AI-powered outfit recommendations
   - Combines user wardrobe, weather, and celebrity styles
   - OpenAI GPT and Google Gemini integration
   - Port: 8005

7. **Media Service** (`media-service`)
   - Image upload and storage
   - Cloudinary and Firebase Storage integration
   - File management and retrieval
   - Port: 8006

### Infrastructure

- **PostgreSQL**: Multi-database setup for different services
- **Redis**: Caching layer for weather data
- **Docker Compose**: Service orchestration

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- API keys for external services
- Flutter SDK (for frontend development)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AnkhAi
   ```

2. **Run the setup script**
   ```bash
   ./setup.sh
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

4. **Start all services**
   ```bash
   docker-compose up -d
   ```

5. **Verify services are running**
   ```bash
   curl http://localhost:8000/health
   ```

## 🔧 Development Workflow

### Adding a New Service

1. **Create service directory**
   ```bash
   mkdir services/new-service
   cd services/new-service
   ```

2. **Create FastAPI application**
   ```python
   # main.py
   from fastapi import FastAPI
   
   app = FastAPI(title="New Service")
   
   @app.get("/")
   async def root():
       return {"message": "New Service"}
   ```

3. **Add requirements.txt**
   ```txt
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   # Add other dependencies
   ```

4. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8007
   CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8007"]
   ```

5. **Update docker-compose.yml**
   ```yaml
   new-service:
     build: ./services/new-service
     ports:
       - "8007:8007"
     networks:
       - ankhai-network
   ```

6. **Add service to API Gateway**
   ```python
   # In gateway-api/main.py
   SERVICE_URLS["new-service"] = os.getenv("NEW_SERVICE_URL", "http://new-service:8007")
   ```

### Database Development

#### Adding New Tables

1. **Update init-db.sql**
   ```sql
   -- Add new table definition
   CREATE TABLE new_table (
       id SERIAL PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **Create SQLAlchemy model**
   ```python
   class NewTable(Base):
       __tablename__ = "new_table"
       
       id = Column(Integer, primary_key=True, index=True)
       name = Column(String, nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow)
   ```

3. **Add Pydantic models**
   ```python
   class NewTableCreate(BaseModel):
       name: str
   
   class NewTableResponse(BaseModel):
       id: int
       name: str
       created_at: datetime
       
       class Config:
           from_attributes = True
   ```

### API Development

#### Adding New Endpoints

1. **Define request/response models**
   ```python
   class CreateItemRequest(BaseModel):
       name: str
       description: Optional[str] = None
   
   class ItemResponse(BaseModel):
       id: int
       name: str
       description: Optional[str]
       created_at: datetime
   ```

2. **Add endpoint**
   ```python
   @app.post("/items", response_model=ItemResponse)
   async def create_item(
       request: CreateItemRequest,
       db: Session = Depends(get_db)
   ):
       db_item = Item(
           name=request.name,
           description=request.description
       )
       db.add(db_item)
       db.commit()
       db.refresh(db_item)
       return ItemResponse.from_orm(db_item)
   ```

3. **Add to API Gateway**
   ```python
   @app.post("/items")
   async def create_item(request: Request):
       body = await request.json()
       return await forward_request("new-service", "/items", "POST", body)
   ```

### Testing

#### Unit Tests

1. **Create test file**
   ```python
   # test_main.py
   import pytest
   from fastapi.testclient import TestClient
   from main import app
   
   client = TestClient(app)
   
   def test_root():
       response = client.get("/")
       assert response.status_code == 200
       assert response.json() == {"message": "Service"}
   ```

2. **Run tests**
   ```bash
   pip install pytest
   pytest test_main.py
   ```

#### Integration Tests

1. **Test service communication**
   ```python
   async def test_service_integration():
       async with httpx.AsyncClient() as client:
           response = await client.get("http://gateway-api:8000/health")
           assert response.status_code == 200
   ```

### Error Handling

#### Standard Error Responses

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```

#### Custom Exception Handlers

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=400,
        content={"message": exc.message, "error_code": exc.error_code}
    )
```

## 🔒 Security Best Practices

### JWT Token Management

1. **Token verification**
   ```python
   async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
       try:
           payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
           user_id: str = payload.get("sub")
           if user_id is None:
               raise HTTPException(status_code=401, detail="Invalid token")
           return int(user_id)
       except JWTError:
           raise HTTPException(status_code=401, detail="Invalid token")
   ```

2. **Protected endpoints**
   ```python
   @app.get("/protected")
   async def protected_endpoint(user_id: int = Depends(verify_token)):
       return {"user_id": user_id, "message": "Protected data"}
   ```

### Input Validation

```python
from pydantic import BaseModel, validator

class UserCreate(BaseModel):
    email: str
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

## 📊 Monitoring and Logging

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.get("/items")
async def get_items():
    logger.info("Fetching items from database")
    # ... implementation
```

### Health Checks

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "service-name",
        "timestamp": datetime.utcnow().isoformat()
    }
```

## 🚀 Deployment

### Production Considerations

1. **Environment Variables**
   - Use secure secrets management
   - Never commit API keys to version control
   - Use different keys for development/production

2. **Database**
   - Use managed PostgreSQL service
   - Implement proper backup strategies
   - Configure connection pooling

3. **Caching**
   - Use managed Redis service
   - Implement cache invalidation strategies
   - Monitor cache hit rates

4. **Load Balancing**
   - Use reverse proxy (nginx/traefik)
   - Implement health checks
   - Configure auto-scaling

### Docker Production Build

```dockerfile
# Multi-stage build for production
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add type hints where possible
- Write comprehensive docstrings

### Git Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. **Push and create pull request**
   ```bash
   git push origin feature/new-feature
   ```

### Commit Message Convention

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

## 📚 Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Flutter Documentation](https://flutter.dev/docs)

### External APIs
- [OpenAI API](https://platform.openai.com/docs)
- [Google Gemini API](https://ai.google.dev/docs)
- [OpenWeatherMap API](https://openweathermap.org/api)
- [Cloudinary API](https://cloudinary.com/documentation)

### Tools
- [Postman](https://www.postman.com/) - API testing
- [pgAdmin](https://www.pgadmin.org/) - PostgreSQL management
- [Redis Commander](https://github.com/joeferner/redis-commander) - Redis management

## 🆘 Troubleshooting

### Common Issues

1. **Service won't start**
   - Check Docker logs: `docker-compose logs [service-name]`
   - Verify environment variables
   - Check port conflicts

2. **Database connection issues**
   - Verify PostgreSQL is running
   - Check connection string
   - Ensure database exists

3. **API Gateway routing issues**
   - Check service URLs in docker-compose.yml
   - Verify services are healthy
   - Check network connectivity

4. **YOLO model issues**
   - Ensure model file exists in models/ directory
   - Check model file permissions
   - Verify model format

### Debug Commands

```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs -f [service-name]

# Access service shell
docker-compose exec [service-name] bash

# Check network connectivity
docker-compose exec gateway-api ping auth-service

# Test API endpoints
curl http://localhost:8000/health
```

## 📞 Support

For questions and support:
- Create an issue on GitHub
- Check the troubleshooting section
- Review service-specific documentation
- Consult the API documentation at `/docs` endpoints
