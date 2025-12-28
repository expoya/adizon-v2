# CRM Field Mappings

Dieser Ordner enthält die Field-Mapping-Konfigurationen für verschiedene CRM-Systeme.

## 📋 Konzept

**Whitelist-Prinzip:** Nur explizit definierte Felder dürfen von Adizon befüllt werden.

**Vorteile:**
- ✅ Sicherheit: Keine versehentlichen Änderungen an kritischen Feldern
- ✅ Flexibilität: Custom Fields einfach hinzufügbar
- ✅ Wartbarkeit: Änderungen ohne Code-Deployment
- ✅ Transparenz: Klar dokumentiert, was Adizon darf

## 📁 Verfügbare Mappings

- **`twenty.yaml`** - Twenty CRM (Production)
- **`zoho.yaml`** - Zoho CRM (TBD)
- **`template.yaml`** - Template für neue CRMs (TBD)

## 🏗️ YAML-Struktur

```yaml
crm_system: "twenty"
version: "1.0"

entities:
  person:
    endpoint: "people"
    fields:
      job:
        crm_field: "jobTitle"        # CRM-spezifischer Feldname
        type: "string"                # Datentyp
        description: "Position"       # Beschreibung
        required: false               # Pflichtfeld?
        example: "CEO"                # Beispielwert
        llm_hint: "z.B. CEO, CTO"    # Hint für LLM
```

## 🔧 Neues CRM hinzufügen

1. Kopiere `template.yaml` (oder `twenty.yaml`)
2. Benenne um zu `<crm_name>.yaml`
3. Passe `crm_field`-Namen an (z.B. Zoho: `Designation` statt `jobTitle`)
4. Füge Custom Fields hinzu
5. Teste mit `test_field_enrichment.py`

## 🎨 Custom Fields

Custom Fields für spezifische Kunden können einfach hinzugefügt werden:

```yaml
roof_area:
  crm_field: "customField_roofArea"
  type: "number"
  unit: "m²"
  custom: true                    # Markiert als Custom Field
  customer: "voltage_solutions"   # Optional: Kundenname
```

## ✅ Validation

Validation-Rules werden automatisch angewendet:

```yaml
validation:
  url:
    auto_fix: true  # Ergänzt https:// automatisch
  linkedin:
    pattern: "linkedin.com"
```

## 📝 Best Practices

1. **Whitelist-First:** Nur Felder hinzufügen, die wirklich gebraucht werden
2. **LLM-Hints:** Gute Hints helfen dem LLM, Felder korrekt zu befüllen
3. **Examples:** Immer Beispielwerte angeben
4. **Validation:** Bei kritischen Feldern Validation-Rules definieren
5. **Custom Fields:** Klar markieren mit `custom: true`

## 🔄 Versionierung

- Version erhöhen bei Breaking Changes
- Changelog in Kommentaren dokumentieren
- Git-History zeigt alle Änderungen

## 🧪 Testing

```bash
# Test Field Mapping Loader
python -m pytest tests/test_field_enrichment.py -v

# Test spezifisches CRM
python -m pytest tests/test_field_enrichment.py::test_twenty_mapping -v
```

