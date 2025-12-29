# Chat-Adapter System

**Version:** 3.0  
**Status:** ✅ Production-Ready  
**Letzte Aktualisierung:** 29.12.2025

---

## 📋 Übersicht

Das **Chat-Adapter-System** ist eine flexible Architektur, die es Adizon ermöglicht, verschiedene Chat-Plattformen zu unterstützen - analog zum CRM-Adapter-Pattern.

**Konzept:** Jede Chat-Plattform (Telegram, Slack, Teams, WhatsApp, etc.) hat einen eigenen Adapter, der einheitliche `StandardMessage` Objekte erstellt.

```
Webhook → Chat-Adapter → StandardMessage → Adizon Core → Response → Chat-Adapter → Platform
```

---

## 🎯 Features

- ✅ **Plattform-agnostisch** - Adizon Core kennt keine plattform-spezifischen Details
- ✅ **Plug & Play** - Neue Plattform = neuer Adapter (~2-3h Aufwand)
- ✅ **Unified Webhook** - Ein Endpoint für alle Plattformen (`/webhook/{platform}`)
- ✅ **Backwards Compatible** - Legacy `/telegram-webhook` funktioniert weiterhin
- ✅ **Testbar** - Mock-basierte Tests für alle Adapter
- ✅ **Type-Safe** - Abstract Base Class erzwingt Interface-Compliance

---

## 🏗️ Architektur

### Interface (`interface.py`)

```python
class ChatAdapter(ABC):
    @abstractmethod
    def parse_incoming(self, webhook_data: dict) -> StandardMessage
    
    @abstractmethod
    def send_message(self, chat_id: str, text: str) -> bool
    
    @abstractmethod
    def get_platform_name(self) -> str
```

### StandardMessage

```python
@dataclass
class StandardMessage:
    user_id: str          # Platform-prefixed: "telegram:123456"
    user_name: str        # "Max Mustermann"
    text: str             # Message content
    platform: str         # "telegram", "slack", etc.
    chat_id: str          # For sending replies
    raw_data: dict        # Original webhook data
```

---

## 📦 Supported Platforms

| Platform | Status | Adapter | Env Variables |
|----------|--------|---------|---------------|
| **Telegram** | ✅ Live | `telegram_adapter.py` | `TELEGRAM_BOT_TOKEN` |
| **Slack** | ✅ Live | `slack_adapter.py` | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` |
| **MS Teams** | 🔜 Planned | - | - |
| **WhatsApp** | 🔜 Planned | - | - |

---

## 🚀 Quick Start

### 1. Webhook Setup

**Telegram:**
```bash
# Set Webhook URL
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/webhook/telegram"}'
```

**Slack:**
1. Erstelle App: https://api.slack.com/apps
2. Bot Token Scopes: `chat:write`, `channels:history`, `im:history`
3. Event Subscriptions: `message.im`, `message.channels`
4. Request URL: `https://your-domain.com/webhook/slack`

### 2. Environment Variables

```bash
# .env
CHAT_PLATFORM=telegram  # oder slack (default: telegram)

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=abc123...
```

### 3. Test Locally

```bash
# Starte Server
python main.py

# Test Telegram
curl -X POST http://localhost:8000/webhook/telegram \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "chat": {"id": 123},
      "from": {"id": 456, "first_name": "Test"},
      "text": "Hello Adizon"
    }
  }'

# Test Slack
curl -X POST http://localhost:8000/webhook/slack \
  -H "Content-Type: application/json" \
  -d '{
    "type": "event_callback",
    "event": {
      "type": "message",
      "user": "U123",
      "text": "Hello Adizon",
      "channel": "C123"
    }
  }'
```

---

## 🧩 Wie füge ich eine neue Plattform hinzu?

### Schritt 1: Adapter erstellen

```python
# tools/chat/whatsapp_adapter.py

from .interface import ChatAdapter, StandardMessage

class WhatsAppAdapter(ChatAdapter):
    def __init__(self):
        self.api_token = os.getenv("WHATSAPP_API_TOKEN")
        # ... setup
    
    def parse_incoming(self, webhook_data: dict) -> StandardMessage:
        # Parse WhatsApp Webhook Format
        return StandardMessage(
            user_id=f"whatsapp:{phone_number}",
            user_name=contact_name,
            text=message_text,
            platform="whatsapp",
            chat_id=chat_id,
            raw_data=webhook_data
        )
    
    def send_message(self, chat_id: str, text: str) -> bool:
        # Send via WhatsApp API
        ...
    
    def get_platform_name(self) -> str:
        return "whatsapp"
```

### Schritt 2: Factory erweitern

```python
# tools/chat/__init__.py

from .whatsapp_adapter import WhatsAppAdapter

def get_chat_adapter(platform: str) -> ChatAdapter:
    if platform == "telegram":
        return TelegramAdapter()
    elif platform == "slack":
        return SlackAdapter()
    elif platform == "whatsapp":  # NEU
        return WhatsAppAdapter()
    else:
        raise ValueError(f"Unknown platform: {platform}")
```

### Schritt 3: Tests schreiben

```python
# tests/test_whatsapp_adapter.py

def test_parse_whatsapp_webhook():
    adapter = WhatsAppAdapter()
    msg = adapter.parse_incoming(webhook_data)
    assert msg.platform == "whatsapp"
    # ...
```

### Schritt 4: Done! 🎉

Neue Plattform ist jetzt verfügbar via `/webhook/whatsapp`

---

## 🧪 Testing

```bash
# Interface Tests
python tests/test_chat_interface.py

# Telegram Adapter Tests
python tests/test_telegram_adapter.py

# Slack Adapter Tests
python tests/test_slack_adapter.py

# Factory Tests
python tests/test_chat_factory.py

# Alle Chat-Tests
pytest tests/test_chat_*.py -v
```

**Test-Coverage:**
- Interface: 8 Tests
- Telegram: 8 Tests
- Slack: 10 Tests
- Factory: 10 Tests
- **Total: 36 Tests** ✅

---

## 📁 Datei-Struktur

```
tools/chat/
├── __init__.py              # Factory (get_chat_adapter)
├── interface.py             # ChatAdapter ABC + StandardMessage
├── telegram_adapter.py      # Telegram Implementation
├── slack_adapter.py         # Slack Implementation
└── README.md                # Diese Datei

tests/
├── test_chat_interface.py   # Interface Tests
├── test_telegram_adapter.py # Telegram Tests
├── test_slack_adapter.py    # Slack Tests
└── test_chat_factory.py     # Factory Tests
```

---

## 🔧 Troubleshooting

### Problem: "TELEGRAM_BOT_TOKEN not set"

**Lösung:** Prüfe `.env` Datei:
```bash
cat .env | grep TELEGRAM_BOT_TOKEN
```

### Problem: Slack Challenge fehlgeschlagen

**Lösung:** Slack sendet beim Setup einen Challenge. Adizon responded automatisch:
```python
# In main.py bereits implementiert
if platform == "slack":
    challenge = handle_slack_challenge(webhook_data)
    if challenge:
        return JSONResponse(content={"challenge": challenge})
```

### Problem: "Unknown platform: teams"

**Lösung:** Platform ist noch nicht implementiert. Siehe "Wie füge ich eine neue Plattform hinzu?"

---

## 💡 Best Practices

### 1. User-ID Format

Nutze immer Platform-Prefix:
```python
user_id = f"{platform}:{platform_specific_id}"
# Beispiele:
# "telegram:123456"
# "slack:U123456"
# "teams:29:abc-def-123"
```

### 2. Error-Handling

Nutze `WebhookParseError` für Parse-Fehler:
```python
if not webhook_data.get("message"):
    raise WebhookParseError("Missing 'message' field")
```

### 3. Bot Message Loop Prevention

Ignoriere Bot Messages:
```python
if event.get("bot_id"):
    raise WebhookParseError("Ignoring bot message (loop prevention)")
```

### 4. Webhook Validation

Implementiere `validate_webhook()` für Production:
```python
def validate_webhook(self, webhook_data: dict) -> bool:
    # Check Signature/Secret
    return is_valid_signature(webhook_data)
```

---

## 📊 Business Impact

**Vorher:**
- ❌ Fest an Telegram gebunden
- ❌ Neue Plattform = großes Refactoring
- ❌ Kunden ohne Telegram ausgeschlossen

**Nachher:**
- ✅ Plattform-agnostisch
- ✅ Neue Plattform = neuer Adapter (2-3h)
- ✅ Jeder Kunde kann seine bevorzugte Plattform nutzen
- ✅ Enterprise-Ready (Teams-Support möglich)

---

## 🚀 Roadmap

### Phase 1 (✅ Done)
- [x] Interface & StandardMessage
- [x] Telegram Adapter
- [x] Slack Adapter
- [x] Factory Pattern
- [x] Unified Webhook
- [x] Test Suite (36 Tests)

### Phase 2 (🔜 Planned)
- [ ] MS Teams Adapter
- [ ] WhatsApp Business API Adapter
- [ ] Webhook Signature Validation
- [ ] Rich Message Support (Buttons, Cards)

### Phase 3 (💡 Future)
- [ ] Multi-Channel Support (User auf mehreren Plattformen)
- [ ] Platform-specific Features (Slack Slash Commands, etc.)
- [ ] Message Threading & Reactions

---

**Maintainer:** Michael & KI  
**Projekt:** Adizon V2 - AI Sales Agent  
**Version:** 3.0.0

