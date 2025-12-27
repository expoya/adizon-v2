"""
Adizon - Conversation Memory mit Redis
Production-Ready Persistent Memory
"""

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import SystemMessage
import os
import redis

redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

def get_conversation_memory(user_id: str, session_id: str = "main") -> ConversationBufferMemory:
    """
    Holt Conversation Memory für User aus Redis
    
    Args:
        user_id: Telegram User ID
        session_id: Optional session identifier
        
    Returns:
        ConversationBufferMemory mit Redis Backend
    """
    
    # Redis Connection String aus Environment
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Unique Key per User + Session
    redis_key = f"adizon:conversation:{user_id}:main"
    
    # Redis Message History
    message_history = RedisChatMessageHistory(
        session_id=redis_key,
        url=redis_url,
        ttl=86400  # 24 Stunden TTL (optional)
    )
    
    # LangChain Memory mit Redis Backend
    memory = ConversationBufferMemory(
        chat_memory=message_history,
        return_messages=True,
        memory_key="chat_history",
        input_key="input",
        output_key="output",
        max_token_limit=2000  # Begrenzt auf ~10-15 Messages
    )
    
    return memory

def set_session_state(user_id: str, state: str):
    """Setzt den Sessions-State"""
    key = f"adizon:state:{user_id}"
    redis_client.set(key, state)
    print(f"🧠 State set for {user_id}: {state}")

def get_session_state(user_id: str) -> str:
    """Holt den Status (Default: IDLE)"""
    key = f"adizon:state:{user_id}"
    state = redis_client.get(key)
    if state:
        return state.decode('utf-8')
    return "IDLE"

def clear_user_session(user_id: str):
    """KILL SWITCH: Löscht Memory UND State"""
    # 1. State löschen
    redis_client.delete(f"adizon:state:{user_id}")
    
    # 2. History löschen (LangChain Key)
    redis_client.delete(f"adizon:conversation:{user_id}:main")
    print(f"💥 Session Nuke executed for {user_id}")