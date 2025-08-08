# 🔑 AnkhAi API Anahtarları Rehberi

Bu dosya AnkhAi projesi için gerekli tüm API anahtarlarını ve nasıl alınacağını açıklar.

## 📋 Gerekli API Anahtarları Listesi

### ✅ 1. OpenWeatherMap API (TAMAMLANDI)
- **API Anahtarı:** `caa3020901fab7bb37dd8155d7be1d1c`
- **Durum:** ✅ Aktif
- **Kullanım:** Hava durumu verileri
- **Limit:** Günlük 1000 istek (ücretsiz)

### 🔑 2. OpenAI API Key
- **Durum:** ❌ Eksik
- **Kullanım:** AI önerileri, stil açıklamaları
- **Nasıl Alınır:**
  1. [OpenAI Platform](https://platform.openai.com/) sitesine gidin
  2. "Sign Up" ile kayıt olun
  3. "API Keys" bölümüne gidin
  4. "Create new secret key" tıklayın
  5. Anahtarı kopyalayın
- **Limit:** Ücretsiz tier - $5 kredi

### 🔑 3. Google Gemini API Key
- **Durum:** ❌ Eksik
- **Kullanım:** AI önerileri, alternatif LLM
- **Nasıl Alınır:**
  1. [Google AI Studio](https://makersuite.google.com/app/apikey) sitesine gidin
  2. Google hesabınızla giriş yapın
  3. "Create API Key" tıklayın
  4. Anahtarı kopyalayın
- **Limit:** Ücretsiz tier - aylık 15 istek/dakika

### 🔑 4. Cloudinary Credentials
- **Durum:** ❌ Eksik
- **Kullanım:** Resim yükleme ve depolama
- **Nasıl Alınır:**
  1. [Cloudinary](https://cloudinary.com/) sitesine gidin
  2. "Sign Up For Free" ile kayıt olun
  3. Dashboard'da şu bilgileri bulun:
     - Cloud Name
     - API Key
     - API Secret
- **Limit:** Ücretsiz tier - 25 kredi/ay

### 🔑 5. Firebase Credentials
- **Durum:** ❌ Eksik
- **Kullanım:** Resim yükleme (alternatif)
- **Nasıl Alınır:**
  1. [Firebase Console](https://console.firebase.google.com/) sitesine gidin
  2. "Create a project" ile yeni proje oluşturun
  3. "Storage" bölümüne gidin
  4. Service account key oluşturun
- **Limit:** Ücretsiz tier - 5GB depolama

## 📝 API Anahtarlarını Sisteme Ekleme

### 1. .env Dosyasını Güncelleyin

```bash
# Mevcut .env dosyasını düzenleyin
nano .env
```

### 2. API Anahtarlarını Ekleyin

```env
# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Google Gemini Configuration
GEMINI_API_KEY=your-gemini-api-key-here

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Firebase Configuration
FIREBASE_STORAGE_BUCKET=your-project-id.appspot.com
```

### 3. Servisleri Yeniden Başlatın

```bash
# Tüm servisleri yeniden başlatın
docker-compose restart
```

## 🧪 Test Etme

### Weather Service Test
```bash
# Token alın
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}' \
  | jq -r '.[0].access_token')

# Hava durumu alın
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/weather/Istanbul"
```

### AI Recommendation Test
```bash
# AI önerisi alın
curl -X POST "http://localhost:8000/recommendations/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "weather_condition": "sunny",
    "temperature": 25,
    "occasion": "casual"
  }'
```

## 🔒 Güvenlik Notları

1. **API anahtarlarını asla GitHub'a push etmeyin**
2. **.env dosyası .gitignore'da olmalı**
3. **Production'da environment variables kullanın**
4. **API anahtarlarını düzenli olarak rotate edin**

## 📊 Durum Takibi

- [x] OpenWeatherMap API
- [ ] OpenAI API
- [ ] Google Gemini API
- [ ] Cloudinary Credentials
- [ ] Firebase Credentials

## 🆘 Sorun Giderme

### API Anahtarı Çalışmıyor
1. Anahtarın doğru kopyalandığından emin olun
2. Servisleri yeniden başlatın: `docker-compose restart`
3. Logları kontrol edin: `docker-compose logs [service-name]`

### Rate Limit Hatası
1. API kullanım limitlerini kontrol edin
2. Cache mekanizmasını kullanın
3. Gerekirse ücretli plana geçin

---

**Son Güncelleme:** 8 Ağustos 2024
**Proje:** AnkhAi Fashion Assistant
