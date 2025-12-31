# Adizon Migration Log: LangGraph (Dezember 2025)

## TL;DR für LLMs
```
Entrypoint: server.py (nicht main.py!)
Graph: graph/builder.py -> StateGraph mit Checkpointing
State: graph/state.py -> AdizonState TypedDict
Persistence: PostgreSQL (nicht Redis!)
Legacy: Alles in _legacy/ -> IGNORIEREN
```

---

## Architektur-Wechsel

### Vorher (Legacy)
```
main.py
├── Monolithischer FastAPI Server
├── Redis für Memory & Session State
├── Spaghetti-Code mit direkten LLM-Calls
└── Kein strukturiertes State Management
```

### Nachher (LangGraph)
```
server.py                    # FastAPI Entrypoint
├── graph/
│   ├── state.py            # TypedDict: AdizonState
│   ├── nodes.py            # Auth, Router, Chat, CRM, SessionGuard
│   └── builder.py          # StateGraph Kompilierung
├── tools/crm/              # CRM Tools (Twenty/Zoho)
├── tools/chat/             # Chat Adapters (Telegram/Slack)
├── api/users.py            # Admin REST API
└── PostgreSQL Checkpointing (ersetzt Redis)
```

---

## Neue Entrypoints

### Lokal starten
```bash
# 1. Postgres starten
docker-compose up -d

# 2. Virtualenv aktivieren
source venv/bin/activate

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Migrationen ausführen
alembic upgrade head

# 5. Server starten
python server.py
# oder: uvicorn server:app --reload
```

### Docker/Railway
```bash
# Automatisch via nixpacks.toml:
uvicorn server:app --host 0.0.0.0 --port $PORT
```

### Health Check
```bash
curl http://localhost:8000/health
# {"status":"healthy","checkpointer":"postgres","graph":"ready"}
```

---

## Dependency Changes

### Hinzugefügt
| Package | Version | Zweck |
|---------|---------|-------|
| `langgraph` | >=0.2.60 | Graph-basiertes Agent Framework |
| `langgraph-checkpoint-postgres` | >=2.0.0 | PostgreSQL State Persistence |
| `psycopg[binary,pool]` | >=3.2.0 | Moderner PostgreSQL Driver (psycopg3) |

### Entfernt
| Package | Grund |
|---------|-------|
| `redis` | State wird jetzt über LangGraph Checkpointing (PostgreSQL) gehandelt |
| `psycopg2-binary` | Ersetzt durch psycopg3 |

### Wichtige Kompatibilität
- **Pydantic V2**: Bereits im Einsatz (2.10.4)
- **Python**: 3.12+ erforderlich
- **SQLAlchemy**: Nutzt jetzt `postgresql+psycopg://` Dialekt

---

## State Management

### AdizonState (graph/state.py)
```python
class AdizonState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user: Optional[User]           # Aus DB
    user_id: str                   # Platform ID
    platform: str                  # "telegram" | "slack"
    chat_id: str                   # Für Antworten
    session_state: Literal["ACTIVE", "IDLE"]
    dialog_state: dict             # Tool-Kontext
    last_action_context: dict      # Undo-Info
```

### Checkpointing
- **Speicherort**: PostgreSQL (gleiche DB wie Users)
- **Thread-ID**: `user_id` (z.B. "telegram:123456")
- **Persistenz**: Automatisch nach jedem Graph-Invoke

---

## Legacy Code

Alter Code wurde nach `_legacy/` verschoben:
- `_legacy/main.py` - Alter Entrypoint
- `_legacy/memory.py` - Redis Memory (nicht mehr in Verwendung)
- `_legacy/agents/` - Alte Agent-Implementierungen

**⚠️ NICHT VERWENDEN** - Nur als Referenz behalten.

---

## Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/webhook/{platform}` | POST | Chat Webhook (telegram/slack) |
| `/api/users` | GET/POST | Admin User Management |
| `/api/users/{id}` | GET/PATCH/DELETE | User CRUD |
| `/api/users/{id}/approve` | POST | User freischalten |
| `/health` | GET | Health Check |
| `/` | GET | API Info |

---

## Bekannte Einschränkungen

1. **Audio/Voice**: Whisper-Transcription noch nicht in LangGraph integriert
2. **Multi-Turn Undo**: Undo funktioniert nur für die letzte Aktion im aktuellen Turn
3. **Parallel Tool Calls**: ReAct Agent führt Tools sequentiell aus

---

*Erstellt: 31.12.2025*
*LangGraph Version: 0.2.60+*

