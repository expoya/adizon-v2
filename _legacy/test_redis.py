"""
Check was in Redis gespeichert ist
"""

import sys
import os

from dotenv import load_dotenv
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory import get_conversation_memory

user_id = "test_123"
session_id = "crm"

memory = get_conversation_memory(user_id, session_id)
history = memory.chat_memory.messages

print(f"=== REDIS CHECK ===")
print(f"User: {user_id}")
print(f"Session: {session_id}")
print(f"Messages: {len(history)}\n")

for i, msg in enumerate(history):
    print(f"{i+1}. [{msg.type}]: {msg.content}")
    print()