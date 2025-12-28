"""
Adizon - Chat Handler
Spezialist für: Smalltalk, Begrüßungen, allgemeine Konversation
"""

from openai import OpenAI
from utils.agent_config import load_agent_config
import os


def handle_chat(message: str, user_name: str) -> str:
    """
    Adizon's Chat-Funktion
    
    Args:
        message: User Nachricht
        user_name: Name des Users
        
    Returns:
        Adizon's Antwort
    """
    
    try:
        # Load Agent Config from YAML
        config = load_agent_config("chat_handler")
        
        model_config = config.get_model_config()
        params = config.get_parameters()
        
        client = OpenAI(
            base_url=model_config['base_url'],
            api_key=model_config['api_key']
        )
        
        # System Prompt aus YAML mit Template-Variablen
        system_prompt = config.get_system_prompt(user_name=user_name)

        print(f"💬 Adizon (Chat) processing: {message[:50]}...")
        
        response = client.chat.completions.create(
            model=model_config['name'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            **params  # temperature, top_p, max_tokens, etc.
        )
        
        ai_response = response.choices[0].message.content
        
        if not ai_response:
            return f"Hey {user_name}! Ich bin gerade etwas verwirrt. Kannst du das anders formulieren?"
        
        return ai_response.strip()
        
    except Exception as e:
        print(f"❌ Chat Handler Error: {e}")
        return f"Hey {user_name}! Entschuldige, mein chat_handler hat einen Fehler. Versuch's nochmal?"
