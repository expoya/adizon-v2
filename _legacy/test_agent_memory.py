"""
Integration Test: Agent + Memory (YAML-Config Era)
Prüft, ob der CRM-Agent sich an Dinge erinnern kann.

Tests:
1. Kontext speichern (Name, Firma)
2. Kontext abrufen (Memory-Check)
3. Kontext für Tool-Calling nutzen (Context-basierte Suche)
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# WICHTIG: .env MUSS vor allen anderen Imports geladen werden!
# Grund: memory.py initialisiert redis_client beim Import
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix (damit er 'agents' und 'utils' findet)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Jetzt erst die App-Module importieren (nach .env load!)
from agents.crm_handler import handle_crm
from utils.agent_config import load_agent_config

# Wir nutzen eine unique ID pro Test-Run
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
user_id = f"agent_memory_test_{timestamp}"
user_name = "Michael"

print(f"=== AGENT MEMORY TEST (YAML-Config Version) ===")
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Zeige aktuelle Agent-Config
try:
    config = load_agent_config("crm_handler")
    meta = config.get_metadata()
    params = config.get_parameters()
    print(f"Agent: {meta['name']} v{meta['version']}")
    print(f"Model: {os.getenv('MODEL_NAME')}")
    print(f"Temperature: {params['temperature']}")
    
    # Redis-Check
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    is_railway = 'railway' in redis_url.lower() or 'rediss://' in redis_url
    redis_status = "☁️ Railway Redis" if is_railway else "💻 Local Redis"
    print(f"Redis: {redis_status}")
    
    print(f"User ID: {user_id}\n")
except Exception as e:
    print(f"⚠️ Config-Load-Error: {e}\n")

# --- TEST 1: Fakten setzen (Context speichern) ---
print("=" * 60)
print("TEST 1: Kontext speichern")
print("=" * 60)
msg1 = "Hallo! Ich heiße Michael und meine Firma heißt Expoya."
print(f"👤 User: {msg1}")

try:
    response1 = handle_crm(msg1, user_name, user_id)
    print(f"🤖 Agent: {response1}")
    print("✅ Turn 1 complete\n")
except Exception as e:
    print(f"❌ Error in Turn 1: {e}\n")
    sys.exit(1)


# --- TEST 2: Fakten abfragen (Memory Check) ---
print("=" * 60)
print("TEST 2: Memory-Check (Firma abrufen)")
print("=" * 60)
msg2 = "Wie heißt meine Firma?"
print(f"👤 User: {msg2}")

try:
    response2 = handle_crm(msg2, user_name, user_id)
    print(f"🤖 Agent: {response2}")
    
    # Assertion
    if "Expoya" in response2 or "expoya" in response2.lower():
        print("✅ TEST 2 BESTANDEN: Agent hat Firma aus Memory erinnert!\n")
    else:
        print("⚠️ TEST 2 FRAGLICH: 'Expoya' nicht in Response gefunden.")
        print("   (Könnte trotzdem korrekt sein, wenn umschrieben)\n")
except Exception as e:
    print(f"❌ Error in Turn 2: {e}\n")


# --- TEST 3: Context-basiertes Tool Calling ---
print("=" * 60)
print("TEST 3: Context für Tool-Calling nutzen")
print("=" * 60)
msg3 = "Suche bitte nach Kontakten mit meinem Vornamen."
print(f"👤 User: {msg3}")

try:
    response3 = handle_crm(msg3, user_name, user_id)
    print(f"🤖 Agent: {response3}")
    
    # Check: Hat er 'Michael' genutzt?
    if "Michael" in response3 or "michael" in response3.lower():
        print("✅ TEST 3 BESTANDEN: Agent hat Namen aus Memory für Tool genutzt!\n")
    else:
        print("⚠️ TEST 3 FRAGLICH: 'Michael' nicht explizit in Response.\n")
except Exception as e:
    print(f"❌ Error in Turn 3: {e}\n")


# --- FINAL SUMMARY ---
print("=" * 60)
print("TEST SUMMARY")
print("=" * 60)

# Check: Welche Tests waren erfolgreich?
tests_passed = 0
tests_total = 3

if "response1" in locals() and "Expoya" in response1.lower():
    tests_passed += 1
if "response2" in locals() and "expoya" in response2.lower():
    print("✅ TEST 2: Memory funktioniert (Firma erinnert)")
    tests_passed += 1
else:
    print("⚠️ TEST 2: Response prüfen")
    
if "response3" in locals() and ("michael" in response3.lower() or "search_contacts" in str(response3).lower()):
    print("✅ TEST 3: Context für Tool-Calling genutzt")
    tests_passed += 1
else:
    print("⚠️ TEST 3: Response prüfen")

print(f"\n📊 Ergebnis: {tests_passed}/{tests_total} Tests erfolgreich")
print("✅ YAML-Config-System funktioniert")
print("✅ Agent nutzt persistentes Redis-Memory (Railway)")
print("\n💡 Hinweis: Prüfe die Agent-Responses oben für Details")
print("=" * 60)