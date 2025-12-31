"""
Adizon - LangGraph Server
FastAPI Entrypoint mit PostgreSQL Checkpointing
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, HTTPException
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

# Load Environment
load_dotenv()

# === GLOBALS ===
pool: AsyncConnectionPool = None
checkpointer: AsyncPostgresSaver = None
graph = None


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
        
        # Checkpointer mit Pool
        checkpointer = AsyncPostgresSaver(pool)
        
        # Checkpointer-Tabellen erstellen (falls nicht vorhanden)
        await checkpointer.setup()
        
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
async def webhook(platform: str, request: Request):
    """
    Universeller Webhook für alle Chat-Plattformen.
    
    Args:
        platform: "telegram" oder "slack"
        
    Body:
        Platform-spezifisches Webhook-Format
        
    Returns:
        {"ok": True} bei Erfolg
    """
    global graph, checkpointer
    
    if not graph:
        raise HTTPException(status_code=503, detail="Graph not initialized")
    
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
    
    # Message parsen
    try:
        msg: StandardMessage = adapter.parse_incoming(body)
    except Exception as e:
        print(f"⚠️ Webhook parse error: {e}")
        # Bei Parse-Fehlern still beenden (z.B. Bot-Messages)
        return {"ok": True}
    
    # Audio-Messages ignorieren (TODO: Whisper Integration)
    if not msg.text or msg.text.strip() == "":
        return {"ok": True}
    
    print(f"📨 Incoming [{platform}]: {msg.user_name}: {msg.text[:50]}...")
    
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
            # Antwort senden
            adapter.send_message(msg.chat_id, response_text)
            print(f"📤 Response sent: {response_text[:50]}...")
        
    except Exception as e:
        print(f"❌ Graph execution error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fehler-Antwort
        adapter.send_message(
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

