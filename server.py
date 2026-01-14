"""
Adizon - LangGraph Server
FastAPI Entrypoint mit PostgreSQL Checkpointing
"""

import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from graph.builder import build_graph
from graph.state import AdizonState
from tools.chat import get_chat_adapter, StandardMessage
from api.users import router as users_router
from utils.database import DATABASE_URL

# === CONSTANTS ===
KILLSWITCH_COMMAND = "//RESET"
KILLSWITCH_RESPONSE = "Alles klar! Mein Gedächtnis ist gelöscht. Womit fangen wir neu an? 🧠✨"
SESSION_TIMEOUT_MINUTES = 15

# Load Environment
load_dotenv()

# === GLOBALS ===
pool: AsyncConnectionPool = None
checkpointer: AsyncPostgresSaver = None
graph = None

# In-memory Session Timestamps (user_id -> last_activity)
# Für Session-Timeout Tracking
_session_timestamps: dict[str, datetime] = {}


# === SESSION MANAGEMENT HELPERS ===

async def clear_user_session(user_id: str) -> bool:
    """
    Löscht die komplette Session eines Users (Checkpoint + Timestamp).

    Args:
        user_id: Platform-spezifische User-ID (z.B. "telegram:123456")

    Returns:
        True wenn erfolgreich, False bei Fehler
    """
    global pool, _session_timestamps

    # Timestamp löschen
    if user_id in _session_timestamps:
        del _session_timestamps[user_id]

    # Checkpoint aus PostgreSQL löschen
    if pool:
        try:
            async with pool.connection() as conn:
                # LangGraph Checkpoint-Tabellen: checkpoint, checkpoint_blobs, checkpoint_writes
                await conn.execute(
                    "DELETE FROM checkpoint_writes WHERE thread_id = %s",
                    (user_id,)
                )
                await conn.execute(
                    "DELETE FROM checkpoint_blobs WHERE thread_id = %s",
                    (user_id,)
                )
                await conn.execute(
                    "DELETE FROM checkpoints WHERE thread_id = %s",
                    (user_id,)
                )
                print(f"🗑️ Session cleared for {user_id}")
                return True
        except Exception as e:
            print(f"⚠️ Failed to clear session: {e}")
            return False
    return True


def is_session_expired(user_id: str) -> bool:
    """
    Prüft ob die Session eines Users abgelaufen ist (> SESSION_TIMEOUT_MINUTES).

    Args:
        user_id: Platform-spezifische User-ID

    Returns:
        True wenn Session abgelaufen oder nicht existiert
    """
    if user_id not in _session_timestamps:
        return True

    last_activity = _session_timestamps[user_id]
    timeout_threshold = datetime.utcnow() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    return last_activity < timeout_threshold


def update_session_timestamp(user_id: str) -> None:
    """Aktualisiert den Timestamp der letzten Aktivität."""
    _session_timestamps[user_id] = datetime.utcnow()


# === LIFESPAN MANAGEMENT ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/Shutdown Lifecycle.
    Initialisiert PostgreSQL Connection Pool und Checkpointer.
    """
    global pool, checkpointer, graph
    
    print("🚀 Starting Adizon Server...")
    
    # PostgreSQL Pool für Checkpointing
    # Konvertiere SQLAlchemy URL zu nativem psycopg/libpq Format
    # SQLAlchemy: postgresql+psycopg://... -> libpq: postgresql://...
    pg_url = DATABASE_URL
    if "+psycopg" in pg_url:
        pg_url = pg_url.replace("+psycopg", "")
    # Manche Tools erwarten postgres:// statt postgresql://
    if pg_url.startswith("postgresql://"):
        pg_url = pg_url.replace("postgresql://", "postgres://", 1)
    
    print(f"📦 Connecting to PostgreSQL for checkpointing...")
    
    try:
        pool = AsyncConnectionPool(
            conninfo=pg_url,
            min_size=2,
            max_size=10,
            open=False  # Manuelles Öffnen
        )
        await pool.open()
        
        # Checkpointer-Tabellen erstellen mit autocommit (wegen CREATE INDEX CONCURRENTLY)
        import psycopg
        async with await psycopg.AsyncConnection.connect(pg_url, autocommit=True) as setup_conn:
            setup_checkpointer = AsyncPostgresSaver(setup_conn)
            await setup_checkpointer.setup()
        
        # Jetzt den echten Checkpointer mit dem Pool erstellen
        checkpointer = AsyncPostgresSaver(pool)
        
        print("✅ PostgreSQL Checkpointer initialized")
        
    except Exception as e:
        print(f"⚠️ Checkpointer setup failed: {e}")
        print("🔄 Running without persistence")
        checkpointer = None
    
    # Graph kompilieren (mit Checkpointer falls verfügbar)
    graph = build_graph(checkpointer=checkpointer)
    
    print("✅ Adizon Server ready!")
    print(f"📡 Webhook endpoint: POST /webhook/{{platform}}")
    print(f"👥 Admin API: /api/users")
    
    yield  # App läuft
    
    # Shutdown
    print("🛑 Shutting down Adizon Server...")
    if pool:
        await pool.close()
    print("👋 Goodbye!")


# === FASTAPI APP ===

app = FastAPI(
    title="Adizon",
    description="LangGraph-powered CRM Assistant",
    version="2.0.0",
    lifespan=lifespan
)

# CORS für Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In Production: Spezifische Origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin API Router
app.include_router(users_router)


# === WEBHOOK ENDPOINT ===

@app.post("/webhook/{platform}")
async def webhook(platform: str, request: Request, background_tasks: BackgroundTasks):
    """
    Universeller Webhook für alle Chat-Plattformen.
    
    Args:
        platform: "telegram" oder "slack"
        
    Body:
        Platform-spezifisches Webhook-Format
        
    Returns:
        {"ok": True} bei Erfolg (sofort, Verarbeitung im Hintergrund)
    """
    global graph, checkpointer
    
    if not graph:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    
    # Slack Retry Detection - ignoriere Retries
    # Slack sendet Webhooks erneut, wenn wir nicht innerhalb 3s antworten
    retry_num = request.headers.get("X-Slack-Retry-Num")
    if retry_num:
        print(f"⏭️ Ignoring Slack retry #{retry_num}")
        return {"ok": True}
    
    try:
        body = await request.json()
    except Exception as e:
        # Slack sendet manchmal URL verification
        body = {}
    
    # Slack URL Verification Challenge
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}
    
    # Chat Adapter für Platform
    try:
        adapter = get_chat_adapter(platform)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Webhook validieren
    if not adapter.validate_webhook(body):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    # Message parsen (async für Voice/Audio Transcription)
    try:
        msg: StandardMessage = await adapter.parse_incoming(body)
    except Exception as e:
        print(f"⚠️ Webhook parse error: {e}")
        # Bei Parse-Fehlern still beenden (z.B. Bot-Messages)
        return {"ok": True}
    
    # Audio-Messages ignorieren (TODO: Whisper Integration)
    if not msg.text or msg.text.strip() == "":
        return {"ok": True}
    
    print(f"📨 Incoming [{platform}]: {msg.user_name}: {msg.text[:50]}...")

    # === KILLSWITCH CHECK ===
    if msg.text.strip().upper() == KILLSWITCH_COMMAND.upper():
        print(f"💥 Killswitch triggered by {msg.user_id}")
        await clear_user_session(msg.user_id)
        await adapter.send_message(msg.chat_id, KILLSWITCH_RESPONSE)
        return {"ok": True}

    # === SESSION TIMEOUT CHECK ===
    if is_session_expired(msg.user_id):
        print(f"⏰ Session expired for {msg.user_id} - clearing old state")
        await clear_user_session(msg.user_id)

    # Update Session Timestamp
    update_session_timestamp(msg.user_id)

    # Initial State
    initial_state: AdizonState = {
        "messages": [HumanMessage(content=msg.text)],
        "user": None,
        "user_id": msg.user_id,
        "platform": platform,
        "chat_id": msg.chat_id,
        "session_state": "IDLE",
        "dialog_state": {},
        "last_action_context": {},
    }

    # Graph Config (Thread-ID für Checkpointing)
    config = {
        "configurable": {
            "thread_id": msg.user_id  # Persistente Konversation pro User
        }
    }

    # Graph ausführen
    try:
        # Graph wurde bereits mit Checkpointer kompiliert (falls verfügbar)
        result = await graph.ainvoke(initial_state, config=config)
        
        # Response aus letzter AI-Message
        response_text = ""
        for msg_item in reversed(result.get("messages", [])):
            if hasattr(msg_item, "content") and msg_item.content:
                # Nur AI-Nachrichten als Response
                if msg_item.__class__.__name__ in ["AIMessage", "AIMessageChunk"]:
                    response_text = msg_item.content
                    break
        
        if response_text:
            # Antwort senden (async)
            await adapter.send_message(msg.chat_id, response_text)
            print(f"📤 Response sent: {response_text[:50]}...")
        
    except Exception as e:
        print(f"❌ Graph execution error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fehler-Antwort (async)
        await adapter.send_message(
            msg.chat_id, 
            "❌ Es ist ein Fehler aufgetreten. Bitte versuche es erneut."
        )
    
    return {"ok": True}


# === HEALTH CHECK ===

@app.get("/health")
async def health():
    """Health Check Endpoint"""
    return {
        "status": "healthy",
        "checkpointer": "postgres" if checkpointer else "memory",
        "graph": "ready" if graph else "not_initialized"
    }


@app.get("/")
async def root():
    """Root Endpoint"""
    return {
        "name": "Adizon",
        "version": "2.0.0",
        "description": "LangGraph-powered CRM Assistant",
        "endpoints": {
            "webhook": "POST /webhook/{platform}",
            "users": "GET/POST /api/users",
            "health": "GET /health"
        }
    }


# === MAIN ===

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True  # In Production: reload=False
    )

