"""
CRM Tools Package - The Switchboard
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain.tools import tool
from typing import Optional

# === Pfad zur .env ===
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

crm_system = os.getenv("CRM_SYSTEM", "MOCK").upper().strip()
print(f"🔌 Loading CRM Adapter: {crm_system}")

# --- 1. DUMMY FALLBACKS ---
# Update: Auch Mock muss jetzt 'title' akzeptieren!
def mock_search(query): return "⚠️ Mock: Suche"
def mock_create(name, email, phone=None): return "⚠️ Mock: Kontakt"
def mock_task(title, body="", due_date=None, target_id=None): return "⚠️ Mock: Task"
def mock_note(title, content, target_id): return "⚠️ Mock: Notiz" # <--- NEU: title parameter

search_func = mock_search
create_contact_func = mock_create
create_task_func = mock_task
create_note_func = mock_note

# --- 2. ADAPTER LADEN ---
adapter = None

if crm_system == "TWENTY":
    try:
        from .twenty_adapter import TwentyCRM
        adapter = TwentyCRM()
        
        search_func = adapter.search_contacts
        create_contact_func = adapter.create_contact
        create_task_func = adapter.create_task
        create_note_func = adapter.create_note # Muss (title, content, target_id) sein
        
        print("✅ Twenty Adapter fully connected")
    except Exception as e:
        print(f"❌ Twenty Init Error: {e}")

# --- 3. LANGCHAIN TOOLS ---

@tool
def search_contacts(query: str) -> str:
    """Sucht nach Kontakten und Firmen im CRM."""
    return search_func(query)

@tool
def create_contact(name: str, email: str, phone: Optional[str] = None) -> str:
    """Erstellt einen neuen Kontakt."""
    return create_contact_func(name, email, phone)

@tool
def create_task(title: str, body: str = "", due_date: Optional[str] = None, target_id: Optional[str] = None) -> str:
    """
    Erstellt eine Aufgabe/Task im CRM.
    Args:
        title: Titel der Aufgabe
        body: Beschreibung (Markdown)
        due_date: ISO Datum (z.B. 2025-12-28T09:00:00Z)
        target_id: ID der Person/Firma
    """
    return create_task_func(title, body, due_date, target_id)

# === UPDATE HIER ===
@tool
def create_note(title: str, content: str, target_id: str) -> str:
    """
    Erstellt eine Notiz/Note im CRM.
    Args:
        title: Ein kurzer, prägnanter Titel für die Notiz (Zusammenfassung des Inhalts).
        content: Der ausführliche Inhalt der Notiz (Markdown erlaubt).
        target_id: Die ID des Kontakts/der Firma (aus der Suche).
    """
    # Wir rufen den Adapter jetzt mit 3 Argumenten auf
    return create_note_func(title, content, target_id)

__all__ = ['search_contacts', 'create_contact', 'create_task', 'create_note']