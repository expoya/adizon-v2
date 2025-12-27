"""
Adizon V2 - AI Assistant für KMUs
"""
# Environment Variables laden
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from agents.chat_handler import handle_chat
from utils.memory import get_session_state, clear_user_session
from agents.crm_handler import handle_crm
import requests

# FastAPI App
app = FastAPI(
    title="Adizon",
    description="AI Assistant für KMUs",
    version="2.0.0"
)


# === PYDANTIC MODELS ===

class TelegramMessage(BaseModel):
    """Telegram Webhook Format"""
    message: str
    user_id: str
    user_name: str = "Unknown"


# === HELPER FUNCTIONS ===

def detect_intent(message: str) -> str:
    """Erkennt Intent: CHAT oder CRM"""
    
    print(f"\n🔍 === INTENT DETECTION START ===")
    print(f"📝 Message: {message}")
    
    try:
        print(f"🔑 API Key exists: {bool(os.getenv('OPENROUTER_API_KEY'))}")
        print(f"🌐 Base URL: {os.getenv('OPENROUTER_BASE_URL')}")
        print(f"🤖 Model: {os.getenv('MODEL_NAME')}")
        
        client = OpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        print(f"✅ Client created")
        
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages=[
                {
                    "role": "system",
                    "content": """Du bist ein strikter Intent Classifier für eine Business-Software.

ENTSCHEIDUNGS-REGELN:

KATEGORIE 'CRM' (Business Logic):
1.  Jede Erwähnung von "CRM", "Datenbank", "System", "Speichern", "Suchen".
2.  Jede Frage nach EXISTENZ ("Haben wir...", "Kennst du...", "Gibt es...").
3.  Jede Nennung von NAMEN (Personen, Firmen) oder E-MAILS.
4.  Befehle: "Erstelle", "Suche", "Verkaufe", "Notiz".

KATEGORIE 'CHAT' (Smalltalk):
1.  NUR reine Begrüßungen ("Hallo", "Moin").
2.  NUR Fragen zum Befinden ("Wie gehts", "Alles fit").
3.  NUR philosophische Fragen ("Wer bist du", "Was kannst du").

WICHTIG: Im Zweifel IMMER 'CRM' wählen, damit der Agent in der Datenbank nachsehen kann!

Antworte NUR mit einem Wort: CHAT oder CRM"""
                },
                {"role": "user", "content": message}
            ],
            temperature=0.0,  
            max_tokens=5    
        )
        
        print(f"✅ API Call successful")
        
        # Content auslesen
        content = response.choices[0].message.content or ""
        
        print(f"🎯 Raw Intent: '{content}'")
        print(f"🔍 === INTENT DETECTION END ===\n")
        
        # Intent extrahieren (letztes Wort oder ganze Antwort)
        intent = content.strip().upper()
        
        if "CRM" in intent:
            return "CRM"
        elif "CHAT" in intent:
            return "CHAT"
        else:
            print(f"⚠️ Unbekannter Intent: {intent}")
            return "CHAT"
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        print(traceback.format_exc())
        print(f"🔍 === INTENT DETECTION END (ERROR) ===\n")
        return "CHAT"

# === ENDPOINTS ===

@app.get("/")
def root():
    """Health Check"""
    return {
        "status": "online",
        "service": "Adizon V2",
        "version": "2.0.0"
    }


@app.post("/test")
def test_intent(message: str):
    """Test Intent Detection"""
    intent = detect_intent(message)
    return {
        "message": message,
        "intent": intent
    }

@app.post("/telegram-webhook")
def telegram_webhook(request: dict):
    """
    Telegram Webhook - Production Endpoint
    """
    try:
        # Telegram Message Format parsen
        message_data = request.get("message", {})
        chat_id = message_data.get("chat", {}).get("id")
        user_message = message_data.get("text", "")
        user_name = message_data.get("from", {}).get("first_name", "Unknown")
        user_id = str(message_data.get("from", {}).get("id", ""))
        
        # Wenn keine Message, ignorieren
        if not chat_id or not user_message:
            return {"status": "ignored"}
        
        print(f"\n{'='*50}")
        print(f"📱 Telegram Message from {user_name}: {user_message}")

        # 1. KILL SWITCH CHECK
        if user_message.strip().upper() in ["NEUSTART", "/RESET", "RESET"]:
            clear_user_session(user_id)
            response_text = "Alles klar! Mein Gedächtnis ist gelöscht. Womit fangen wir neu an? 🧠✨"
            requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", 
                          json={"chat_id": chat_id, "text": response_text})
            return {"status": "reset"}

        # 2. STATE CHECK (Sticky Session)
        current_state = get_session_state(user_id)
        print(f"🧠 Current Session State: {current_state}")

        if current_state == "ACTIVE":
            print("⏩ Skipping Router (State is ACTIVE) -> Direct to CRM")
            response_text = handle_crm(user_message, user_name, user_id)
        
        else:
            # 3. NORMAL ROUTING (State is IDLE)
            intent = detect_intent(user_message)
            
            if intent == "CHAT":
                response_text = handle_chat(user_message, user_name)
            elif intent == "CRM":
                response_text = handle_crm(user_message, user_name, user_id)
            else:
                response_text = "Error."
    
        # ANTWORT AN TELEGRAM SENDEN
        telegram_api_url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage"
        
        telegram_response = requests.post(
            telegram_api_url,
            json={
                "chat_id": chat_id,
                "text": response_text
            }
        )
        
        if telegram_response.status_code == 200:
            print("✅ Message sent to Telegram!")
        else:
            print(f"❌ Telegram API Error: {telegram_response.text}")
        
        print(f"{'='*50}\n")
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Telegram Webhook Error: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/adizon")
def adizon_test(message: str, user_name: str = "Test User"):
    """
    Kompletter Adizon Flow Lokal
    """
    print(f"\n{'='*50}")
    print(f"📥 New Message from {user_name}")
    
    user_id = "local_dev_user_1"

    # Kill Switch Check
    if message.strip().upper() == "NEUSTART":
        clear_user_session(user_id)
        return {"response": "Session Reset executed."}

    # State Check
    current_state = get_session_state(user_id)
    print(f"🧠 State: {current_state}")
    
    if current_state == "ACTIVE":
        response_text = handle_crm(message, user_name, user_id)
        handler = "CRM (Sticky)"
    else:
        intent = detect_intent(message)
        if intent == "CHAT":
            response_text = handle_chat(message, user_name)
            handler = "Chat"
        else:
            response_text = handle_crm(message, user_name, user_id)
            handler = "CRM"
            
    print(f"✅ Response ({handler}): {response_text[:100]}...")
    return {
        "status": "success",
        "handler": handler,
        "response": response_text,
        "new_state": get_session_state(user_id)
    } 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)