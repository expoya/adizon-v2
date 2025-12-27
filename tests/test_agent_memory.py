"""
Integration Test: Agent + Memory
Prüft, ob der CRM-Agent sich an Dinge erinnern kann.
"""

import sys
import os
from dotenv import load_dotenv

# Path Fix (damit er 'agents' und 'utils' findet)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.crm_handler import handle_crm

load_dotenv()

# Wir nutzen eine neue ID, damit wir bei 0 starten
user_id = "agent_memory_test_v1"
user_name = "Michael"

print(f"=== AGENT MEMORY TEST ===")
print(f"Model: {os.getenv('MODEL_NAME')}")
print(f"User ID: {user_id}\n")

# --- TURN 1: Fakten setzen ---
msg1 = "Hallo, ich heiße Michael und meine Firma heißt Expoya."
print(f"1️⃣  User: {msg1}")

response1 = handle_crm(msg1, user_name, user_id)
print(f"🤖 Agent: {response1}\n")


# --- TURN 2: Fakten abfragen (Memory Check) ---
msg2 = "Wie heißt meine Firma?"
print(f"2️⃣  User: {msg2}")

response2 = handle_crm(msg2, user_name, user_id)
print(f"🤖 Agent: {response2}\n")

# Check: Hat er es gewusst?
if "Expoya" in response2:
    print("✅ TEST BESTANDEN: Der Agent hat das Gedächtnis genutzt!")
else:
    print("❌ TEST FEHLGESCHLAGEN: Der Agent wusste die Antwort nicht.")


# --- TURN 3: Context-basiertes Tool Calling ---
# Hier testen wir, ob er den Namen aus dem Gedächtnis für das Tool nutzen kann
msg3 = "Suche bitte nach Kontakten mit meinem Vornamen."
print(f"3️⃣  User: {msg3}")

response3 = handle_crm(msg3, user_name, user_id)
print(f"🤖 Agent: {response3}\n")