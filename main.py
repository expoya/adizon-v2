"""
Adizon V2 - AI Assistant für KMUs
"""

from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
from agents.chat_handler import handle_chat
from agents.crm_handler import handle_crm
import requests

# Environment Variables laden
load_dotenv()

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
                    "content": """Du bist ein Intent Classifier. Antworte NUR mit: CHAT oder CRM

CRM: erstelle, zeige, suche Kontakt/Lead/Deal
CHAT: hallo, wie geht's, smalltalk

Antworte NUR: CHAT oder CRM"""
                },
                {"role": "user", "content": message}
            ],
            temperature=0.0,
            max_tokens=5
        )
        
        print(f"✅ API Call successful")
        
        intent = response.choices[0].message.content.strip().upper()
        
        print(f"🎯 Raw Intent: '{intent}'")
        print(f"🔍 === INTENT DETECTION END ===\n")
        
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
        print(f"📱 Telegram Message from {user_name}")
        print(f"{'='*50}")
        
        # Intent Detection
        intent = detect_intent(user_message)
        print(f"🎯 Intent: {intent}")
        
        # Handler aufrufen
        if intent == "CHAT":
            response_text = handle_chat(
                message=user_message,
                user_name=user_name
            )
            handler = "Chat"
            
        elif intent == "CRM":
            response_text = handle_crm(
                message=user_message,
                user_name=user_name,
                user_id=user_id
            )
            handler = "CRM"
            
        else:
            response_text = "Entschuldigung, ich konnte deine Anfrage nicht verarbeiten."
            handler = "Unknown"
        
        print(f"✅ Response from {handler}: {response_text[:100]}...")
        
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
    Kompletter Adizon Flow - Lokal testen
    """
    print(f"\n{'='*50}")
    print(f"📥 New Message from {user_name}")
    print(f"{'='*50}")
    
    try:
        # Schritt 1: Intent Detection
        intent = detect_intent(message)
        print(f"🎯 Intent: {intent}")
        
        # Schritt 2: Handler aufrufen
        if intent == "CHAT":
            response_text = handle_chat(
                message=message,
                user_name=user_name
            )
            handler = "Chat"
            
        elif intent == "CRM":
            response_text = handle_crm(
                message=message,
                user_name=user_name,
                user_id="test_123"
            )
            handler = "CRM"
            
        else:
            response_text = "Entschuldigung, ich konnte deine Anfrage nicht verarbeiten."
            handler = "Unknown"
        
        print(f"✅ Response from {handler}: {response_text[:100]}...")
        print(f"{'='*50}\n")
        
        return {
            "status": "success",
            "intent": intent,
            "handler": handler,
            "response": response_text
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)