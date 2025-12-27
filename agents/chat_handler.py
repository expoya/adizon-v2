"""
Adizon - Chat Handler
Spezialist für: Smalltalk, Begrüßungen, allgemeine Konversation
"""

from openai import OpenAI
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
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        system_prompt = f"""Du bist Adizon, ein freundlicher, hilfreicher Assistent für Sales.

CHAT-MODUS:
- Antworte auf Deutsch
- Du duzt ({user_name})
- Halte Antworten kurz (2-4 Sätze)
- Biete dem User an deine Fähigkeiten zu nutzen: CRM-Aufgaben, Sales-Coaching, den letzten Kundentermin evaluieren, auf den nächsten Termin vorbereiten, Einwandbehandlung üben etc.

Du führst gerade einen lockeren Chat."""

        print(f"💬 Adizon (Chat) processing: {message[:50]}...")
        
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            top_p=0.9,
            temperature=0.6,
            max_tokens=200
        )
        
        ai_response = response.choices[0].message.content
        
        if not ai_response:
            return f"Hey {user_name}! Ich bin gerade etwas verwirrt. Kannst du das anders formulieren?"
        
        return ai_response.strip()
        
    except Exception as e:
        print(f"❌ Chat Handler Error: {e}")
        return f"Hey {user_name}! Entschuldige, mein chat_handler hat einen Fehler. Versuch's nochmal?"
