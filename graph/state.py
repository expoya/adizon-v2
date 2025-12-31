"""
Adizon - LangGraph State Definition
Single Source of Truth für den gesamten Workflow
"""

from typing import TypedDict, Literal, Optional, Annotated, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class LastActionContext(TypedDict, total=False):
    """
    Kontext der letzten CRM-Aktion für Undo-Funktionalität.
    
    Attributes:
        entity_type: Art des Eintrags ("lead", "person", "task", "note")
        entity_id: CRM ID für Undo-Löschung
        action: Ausgeführte Aktion ("create", "update", "delete")
    """
    entity_type: str
    entity_id: str
    action: str


class AdizonState(TypedDict):
    """
    Haupt-State für den Adizon LangGraph Workflow.
    
    Attributes:
        messages: Konversations-History (mit add_messages Reducer)
        user: Authentifizierter User aus der Datenbank (oder None)
        user_id: Platform-spezifische User-ID (z.B. "telegram:123456")
        platform: Chat-Plattform ("telegram", "slack")
        chat_id: Platform-spezifische Chat-ID für Antworten
        session_state: "ACTIVE" (Sticky CRM) oder "IDLE" (Router entscheidet)
        dialog_state: Zusätzlicher Kontext für Tools
        last_action_context: Letzte CRM-Aktion für Undo
    """
    # Conversation
    messages: Annotated[list[BaseMessage], add_messages]
    
    # User Context (aus Auth Node) - serialisiert als dict via user.to_dict()
    user: Optional[dict]  # User-Dict (id, email, name, crm_display_name, etc.)
    user_id: str
    platform: str
    chat_id: str
    
    # Session Management
    session_state: Literal["ACTIVE", "IDLE"]
    
    # Tool Context
    dialog_state: dict
    last_action_context: LastActionContext

