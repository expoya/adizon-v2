# Agent Prompts & Configuration

Dieser Ordner enthält YAML-basierte Konfigurationen für alle AI-Agenten in Adizon V2.

## 📁 Struktur

Jede YAML-Datei definiert ein vollständiges **Agent-Profil**:

- **System Prompt** - Die Persönlichkeit und Anweisungen des Agents
- **LLM Model Config** - API-Verbindung und Modell-Name
- **LLM Parameters** - Temperature, Top-P, Max-Tokens, etc.
- **Agent Settings** - Verbose, Max-Iterations, etc.
- **Metadata** - Name, Version, Changelog

## 🤖 Verfügbare Agenten

### 1. `crm_handler.yaml`
**Zweck:** Business Logic, CRM-Operationen, Tool-Calling  
**Settings:** temperature=0.4 (präzise, aber kreativ genug für Problemlösung)

### 2. `chat_handler.yaml`
**Zweck:** Smalltalk, Begrüßungen, allgemeine Konversation  
**Settings:** temperature=0.6 (natürlicher, conversational)

### 3. `intent_detection.yaml`
**Zweck:** Routing zwischen CHAT und CRM  
**Settings:** temperature=0.0 (deterministisch für konsistente Entscheidungen)

### 4. `session_guard.yaml`
**Zweck:** Entscheidet, ob Session ACTIVE (Sticky) oder IDLE bleibt  
**Settings:** temperature=0.0 (deterministisch)

## 🔧 Wie man Prompts bearbeitet

### 1. YAML-Datei öffnen
```bash
code prompts/crm_handler.yaml
```

### 2. Prompt anpassen
```yaml
system_prompt: |
  Du bist Adizon...
  [Deine Änderungen hier]
```

### 3. Parameter optimieren (optional)
```yaml
parameters:
  temperature: 0.4  # Niedriger = konsistenter, höher = kreativer
  max_tokens: 500   # Maximale Antwortlänge
```

### 4. Speichern & Testen
Die Änderungen werden **automatisch beim nächsten Request** geladen (Caching).

Für sofortiges Reload in Development:
```python
from utils.agent_config import reload_config
reload_config("crm_handler")
```

## 🎨 Template-Variablen

Prompts unterstützen **dynamische Variablen**:

| Variable | Beschreibung | Beispiel |
|----------|--------------|----------|
| `{user_name}` | Name des Users | "Max" |
| `{current_date}` | Aktuelles Datum | "Monday, 2025-12-28" |
| `{user_message}` | User-Input | "Erstelle Kontakt" |
| `{last_ai_response}` | Letzte AI-Antwort | "Kontakt erstellt!" |

**Verwendung im Prompt:**
```yaml
system_prompt: |
  Du bist Adizon.
  USER: {user_name}
  DATUM: {current_date}
```

## 🌍 Environment Variables

Alle YAML-Files unterstützen **Environment Variable Substitution**:

```yaml
model:
  name: "${MODEL_NAME}"          # Aus .env geladen
  api_key: "${OPENROUTER_API_KEY}"
```

**Syntax:** `${VAR_NAME}` wird automatisch durch `os.getenv("VAR_NAME")` ersetzt.

## 📊 Best Practices

### 1. **Versionierung**
Ändere die `version` und füge einen Changelog-Eintrag hinzu:
```yaml
version: "2.2"
changelog:
  - "2.2: Neue Anweisungen für XYZ"
  - "2.1: Workflow-Anweisungen für Verknüpfungen"
```

### 2. **A/B Testing**
Kopiere eine Config für Tests:
```bash
cp crm_handler.yaml crm_handler_v2.yaml
```

Lade im Code:
```python
config = load_agent_config("crm_handler_v2")
```

### 3. **Temperature-Guide**

| Temperature | Verhalten | Use Case |
|-------------|-----------|----------|
| 0.0 | Deterministisch | Intent Detection, Session Guard |
| 0.3-0.5 | Präzise, fokussiert | CRM Operations, Tool-Calling |
| 0.6-0.8 | Natürlich, conversational | Chat, Smalltalk |
| 0.9-1.2 | Kreativ, variabel | Sales Coaching, Brainstorming |

### 4. **Prompt-Länge**
- **Kurz & präzise** für einfache Tasks (Intent Detection)
- **Detailliert mit Beispielen** für komplexe Tasks (CRM Handler)

## 🔍 Debugging

### Config ausgeben
```python
from utils.agent_config import load_agent_config

config = load_agent_config("crm_handler")
print(config.get_metadata())
print(config.get_parameters())
```

### Gerenderten Prompt ansehen
```python
prompt = config.get_system_prompt(
    user_name="Test User",
    current_date="2025-12-28"
)
print(prompt)
```

## 🚀 Deployment

**Production:** Settings werden aus `.env` geladen  
**Development:** Nutze `.env.local` für lokale Overrides

**Wichtig:** Die YAML-Files selbst enthalten **keine Secrets** (nur Referenzen wie `${API_KEY}`).

## 📝 Schema Reference

Vollständige YAML-Struktur:

```yaml
# Metadata
name: "Agent Name"
description: "Was macht dieser Agent?"
version: "1.0"

# LLM Configuration
model:
  name: "${MODEL_NAME}"
  base_url: "${OPENROUTER_BASE_URL}"
  api_key: "${OPENROUTER_API_KEY}"

# LLM Parameters
parameters:
  temperature: 0.4
  top_p: 0.9
  top_k: null
  max_tokens: 500
  presence_penalty: 0.0
  frequency_penalty: 0.0

# Agent Settings (optional, nur für LangChain Agents)
agent:
  verbose: true
  handle_parsing_errors: true
  max_iterations: 5

# System Prompt
system_prompt: |
  Dein Prompt hier...
  {template_var}

# Changelog
changelog:
  - "1.0: Initial Release"
```

## 🤝 Contributing

Beim Ändern von Prompts:
1. ✅ Version hochzählen
2. ✅ Changelog aktualisieren
3. ✅ Testen mit realen Inputs
4. ✅ Git Commit mit klarer Beschreibung

---

**Letzte Aktualisierung:** 2025-12-28  
**Maintainer:** Michael & KI

