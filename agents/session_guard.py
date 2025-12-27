"""
Session Guard
Entscheidet, ob eine Session aktiv bleiben muss oder beendet ist.
"""

from openai import OpenAI
import os

def check_session_status(last_ai_response: str, user_message: str) -> str:
    """
    Entscheidet basierend auf der letzten Antwort, ob wir im CRM-Modus bleiben.
    
    Returns:
        'ACTIVE' -> Router überspringen, direkt zurück zum Agent
        'IDLE'   -> Zurück zum Router (Intent Detection)
    """
    try:
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # Der Prompt entscheidet über "Tunnel" oder "Lobby"
        prompt = f"""Du bist der Session-Manager eines KI-Agents.
Entscheide anhand der letzten AI-Antwort, ob die Konversation fortgesetzt werden MUSS (ACTIVE) oder abgeschlossen ist (IDLE).

INPUTS:
User sagte: "{user_message}"
AI antwortete: "{last_ai_response}"

KRITERIEN FÜR 'ACTIVE' (Session behalten):
1. Die AI hat eine RÜCKFRAGE gestellt (z.B. "Wie ist die Email?", "Möchtest du noch was wissen?").
2. Der Prozess ist offensichtlich noch nicht fertig (fehlende Daten).
3. Es ist ein laufendes Coaching/Rollenspiel.

KRITERIEN FÜR 'IDLE' (Session beenden / Router einschalten):
1. Die AI hat einen Task erfolgreich abgeschlossen ("Kontakt erstellt", "Erledigt").
2. Die AI hat sich verabschiedet.
3. Der User hat explizit "Stop", "Danke", "Ende" gesagt.
4. Die Antwort ist eine abschließende Aussage ohne Frage.

ANTWORTE NUR MIT EINEM WORT: ACTIVE oder IDLE"""

        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"), # Nutzt Ministral (smart genug dafür)
            messages=[
                {"role": "system", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=5
        )
        
        decision = response.choices[0].message.content.strip().upper()
        
        # Fallback für Sicherheit
        if "ACTIVE" in decision:
            return "ACTIVE"
        return "IDLE"

    except Exception as e:
        print(f"⚠️ Session Guard Error: {e} -> Fallback to IDLE")
        return "IDLE"