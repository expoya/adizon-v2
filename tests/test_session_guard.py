"""
Test: Session Guard (Sticky Sessions)
Kritisch für: Context-Erhalt, Router-Bypass, UX

Tests:
- check_session_status() gibt ACTIVE oder IDLE zurück
- ACTIVE bei offenen Fragen
- IDLE bei abgeschlossenen Tasks
- Edge-Cases (unklare Antworten)
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

from agents.session_guard import check_session_status

print("=" * 70)
print("SESSION GUARD TEST (Sticky Sessions)")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("⚠️  Hinweis: Macht echte LLM-Calls (verbraucht Tokens)\n")

# Test Counter
tests_passed = 0
tests_total = 0


# === TEST 1: ACTIVE bei offener Frage ===
tests_total += 1
print(f"TEST 1: ACTIVE bei offener Frage")
print("-" * 70)

try:
    user_message = "Erstelle eine Notiz für Max"
    ai_response = "Klar! Wie lautet der Inhalt der Notiz?"
    
    status = check_session_status(ai_response, user_message)
    
    print(f"✓ User: {user_message}")
    print(f"✓ AI: {ai_response}")
    print(f"✓ Status: {status}")
    
    # Sollte ACTIVE sein (offene Frage)
    assert status == "ACTIVE", f"Expected ACTIVE, got {status}"
    
    print("✅ TEST 1 BESTANDEN: Offene Frage → ACTIVE\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}\n")


# === TEST 2: IDLE bei abgeschlossenem Task ===
tests_total += 1
print(f"TEST 2: IDLE bei abgeschlossenem Task")
print("-" * 70)

try:
    user_message = "Erstelle Kontakt Max Mustermann"
    ai_response = "✅ Kontakt erfolgreich erstellt! Max Mustermann ist jetzt im CRM."
    
    status = check_session_status(ai_response, user_message)
    
    print(f"✓ User: {user_message}")
    print(f"✓ AI: {ai_response}")
    print(f"✓ Status: {status}")
    
    # Sollte IDLE sein (Task abgeschlossen)
    assert status == "IDLE", f"Expected IDLE, got {status}"
    
    print("✅ TEST 2 BESTANDEN: Abgeschlossener Task → IDLE\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}\n")


# === TEST 3: ACTIVE bei fehlendem Input ===
tests_total += 1
print(f"TEST 3: ACTIVE bei fehlendem Input")
print("-" * 70)

try:
    user_message = "Erstelle Task"
    ai_response = "Gerne! Wie soll der Task heißen und wann ist die Deadline?"
    
    status = check_session_status(ai_response, user_message)
    
    print(f"✓ User: {user_message}")
    print(f"✓ AI: {ai_response}")
    print(f"✓ Status: {status}")
    
    # Sollte ACTIVE sein (braucht mehr Info)
    assert status == "ACTIVE", f"Expected ACTIVE, got {status}"
    
    print("✅ TEST 3 BESTANDEN: Fehlende Daten → ACTIVE\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}\n")


# === TEST 4: IDLE bei "Danke" ===
tests_total += 1
print(f"TEST 4: IDLE bei explizitem Ende")
print("-" * 70)

try:
    user_message = "Danke, das war's"
    ai_response = "Gerne! Melde dich, wenn du wieder was brauchst."
    
    status = check_session_status(ai_response, user_message)
    
    print(f"✓ User: {user_message}")
    print(f"✓ AI: {ai_response}")
    print(f"✓ Status: {status}")
    
    # Sollte IDLE sein (explizites Ende)
    assert status == "IDLE", f"Expected IDLE, got {status}"
    
    print("✅ TEST 4 BESTANDEN: Explizites Ende → IDLE\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 4 ERROR: {e}\n")


# === TEST 5: IDLE bei Verabschiedung ===
tests_total += 1
print(f"TEST 5: IDLE bei Verabschiedung")
print("-" * 70)

try:
    user_message = "Ok, bis später!"
    ai_response = "Bis bald! 👋"
    
    status = check_session_status(ai_response, user_message)
    
    print(f"✓ User: {user_message}")
    print(f"✓ AI: {ai_response}")
    print(f"✓ Status: {status}")
    
    # Sollte IDLE sein (Verabschiedung)
    assert status == "IDLE", f"Expected IDLE, got {status}"
    
    print("✅ TEST 5 BESTANDEN: Verabschiedung → IDLE\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 5 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 5 ERROR: {e}\n")


# === TEST 6: Fallback bei unklarer Situation ===
tests_total += 1
print(f"TEST 6: Fallback-Verhalten")
print("-" * 70)

try:
    user_message = "Hmm..."
    ai_response = "Kann ich dir helfen?"
    
    status = check_session_status(ai_response, user_message)
    
    print(f"✓ User: {user_message}")
    print(f"✓ AI: {ai_response}")
    print(f"✓ Status: {status}")
    
    # Sollte entweder ACTIVE oder IDLE sein (beide ok)
    assert status in ["ACTIVE", "IDLE"], f"Expected ACTIVE or IDLE, got {status}"
    
    print(f"✅ TEST 6 BESTANDEN: Fallback funktioniert ({status})\n")
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
    print("✅ Session Guard funktioniert korrekt")
    print("✅ Sticky Sessions sind production-ready")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")

print("\n💡 Hinweise:")
print("   - Diese Tests machen echte LLM-Calls")
print("   - Temperature=0.0 für deterministisches Verhalten")
print("   - Fallback auf IDLE bei Fehlern (fail-safe)")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

