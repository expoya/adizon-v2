"""
Test: CRM Adapter (Mock Tests)
Kritisch für: CRM-Wechsel (Twenty → Zoho), Adapter-Pattern, Self-Healing

Tests:
- create_contact() gibt ID zurück
- create_task() gibt ID zurück
- create_note() gibt ID zurück
- search_contacts() funktioniert
- delete_item() funktioniert
- _resolve_target_id() (Self-Healing)
- ID-Extraktion aus Responses

WICHTIG: Diese Tests nutzen MOCKS, keine echten API-Calls!
Zweck: Validieren, dass Adapter-Interface korrekt implementiert ist.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# .env vor allen Imports laden
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Twenty Adapter importieren
from tools.crm.twenty_adapter import TwentyCRM

print("=" * 70)
print("CRM ADAPTER TEST (Mock-basiert)")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("⚠️  Hinweis: Nutzt MOCKS, keine echten API-Calls\n")

# Test Counter
tests_passed = 0
tests_total = 0


# === TEST 1: create_contact() gibt ID zurück ===
tests_total += 1
print(f"TEST 1: create_contact() ID-Format")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    # Mock the _request method
    with patch.object(adapter, '_request') as mock_request:
        # Simuliere API-Response
        mock_request.return_value = {
            'createPerson': {
                'id': 'test-uuid-12345'
            }
        }
        
        result = adapter.create_contact("Max Mustermann", "max@test.com", "+49123456")
        
        print(f"✓ Response: {result}")
        
        # Prüfe ob ID im richtigen Format ist
        assert "(ID: test-uuid-12345)" in result, f"ID nicht im Response: {result}"
        assert "Max Mustermann" in result, f"Name nicht im Response: {result}"
        assert "✅" in result, f"Success-Marker fehlt: {result}"
        
        print("✅ TEST 1 BESTANDEN: create_contact() gibt ID korrekt zurück\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}\n")


# === TEST 2: create_task() gibt ID zurück ===
tests_total += 1
print(f"TEST 2: create_task() ID-Format")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    with patch.object(adapter, '_request') as mock_request:
        # Simuliere Task-Erstellung
        mock_request.return_value = {
            'createTask': {
                'id': 'task-uuid-67890'
            }
        }
        
        result = adapter.create_task("Follow-up anrufen", "Kunde kontaktieren", "2025-12-30")
        
        print(f"✓ Response: {result}")
        
        # Prüfe Format
        assert "(ID: task-uuid-67890)" in result, f"Task-ID nicht im Response: {result}"
        assert "Follow-up anrufen" in result, f"Title nicht im Response: {result}"
        assert "✅" in result, f"Success-Marker fehlt: {result}"
        
        print("✅ TEST 2 BESTANDEN: create_task() gibt ID korrekt zurück\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}\n")


# === TEST 3: create_note() gibt ID zurück ===
tests_total += 1
print(f"TEST 3: create_note() ID-Format")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    with patch.object(adapter, '_request') as mock_request:
        # Simuliere Note-Erstellung
        mock_request.return_value = {
            'createNote': {
                'id': 'note-uuid-abc123'
            }
        }
        
        result = adapter.create_note("Interesse Solar", "Kunde zeigt Interesse an Solarlösungen", "target-id-123")
        
        print(f"✓ Response: {result}")
        
        # Prüfe Format
        assert "(ID: note-uuid-abc123)" in result, f"Note-ID nicht im Response: {result}"
        assert "Interesse Solar" in result, f"Title nicht im Response: {result}"
        assert "✅" in result, f"Success-Marker fehlt: {result}"
        
        print("✅ TEST 3 BESTANDEN: create_note() gibt ID korrekt zurück\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}\n")


# === TEST 4: search_contacts() funktioniert ===
tests_total += 1
print(f"TEST 4: search_contacts() Fuzzy-Search")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    with patch.object(adapter, '_request') as mock_request:
        # Simuliere Search-Results
        def side_effect(method, endpoint, params=None, data=None):
            if endpoint == "companies":
                return {'companies': []}
            elif endpoint == "people":
                return {
                    'people': [
                        {
                            'id': 'person-123',
                            'name': {'firstName': 'Max', 'lastName': 'Mustermann'},
                            'emails': [{'primaryEmail': 'max@test.com'}]
                        }
                    ]
                }
            return {}
        
        mock_request.side_effect = side_effect
        
        result = adapter.search_contacts("Max")
        
        print(f"✓ Response: {result[:100]}...")
        
        # Prüfe ob Person gefunden wurde
        assert "Max Mustermann" in result, f"Name nicht gefunden: {result}"
        assert "max@test.com" in result, f"Email nicht gefunden: {result}"
        assert "(ID: person-123)" in result, f"ID nicht gefunden: {result}"
        assert "✅" in result, f"Success-Marker fehlt: {result}"
        
        print("✅ TEST 4 BESTANDEN: search_contacts() funktioniert\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 4 ERROR: {e}\n")


# === TEST 5: delete_item() funktioniert ===
tests_total += 1
print(f"TEST 5: delete_item() Undo")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    # Mock requests.delete
    with patch('requests.delete') as mock_delete:
        # Simuliere erfolgreiche Löschung
        mock_response = Mock()
        mock_response.status_code = 200
        mock_delete.return_value = mock_response
        
        result = adapter.delete_item("note", "note-uuid-123")
        
        print(f"✓ Response: {result}")
        
        # Prüfe ob Löschung erfolgreich
        assert "✅" in result, f"Success-Marker fehlt: {result}"
        assert "rückgängig" in result.lower(), f"'rückgängig' nicht im Response: {result}"
        
        print("✅ TEST 5 BESTANDEN: delete_item() funktioniert\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 5 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 5 ERROR: {e}\n")


# === TEST 6: _resolve_target_id() UUID-Check ===
tests_total += 1
print(f"TEST 6: _resolve_target_id() UUID-Erkennung")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    # Test 1: Echte UUID sollte durchgehen
    uuid = "10000000-0000-4000-8000-000000000008"
    result_uuid = adapter._resolve_target_id(uuid)
    
    assert result_uuid == uuid, f"UUID nicht durchgegangen: {result_uuid}"
    print(f"✓ UUID durchgegangen: {uuid}")
    
    # Test 2: Name sollte gesucht werden (Mock erforderlich)
    with patch.object(adapter, '_request') as mock_request:
        mock_request.return_value = {
            'people': [
                {
                    'id': 'resolved-id-123',
                    'name': {'firstName': 'Thomas', 'lastName': 'Braun'},
                    'emails': []
                }
            ]
        }
        
        result_name = adapter._resolve_target_id("Thomas Braun")
        
        # Sollte die ID zurückgeben
        assert result_name == 'resolved-id-123', f"Name nicht aufgelöst: {result_name}"
        print(f"✓ Name 'Thomas Braun' aufgelöst zu: {result_name}")
    
    print("✅ TEST 6 BESTANDEN: _resolve_target_id() funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 6 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 6 ERROR: {e}\n")


# === TEST 7: Error-Handling bei API-Fehlern ===
tests_total += 1
print(f"TEST 7: Error-Handling")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    with patch.object(adapter, '_request') as mock_request:
        # Simuliere API-Fehler (None zurück)
        mock_request.return_value = None
        
        result = adapter.create_contact("Test", "test@test.com")
        
        print(f"✓ Response bei Fehler: {result}")
        
        # Sollte Fehler-Message enthalten
        assert "❌" in result or "Fehler" in result, f"Fehler nicht korrekt gehandhabt: {result}"
        
        print("✅ TEST 7 BESTANDEN: Error-Handling funktioniert\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 7 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 7 ERROR: {e}\n")


# === TEST 8: Payload-Struktur (Name-Splitting) ===
tests_total += 1
print(f"TEST 8: Name-Splitting für CRM-Payload")
print("-" * 70)

try:
    adapter = TwentyCRM()
    
    with patch.object(adapter, '_request') as mock_request:
        mock_request.return_value = {'id': 'test-123'}
        
        # Name mit Vorname + Nachname
        adapter.create_contact("Max Mustermann", "max@test.com")
        
        # Prüfe ob _request mit richtigem Payload aufgerufen wurde
        call_args = mock_request.call_args
        payload = call_args[1]['data']
        
        print(f"✓ Payload: {payload}")
        
        # Prüfe Struktur
        assert payload['name']['firstName'] == "Max", f"Vorname falsch: {payload}"
        assert payload['name']['lastName'] == "Mustermann", f"Nachname falsch: {payload}"
        assert payload['emails']['primaryEmail'] == "max@test.com", f"Email falsch: {payload}"
        
        print("✅ TEST 8 BESTANDEN: Name-Splitting korrekt\n")
        tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 8 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 8 ERROR: {e}\n")


# === FINAL SUMMARY ===
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"📊 Ergebnis: {tests_passed}/{tests_total} Tests bestanden")

if tests_passed == tests_total:
    print("✅ Alle Tests erfolgreich!")
    print("✅ CRM Adapter-Interface ist korrekt implementiert")
    print("✅ Bereit für CRM-Wechsel (Twenty → Zoho)")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")

print("\n💡 Hinweise:")
print("   - Diese Tests nutzen MOCKS (keine echten API-Calls)")
print("   - Für echte API-Tests siehe test_agent_memory.py")
print("   - Adapter-Pattern ermöglicht einfachen CRM-Wechsel")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

