"""
Test: Undo-Funktionalität
Kritisch für: Multi-User Safety, Redis-State, Business-Logic

Tests:
- save_undo_context() speichert korrekt
- get_undo_context() liest korrekt
- clear_undo_context() löscht korrekt
- Multi-User Isolation (User A ≠ User B)
- Overwrite bei neuer Aktion
- TTL (1 Stunde) [Optional - dauert zu lange]
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import time

# .env MUSS vor allen anderen Imports geladen werden!
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory import save_undo_context, get_undo_context, clear_undo_context

print("=" * 70)
print("UNDO-FUNKTIONALITÄT TEST")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Test Counter
tests_passed = 0
tests_total = 0

# === TEST 1: Save & Retrieve ===
tests_total += 1
print(f"TEST 1: Save und Retrieve")
print("-" * 70)

try:
    user_id = "test_undo_user_1"
    
    # Speichern
    save_undo_context(user_id, "note", "abc-123-def-456")
    print("✓ save_undo_context() ausgeführt")
    
    # Abrufen
    typ, iid = get_undo_context(user_id)
    print(f"✓ get_undo_context() -> type={typ}, id={iid}")
    
    # Assertions
    assert typ == "note", f"Expected type='note', got '{typ}'"
    assert iid == "abc-123-def-456", f"Expected id='abc-123...', got '{iid}'"
    
    print("✅ TEST 1 BESTANDEN: Save & Retrieve funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}\n")


# === TEST 2: Multi-User Isolation ===
tests_total += 1
print(f"TEST 2: Multi-User Isolation")
print("-" * 70)

try:
    user_a = "test_user_alice"
    user_b = "test_user_bob"
    
    # Alice erstellt Note
    save_undo_context(user_a, "note", "alice-note-123")
    print(f"✓ Alice saved: note → alice-note-123")
    
    # Bob erstellt Task
    save_undo_context(user_b, "task", "bob-task-456")
    print(f"✓ Bob saved: task → bob-task-456")
    
    # Alice holt ihre Undo (sollte ihre Note sein, nicht Bobs Task!)
    typ_a, iid_a = get_undo_context(user_a)
    print(f"✓ Alice retrieved: {typ_a} → {iid_a}")
    
    # Bob holt seinen Undo
    typ_b, iid_b = get_undo_context(user_b)
    print(f"✓ Bob retrieved: {typ_b} → {iid_b}")
    
    # Assertions
    assert typ_a == "note", f"Alice: Expected 'note', got '{typ_a}'"
    assert iid_a == "alice-note-123", f"Alice: Expected 'alice-note-123', got '{iid_a}'"
    assert typ_b == "task", f"Bob: Expected 'task', got '{typ_b}'"
    assert iid_b == "bob-task-456", f"Bob: Expected 'bob-task-456', got '{iid_b}'"
    
    print("✅ TEST 2 BESTANDEN: Multi-User Isolation funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}\n")


# === TEST 3: Clear Context ===
tests_total += 1
print(f"TEST 3: Clear Context")
print("-" * 70)

try:
    user_id = "test_undo_user_clear"
    
    # Speichern
    save_undo_context(user_id, "contact", "contact-789")
    typ, iid = get_undo_context(user_id)
    assert iid == "contact-789", "Speichern fehlgeschlagen"
    print(f"✓ Saved: contact → contact-789")
    
    # Löschen
    clear_undo_context(user_id)
    print(f"✓ clear_undo_context() ausgeführt")
    
    # Prüfen (sollte jetzt None sein)
    typ_after, iid_after = get_undo_context(user_id)
    print(f"✓ Nach Clear: type={typ_after}, id={iid_after}")
    
    # Assertions
    assert typ_after is None, f"Expected None, got '{typ_after}'"
    assert iid_after is None, f"Expected None, got '{iid_after}'"
    
    print("✅ TEST 3 BESTANDEN: Clear funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}\n")


# === TEST 4: Overwrite bei neuer Aktion ===
tests_total += 1
print(f"TEST 4: Overwrite bei neuer Aktion")
print("-" * 70)

try:
    user_id = "test_undo_user_overwrite"
    
    # Erste Aktion
    save_undo_context(user_id, "note", "first-note-111")
    typ1, iid1 = get_undo_context(user_id)
    print(f"✓ Erste Aktion: {typ1} → {iid1}")
    
    # Zweite Aktion (sollte erste überschreiben)
    save_undo_context(user_id, "task", "second-task-222")
    typ2, iid2 = get_undo_context(user_id)
    print(f"✓ Zweite Aktion: {typ2} → {iid2}")
    
    # Assertions
    assert typ2 == "task", f"Expected 'task', got '{typ2}'"
    assert iid2 == "second-task-222", f"Expected 'second-task-222', got '{iid2}'"
    assert iid2 != iid1, "Zweite Aktion hat erste nicht überschrieben!"
    
    print("✅ TEST 4 BESTANDEN: Overwrite funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 4 ERROR: {e}\n")


# === TEST 5: Empty Context (kein Undo vorhanden) ===
tests_total += 1
print(f"TEST 5: Empty Context (kein Undo)")
print("-" * 70)

try:
    user_id = "test_undo_never_used"
    
    # Abrufen ohne vorheriges Speichern
    typ, iid = get_undo_context(user_id)
    print(f"✓ get_undo_context() für neuen User: type={typ}, id={iid}")
    
    # Assertions
    assert typ is None, f"Expected None, got '{typ}'"
    assert iid is None, f"Expected None, got '{iid}'"
    
    print("✅ TEST 5 BESTANDEN: Empty Context gibt (None, None)\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 5 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 5 ERROR: {e}\n")


# === TEST 6: Verschiedene Item-Types ===
tests_total += 1
print(f"TEST 6: Verschiedene Item-Types")
print("-" * 70)

try:
    user_id = "test_undo_types"
    
    # Teste alle Item-Types
    item_types = [
        ("note", "note-id-123"),
        ("task", "task-id-456"),
        ("contact", "contact-id-789"),
        ("person", "person-id-abc")
    ]
    
    for item_type, item_id in item_types:
        save_undo_context(user_id, item_type, item_id)
        typ, iid = get_undo_context(user_id)
        
        assert typ == item_type, f"Type mismatch for {item_type}"
        assert iid == item_id, f"ID mismatch for {item_id}"
        
        print(f"✓ {item_type} → {item_id} korrekt")
    
    print("✅ TEST 6 BESTANDEN: Alle Item-Types funktionieren\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 6 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 6 ERROR: {e}\n")


# === OPTIONAL TEST 7: TTL (1 Stunde) - SKIP (zu lange) ===
print(f"TEST 7: TTL (1 Stunde) - SKIPPED")
print("-" * 70)
print("⏭️  TTL-Test übersprungen (dauert 1 Stunde)")
print("💡 Manueller Test empfohlen: Warte 1h und prüfe ob Context weg ist\n")


# === FINAL SUMMARY ===
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"📊 Ergebnis: {tests_passed}/{tests_total} Tests bestanden")

if tests_passed == tests_total:
    print("✅ Alle Tests erfolgreich!")
    print("✅ Undo-System ist production-ready")
    print("✅ Multi-User Safety validiert")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")

print("\n💡 Hinweise:")
print("   - TTL-Test (1h) kann nur manuell validiert werden")
print("   - Redis muss laufen (Railway oder lokal)")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

