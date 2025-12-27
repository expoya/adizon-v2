"""
Test Redis Memory 
"""
import os
from dotenv import load_dotenv
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory import get_conversation_memory
load_dotenv()

print("=== REDIS MEMORY TEST ===\n")

# Test User ID
user_id = "test_new_user1"

print("1. Memory holen...")
try:
    memory = get_conversation_memory(user_id, "test_session")
    print(f"✅ Memory created: {memory}\n")
except Exception as e:
    print(f"❌ Fehler beim Erstellen des Memory: {e}")
    sys.exit(1)

try:
    memory.save_context(
        {"input": "Hallo! Ich bin Michael"},
        {"output": "Hey Michael! Schön dich kennenzulernen!"}
    )
    print("✅ Saved to Redis\n")
except Exception as e:
    print(f"❌ Fehler beim Speichern in Redis: {e}")
    print("   Ist Docker gestartet? (docker ps)")
    sys.exit(1)

print("3. Memory nochmal holen (sollte History haben)...")
memory2 = get_conversation_memory(user_id, "test_session")
history = memory2.chat_memory.messages
print(f"✅ Messages in History: {len(history)}")
for msg in history:
    print(f"   - {msg.type}: {msg.content}")
print()

print("4. Mehr Messages hinzufügen...")
memory2.save_context(
    {"input": "Erstelle einen Kontakt für Anna"},
    {"output": "Welche Email hat Anna?"}
)
memory2.save_context(
    {"input": "anna@test.com"},
    {"output": "✅ Kontakt erstellt!"}
)
print("✅ Saved 2 more messages\n")

print("5. Memory wieder holen...")
memory3 = get_conversation_memory(user_id, "test_session")
history = memory3.chat_memory.messages
print(f"✅ Total Messages: {len(history)}")
for msg in history:
    print(f"   - {msg.type}: {msg.content[:50]}...")
print()

print("6. Anderer User - sollte eigene History haben...")
memory_other = get_conversation_memory("other_user", "test_session")
history_other = memory_other.chat_memory.messages
print(f"✅ Other User Messages: {len(history_other)} (sollte 0 sein!)")
print()

print("=== TEST COMPLETE ===")