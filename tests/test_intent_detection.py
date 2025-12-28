"""
Test: Intent Detection (Router)
Kritisch für: CHAT vs CRM Routing, User Experience

Tests:
- CRM bei Business-Befehlen
- CRM bei Namen/E-Mails
- CHAT bei Begrüßungen
- CHAT bei Smalltalk
- Edge-Cases
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# .env vor allen Imports laden
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import detect_intent from main
from main import detect_intent

print("=" * 70)
print("INTENT DETECTION TEST (Router)")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("⚠️  Hinweis: Macht echte LLM-Calls (verbraucht Tokens)\n")

# Test Counter
tests_passed = 0
tests_total = 0


# === CRM Tests ===
crm_test_cases = [
    ("Erstelle einen Kontakt für Max Mustermann", "Business-Befehl"),
    ("Suche nach Thomas", "Name genannt"),
    ("Haben wir eine Email von anna@test.com?", "E-Mail genannt"),
    ("Notiere: Kunde interessiert an Solar", "Notiz-Befehl"),
    ("Erstelle Task für morgen", "Task-Befehl"),
    ("Kennst du die Firma Expoya?", "Existenz-Frage"),
]

print("CRM-TESTS (sollten alle CRM geben)")
print("-" * 70)

for message, reason in crm_test_cases:
    tests_total += 1
    try:
        intent = detect_intent(message)
        
        print(f"✓ '{message[:40]}...' → {intent} ({reason})")
        
        assert intent == "CRM", f"Expected CRM, got {intent}"
        tests_passed += 1
        
    except AssertionError as e:
        print(f"❌ FEHLGESCHLAGEN: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

print()


# === CHAT Tests ===
chat_test_cases = [
    ("Hallo!", "Begrüßung"),
    ("Guten Morgen", "Begrüßung"),
    ("Wie geht's?", "Befinden"),
    ("Alles fit?", "Befinden"),
    ("Wer bist du?", "Philosophisch"),
    ("Was kannst du?", "Philosophisch"),
]

print("CHAT-TESTS (sollten alle CHAT geben)")
print("-" * 70)

for message, reason in chat_test_cases:
    tests_total += 1
    try:
        intent = detect_intent(message)
        
        print(f"✓ '{message[:40]}...' → {intent} ({reason})")
        
        assert intent == "CHAT", f"Expected CHAT, got {intent}"
        tests_passed += 1
        
    except AssertionError as e:
        print(f"❌ FEHLGESCHLAGEN: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

print()


# === Edge-Cases (im Zweifel CRM) ===
edge_cases = [
    ("Max", "Nur Name → CRM (Zweifel)"),
    ("test@example.com", "Nur Email → CRM (Zweifel)"),
    ("System", "System-Keyword → CRM"),
]

print("EDGE-CASES (im Zweifel CRM)")
print("-" * 70)

for message, reason in edge_cases:
    tests_total += 1
    try:
        intent = detect_intent(message)
        
        print(f"✓ '{message[:40]}...' → {intent} ({reason})")
        
        # Im Zweifel sollte es CRM sein (laut Prompt-Regel)
        assert intent == "CRM", f"Expected CRM (Zweifel), got {intent}"
        tests_passed += 1
        
    except AssertionError as e:
        print(f"❌ FEHLGESCHLAGEN: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

print()


# === FINAL SUMMARY ===
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"📊 Ergebnis: {tests_passed}/{tests_total} Tests bestanden")

if tests_passed == tests_total:
    print("✅ Alle Tests erfolgreich!")
    print("✅ Intent Detection ist akkurat")
    print("✅ Router funktioniert production-ready")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")
    print("💡 LLM-Verhalten kann variieren - evtl. Prompt anpassen")

print("\n💡 Hinweise:")
print("   - Diese Tests machen echte LLM-Calls")
print("   - Temperature=0.0 für deterministisches Routing")
print("   - Im Zweifel: CRM (damit Agent in DB schauen kann)")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

