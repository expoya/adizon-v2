# Projektstatus-Bericht: Adizon V2

**Stand:** 28.12.2025 - 07:30 Uhr  
**Status:** Operational / Polished 🟢  
**Entwickler:** Michael (Architekt/Integrator) & KI (Coder)  
**Ziel:** Production-Ready AI Sales Agent für KMUs (Expoya). Späterer Betrieb on-premise (lokale LLMs, z.B. Ministral 14B, 128GB RAM Hardware)

---

## 1. Architektur & Tech Stack

Der Wechsel von n8n zu Python (Code-First) ist vollzogen.

- **Core:** Python 3.12+, FastAPI (Webserver & Webhook-Handler)
- **Framework:** LangChain (für Tool-Calling Agents und Memory-Verwaltung)
- **Datenbank/Memory:** Redis (Docker) für persistente Chat-Historie (RedisChatMessageHistory)
- **LLM Inference:** Aktuell OpenRouter API (Simulation der lokalen Modelle)
- **Ziel-Modell:** Ministral 14B (via OpenRouter für Dev, später lokal)

---

## 2. Codebasis Analyse (Ist-Stand)

### A. Entry Point (main.py)

- Stellt FastAPI Endpoints bereit (`/telegram-webhook`, `/adizon` für Tests)
- **Logic Flow:** Eingehende Nachricht → `detect_intent()` → Routing zu Handler
- **Intent Detection:** Ein LLM-Call klassifiziert Input hart in CHAT oder CRM

### B. Agenten & Handler

**Chat Handler (`agents/chat_handler.py`):**
- Zuständig für Smalltalk/Begrüßung
- Nutzung: Direkter LLM Call (kein LangChain Agent Overhead)
- Status: Funktional, stateless (nutzt aktuell scheinbar kein Memory?)

**CRM Handler (`agents/crm_handler.py`):**
- Zuständig für Business-Logik
- Nutzung: LangChain `create_tool_calling_agent`
- Tools: `create_contact`, `search_contacts` (derzeit Mock-Returns, noch keine echte Zoho-API)
- Status: Implementiert, aber Memory-Integration war fehleranfällig

### C. Memory (`utils/memory.py`)

- Implementiert `get_conversation_memory` mittels `RedisChatMessageHistory`
- Unterscheidet Sessions via `adizon:conversation:{user_id}:{session_id}`
- **Problem:** Die Anbindung an den LangChain Agent (crm_handler) und das persistente "Merken" über Turns hinweg schlug beim letzten Test fehl oder war inkonsistent

---

## 3. Erreichte Meilensteine

### Core Architecture Complete (27.12.2025 - 09:10 Uhr)

- ✅ Erfolgreicher Switch von n8n auf Python/FastAPI
- ✅ Memory: RedisChatMessageHistory speichert Verläufe persistent (Docker/Railway)
- ✅ Routing: `detect_intent` ist auf Speed optimiert und erkennt implizite CRM-Befehle (Namen)

### Session Management (Sticky Sessions)

- ✅ **Shared Brain:** Chat & CRM nutzen dieselbe Redis-Session
- ✅ **Session Guard:** Ein dedizierter LLM-Call entscheidet nach jedem Turn, ob die Session ACTIVE (Tunnel) oder IDLE (Router) ist
- ✅ **Bypass:** Solange ACTIVE, wird der Intent-Router übersprungen

### Qualitätssicherung

- ✅ `top_p=0.9` & `temperature=0.6` verhindern Halluzinationen ("Spannig"-Problem gelöst)
- ✅ System-Prompts verhindern rhetorische Fragen des Bots

### Integration Complete (27.12.2025 - 11:50 Uhr)

- ✅ **Brain:** Intent-Router trennt sauber zwischen "Smalltalk" und "Business/CRM"
- ✅ **Connection:** Adapter-Pattern implementiert. Adizon schreibt erfolgreich Daten in Twenty CRM (via REST API)
- ✅ **Session Guard:** Sticky Sessions funktionieren (ACTIVE State). Kontext bleibt erhalten ("Erstelle eine Notiz für ihn")
- ✅ **Security:** HTTPS Enforcement und robustes Error-Handling im Adapter implementiert

### CRM Core Complete (27.12.2025 - 13:30 Uhr)

**Intelligente Notizen (Smart Notes):**
- ✅ Automatische Titel-Generierung aus Kontext (z.B. "Interesse an Solarlösungen")
- ✅ Rich-Text/Markdown Support (`bodyV2`)
- ✅ Korrekte Verknüpfung via `noteTargets`

**Task Management mit "Self-Healing":**
- ✅ Automatisches Auflösen von E-Mail-Adressen zu internen UUIDs
- ✅ Datums-Intelligenz: Agent versteht "morgen" oder "nächsten Dienstag"

**Relationale Suche (Smart Search):**
- ✅ Erkennt Zusammenhänge zwischen Firmen und Mitarbeitern
- ✅ Liefert bei Firmensuche automatisch die Ansprechpartner mit

### Undo & Robustness Update (28.12.2025 - 07:30 Uhr)

**Undo-Funktion (Multi-User Safe):**
- ✅ "Zeitmaschine" mittels Redis
- ✅ Factory-Pattern: Tools werden dynamisch pro Request generiert (`get_crm_tools_for_user`)
- ✅ Wrapper-Logik: Interceptor speichert IDs user-spezifisch für 1 Stunde
- ✅ "Rückgängig"-Befehl löscht zuletzt erstelltes Objekt hard aus dem CRM

**Smart Target Resolution (Self-Healing V2):**
- ✅ Problem behoben: Agent hat bei fehlender UUID E-Mails "erfunden" (halluziniert)
- ✅ Zentrale `_resolve_target_id` Methode im Adapter
- ✅ Hierarchische Prüfung: UUID → E-Mail-Match → Namens-Match (in letzten 500 Kontakten)
- ✅ User kann "Notiz für Thomas Braun" sagen, System findet korrekte UUID automatisch

---

## 4. Technische Architektur & Härtung

### Adapter-Pattern (Finalized)

- `twenty_adapter.py` ist vollständig typisiert
- Sauberes Abfangen von API-Fehlern (400 Bad Request)

### Switchboard (`__init__.py`)

- Leitet komplexe Argumente (Titel, Datum, Target-IDs) verlustfrei an Adapter weiter

### Schema-Compliance

- Strikte Einhaltung der Twenty-API-Vorgaben (z.B. `bodyV2` statt `body`, `dueAt` für Tasks)

### Clean Code Refactoring

- ✅ Entfernung von Spaghetti-Code im `crm_handler`
- ✅ Logik für Wrapper und State-Management in `tools/crm/__init__.py` (Factory) und `utils/memory.py` ausgelagert

### Separation of Concerns

- **Handler:** Orchestriert nur noch den Ablauf
- **Factory:** Baut die Tools und injiziert das Gedächtnis
- **Adapter:** Handhabt die reine API-Kommunikation und Fehlerbehandlung

---

## 5. Aktuelle Capabilities (MVP)

- ✅ **Kontakt-Suche:** Findet Personen im CRM (Live-Daten) mit Fuzzy-Matching
- ✅ **Kontakt-Anlage:** Erstellt neue Kontakte via Chat
- ✅ **Task Management:** Erstellt und verknüpft Tasks mit intelligentem Datum-Parsing
- ✅ **Notizen:** Erstellt kontextbezogene Notizen mit Smart Titles
- ✅ **Undo:** Macht letzte Aktion rückgängig (multi-user safe)
- ✅ **Flexibilität:** Umschaltbar zwischen Demo (Twenty/Lokal) und Produktion (Zoho/Cloud) via `.env`
- ✅ **Fuzzy-Search:** Tippfehler-tolerante Suche mit Score-Ranking (Voice-Ready)

---

## 6. Bekannte Hürden & Fixes

### ~~LLM Wechsel~~
- ✅ Tests mit Qwen durchgeführt
- ✅ Wechsel auf Ministral 14B (via OpenRouter) erfolgreich
- ✅ Tool-Calling mit Ministral validiert

### ~~Memory Bruch~~
- ✅ Redis-Integration funktioniert stabil
- ✅ Kontext bleibt über Turns erhalten

### ~~Halluzination Problem~~
- ✅ E-Mail-Erfindung bei Target-Resolution behoben
- ✅ Zentrale Resolver-Logik implementiert

---

## 7. Nächste Schritte (Phase 2: Deep Integration)

### Kurzfristig
- [x] **Erweiterte Suche:** Fuzzy-Search (Fehlertoleranz) ✅ 28.12.2025
- [ ] **Briefing-Modus:** Zusammenfassung aller Kontakt-Daten für Sales-Prep
- [ ] **Voice Input:** Whisper Integration für Sprachnachrichten

### Mittelfristig
- [ ] **Zoho-Migration:** Übertragung der Logik auf `zoho_adapter.py` (Produktiv-System)
- [ ] **Local LLM Deploy:** Testlauf auf Zielhardware (Ministral lokal statt via OpenRouter)

### Langfristig
- [ ] **Multi-Agent System:** Integration von Mira (WhatsApp) und Iris (Sales Coaching)
- [ ] **On-Premise Deployment:** Vollständiger Betrieb auf eigener Hardware (128GB RAM)

---

## 8. Environment & Dependencies

### Required Environment Variables
```bash
OPENROUTER_API_KEY=<your_key>
MODEL_NAME=mistralai/ministral-8b-instruct
REDIS_URL=redis://localhost:6379
TELEGRAM_TOKEN=<your_token>
TWENTY_API_KEY=<your_key>
TWENTY_API_URL=https://api.twenty.com/graphql (or local)
```

### Key Dependencies
- Python 3.12+
- FastAPI
- LangChain
- Redis
- python-telegram-bot
- requests (für CRM API Calls)

---

## 9. Projektziele (WU Wien Zertifikat)

**Kurs:** AI Transforming Business  
**Jahr:** 2025  
**Projekt:** Adizon - Multi-Agent AI System  

**Fokus:**
- Praktische Anwendung von AI in KMU-Prozessen
- Workflow-Automatisierung mit LLM-Agents
- GDPR-konforme Self-Hosted Lösungen
- Integration in bestehende CRM-Systeme