"""
Adizon V2 - AI Assistant für KMUs
Version 3.0 - Chat-Adapter System
"""
# Environment Variables laden
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import os
from agents.chat_handler import handle_chat
from utils.memory import get_session_state, clear_user_session
from agents.crm_handler import handle_crm
from utils.agent_config import load_agent_config

# Chat-Adapter System
from tools.chat import get_chat_adapter, StandardMessage
from tools.chat.interface import WebhookParseError
from tools.chat.slack_adapter import handle_slack_challenge

# FastAPI App
app = FastAPI(
    title="Adizon",
    description="AI Assistant für KMUs - Multi-Platform Chat Adapter",
    version="3.0.0"
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
        # Load Agent Config from YAML
        config = load_agent_config("intent_detection")
        
        model_config = config.get_model_config()
        params = config.get_parameters()
        
        print(f"🔑 API Key exists: {bool(model_config.get('api_key'))}")
        print(f"🌐 Base URL: {model_config.get('base_url')}")
        print(f"🤖 Model: {model_config.get('name')}")
        
        client = OpenAI(
            base_url=model_config['base_url'],
            api_key=model_config['api_key']
        )
        
        print(f"✅ Client created")
        
        # System Prompt aus YAML
        system_prompt = config.get_system_prompt()
        
        response = client.chat.completions.create(
            model=model_config['name'],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            **params
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


def handle_message(msg: StandardMessage) -> str:
    """
    Platform-agnostic Message Handler.
    
    Verarbeitet Messages von allen Chat-Plattformen (Telegram, Slack, etc.)
    
    Args:
        msg: StandardMessage mit User-Info und Text
        
    Returns:
        Response text
    """
    print(f"\n{'='*50}")
    print(f"💬 [{msg.platform.upper()}] Message from {msg.user_name}: {msg.text}")
    
    # 1. KILL SWITCH CHECK
    if msg.text.strip().upper() in ["NEUSTART", "/RESET", "RESET"]:
        clear_user_session(msg.user_id)
        print(f"💥 Session Reset for {msg.user_id}")
        return "Alles klar! Mein Gedächtnis ist gelöscht. Womit fangen wir neu an? 🧠✨"
    
    # 2. STATE CHECK (Sticky Session)
    current_state = get_session_state(msg.user_id)
    print(f"🧠 Current Session State: {current_state}")
    
    if current_state == "ACTIVE":
        print("⏩ Skipping Router (State is ACTIVE) -> Direct to CRM")
        response_text = handle_crm(msg.text, msg.user_name, msg.user_id)
    else:
        # 3. NORMAL ROUTING (State is IDLE)
        intent = detect_intent(msg.text)
        
        if intent == "CHAT":
            response_text = handle_chat(msg.text, msg.user_name)
        elif intent == "CRM":
            response_text = handle_crm(msg.text, msg.user_name, msg.user_id)
        else:
            response_text = "Error."
    
    print(f"✅ Response generated ({len(response_text)} chars)")
    print(f"{'='*50}\n")
    
    return response_text


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


@app.post("/webhook/{platform}")
async def unified_webhook(platform: str, request: Request):
    """
    Unified Webhook für alle Chat-Plattformen.
    
    Endpoints:
    - POST /webhook/telegram → Telegram Bot
    - POST /webhook/slack → Slack Bot
    - POST /webhook/teams → MS Teams Bot (future)
    
    Args:
        platform: Platform identifier (telegram, slack, teams)
        request: FastAPI Request mit Webhook Data
    """
    try:
        # Parse Request Body
        webhook_data = await request.json()
        
        print(f"📨 Webhook received: platform={platform}")
        print(f"📄 Data type: {webhook_data.get('type', 'unknown')}")
        
        # 1. Slack Challenge Handling (Webhook Verification)
        if platform == "slack":
            challenge = handle_slack_challenge(webhook_data)
            if challenge:
                print(f"✅ Slack Challenge received: {challenge[:50]}...")
                print(f"✅ Responding with challenge")
                return {"challenge": challenge}
        
        # 2. Get Chat-Adapter
        try:
            adapter = get_chat_adapter(platform)
        except ValueError as e:
            print(f"❌ Unknown platform: {platform}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": str(e)}
            )
        
        # 3. Parse Message
        try:
            msg = adapter.parse_incoming(webhook_data)
        except WebhookParseError as e:
            error_msg = str(e)
            # Spezial-Handling für bestimmte Fehler
            if "Ignoring bot message" in error_msg:
                print(f"⏭️ Skipping: {error_msg}")
                return {"status": "ignored"}
            print(f"❌ Webhook Parse Error: {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": error_msg}
            )
        
        # 4. Handle Message (Platform-agnostic)
        response_text = handle_message(msg)
        
        # 5. Send Response
        success = adapter.send_message(msg.chat_id, response_text)
        
        if success:
            return {"status": "success"}
        else:
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": "Failed to send response"}
            )
        
    except Exception as e:
        print(f"❌ Unified Webhook Error ({platform}): {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/telegram-webhook")
async def telegram_webhook_legacy(request: Request):
    """
    Legacy Telegram Webhook - Backwards Compatible.
    Redirects to unified webhook.
    
    Note: Für neue Deployments nutze /webhook/telegram stattdessen.
    """
    print("📱 Legacy Telegram Webhook called (redirecting to unified)")
    webhook_data = await request.json()
    
    # Redirect zu unified webhook
    return await unified_webhook("telegram", request)


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