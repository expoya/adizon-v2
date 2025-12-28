"""
Session Guard
Entscheidet, ob eine Session aktiv bleiben muss oder beendet ist.
"""

from openai import OpenAI
from utils.agent_config import load_agent_config
import os

def check_session_status(last_ai_response: str, user_message: str) -> str:
    """
    Entscheidet basierend auf der letzten Antwort, ob wir im CRM-Modus bleiben.
    
    Returns:
        'ACTIVE' -> Router überspringen, direkt zurück zum Agent
        'IDLE'   -> Zurück zum Router (Intent Detection)
    """
    try:
        # Load Agent Config from YAML
        config = load_agent_config("session_guard")
        
        model_config = config.get_model_config()
        params = config.get_parameters()
        
        client = OpenAI(
            base_url=model_config['base_url'],
            api_key=model_config['api_key']
        )
        
        # System Prompt aus YAML mit Template-Variablen
        system_prompt = config.get_system_prompt(
            user_message=user_message,
            last_ai_response=last_ai_response
        )

        response = client.chat.completions.create(
            model=model_config['name'],
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            **params
        )
        
        decision = response.choices[0].message.content.strip().upper()
        
        # Fallback für Sicherheit
        if "ACTIVE" in decision:
            return "ACTIVE"
        return "IDLE"

    except Exception as e:
        print(f"⚠️ Session Guard Error: {e} -> Fallback to IDLE")
        return "IDLE"