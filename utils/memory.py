"""
Adizon - Conversation Memory mit Redis
Production-Ready Persistent Memory
"""

from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
import os


def get_conversation_memory(user_id: str, session_id: str = "default") -> ConversationBufferMemory:
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
    redis_key = f"adizon:conversation:{user_id}:{session_id}"
    
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