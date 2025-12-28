# Quick Reference: Dynamic Field Enrichment

**Feature:** Vollständige CRM-Feld-Befüllung via Chat  
**Status:** ✅ Production-Ready  
**Version:** 2.2

---

## 🚀 Schnellstart

### Person-Felder aktualisieren

```
User: "Thomas Braun ist CEO, LinkedIn: linkedin.com/in/thomas"

Adizon nutzt automatisch:
update_entity(
  target="Thomas Braun",
  entity_type="person",
  job="CEO",
  linkedin="linkedin.com/in/thomas"
)

Result: ✅ Person aktualisiert
```

### Company-Felder aktualisieren

```
User: "Expoya hat Website expoya.com, 50 Mitarbeiter, Industry Solar"

Adizon nutzt automatisch:
update_entity(
  target="Expoya",
  entity_type="company",
  website="expoya.com",
  size=50,
  industry="Solar"
)

Result: ✅ Company aktualisiert (Website auto-fixed zu https://)
```

---

## 📋 Verfügbare Felder

### Person
| Generic Name | CRM Field | Type | Beispiel | Validation |
|--------------|-----------|------|----------|------------|
| `job` | jobTitle | string | "CEO" | - |
| `linkedin` | linkedIn | url | "linkedin.com/in/max" | Muss linkedin.com enthalten |
| `city` | city | string | "Wien" | - |
| `birthday` | birthday | date | "1990-05-15" | Format: YYYY-MM-DD |

### Company
| Generic Name | CRM Field | Type | Beispiel | Validation |
|--------------|-----------|------|----------|------------|
| `website` | domainName | url | "expoya.com" | Auto-Fix: ergänzt https:// |
| `size` | employees | number | 50 | Min: 1 |
| `industry` | idealCustomerProfile | string | "Solar" | - |
| `address` | address | string | "Hauptstr. 1, 1010 Wien" | - |
| `roof_area` | customField_roofArea | number | 300 | Custom Field (Voltage Solutions) |

---

## 🛠️ Für Entwickler

### Custom Field hinzufügen

**Datei:** `tools/crm/field_mappings/twenty.yaml`

```yaml
entities:
  company:
    fields:
      # ... existing fields ...
      
      # NEUES CUSTOM FIELD:
      solar_capacity:
        crm_field: "customField_solarCapacity"
        type: "number"
        unit: "kWp"
        description: "Installierte Solarleistung"
        required: false
        custom: true
        customer: "voltage_solutions"
        example: 25
```

**Das war's!** Kein Code-Change nötig, LLM kann Field sofort nutzen.

### Neues CRM hinzufügen

1. Kopiere `tools/crm/field_mappings/twenty.yaml`
2. Benenne um zu `<crm_name>.yaml` (z.B. `zoho.yaml`)
3. Passe `crm_field`-Namen an:

```yaml
# twenty.yaml
website:
  crm_field: "domainName"  # Twenty-spezifisch

# zoho.yaml
website:
  crm_field: "Website"     # Zoho-spezifisch
```

4. Fertig! System nutzt automatisch korrektes Mapping.

---

## 🧪 Testing

### Unit Tests
```bash
pytest tests/test_field_enrichment.py -v
```

### Manuelle Tests
```bash
curl -X POST http://localhost:8000/adizon \
  -d "message=Expoya hat Website expoya.com&user_name=Test"
```

---

## 🔐 Whitelist-Prinzip

**Nur explizit definierte Felder** werden akzeptiert:

```python
# ✅ Erlaubt (in YAML definiert)
update_entity(..., fields={"website": "test.com"})

# ❌ Blockiert (nicht in YAML)
update_entity(..., fields={"hacker_field": "malicious"})
```

**Ergebnis:** Sicher vor versehentlichen oder böswilligen Änderungen.

---

## 📊 Auto-Fix Examples

### URLs
```
Input:  "expoya.com"
Output: "https://expoya.com" ✅ (https:// ergänzt)
```

### Numbers
```
Input:  "50" (String)
Output: 50 (Number) ✅ (Type Conversion)
```

### LinkedIn
```
Input:  "https://linkedin.com/in/thomas"
Output: ✅ (linkedin.com enthalten)

Input:  "https://facebook.com/thomas"
Output: ❌ (muss linkedin.com enthalten)
```

---

## 🎯 Use Cases

### 1. Lead-Qualifizierung
```
User: "ACME Corp, 200 Mitarbeiter, Industry IT"
→ Alle Infos landen sofort im CRM
→ Lead-Scoring kann direkt laufen
```

### 2. Event Follow-Up
```
User: "Max Müller, CEO bei ACME, LinkedIn: linkedin.com/in/max-mueller"
→ Vollständiges Kontakt-Profil
→ Bessere Ansprache möglich
```

### 3. Sales-Prep
```
User: "Die Firma hat 500 Mitarbeiter und Website acme.com"
→ Komplette Firmen-Info
→ Sales kann sofort loslegen
```

---

## ⚙️ Configuration

### .env
```bash
CRM_SYSTEM=TWENTY           # Feature nur im Live-Modus
TWENTY_API_URL=...
TWENTY_API_KEY=...
```

### Feature Check
```python
from tools.crm import get_crm_tools_for_user

tools = get_crm_tools_for_user("test_user")
tool_names = [tool.name for tool in tools]

if "update_entity" in tool_names:
    print("✅ Field Enrichment verfügbar")
else:
    print("❌ Field Enrichment nicht verfügbar (nur Mock-Modus)")
```

---

## 🐛 Troubleshooting

### "Feld nicht in Whitelist"
**Problem:** LLM versucht ungültiges Feld zu setzen  
**Lösung:** Feld in `twenty.yaml` hinzufügen

### "Target nicht gefunden"
**Problem:** Name/Email kann nicht aufgelöst werden  
**Lösung:** Kontakt/Firma muss erst existieren (via `create_contact`)

### "Validation failed"
**Problem:** Wert entspricht nicht dem erwarteten Format  
**Lösung:** Prüfe Validation-Rules in YAML (z.B. LinkedIn muss linkedin.com enthalten)

### Tests schlagen fehl
**Problem:** Field Mapping kann nicht geladen werden  
**Lösung:** Prüfe ob `tools/crm/field_mappings/twenty.yaml` existiert

---

## 📚 Weitere Dokumentation

- **Full Docs:** `Roadmap/feature-dynamic-field-enrichment.md`
- **Changelog:** `Roadmap/changelog.md` (28.12.2025 - Nacht)
- **Implementation:** `Roadmap/IMPLEMENTATION-SUMMARY.md`
- **Tests:** `tests/test_field_enrichment.py`
- **Mapping:** `tools/crm/field_mappings/README.md`

---

**Version:** 2.2  
**Implementiert:** 28.12.2025  
**Status:** ✅ Production-Ready

