"""
Adizon - LangGraph Builder
Kompiliert den StateGraph mit allen Nodes und Edges
"""

from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import AdizonState
from .nodes import (
    auth_node,
    router_node,
    route_decision,
    chat_node,
    crm_node,
    session_guard_node,
)


def build_graph(checkpointer: Optional[BaseCheckpointSaver] = None) -> StateGraph:
    """
    Baut den Adizon LangGraph Workflow.
    
    Args:
        checkpointer: Optional Checkpointer für State Persistence
    
    Flow:
        START -> auth -> router -> [chat|crm] -> session_guard -> END
    
    Returns:
        Kompilierter StateGraph mit optionalem Checkpointer
    """
    # StateGraph mit unserem State-Schema
    graph = StateGraph(AdizonState)
    
    # === NODES HINZUFÜGEN ===
    graph.add_node("auth", auth_node)
    graph.add_node("router", router_node)
    graph.add_node("chat", chat_node)
    graph.add_node("crm", crm_node)
    graph.add_node("session_guard", session_guard_node)
    
    # === EDGES DEFINIEREN ===
    
    # Start -> Auth (immer)
    graph.add_edge(START, "auth")
    
    # Auth -> Router (immer)
    graph.add_edge("auth", "router")
    
    # Router -> Conditional (Chat oder CRM oder End)
    graph.add_conditional_edges(
        "router",
        route_decision,
        {
            "chat": "chat",
            "crm": "crm",
            "__end__": END,  # Bei Pending/Neuen Usern
        }
    )
    
    # Chat -> Session Guard
    graph.add_edge("chat", "session_guard")
    
    # CRM -> Session Guard
    graph.add_edge("crm", "session_guard")
    
    # Session Guard -> End
    graph.add_edge("session_guard", END)
    
    # === KOMPILIEREN ===
    compiled = graph.compile(checkpointer=checkpointer)
    
    if checkpointer:
        print("✅ LangGraph compiled with checkpointer")
    else:
        print("✅ LangGraph compiled (no persistence)")
    
    return compiled


def get_graph_visualization() -> str:
    """
    Gibt eine ASCII-Visualisierung des Graphen zurück.
    Nützlich für Debugging.
    """
    return """
    ┌─────────┐
    │  START  │
    └────┬────┘
         │
    ┌────▼────┐
    │  AUTH   │ (User lookup / Registration)
    └────┬────┘
         │
    ┌────▼────┐
    │ ROUTER  │ (Intent Detection / Session Check)
    └────┬────┘
         │
    ┌────┴────┬─────────────┐
    │         │             │
    ▼         ▼             ▼
  ┌────┐   ┌─────┐      ┌─────┐
  │CHAT│   │ CRM │      │ END │ (Pending Users)
  └──┬─┘   └──┬──┘      └─────┘
     │        │
     └───┬────┘
         │
    ┌────▼────────┐
    │SESSION GUARD│ (ACTIVE / IDLE)
    └────┬────────┘
         │
    ┌────▼────┐
    │   END   │
    └─────────┘
    """


# === EXPORT ===

__all__ = ["build_graph", "get_graph_visualization"]

