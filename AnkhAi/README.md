# AnkhAi - AI-Powered Fashion Assistant

AnkhAi is a multi-service AI-powered fashion assistant app that helps users dress like their favorite celebrities by analyzing their wardrobe, weather conditions, and celebrity styles.

## 🏗️ Architecture

The application is built using a microservices architecture with the following components:

### Backend Services
- **auth-service**: User authentication and authorization (JWT)
- **outfit-service**: AI-powered outfit analysis using YOLOv8
- **celebrity-style-service**: Celebrity style data and LLM-powered descriptions
- **weather-service**: Weather data integration via OpenWeatherMap API
- **recommendation-service**: AI-powered outfit recommendations using LLMs
- **media-service**: Image upload and storage management
- **gateway-api**: API Gateway for frontend communication

### Frontend
- **Flutter app**: Cross-platform mobile application

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.9+
- Flutter SDK
- API keys for:
  - OpenWeatherMap
  - OpenAI/Gemini
  - Cloudinary/Firebase Storage

### Running the Application

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AnkhAi
   ```

2. **Environment variables are already configured**
   ```bash
   # API keys are included in .env file:
   # - OpenWeatherMap API: ✅ Configured
   # - OpenAI API: ✅ Configured  
   # - Google Gemini API: ✅ Configured
   # - Cloudinary: ⚠️ Needs configuration
   # - Firebase: ⚠️ Needs configuration
   ```

3. **Start all services**
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - API Gateway: http://localhost:8000
   - Individual services: http://localhost:8001-8007
   - Flutter app: Run `flutter run` in the `frontend/` directory

## 📁 Project Structure

```
AnkhAi/
├── services/
│   ├── auth-service/
│   ├── outfit-service/
│   ├── celebrity-style-service/
│   ├── weather-service/
│   ├── recommendation-service/
│   ├── media-service/
│   └── gateway-api/
├── frontend/
├── docker-compose.yml
├── .env.example
└── README.md
```

## 🔧 Development

Each service is self-contained with its own:
- FastAPI application
- Dockerfile
- Requirements file
- Environment configuration
- Unit tests

### Adding a New Service
1. Create a new directory under `services/`
2. Add FastAPI app with proper structure
3. Create Dockerfile
4. Update docker-compose.yml
5. Add service to API Gateway

## 📚 API Documentation

Each service provides its own API documentation at `/docs` endpoint when running.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.
