# Adizon V2 - Test Suite

**Letzte Aktualisierung:** 28.12.2025  
**Status:** Aktiv

---

## 📋 Übersicht

Dieser Ordner enthält Tests für die Kernfunktionalität von Adizon V2.

---

## 🧪 Verfügbare Tests

### 1. `test_memory.py` - Memory Core Test ✅

**Zweck:** Validiert Redis-basiertes Memory-System

**Testet:**
- Memory-Erstellung pro User
- Speichern von Konversationen
- Persistenz über Requests hinweg
- Multi-User Isolation

**Ausführen:**
```bash
cd /Users/michaelschiestl/python/adizon-v2
source venv/bin/activate
python tests/test_memory.py
```

**Voraussetzungen:**
- Redis läuft (Docker: `docker ps`)
- `.env` ist konfiguriert

**Erwartete Ausgabe:**
```
=== REDIS MEMORY TEST ===
✅ Memory created
✅ Saved to Redis
✅ Messages in History: 2
✅ Total Messages: 6
✅ Other User Messages: 0
=== TEST COMPLETE ===
```

---

### 2. `test_redis.py` - Redis Quick-Check 🔍

**Zweck:** Zeigt gespeicherte Messages für einen User

**Use Case:** Debugging - "Was ist im Memory für User X?"

**Ausführen:**
```bash
python tests/test_redis.py
```

**Anpassung:**
```python
# In test_redis.py ändern:
user_id = "deine_telegram_user_id"
session_id = "main"
```

**Erwartete Ausgabe:**
```
=== REDIS CHECK ===
User: test_123
Session: crm
Messages: 4

1. [human]: Hallo!
2. [ai]: Hey! Wie kann ich helfen?
...
```

---

### 3. `test_agent_memory.py` - Integration Test 🤖

**Zweck:** End-to-End Test mit echtem LLM

**Testet:**
- Agent erinnert sich an Fakten (Name, Firma)
- Agent nutzt Memory für Antworten
- Agent nutzt Context für Tool-Calling

**Ausführen:**
```bash
python tests/test_agent_memory.py
```

**Warnung:** Verbraucht API-Tokens! (OpenRouter API Call)

**Erwartete Ausgabe:**
```
=== AGENT MEMORY TEST (YAML-Config Version) ===
Agent: CRM Handler v2.1
Model: ministral-14b-2512
Temperature: 0.4

TEST 1: Kontext speichern
✅ Turn 1 complete

TEST 2: Memory-Check
✅ TEST 2 BESTANDEN: Agent hat Firma aus Memory erinnert!

TEST 3: Context für Tool-Calling
✅ TEST 3 BESTANDEN: Agent hat Namen aus Memory genutzt!

✅ Alle 3 Turns erfolgreich durchlaufen
```

---

## 🚀 Quick Start

### Alle Tests nacheinander ausführen:

```bash
cd /Users/michaelschiestl/python/adizon-v2
source venv/bin/activate

echo "=== TEST 1: Memory ==="
python tests/test_memory.py

echo "\n=== TEST 2: Redis Check ==="
python tests/test_redis.py

echo "\n=== TEST 3: Agent Memory ==="
python tests/test_agent_memory.py
```

---

## 🔧 Troubleshooting

### "Connection refused" bei Redis-Tests

**Problem:** Redis läuft nicht

**Lösung:**
```bash
# Prüfen ob Redis läuft
docker ps | grep redis

# Falls nicht, starten
docker run -d -p 6379:6379 redis
```

---

### "Module not found" Fehler

**Problem:** Virtual Environment nicht aktiviert

**Lösung:**
```bash
source venv/bin/activate
```

---

### "API Key not found" bei agent_memory Test

**Problem:** `.env` fehlt oder unvollständig

**Lösung:**
```bash
# Prüfe .env
cat .env | grep OPENROUTER_API_KEY

# Falls leer, setze:
echo "OPENROUTER_API_KEY=your_key" >> .env
```

---

## 📊 Test-Status

| Test | Status | Tests | Coverage | Notes |
|------|--------|-------|----------|-------|
| `test_memory.py` | ✅ | 100% | Memory Core | Redis Persistence |
| `test_redis.py` | ✅ | - | Quick-Check | Debugging-Tool |
| `test_agent_memory.py` | ✅ | 2/3 | Integration | End-to-End mit LLM |
| `test_undo.py` | ✅ | 6/6 | Undo System | Multi-User Safety |
| `test_agent_config.py` | ✅ | 7/7 | YAML Config | Alle 4 Agents |
| `test_crm_adapter.py` | ✅ | 8/8 | CRM Interface | Mock-basiert |
| `test_fuzzy_search.py` | 🆕 | 16/16 | Fuzzy-Matching | Voice-Ready Search |

---

## 🆕 Phase 1 Tests (28.12.2025)

### 4. `test_undo.py` - Undo-Funktionalität ✅

**Zweck:** Multi-User Safety & Redis-State

**Testet:**
- Save/Retrieve/Clear Undo-Context
- Multi-User Isolation (Alice ≠ Bob)
- Overwrite bei neuer Aktion
- Empty Context Handling
- Verschiedene Item-Types (note, task, contact)

**Ausführen:**
```bash
python tests/test_undo.py
```

**Erwartete Ausgabe:**
```
📊 Ergebnis: 6/6 Tests bestanden
✅ Multi-User Safety validiert
```

---

### 5. `test_agent_config.py` - YAML Config System ✅

**Zweck:** Config-Loader Validation

**Testet:**
- Config laden aus YAML
- Environment Variable Substitution (`${VAR}`)
- Template Rendering (`{user_name}`)
- Parameter Validation (temperature, top_p)
- Caching
- Alle 4 Agent-Configs (crm, chat, intent, session)

**Ausführen:**
```bash
python tests/test_agent_config.py
```

**Erwartete Ausgabe:**
```
📊 Ergebnis: 7/7 Tests bestanden
✅ YAML Config System ist production-ready
```

---

### 6. `test_crm_adapter.py` - CRM-Abstraktion (Mocks) ✅

**Zweck:** CRM-Wechsel Vorbereitung (Twenty → Zoho)

**Testet:**
- `create_contact()` / `create_task()` / `create_note()` ID-Format
- `search_contacts()` Fuzzy-Search
- `delete_item()` Undo
- `_resolve_target_id()` Self-Healing
- Error-Handling
- Payload-Struktur (Name-Splitting)

**Ausführen:**
```bash
python tests/test_crm_adapter.py
```

**Erwartete Ausgabe:**
```
📊 Ergebnis: 8/8 Tests bestanden
✅ Bereit für CRM-Wechsel
```

---

### 9. `test_fuzzy_search.py` - Fuzzy-Matching Engine 🆕 ✅

**Zweck:** Voice-Ready Tippfehler-tolerante Suche

**Testet:**
- `_fuzzy_match()` Kern-Funktion (8 Unit Tests)
  - Exakte Matches (100% Score)
  - Tippfehler-Toleranz ("Tomas" → "Thomas" = 92%)
  - Wort-Reihenfolge ("Braun Thomas" = "Thomas Braun")
  - Partial Matches ("Thomas" in "Thomas Braun")
  - Case-Insensitivity
  - Below-Threshold Rejection
  - Empty String Handling
  - Custom Thresholds
- `_resolve_target_id()` mit Fuzzy (4 Integration Tests)
  - Fuzzy Name-Match
  - Fuzzy Email-Match
  - Best-Match-Wins Logik
  - No-Match Fallback
- `search_contacts()` mit Scoring (3 Integration Tests)
  - Fuzzy Person-Search
  - Score-basierte Sortierung
  - Fuzzy Company-Search
- Performance Test (1 Test)
  - 1000 Matches in <100ms
- Edge Cases (2 Tests)
  - Sonderzeichen (Umlaute, Bindestriche)
  - Sehr lange Strings

**Ausführen:**
```bash
# Installation
pip install rapidfuzz

# Tests ausführen
python tests/test_fuzzy_search.py

# Oder via pytest
pytest tests/test_fuzzy_search.py -v
```

**Erwartete Ausgabe:**
```
🧪 Running Fuzzy-Search Tests...
✅ rapidfuzz ist installiert

==================== 16 passed in 0.15s ====================
📊 Ergebnis: 16/16 Tests bestanden
✅ Voice-Ready Search validiert
⚡ Performance: <0.1ms pro Match
```

**Dependency:**
```bash
# Benötigt rapidfuzz (bereits in requirements.txt)
pip install rapidfuzz==3.10.1
```

---

## 🗑️ Entfernte Tests

### `test_qwen.py` - ❌ Gelöscht (28.12.2025)

**Grund:** Qwen-Modelle werden nicht mehr genutzt (Wechsel zu Ministral)

---

## 💡 Zukünftige Tests (Ideen)

### `test_agent_config.py`
- Validiert YAML-Config-Loader
- Prüft Environment Variable Substitution
- Testet Template Rendering

### `test_undo.py`
- Testet Undo save/retrieve/delete
- Multi-User Undo-Isolation
- TTL (1 Stunde) Verhalten

### `test_twenty_adapter.py`
- Mock-Tests für CRM API Calls
- Validiert Payload-Struktur
- Testet Error-Handling

### `test_field_enrichment.py` 🆕
**Was:** Dynamic Field Enrichment Feature
- Field Mapping Loader (YAML-basiert)
- Field Validation & Auto-Fix
- update_entity() Integration
- Custom Fields Support

**Kategorien:**
1. Field Mapping Loader (8 Tests)
2. Field Validation (7 Tests)
3. Adapter Integration - Mock (6 Tests)
4. Tool Factory (2 Tests)
5. Full Integration (3 Tests)

**Total:** 26 Tests

---

## 📝 Best Practices

1. **Vor jedem Test:** Redis starten & .env prüfen
2. **Nach Änderungen:** Alle Tests durchlaufen lassen
3. **Neue Features:** Passenden Test schreiben
4. **API-Tests:** Sparsam nutzen (Kosten!)

---

**Maintainer:** Michael & KI  
**Projekt:** Adizon V2 - AI Sales Agent

