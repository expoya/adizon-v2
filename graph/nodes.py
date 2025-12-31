"""
Adizon - LangGraph Node Definitions
Alle Workflow-Nodes für Auth, Routing, Chat, CRM und Session Guard
"""

import os
from datetime import datetime
from typing import Literal

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from utils.database import SessionLocal
from utils.agent_config import load_agent_config
from repositories.user_repository import UserRepository
from services.registration_service import RegistrationService
from .state import AdizonState


# === HELPER: LLM Factory ===

def get_llm_from_config(config_name: str) -> ChatOpenAI:
    """
    Erstellt ChatOpenAI Instanz aus YAML-Config.
    
    Args:
        config_name: Name der Config (z.B. 'crm_handler')
        
    Returns:
        Konfigurierte ChatOpenAI Instanz
    """
    config = load_agent_config(config_name)
    model_config = config.get_model_config()
    params = config.get_parameters()
    
    return ChatOpenAI(
        model=model_config.get("name", "gpt-4"),
        base_url=model_config.get("base_url"),
        api_key=model_config.get("api_key") or os.getenv("OPENAI_API_KEY"),
        temperature=params.get("temperature", 0.7),
        max_tokens=params.get("max_tokens", 500),
    )


# === NODE 1: Auth Node ===

def auth_node(state: AdizonState) -> dict:
    """
    Authentifiziert User anhand der Platform-ID.
    
    - Bekannter User: Lädt User-Objekt aus DB
    - Neuer User: Erstellt Pending-Registration
    
    Returns:
        Updated state mit user, session_state (initial IDLE)
    """
    user_id = state["user_id"]
    platform = state["platform"]
    
    # Platform-ID extrahieren (Format: "telegram:123456" -> "123456")
    platform_user_id = user_id.split(":", 1)[-1] if ":" in user_id else user_id
    
    db = SessionLocal()
    try:
        repo = UserRepository(db)
        
        # User-Lookup via Platform-ID
        user = repo.get_user_by_platform_id(platform, platform_user_id)
        
        if user:
            # Bekannter User
            if user.is_approved and user.is_active:
                print(f"✅ Auth: User {user.name} authenticated")
                return {
                    "user": user,
                    "session_state": state.get("session_state", "IDLE"),
                    "dialog_state": state.get("dialog_state", {}),
                    "last_action_context": state.get("last_action_context", {}),
                }
            else:
                # User nicht approved - Pending-Nachricht
                pending_msg = (
                    f"⏳ Hallo! Dein Zugang wartet noch auf Freischaltung.\n"
                    f"Du wirst benachrichtigt, sobald ein Admin dich freischaltet."
                )
                return {
                    "user": None,
                    "messages": [AIMessage(content=pending_msg)],
                    "session_state": "IDLE",
                    "dialog_state": {},
                    "last_action_context": {},
                }
        else:
            # Neuer User - Registration starten
            reg_service = RegistrationService(repo)
            
            # User-Name aus letzter Nachricht extrahieren (Fallback)
            last_message = state["messages"][-1] if state["messages"] else None
            user_name = "Neuer User"  # Default
            
            # Registration
            new_user, response_msg = reg_service.register_pending_user(
                platform=platform,
                platform_id=platform_user_id,
                user_name=user_name
            )
            
            print(f"🆕 Auth: New user registered (pending): {platform_user_id}")
            
            return {
                "user": None,
                "messages": [AIMessage(content=response_msg)],
                "session_state": "IDLE",
                "dialog_state": {},
                "last_action_context": {},
            }
    finally:
        db.close()


# === NODE 2: Router Node ===

def router_node(state: AdizonState) -> dict:
    """
    Entscheidet über das Routing basierend auf Session-State und Intent.
    
    - session_state="ACTIVE" -> Immer CRM (Sticky Session)
    - session_state="IDLE" -> LLM-basierte Intent Detection
    
    Note: Diese Node gibt nur State zurück, das eigentliche Routing
    passiert via conditional_edges im Builder.
    """
    # Bei keinem User (Pending/Neu) -> Keine Routing-Entscheidung nötig
    if not state.get("user"):
        return {}
    
    # Bei ACTIVE Session -> CRM direkt (wird via Edge gehandelt)
    if state.get("session_state") == "ACTIVE":
        print("🔀 Router: ACTIVE session -> CRM")
        return {}
    
    # Intent Detection via LLM
    llm = get_llm_from_config("intent_detection")
    config = load_agent_config("intent_detection")
    system_prompt = config.get_system_prompt()
    
    # Letzte User-Nachricht
    last_message = state["messages"][-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_text)
    ]
    
    response = llm.invoke(messages)
    intent = response.content.strip().upper()
    
    # Fallback auf CRM bei unklarem Intent
    if intent not in ["CHAT", "CRM"]:
        intent = "CRM"
    
    print(f"🔀 Router: Intent detected -> {intent}")
    
    # Intent wird im dialog_state gespeichert für conditional_edges
    return {
        "dialog_state": {
            **state.get("dialog_state", {}),
            "detected_intent": intent
        }
    }


def route_decision(state: AdizonState) -> Literal["chat", "crm", "__end__"]:
    """
    Routing-Funktion für conditional_edges.
    
    Returns:
        Node-Name für nächsten Schritt
    """
    # Kein User (Pending/Neu) -> Direkt zu End (Auth hat bereits geantwortet)
    if not state.get("user"):
        return "__end__"
    
    # ACTIVE Session -> CRM
    if state.get("session_state") == "ACTIVE":
        return "crm"
    
    # Intent-basiertes Routing
    intent = state.get("dialog_state", {}).get("detected_intent", "CRM")
    
    if intent == "CHAT":
        return "chat"
    else:
        return "crm"


# === NODE 3: Chat Node ===

def chat_node(state: AdizonState) -> dict:
    """
    Einfacher Chat ohne Tools.
    Für Smalltalk, Begrüßungen, allgemeine Fragen.
    """
    user = state.get("user")
    user_name = user.name if user else "User"
    
    # LLM mit Chat-Config
    llm = get_llm_from_config("chat_handler")
    config = load_agent_config("chat_handler")
    
    system_prompt = config.get_system_prompt(user_name=user_name)
    
    # Konversation aufbauen
    messages = [SystemMessage(content=system_prompt)]
    
    # Letzte N Nachrichten als Kontext
    for msg in state["messages"][-10:]:
        messages.append(msg)
    
    response = llm.invoke(messages)
    
    print(f"💬 Chat: Response generated")
    
    return {
        "messages": [response]
    }


# === NODE 4: CRM Node (ReAct) ===

def crm_node(state: AdizonState) -> dict:
    """
    CRM Agent mit ReAct-Pattern und Tool-Calling.
    Nutzt dynamisch geladene CRM-Tools.
    """
    from tools.crm import get_crm_tools_for_user
    from langgraph.prebuilt import create_react_agent
    
    user = state.get("user")
    if not user:
        return {"messages": [AIMessage(content="❌ Nicht authentifiziert.")]}
    
    user_name = user.name
    user_id = state["user_id"]
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    # LLM mit CRM-Config
    llm = get_llm_from_config("crm_handler")
    config = load_agent_config("crm_handler")
    
    system_prompt = config.get_system_prompt(
        user_name=user_name,
        current_date=current_date
    )
    
    # Tools laden (mit State-Aware Wrapper)
    base_tools = get_crm_tools_for_user(user_id, user)
    
    # Wrapper für Undo-Context (schreibt in State)
    tools_with_state = _wrap_tools_for_state(base_tools, state)
    
    # ReAct Agent erstellen
    react_agent = create_react_agent(
        llm,
        tools_with_state,
        state_modifier=system_prompt
    )
    
    # Agent ausführen
    result = react_agent.invoke({
        "messages": state["messages"]
    })
    
    print(f"🔧 CRM: Agent completed with {len(result.get('messages', []))} messages")
    
    # Last Action Context extrahieren (falls Tool ausgeführt wurde)
    last_action = _extract_last_action_from_messages(result.get("messages", []))
    
    return {
        "messages": result.get("messages", []),
        "last_action_context": last_action or state.get("last_action_context", {}),
    }


def _wrap_tools_for_state(tools: list, state: AdizonState) -> list:
    """
    Wrapper um Tools, die den last_action_context tracken.
    
    Note: In LangGraph wird der State automatisch persistiert,
    daher können wir die Tool-Outputs parsen und den Context extrahieren.
    """
    # Für jetzt geben wir die Tools unverändert zurück
    # Der last_action_context wird aus den Tool-Messages extrahiert
    return tools


def _extract_last_action_from_messages(messages: list) -> dict:
    """
    Extrahiert last_action_context aus Tool-Messages.
    
    Parst Tool-Outputs auf ID-Patterns wie "(ID: abc-123)".
    """
    import re
    
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.content:
            content = msg.content
            
            # Pattern für erstellte Entities
            # z.B. "✅ Kontakt erstellt: Max Mustermann (ID: abc-123-def)"
            if "✅" in content and "(ID:" in content:
                # ID extrahieren
                id_match = re.search(r"\(ID:\s*([a-f0-9\-]+|\d+)\)", content)
                if id_match:
                    entity_id = id_match.group(1)
                    
                    # Entity Type bestimmen
                    entity_type = "unknown"
                    if "Kontakt" in content or "Lead" in content or "Person" in content:
                        entity_type = "person"
                    elif "Task" in content or "Aufgabe" in content:
                        entity_type = "task"
                    elif "Notiz" in content or "Note" in content:
                        entity_type = "note"
                    elif "Firma" in content or "Company" in content:
                        entity_type = "company"
                    
                    return {
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "action": "create"
                    }
    
    return {}


# === NODE 5: Session Guard ===

def session_guard_node(state: AdizonState) -> dict:
    """
    Entscheidet nach jedem Turn, ob die Session ACTIVE bleibt oder IDLE wird.
    
    ACTIVE: Bei Rückfragen, laufenden Prozessen
    IDLE: Bei abgeschlossenen Tasks, Verabschiedungen
    """
    # Letzte AI-Antwort
    messages = state.get("messages", [])
    last_ai_response = ""
    last_user_message = ""
    
    for msg in reversed(messages):
        if hasattr(msg, "content"):
            if isinstance(msg, AIMessage) and not last_ai_response:
                last_ai_response = msg.content
            elif isinstance(msg, HumanMessage) and not last_user_message:
                last_user_message = msg.content
        if last_ai_response and last_user_message:
            break
    
    if not last_ai_response:
        return {"session_state": "IDLE"}
    
    # LLM für Session-Entscheidung
    llm = get_llm_from_config("session_guard")
    config = load_agent_config("session_guard")
    
    system_prompt = config.get_system_prompt(
        user_message=last_user_message,
        last_ai_response=last_ai_response
    )
    
    messages_for_llm = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Entscheide: ACTIVE oder IDLE?")
    ]
    
    response = llm.invoke(messages_for_llm)
    decision = response.content.strip().upper()
    
    # Nur ACTIVE oder IDLE erlaubt
    if decision not in ["ACTIVE", "IDLE"]:
        decision = "IDLE"
    
    print(f"🛡️ Session Guard: {decision}")
    
    return {"session_state": decision}

