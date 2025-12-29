# Adizon V2 - Architektur-Übersicht

## Überblick
Adizon V2 ist ein Multi-Plattform AI-Assistent für KMUs, der Chat-Plattformen (Telegram, Slack) mit CRM-Systemen (Twenty, Zoho) verbindet. Die Architektur folgt einem modularen Adapter-Pattern.

## Architektur-Übersicht (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNE SYSTEME                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Telegram │  │  Slack   │  │ MS Teams │  │ Twenty   │  │  Zoho    │ │
│  │   Bot    │  │   Bot    │  │ (Future) │  │   CRM    │  │  CRM     │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────▲─────┘  └────▲─────┘ │
└───────┼─────────────┼─────────────┼──────────────┼──────────────┼───────┘
        │             │             │              │              │
        │ POST        │ POST        │ POST         │              │
        └─────────────┴─────────────┴──────────────┼──────────────┼────┐
                                                   │              │    │
┌───────────────────────────────────────────────────┼──────────────┼────┘
│                    FASTAPI SERVER (main.py)       │              │     
│  ┌─────────────────────────────────────────┐     │              │     
│  │    /webhook/{platform} Endpoint         │     │              │     
│  └───────────────┬─────────────────────────┘     │              │     
│                  │                               │              │     
│  ┌───────────────▼─────────────────────────┐     │              │     
│  │         Message Handler                 │     │              │     
│  └───────────────┬─────────────────────────┘     │              │     
│                  │                               │              │     
│  ┌───────────────▼─────────────────────────┐     │              │     
│  │      Session State Check (Redis)        │     │              │     
│  └────┬─────────────────────────────────┬──┘     │              │     
│       │ IDLE                            │ACTIVE  │              │     
│  ┌────▼──────────┐                 ┌────▼────┐   │              │     
│  │    Intent     │                 │   Skip  │   │              │     
│  │   Detection   │                 │  Router │   │              │     
│  └────┬──────────┘                 └────┬────┘   │              │     
│       │                                 │        │              │     
│   ┌───┴────┬─────────────────────────────┘        │              │     
└───┼────────┼──────────────────────────────────────┼──────────────┼────┘
    │ CHAT   │ CRM                                  │              │     
┌───┴────┐ ┌─▼────────────────────────────────────┐ │              │     
│  Chat  │ │          CRM Handler                 │ │              │     
│ Handler│ │   (LangChain Agent + Tools)          │ │              │     
└───┬────┘ └─┬─────────────────┬──────────────────┘ │              │     
    │        │                 │                    │              │     
    │    ┌───▼────────┐   ┌────▼─────────────────┐  │              │     
    │    │  Session   │   │    CRM Tools         │  │              │     
    │    │   Guard    │   └────┬─────────────────┘  │              │     
    │    └───┬────────┘        │                    │              │     
    └────────┴─────────────────┼────────────────────┼──────────────┼────┐
                               │                    │              │    │
┌──────────────────────────────┼────────────────────┼──────────────┼────┘
│                TOOLS LAYER   │                    │              │     
│  ┌───────────────────────────▼──────────┐  ┌──────▼──────────────▼───┐
│  │      Chat Adapters                   │  │    CRM Adapters         │
│  │  ┌──────────────┐  ┌──────────────┐  │  │  ┌────────┐  ┌────────┐│
│  │  │  Telegram    │  │    Slack     │  │  │  │ Twenty │  │  Zoho  ││
│  │  │   Adapter    │  │   Adapter    │  │  │  │Adapter │  │ Adapter││
│  │  └──────────────┘  └──────────────┘  │  │  └───┬────┘  └───┬────┘│
│  │  ┌──────────────────────────────────┐│  │  ┌───▼────────────▼────┐│
│  │  │ Chat Interface: StandardMessage  ││  │  │  Field Mapping      ││
│  │  └──────────────────────────────────┘│  │  │  Loader (YAML)      ││
│  └───────────────────────────────────────┘  └───┴────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                               │                                          
┌──────────────────────────────┼──────────────────────────────────────────┐
│                 UTILS LAYER  │                                          │
│  ┌───────────────────────────▼────────────────────────────────────────┐│
│  │  Memory System (Redis)           Agent Config (YAML Loader)        ││
│  │  • Conversation History           • System Prompts                 ││
│  │  • Session State (ACTIVE/IDLE)    • Model Settings                 ││
│  │  • Undo Context                   • LLM Parameters                 ││
│  └───────────────────────────────────────────────────────────────────┘│
│  ┌───────────────────────────────────────────────────────────────────┐│
│  │                    Redis Database                                 ││
│  │           • TTL Management  • Deduplication  • Caching            ││
│  └───────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
                               │                                          
┌──────────────────────────────┼──────────────────────────────────────────┐
│           CONFIGURATION      │                                          │
│  ┌───────────────────────────▼────────────────────────────────────────┐│
│  │                    YAML Config Files (prompts/)                    ││
│  │  • chat_handler.yaml      • crm_handler.yaml                       ││
│  │  • session_guard.yaml     • intent_detection.yaml                  ││
│  └────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

## Architektur-Diagramm (Mermaid)

> **Hinweis:** Falls das Mermaid-Diagramm nicht angezeigt wird, installiere die "Markdown Preview Mermaid Support" Extension in VS Code/Cursor, oder verwende die ASCII-Darstellung oben.

```mermaid
flowchart TB
    telegram[Telegram Bot]
    slack[Slack Bot]
    twentyCRM[Twenty CRM]
    zohoCRM[Zoho CRM]
    
    webhook[Unified Webhook]
    intent[Intent Detection]
    sessionCheck[Session Check]
    
    chatHandler[Chat Handler]
    crmHandler[CRM Handler]
    sessionGuard[Session Guard]
    
    chatAdapters[Chat Adapters]
    crmAdapters[CRM Adapters]
    
    memory[Memory Redis]
    config[Agent Config]
    redis[(Redis DB)]
    
    telegram -->|POST| webhook
    slack -->|POST| webhook
    
    webhook --> sessionCheck
    sessionCheck -->|IDLE| intent
    sessionCheck -->|ACTIVE| crmHandler
    
    intent -->|CHAT| chatHandler
    intent -->|CRM| crmHandler
    
    chatHandler --> chatAdapters
    crmHandler --> crmAdapters
    crmHandler --> sessionGuard
    
    chatAdapters --> telegram
    chatAdapters --> slack
    
    crmAdapters --> twentyCRM
    crmAdapters --> zohoCRM
    
    crmHandler --> memory
    sessionGuard --> memory
    memory --> redis
    
    chatHandler --> config
    crmHandler --> config
```

## Komponenten-Beschreibung

### 1. Entry Point: `main.py`
Der zentrale FastAPI-Server, der alle eingehenden Requests verarbeitet.

**Hauptfunktionen:**
- **Unified Webhook**: `/webhook/{platform}` - Ein Endpoint für alle Chat-Plattformen
- **Intent Detection**: Klassifiziert Messages als `CHAT` oder `CRM`
- **Session State Management**: Prüft ob User in aktiver CRM-Session ist (ACTIVE/IDLE)
- **Message Routing**: Leitet zu Chat- oder CRM-Handler weiter
- **Duplicate Event Prevention**: Redis-basierte Deduplication für Telegram/Slack

**Wichtige Endpoints:**
- `POST /webhook/{platform}` - Unified webhook für alle Plattformen
- `POST /telegram-webhook` - Legacy Telegram endpoint
- `POST /adizon` - Lokaler Test-Endpoint
- `GET /` - Health check

### 2. Agents Layer (`agents/`)
KI-Agenten, die verschiedene Aufgaben übernehmen.

#### Chat Handler (`agents/chat_handler.py`)
- Einfache Konversationen und Smalltalk
- Verwendet OpenAI API direkt
- YAML-basierte Konfiguration

#### CRM Handler (`agents/crm_handler.py`)
- LangChain-basierter Agent mit Tool-Calling
- Zugriff auf CRM-Tools (search, create, etc.)
- Conversation Memory Integration
- Datums-Awareness (Vienna Timezone)

#### Session Guard (`agents/session_guard.py`)
- Entscheidet nach jeder CRM-Interaktion ob Session aktiv bleibt
- Verhindert unnötige Intent-Detection bei laufenden Gesprächen
- Gibt `ACTIVE` oder `IDLE` zurück

### 3. Tools Layer (`tools/`)

#### Chat Adapters (`tools/chat/`)
Abstrahieren verschiedene Chat-Plattformen für einheitliche Verarbeitung.

**Interface** (`interface.py`):
- `StandardMessage`: Plattform-agnostisches Message-Format
- `ChatAdapter`: Abstract Base Class mit `parse_incoming()` und `send_message()`

**Implementierungen:**
- `telegram_adapter.py`: Telegram Bot API Integration
- `slack_adapter.py`: Slack Events API Integration

**Features:**
- Unified Message Format
- Platform-specific parsing
- Automatic error handling
- Event deduplication support

#### CRM Adapters (`tools/crm/`)
Abstrahieren verschiedene CRM-Systeme für einheitliche Operationen.

**Interface** (`interface.py`):
- `CRMInterface`: Protocol mit `search_contacts()` und `create_contact()`

**Implementierungen:**
- `twenty_adapter.py`: Twenty CRM GraphQL Integration
- `zoho_adapter.py`: Zoho CRM REST API Integration

**Features:**
- Unified CRM operations
- Dynamic field mapping (YAML)
- Fuzzy search für Kontakte
- Automatic field enrichment
- Support für Custom Fields

**Field Mapping System:**
- `field_mapping_loader.py`: YAML-basiertes Field-Mapping
- `field_mappings/`: CRM-spezifische Konfigurationen
  - `twenty.yaml`: Twenty CRM Fields
  - `zoho.yaml`: Zoho CRM Fields

### 4. Utils Layer (`utils/`)

#### Memory (`utils/memory.py`)
Redis-basierte Conversation History und Session State Management.

**Features:**
- LangChain `ConversationBufferMemory` mit Redis Backend
- Session State Tracking (ACTIVE/IDLE)
- Automatic TTL (Active: 10 Min, Idle: 24h)
- Undo Context für CRM-Operationen
- Kill Switch für Session Reset

**Funktionen:**
- `get_conversation_memory(user_id)`: Lädt Chat History
- `set_session_state(user_id, state)`: Setzt State mit TTL
- `get_session_state(user_id)`: Liest aktuellen State
- `clear_user_session(user_id)`: Löscht alles (Neustart)
- `save_undo_context()`: Speichert letzte Aktion
- `get_undo_context()`: Liest Undo-Info

#### Agent Config (`utils/agent_config.py`)
YAML-basierte Konfiguration für LLM-Settings und Prompts.

**Features:**
- Environment Variable Substitution (`${VAR_NAME}`)
- Template Variable Rendering (`{user_name}`, `{current_date}`)
- LRU Caching für Performance
- Validation für LLM-Parameter

**Funktionen:**
- `load_agent_config(name)`: Lädt YAML-Config
- `get_system_prompt(**vars)`: Rendert System Prompt
- `get_model_config()`: LLM Model Settings
- `get_parameters()`: Temperature, Top-P, etc.
- `get_agent_config()`: Agent-spezifische Settings

### 5. Configuration (`prompts/`)
YAML-Dateien mit System-Prompts, Model-Settings und Parametern.

**Konfigurationsdateien:**
- `chat_handler.yaml`: Chat-Agent Konfiguration
- `crm_handler.yaml`: CRM-Agent Konfiguration
- `session_guard.yaml`: Session Guard Settings
- `intent_detection.yaml`: Intent Classification

**Struktur:**
```yaml
name: "Agent Name"
version: "1.0"
description: "..."

model:
  base_url: "${OPENROUTER_BASE_URL}"
  api_key: "${OPENROUTER_API_KEY}"
  name: "gpt-4"

parameters:
  temperature: 0.7
  max_tokens: 1000

system_prompt: |
  Du bist {user_name}...
```

## Datenfluss

### 1. Incoming Message Flow
```
Chat-Plattform (Telegram/Slack)
  ↓ POST Webhook
FastAPI Unified Webhook Handler
  ↓ Parse mit Chat-Adapter
StandardMessage (Platform-agnostic)
  ↓
Message Handler
```

### 2. Session & Routing
```
Session State Check (Redis)
  ├─ IDLE → Intent Detection
  │           ├─ CHAT → Chat Handler
  │           └─ CRM → CRM Handler
  └─ ACTIVE → CRM Handler (Sticky Session)
```

### 3. CRM Processing Flow
```
CRM Handler (LangChain Agent)
  ↓
CRM Tools (via Factory)
  ↓
CRM Adapter (Twenty/Zoho)
  ↓
External CRM API
  ↓
Response → Session Guard
  ↓
State Update (ACTIVE/IDLE)
```

### 4. Response Flow
```
Agent Response
  ↓
Message Handler
  ↓
Chat Adapter (format & send)
  ↓
Chat-Plattform (User erhält Antwort)
```

## Design Patterns

### Adapter Pattern
Abstrahiert externe Systeme (Chat-Plattformen, CRM-Systeme) hinter einheitlichen Interfaces.

**Vorteile:**
- Neue Plattformen einfach hinzufügbar
- Core-Logic bleibt unverändert
- Testbarkeit durch Mocking

### Factory Pattern
Dynamische Erstellung von Adaptern und Tools basierend auf Kontext.

**Implementierungen:**
- `get_chat_adapter(platform)`: Liefert passenden Chat-Adapter
- `get_crm_tools_for_user(user_id)`: Erstellt CRM-Tools für User

### Strategy Pattern
Verschiedene Agents für verschiedene Intents (Chat vs. CRM).

**Vorteile:**
- Klare Trennung der Verantwortlichkeiten
- Spezialisierte LLM-Prompts pro Agent
- Einfache Erweiterung um neue Agents

### State Pattern
Session State Management für Sticky Sessions (ACTIVE/IDLE).

**States:**
- `IDLE`: Normale Intent Detection
- `ACTIVE`: Direkt zum CRM Handler (kein Routing)

**Vorteile:**
- Natürlicherer Gesprächsfluss
- Keine unnötigen LLM-Calls
- Automatic Timeout bei Inaktivität

## Skalierbarkeit & Performance

### Redis für State & Memory
- Persistent Storage für Conversations
- Automatic TTL für Cleanup
- Deduplication für Webhook Events
- Horizontal skalierbar

### Caching
- YAML Configs werden gecached (LRU)
- Field Mappings werden beim Start geladen
- Redis für Session States

### Async Processing
- FastAPI mit async/await
- Non-blocking Webhook Processing
- Parallel Tool Execution (LangChain)

## Erweiterbarkeit

### Neue Chat-Plattform hinzufügen
1. Neue Adapter-Klasse erstellen (erbt von `ChatAdapter`)
2. `parse_incoming()` und `send_message()` implementieren
3. In Factory registrieren
4. Webhook konfigurieren → Fertig!

### Neues CRM-System hinzufügen
1. Neue Adapter-Klasse erstellen (implementiert `CRMInterface`)
2. Field-Mapping YAML erstellen
3. In Factory registrieren
4. Environment Variables setzen → Fertig!

### Neuen Agent hinzufügen
1. Agent-Datei in `agents/` erstellen
2. YAML-Config in `prompts/` erstellen
3. In Intent Detection registrieren (oder neuer Routing-Logic)
4. In Message Handler einbinden → Fertig!

## Sicherheit

### Webhook Verification
- Slack: Signing Secret Verification (implementiert)
- Telegram: Secret Token Support (vorbereitet)

### Environment Variables
- Alle Credentials in Environment Variables
- Keine Secrets im Code
- `.gitignore` für `.env`

### Redis Security
- TTL für alle Keys (keine Leaks)
- Namespaced Keys (`adizon:*`)
- Optional: Redis AUTH via Connection String

## Monitoring & Debugging

### Logging
- Extensive Print-Statements für Debugging
- Request/Response Logging
- Error Tracking mit Tracebacks

### Testing
Umfangreiche Test-Suite in `tests/`:
- Unit Tests für alle Adapter
- Integration Tests für Workflows
- Mock-basierte Tests (keine echten API-Calls)

### Development Tools
- `/adizon` Endpoint für lokales Testing
- Hot-Reload während Development
- Verbose Agent Output (konfigurierbar)

## Deployment

### Requirements
- Python 3.12+
- Redis Server
- Environment Variables (siehe `.env`)

### Production Setup
```bash
# 1. Install Dependencies
pip install -r requirements.txt

# 2. Set Environment Variables
export OPENROUTER_API_KEY="..."
export TELEGRAM_BOT_TOKEN="..."
export SLACK_BOT_TOKEN="..."
export TWENTY_API_KEY="..."
export REDIS_URL="redis://localhost:6379"

# 3. Start Server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Heroku Deployment
- `Procfile` vorhanden
- Redis Add-on konfigurieren
- Config Vars setzen
- `git push heroku main`

## Weitere Dokumentation

- [Feature List](FEATURE-LIST.md) - Alle implementierten Features
- [Troubleshooting](TROUBLESHOOTING.md) - Häufige Probleme & Lösungen
- [Field Enrichment Guide](../Quick%20Reference%20Field%20enrichment.md) - CRM Field-Mapping Details
- [Test README](../tests/README.md) - Test-Suite Dokumentation

