# Adizon Architecture

## Übersicht

Adizon ist ein AI-gestützter CRM-Assistent, der über Chat-Plattformen (Telegram, Slack) erreichbar ist. Das System verwendet LangGraph für die Workflow-Orchestrierung und unterstützt verschiedene CRM-Backends (Twenty CRM, Zoho CRM).

---

## Request Flow Diagramm

```mermaid
flowchart TB
    subgraph Input["USER NACHRICHT"]
        A[Telegram / Slack]
    end

    subgraph Webhook["WEBHOOK ENDPOINT<br/>POST /webhook/{platform}"]
        B1[1. Webhook-Signatur validieren]
        B2[2. Platform-Adapter auswählen]
        B3[3. Nachricht zu StandardMessage parsen]
        B4[4. AdizonState initialisieren]
        B1 --> B2 --> B3 --> B4
    end

    subgraph LangGraph["LANGGRAPH PIPELINE<br/>(mit PostgreSQL Checkpointer)"]
        C1[AUTH NODE]
        C2[ROUTER NODE]
        C3[CHAT / CRM NODE]
        C4[SESSION GUARD]
        C1 --> C2 --> C3 --> C4
    end

    subgraph Response["RESPONSE SENDEN"]
        D1[1. AIMessage aus State extrahieren]
        D2[2. Antwort für Platform formatieren]
        D3[3. Via Chat-Adapter senden]
        D1 --> D2 --> D3
    end

    subgraph Output["USER ERHÄLT ANTWORT"]
        E[Telegram / Slack]
    end

    A --> B1
    B4 --> C1
    C4 --> D1
    D3 --> E
```

---

## Detaillierter Node-Flow

```mermaid
flowchart TD
    START([START]) --> AUTH

    subgraph AUTH["AUTH NODE"]
        AUTH_DESC["• User-Lookup<br/>• Registrierung<br/>• Admin-Notify"]
    end

    AUTH --> CHECK{User Status?}

    CHECK -->|"pending / nicht gefunden"| END_PENDING([END<br/>Pending Message])
    CHECK -->|"approved"| ROUTER

    subgraph ROUTER["ROUTER NODE"]
        ROUTER_DESC["• Intent LLM<br/>• CHAT vs CRM"]
    end

    ROUTER --> ROUTE{Routing Decision}

    ROUTE -->|"Session ACTIVE"| CRM
    ROUTE -->|"Intent: CHAT"| CHAT
    ROUTE -->|"Intent: CRM"| CRM

    subgraph CHAT["CHAT NODE"]
        CHAT_DESC["• Smalltalk<br/>• Keine Tools<br/>• Temp: 0.6"]
    end

    subgraph CRM["CRM NODE"]
        CRM_DESC["• ReAct Agent<br/>• Tool Calling<br/>• Temp: 0.1"]
    end

    CHAT --> SESSION_GUARD
    CRM --> SESSION_GUARD

    subgraph SESSION_GUARD["SESSION GUARD"]
        GUARD_DESC["• ACTIVE/IDLE<br/>• Entscheidung"]
    end

    SESSION_GUARD --> END_FINAL([END])
```

---

## Komponenten-Architektur

### 1. Entry Point (server.py)

```mermaid
flowchart LR
    subgraph Server["server.py"]
        subgraph Webhook["Webhook Handler"]
            WH1[Retry Detection]
            WH2[Platform Adapter Selection]
            WH3[Graph Invocation]
        end

        subgraph Lifespan["Lifespan Events"]
            LS1[PostgreSQL Pool Setup]
            LS2[Checkpointer Initialization]
        end

        Health[Health Endpoints]
    end
```

**Schlüsselfunktionen:**
- Webhook-Empfang und Validierung
- Async Message Processing
- State Persistierung via LangGraph Checkpointer

### 2. LangGraph Pipeline (graph/)

```mermaid
flowchart LR
    subgraph Graph["graph/"]
        builder["builder.py<br/>Graph-Kompilierung"]
        state["state.py<br/>AdizonState Definition"]
        nodes["nodes.py<br/>Alle Workflow-Nodes"]
    end
```

**AdizonState Schema:**
```python
AdizonState = {
    "messages": list[BaseMessage],      # Konversationshistorie
    "user": Optional[dict],             # Authentifizierter User
    "user_id": str,                     # Platform-ID (z.B. "telegram:123456")
    "platform": str,                    # "telegram" oder "slack"
    "chat_id": str,                     # Für Antworten
    "session_state": "ACTIVE" | "IDLE", # Session-Modus
    "dialog_state": dict,               # Tool-Kontext
    "last_action_context": dict         # Undo-Tracking
}
```

### 3. Node-Beschreibungen

| Node | Zweck | Konfiguration |
|------|-------|---------------|
| **Auth** | User-Authentifizierung & Registrierung | - |
| **Router** | Intent-Klassifikation (CHAT/CRM) | `prompts/intent_detection.yaml` |
| **Chat** | Einfache Konversation ohne Tools | `prompts/chat_handler.yaml` |
| **CRM** | Business-Logik mit ReAct Agent | `prompts/crm_handler.yaml` |
| **Session Guard** | ACTIVE/IDLE Entscheidung | `prompts/session_guard.yaml` |

### 4. CRM Tools (tools/crm/)

```mermaid
flowchart TB
    subgraph CRM_Tools["tools/crm/"]
        init["__init__.py<br/>Tool Factory & Undo Context"]
        interface["interface.py<br/>CRM Adapter Interface"]
        twenty["twenty_adapter.py<br/>Twenty CRM"]
        zoho["zoho_adapter.py<br/>Zoho CRM"]

        init --> interface
        interface --> twenty
        interface --> zoho
    end
```

**Verfügbare Tools:**
| Tool | Funktion |
|------|----------|
| `search_contacts` | Volltextsuche nach Personen/Firmen |
| `create_contact` | Lead/Person erstellen |
| `create_task` | Aufgabe mit Attribution erstellen |
| `create_note` | Notiz mit Attribution erstellen |
| `undo_last_action` | Letzte Aktion rückgängig machen |
| `update_entity` | Kontaktfelder aktualisieren |
| `get_contact_details` | Alle Felder eines Kontakts abrufen |

### 5. Chat Adapters (tools/chat/)

```mermaid
flowchart TB
    subgraph Chat_Adapters["tools/chat/"]
        factory["__init__.py<br/>Adapter Factory"]
        iface["interface.py<br/>ChatAdapter Interface"]
        telegram["telegram_adapter.py<br/>Telegram"]
        slack["slack_adapter.py<br/>Slack"]

        factory --> iface
        iface --> telegram
        iface --> slack
    end
```

**StandardMessage Format:**
```python
StandardMessage = {
    "user_id": str,      # "telegram:123456"
    "user_name": str,    # Display Name
    "text": str,         # Nachrichteninhalt
    "platform": str,     # "telegram" oder "slack"
    "chat_id": str,      # Für Antworten
    "raw_data": dict     # Original Webhook
}
```

### 6. Datenbank Layer

```mermaid
flowchart LR
    subgraph DB["Datenbank Layer"]
        subgraph Models["models/"]
            user_model["user.py<br/>User SQLAlchemy Model"]
        end

        subgraph Repos["repositories/"]
            user_repo["user_repository.py<br/>User CRUD Operations"]
        end

        subgraph Utils["utils/"]
            db_utils["database.py<br/>Connection Pool & Config"]
        end

        user_repo --> user_model
        user_repo --> db_utils
    end
```

**User Model:**
```python
User = {
    "id": UUID,
    "email": str,
    "name": str,
    "telegram_id": str,      # Optional
    "slack_id": str,         # Optional
    "is_active": bool,
    "is_approved": bool,     # Muss approved sein
    "role": "ADMIN" | "USER",
    "crm_display_name": str  # Attribution im CRM
}
```

### 7. Admin API (api/)

```mermaid
flowchart LR
    subgraph API["api/users.py"]
        GET_ALL["GET /api/users<br/>Alle User"]
        GET_PENDING["GET /api/users/pending<br/>Pending Approvals"]
        GET_STATS["GET /api/users/stats<br/>Statistiken"]
        POST_APPROVE["POST /api/users/{id}/approve<br/>User freischalten"]
        PATCH_USER["PATCH /api/users/{id}<br/>User aktualisieren"]
    end
```

### 8. Frontend (frontend/)

```mermaid
flowchart TB
    subgraph Frontend["frontend/"]
        subgraph Pages["src/pages/"]
            dashboard["Dashboard.tsx"]
            users["Users.tsx"]
            approvals["Approvals.tsx"]
        end

        subgraph Services["src/services/"]
            api["api.ts<br/>API Client"]
        end

        Pages --> Services
    end
```

---

## Datenfluss-Zusammenfassung

```mermaid
flowchart TB
    subgraph Request["REQUEST PATH"]
        R1[Chat Platform] --> R2[Webhook] --> R3[Adapter] --> R4[StandardMessage] --> R5[State] --> R6[LangGraph]
    end

    subgraph Processing["PROCESSING"]
        P1[Auth] --> P2[Router] --> P3[Chat/CRM] --> P4[Session Guard] --> P5[PostgreSQL]
    end

    subgraph Response["RESPONSE PATH"]
        RS1[AIMessage] --> RS2[Chat Adapter] --> RS3[Platform API] --> RS4[User]
    end

    subgraph Admin["ADMIN MANAGEMENT"]
        A1[Frontend] --> A2[REST API] --> A3[Repository] --> A4[PostgreSQL] --> A5[Notifications]
    end

    R6 --> P1
    P5 --> RS1
```

---

## Session Management

### Killswitch & Session Timeout

```mermaid
flowchart TD
    MSG[Incoming Message] --> KILL{Text == "RESTART"?}

    KILL -->|Ja| CLEAR[Session löschen<br/>Checkpoint + Timestamp]
    CLEAR --> RESPONSE1["Alles klar! Mein Gedächtnis<br/>ist gelöscht..."]
    RESPONSE1 --> END1([Ende])

    KILL -->|Nein| TIMEOUT{Session > 15 Min?}

    TIMEOUT -->|Ja| EXPIRE[Session automatisch löschen]
    EXPIRE --> CONTINUE[Weiter zu Graph]

    TIMEOUT -->|Nein| UPDATE[Timestamp aktualisieren]
    UPDATE --> CONTINUE

    CONTINUE --> GRAPH[LangGraph Pipeline]
```

| Feature | Wert | Beschreibung |
|---------|------|--------------|
| **Killswitch** | `RESTART` | Löscht komplette Session (Messages + State) |
| **Timeout** | 15 Minuten | Automatischer Reset bei Inaktivität |
| **Response** | Standardnachricht | "Alles klar! Mein Gedächtnis ist gelöscht..." |

### Sticky Sessions (ACTIVE Mode)

```mermaid
sequenceDiagram
    participant User
    participant Router
    participant CRM as CRM Node
    participant Guard as Session Guard

    User->>CRM: "Erstelle Kontakt für Max Müller"
    CRM->>CRM: Erstellt Kontakt...
    CRM->>User: "Welche E-Mail?"
    CRM->>Guard: Response analysieren
    Guard->>Guard: Offene Frage erkannt
    Guard-->>Guard: session_state = ACTIVE

    User->>Router: "max@example.com"
    Router->>Router: Session ist ACTIVE
    Router->>CRM: Direkt weiterleiten (kein Intent-Check)
    CRM->>CRM: Fügt E-Mail hinzu
    CRM->>User: "Fertig!"
    CRM->>Guard: Response analysieren
    Guard->>Guard: Task abgeschlossen
    Guard-->>Guard: session_state = IDLE
```

---

## Architektur-Patterns

```mermaid
mindmap
  root((Adizon Patterns))
    State Reduction
      add_messages Reducer
      Automatisches Appending
      Persistente Multi-Turn
    Conditional Routing
      route_decision Funktion
      Dynamische Workflows
      Early Termination
    Configuration-Driven
      YAML-basierte Prompts
      Environment Variables
      Template Rendering
    Platform-Agnostic
      ChatAdapter Interface
      StandardMessage
      Ein Webhook-Endpoint
    Attribution & Undo
      Username Tagging
      Undo-Context im State
      Error Recovery
```

---

## Deployment

```mermaid
flowchart TB
    subgraph Cloud["RAILWAY / RENDER"]
        subgraph Services["Services"]
            FastAPI["FastAPI<br/>Backend"]
            PostgreSQL[(PostgreSQL<br/>Database)]
            Frontend["Frontend<br/>Static"]
        end

        FastAPI <--> PostgreSQL
        PostgreSQL <--> Frontend
    end

    subgraph External["External Services"]
        Telegram["Telegram<br/>Bot API"]
        TwentyCRM["Twenty CRM<br/>GraphQL API"]
        Slack["Slack<br/>API"]
    end

    FastAPI <--> Telegram
    FastAPI <--> Slack
    FastAPI <--> TwentyCRM
```

---

## ReAct Agent Loop (CRM Node)

```mermaid
flowchart TD
    START([User Message]) --> THINK

    THINK[LLM: Analyse & Planung] --> DECIDE{Tool benötigt?}

    DECIDE -->|Ja| SELECT[Tool auswählen]
    SELECT --> EXECUTE[Tool ausführen]
    EXECUTE --> OBSERVE[Ergebnis analysieren]
    OBSERVE --> THINK

    DECIDE -->|Nein| RESPOND[Antwort generieren]
    RESPOND --> END([Response an User])
```

---

## Wichtige Dateien

| Datei | Funktion | Zeilen |
|-------|----------|--------|
| `server.py` | FastAPI Server, Webhooks | ~275 |
| `graph/builder.py` | LangGraph Kompilierung | ~126 |
| `graph/state.py` | State Schema | ~54 |
| `graph/nodes.py` | Alle Workflow Nodes | ~401 |
| `models/user.py` | User Datenbank Model | ~102 |
| `repositories/user_repository.py` | User CRUD | ~265 |
| `tools/crm/__init__.py` | CRM Tools Factory | ~338 |
| `tools/chat/interface.py` | Chat Adapter Interface | ~134 |
| `prompts/*.yaml` | Agent Konfigurationen | 4 Dateien |
