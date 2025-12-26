"""
Adizon - CRM Handler
Spezialist für: Kontakte, Leads, Deals, CRM-Operationen
"""

from openai import OpenAI
import os


def handle_crm(message: str, user_name: str, user_id: str) -> str:
    """
    Adizon's CRM-Funktion
    
    Args:
        message: User Nachricht
        user_name: Name des Users
        user_id: User ID
        
    Returns:
        Adizon's Antwort
    """
    
    try:
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        system_prompt = f"""Du bist Adizon, ein KI-Assistent für KMUs.

CRM-MODUS:
- Professionell und strukturiert
- Antworte auf Deutsch
- Du duzt ({user_name})

WICHTIG - DUMMY PHASE:
Du hast noch KEINE echten CRM-Tools!
Antworte dass du verstehst was gewünscht wird, aber die Funktion noch in Entwicklung ist.

Beispiel: "Alles klar! Du möchtest [AKTION]. 
Diese Funktion baue ich gerade auf. Bald kann ich das direkt für dich erledigen! 🔧"

User ID: {user_id}"""

        print(f"🏢 Adizon (CRM) processing: {message[:50]}...")
        
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.3,
            max_tokens=250
        )
        
        ai_response = response.choices[0].message.content
        
        if not ai_response:
            return f"Hi {user_name}, ich hatte gerade technische Probleme. Versuch's bitte nochmal!"
        
        return ai_response.strip()
        
    except Exception as e:
        print(f"❌ CRM Handler Error: {e}")
        return f"Hi {user_name}, ich hatte gerade technische Probleme im crm handler. Versuch's bitte nochmal!"