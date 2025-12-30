# Voice Transcription Module

**Speech-to-Text Service für Adizon V2**

Ermöglicht Voice Message Support über selbst-gehosteten Whisper Server.

---

## 🎯 Features

- ✅ **Flexible API Integration** - REST API, Python Library, gRPC ready
- ✅ **Retry Logic** - Automatische Wiederholungen mit exponential backoff
- ✅ **Multi-Format Support** - OGG, MP3, WAV, M4A
- ✅ **Error Handling** - User-friendly Error Messages
- ✅ **Cleanup** - Automatisches Löschen von Temp-Files
- ✅ **Language Support** - Deutsch/Englisch, Auto-Detection
- ✅ **Production-Ready** - Timeout Handling, Logging, Monitoring

---

## 📦 Installation

**Keine zusätzlichen Dependencies nötig!**

Das Modul nutzt bereits vorhandene Packages:
- `requests` - für HTTP API Calls (bereits in `requirements.txt`)

---

## ⚙️ Configuration

### Environment Variables

```bash
# Whisper API URL (Required)
WHISPER_API_URL=https://trooper.ai/whisper

# Optional: API Key für Authentication
WHISPER_API_KEY=your-api-key-here

# Optional: Timeout (default: 30 seconds)
WHISPER_TIMEOUT=30

# Optional: Retry Count (default: 3)
WHISPER_RETRY_COUNT=3
```

### Check if Enabled

```python
from tools.transcription import get_transcriber

transcriber = get_transcriber()
if transcriber.is_enabled():
    print("✅ Whisper transcription available")
else:
    print("⚠️ Whisper disabled (no WHISPER_API_URL)")
```

---

## 🚀 Usage

### Basic Transcription

```python
from tools.transcription import get_transcriber

# Get singleton instance
transcriber = get_transcriber()

# Transcribe audio file
result = transcriber.transcribe("/tmp/audio.ogg")

print(f"Text: {result.text}")
print(f"Language: {result.language}")
print(f"Duration: {result.duration}s")
print(f"Confidence: {result.confidence}")
```

### With Custom Language

```python
# Force English transcription
result = transcriber.transcribe("/tmp/audio.wav", language="en")
```

### Error Handling

```python
from tools.transcription import TranscriptionError, WhisperAPIError, WhisperTimeoutError

try:
    result = transcriber.transcribe("/tmp/audio.mp3")
except WhisperTimeoutError:
    print("⏱️ Transcription timeout - audio too long")
except WhisperAPIError as e:
    print(f"❌ Whisper API error: {e}")
except TranscriptionError as e:
    print(f"❌ Transcription failed: {e}")
```

---

## 🏗️ Architecture

### Flow

```
Audio File → Transcriber → Whisper API → Transcript
                ↓
           Retry Logic
           Timeout Check
           Error Handling
```

### Integration in Chat-Adapters

**Telegram:**
```python
# telegram_adapter.py
def _handle_voice_message(self, voice_data: dict) -> str:
    audio_path = self._download_voice_file(voice_data["file_id"])
    
    from tools.transcription import get_transcriber
    transcriber = get_transcriber()
    result = transcriber.transcribe(audio_path)
    
    os.remove(audio_path)  # Cleanup
    return result.text
```

**Slack:**
```python
# slack_adapter.py
def _handle_audio_file(self, file_data: dict) -> str:
    audio_path = self._download_audio_file(file_data["url_private"])
    
    from tools.transcription import get_transcriber
    transcriber = get_transcriber()
    result = transcriber.transcribe(audio_path)
    
    os.remove(audio_path)  # Cleanup
    return result.text
```

---

## 🧪 Testing

Run tests:
```bash
pytest tests/test_whisper_transcriber.py -v
```

**Test Coverage:** 15 Tests
- Initialization & Config
- Successful Transcription
- Retry Logic mit Exponential Backoff
- Error Handling (Timeout, API Error, Empty Response)
- Custom Language Parameter
- API Key Authentication
- Singleton Pattern

---

## 📊 API Response Format

### Expected Whisper API Response

```json
{
  "text": "Das ist der transkribierte Text",
  "language": "de",
  "confidence": 0.95
}
```

**Alternative Format** (auch unterstützt):
```json
{
  "transcription": "Transcribed text here",
  "lang": "en"
}
```

---

## 🔧 Whisper API Specification

### Current Implementation (REST API)

**Endpoint:** `POST {WHISPER_API_URL}/transcribe`

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file`: Audio file (binary)
  - `language`: Language code (e.g., "de", "en")
- Headers:
  - `Authorization: Bearer {WHISPER_API_KEY}` (optional)

**Response:**
- Status: `200 OK`
- Body: JSON mit `text`, `language`, `confidence`

### Flexible API Adapter

Die `_call_whisper_api()` Methode kann einfach angepasst werden für:
- **gRPC** - Binary Protocol
- **Python Library** - Direkter Import von `whisper`
- **Custom REST Format** - Andere JSON-Struktur

---

## ⚡ Performance

**Typische Zeiten:**
- 10s Audio → ~2-5s Transcription
- 30s Audio → ~5-10s Transcription
- 60s Audio → ~10-15s Transcription

**Bottleneck:** GPU auf Whisper Server, nicht Netzwerk

**Retry Timing:**
- Attempt 1: Sofort
- Attempt 2: +1s Delay
- Attempt 3: +2s Delay
- Attempt 4: +4s Delay

---

## 🚨 Error Messages

**User-Friendly Errors** (via `WebhookParseError` in Chat-Adapters):

- Whisper disabled: *"🚫 Sprachnachrichten sind aktuell nicht verfügbar. Bitte schreibe eine Textnachricht."*
- Transcription failed: *"❌ Sprachnachricht konnte nicht verarbeitet werden. Bitte versuche es nochmal oder schreibe eine Textnachricht."*

---

## 📈 Monitoring

### Logs

```
🎤 Transcribing audio (attempt 1/3)...
✅ Transcription successful: 125 chars
⏱️  Timeout on attempt 1/3
❌ API Error on attempt 2/3: 503 Service Unavailable
🗑️  Temp file deleted: /tmp/telegram_ABC123_a1b2c3d4.ogg
```

### Metrics to Track

- Transcription Success Rate
- Average Transcription Duration
- Retry Rate
- Error Types (Timeout vs API Error)

---

## 🔐 Security

- ✅ **Temp Files:** Sofort nach Transcription gelöscht
- ✅ **No Logging:** Transcripts werden NICHT geloggt (GDPR)
- ✅ **API Key:** Optional über Environment Variable
- ✅ **Unique Filenames:** Verhindert Collisions bei Multi-User

---

## 🚀 Deployment

### Railway / Heroku

```bash
# Set Environment Variables
railway env set WHISPER_API_URL=https://trooper.ai/whisper
railway env set WHISPER_API_KEY=your-key

# Check /tmp write permissions (should work on Railway)
railway run python -c "import os; open('/tmp/test', 'w').close(); os.remove('/tmp/test'); print('✅ /tmp writable')"
```

### Docker

```dockerfile
# Ensure /tmp is writable
RUN mkdir -p /tmp && chmod 777 /tmp

# Set environment in docker-compose.yml or Dockerfile
ENV WHISPER_API_URL=https://trooper.ai/whisper
```

---

## 🔮 Future Enhancements

- [ ] **Queue System** - Celery/Redis für async processing
- [ ] **Transcript Cache** - Redis Cache für wiederholte Anfragen
- [ ] **Language Auto-Detection Feedback** - User bekommt erkannte Sprache
- [ ] **Confidence Score Threshold** - Warn bei niedrigem Score
- [ ] **Fallback to Cloud** - OpenAI Whisper API wenn trooper.ai down
- [ ] **Streaming Support** - Real-time transcription für lange Audio

---

## 📞 Support

**Für Fragen:**
- Code: `tools/transcription/whisper_transcriber.py`
- Tests: `tests/test_whisper_transcriber.py`
- Integration: Chat-Adapters (`telegram_adapter.py`, `slack_adapter.py`)

---

**Status:** ✅ Production-Ready  
**Version:** 1.0.0  
**Erstellt:** 30.12.2025

