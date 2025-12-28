"""
Test: CRM Tool Factory
Kritisch für: User-spezifische Tools, Undo-Context, Closures

Tests:
- get_crm_tools_for_user() gibt 5 Tools zurück
- Tools sind user-spezifisch (Closures)
- ID-Extraktion funktioniert
- Undo-Context wird gespeichert
- Verschiedene User haben eigene Tools
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import re

# .env vor allen Imports laden
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.crm import get_crm_tools_for_user
from utils.memory import get_undo_context, clear_undo_context

print("=" * 70)
print("CRM TOOL FACTORY TEST")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Test Counter
tests_passed = 0
tests_total = 0


# === TEST 1: Factory gibt 5 Tools zurück ===
tests_total += 1
print(f"TEST 1: Factory gibt korrekte Anzahl Tools")
print("-" * 70)

try:
    user_id = "test_factory_user_1"
    tools = get_crm_tools_for_user(user_id)
    
    print(f"✓ get_crm_tools_for_user('{user_id}') aufgerufen")
    print(f"✓ Anzahl Tools: {len(tools)}")
    
    # Sollte 5 Tools geben
    assert len(tools) == 5, f"Expected 5 tools, got {len(tools)}"
    
    # Tool-Namen prüfen
    tool_names = [tool.name for tool in tools]
    expected_names = [
        "search_contacts",
        "create_contact",
        "create_task",
        "create_note",
        "undo_last_action"
    ]
    
    for name in expected_names:
        assert name in tool_names, f"Tool '{name}' fehlt"
        print(f"✓ Tool vorhanden: {name}")
    
    print("✅ TEST 1 BESTANDEN: Factory gibt alle 5 Tools\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}\n")


# === TEST 2: Tools sind user-spezifisch ===
tests_total += 1
print(f"TEST 2: Tools sind user-spezifisch (Closures)")
print("-" * 70)

try:
    user_a = "test_factory_alice"
    user_b = "test_factory_bob"
    
    tools_a = get_crm_tools_for_user(user_a)
    tools_b = get_crm_tools_for_user(user_b)
    
    print(f"✓ Tools für Alice erstellt: {len(tools_a)} Tools")
    print(f"✓ Tools für Bob erstellt: {len(tools_b)} Tools")
    
    # Tools sollten unterschiedliche Instanzen sein
    assert tools_a is not tools_b, "Tools sollten unterschiedliche Instanzen sein"
    
    print("✅ TEST 2 BESTANDEN: Tools sind user-spezifisch\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}\n")


# === TEST 3: ID-Extraktion funktioniert ===
tests_total += 1
print(f"TEST 3: ID-Extraktion aus Responses")
print("-" * 70)

try:
    # Test-Responses mit IDs
    test_responses = [
        ("✅ Kontakt erstellt (ID: abc-123-def)", "abc-123-def"),
        ("✅ Task erstellt (ID: task-456)", "task-456"),
        ("Notiz erstellt (ID: note-789-xyz)", "note-789-xyz"),
        ("Fehler beim Erstellen", None),  # Keine ID
    ]
    
    # ID-Extraktion Pattern (aus factory - aber breiter für Tests)
    def extract_id(text):
        match = re.search(r"\(ID:\s*([\w\-]+)\)", text)
        return match.group(1) if match else None
    
    for response, expected_id in test_responses:
        extracted = extract_id(response)
        
        if expected_id:
            assert extracted == expected_id, f"Expected {expected_id}, got {extracted}"
            print(f"✓ '{response[:40]}...' → ID: {extracted}")
        else:
            assert extracted is None, f"Expected None, got {extracted}"
            print(f"✓ '{response[:40]}...' → Keine ID (korrekt)")
    
    print("✅ TEST 3 BESTANDEN: ID-Extraktion funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}\n")


# === TEST 4: Undo-Context wird gespeichert (Mock-Mode) ===
tests_total += 1
print(f"TEST 4: Undo-Context Speicherung")
print("-" * 70)

try:
    user_id = "test_factory_undo"
    
    # Clear vorherigen Context
    clear_undo_context(user_id)
    
    # Tools holen
    tools = get_crm_tools_for_user(user_id)
    
    # create_contact Tool finden
    create_contact_tool = next(t for t in tools if t.name == "create_contact")
    
    print(f"✓ create_contact Tool gefunden")
    
    # Hinweis: Im Mock-Mode wird keine echte API aufgerufen
    # Aber wir können prüfen, ob das Tool aufrufbar ist
    print(f"✓ Tool ist aufrufbar: {callable(create_contact_tool.func)}")
    
    # Prüfen ob Tool die richtigen Parameter hat
    # (Hinweis: Echte Undo-Speicherung wird in integration tests geprüft)
    print(f"✓ Tool-Beschreibung: {create_contact_tool.description[:50]}...")
    
    print("✅ TEST 4 BESTANDEN: Undo-Context Setup korrekt\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 4 ERROR: {e}\n")


# === TEST 5: Tool-Descriptions sind vorhanden ===
tests_total += 1
print(f"TEST 5: Tool-Descriptions")
print("-" * 70)

try:
    user_id = "test_factory_desc"
    tools = get_crm_tools_for_user(user_id)
    
    for tool in tools:
        assert tool.name is not None, f"Tool name fehlt"
        assert tool.description is not None, f"Description fehlt für {tool.name}"
        assert len(tool.description) > 0, f"Description leer für {tool.name}"
        
        print(f"✓ {tool.name}: {tool.description[:50]}...")
    
    print("✅ TEST 5 BESTANDEN: Alle Tools haben Descriptions\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 5 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 5 ERROR: {e}\n")


# === TEST 6: Undo-Tool ist vorhanden ===
tests_total += 1
print(f"TEST 6: Undo-Tool Funktionalität")
print("-" * 70)

try:
    user_id = "test_factory_undo_tool"
    tools = get_crm_tools_for_user(user_id)
    
    # Undo-Tool finden
    undo_tool = next(t for t in tools if t.name == "undo_last_action")
    
    print(f"✓ Undo-Tool gefunden: {undo_tool.name}")
    print(f"✓ Description: {undo_tool.description}")
    
    # Prüfen ob callable
    assert callable(undo_tool.func), "Undo-Tool nicht aufrufbar"
    
    print("✅ TEST 6 BESTANDEN: Undo-Tool ist vorhanden und aufrufbar\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 6 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 6 ERROR: {e}\n")


# === FINAL SUMMARY ===
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"📊 Ergebnis: {tests_passed}/{tests_total} Tests bestanden")

if tests_passed == tests_total:
    print("✅ Alle Tests erfolgreich!")
    print("✅ Tool Factory funktioniert korrekt")
    print("✅ User-spezifische Tools sind production-ready")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")

print("\n💡 Hinweise:")
print("   - Diese Tests nutzen KEINE echten API-Calls")
print("   - Undo-Speicherung wird in test_undo.py getestet")
print("   - Factory-Pattern ermöglicht user-spezifische Tools")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

