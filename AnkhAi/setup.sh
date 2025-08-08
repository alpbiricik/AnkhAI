#!/bin/bash

# AnkhAi Setup Script
# This script helps set up the AnkhAi fashion assistant project

set -e

echo "🚀 Welcome to AnkhAi - AI-Powered Fashion Assistant"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your API keys before starting services"
    echo "   Required API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - GEMINI_API_KEY" 
    echo "   - OPENWEATHER_API_KEY"
    echo "   - CLOUDINARY_* (optional)"
    echo "   - FIREBASE_* (optional)"
    echo ""
    echo "🔑 You can get these API keys from:"
    echo "   - OpenAI: https://platform.openai.com/api-keys"
    echo "   - Google Gemini: https://makersuite.google.com/app/apikey"
    echo "   - OpenWeatherMap: https://openweathermap.org/api"
    echo "   - Cloudinary: https://cloudinary.com/console"
    echo "   - Firebase: https://console.firebase.google.com/"
    echo ""
    read -p "Press Enter after you've configured your .env file..."
else
    echo "✅ .env file already exists"
fi

# Create models directory for YOLO
if [ ! -d models ]; then
    echo "📁 Creating models directory..."
    mkdir -p models
    echo "⚠️  Please download YOLOv8 model to models/ directory"
    echo "   You can download it from: https://github.com/ultralytics/ultralytics"
    echo "   Or run: wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O models/yolov8n.pt"
fi

# Create firebase credentials placeholder
if [ ! -f firebase-credentials.json ]; then
    echo "📄 Creating Firebase credentials placeholder..."
    echo '{"type": "service_account", "project_id": "your-project-id"}' > firebase-credentials.json
    echo "⚠️  Please replace firebase-credentials.json with your actual Firebase service account key"
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "✅ AnkhAi is starting up!"
echo "=================================================="
echo "📊 Service Status:"
echo "   - API Gateway: http://localhost:8000"
echo "   - Auth Service: http://localhost:8001"
echo "   - Outfit Service: http://localhost:8002"
echo "   - Celebrity Service: http://localhost:8003"
echo "   - Weather Service: http://localhost:8004"
echo "   - Recommendation Service: http://localhost:8005"
echo "   - Media Service: http://localhost:8006"
echo "   - PostgreSQL: localhost:5432"
echo "   - Redis: localhost:6379"
echo ""
echo "📚 API Documentation:"
echo "   - Gateway API: http://localhost:8000/docs"
echo "   - Individual services: http://localhost:8001-8006/docs"
echo ""
echo "🔍 Check service health:"
echo "   curl http://localhost:8000/health"
echo ""
echo "🛑 To stop services:"
echo "   docker-compose down"
echo ""
echo "📝 To view logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🎉 Happy styling with AnkhAi!"
