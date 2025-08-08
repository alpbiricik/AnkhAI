# AnkhAi Flutter Frontend

This is the Flutter mobile application for AnkhAi - an AI-powered fashion assistant.

## Features

- User authentication and registration
- Outfit analysis using AI
- Weather-based clothing recommendations
- Celebrity style inspiration
- Personalized outfit suggestions
- Image upload and management

## Setup

### Prerequisites

- Flutter SDK (3.0 or higher)
- Dart SDK
- Android Studio / Xcode (for mobile development)
- API Gateway running on localhost:8000

### Installation

1. **Install Flutter**
   ```bash
   # Follow official Flutter installation guide
   # https://flutter.dev/docs/get-started/install
   ```

2. **Clone and setup**
   ```bash
   cd frontend
   flutter pub get
   ```

3. **Configure API endpoints**
   - Update `lib/config/api_config.dart` with your API Gateway URL
   - Ensure all backend services are running

4. **Run the app**
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── config/
│   ├── api_config.dart
│   └── app_config.dart
├── models/
│   ├── user.dart
│   ├── outfit.dart
│   ├── weather.dart
│   └── recommendation.dart
├── services/
│   ├── auth_service.dart
│   ├── outfit_service.dart
│   ├── weather_service.dart
│   └── recommendation_service.dart
├── screens/
│   ├── auth/
│   ├── home/
│   ├── outfit_analysis/
│   ├── recommendations/
│   └── profile/
├── widgets/
│   ├── common/
│   └── custom/
└── main.dart
```

## Development

### Key Dependencies

- `http`: API communication
- `provider`: State management
- `shared_preferences`: Local storage
- `image_picker`: Image selection
- `flutter_secure_storage`: Secure token storage

### State Management

The app uses Provider pattern for state management:
- `AuthProvider`: User authentication state
- `OutfitProvider`: Outfit analysis and management
- `WeatherProvider`: Weather data and recommendations
- `RecommendationProvider`: AI-generated recommendations

### API Integration

All API calls go through the API Gateway at `localhost:8000`:
- Authentication: `/auth/*`
- Outfit analysis: `/outfits/*`
- Weather data: `/weather/*`
- Recommendations: `/recommendations/*`
- Media upload: `/media/*`

## Building for Production

### Android
```bash
flutter build apk --release
```

### iOS
```bash
flutter build ios --release
```

## Contributing

1. Follow Flutter best practices
2. Use meaningful variable and function names
3. Add comments for complex logic
4. Test on both Android and iOS
5. Ensure responsive design

## Troubleshooting

- **API connection issues**: Check if backend services are running
- **Image upload failures**: Verify media service configuration
- **Authentication errors**: Check JWT token validity
- **Build errors**: Run `flutter clean` and `flutter pub get`
