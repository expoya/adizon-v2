"""
CRM Tools Factory
Stellt dem Agenten Tools bereit, die wissen, wer der User ist (für Undo).
"""
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain.tools import StructuredTool
from typing import Optional

# Redis Utils importieren
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from utils.memory import save_undo_context, get_undo_context, clear_undo_context

# .env laden
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Adapter Setup (wie gehabt)
crm_system = os.getenv("CRM_SYSTEM", "MOCK").upper().strip()

# --- MOCKS & ADAPTER LOGIC (Gekürzt für Übersicht, dein bestehender Code hier) ---
# (Hier kommen deine mock_... Funktionen und der Adapter-Import Block hin)
# Wir simulieren das hier kurz, damit der Code vollständig ist:

def mock_create(name, email, phone=None): return "⚠️ Mock: Kontakt (ID: mock-1)"
def mock_task(title, body="", due_date=None, target_id=None): return "⚠️ Mock: Task (ID: mock-2)"
def mock_note(title, content, target_id): return "⚠️ Mock: Note (ID: mock-3)"
def mock_search(query): return "⚠️ Mock Search"

adapter = None
search_func = mock_search
create_contact_func = mock_create
create_task_func = mock_task
create_note_func = mock_note

if crm_system == "TWENTY":
    from .twenty_adapter import TwentyCRM
    try:
        adapter = TwentyCRM()
        search_func = adapter.search_contacts
        create_contact_func = adapter.create_contact
        create_task_func = adapter.create_task
        create_note_func = adapter.create_note
        print("✅ Twenty Adapter connected")
    except Exception as e:
        print(f"❌ Adapter Error: {e}")

# === DIE FACTORY (Das Profi-Teil) ===

def get_crm_tools_for_user(user_id: str) -> list:
    """
    Erstellt ein Tool-Set speziell für diesen User.
    Damit landen Undo-Infos im richtigen Redis-Key.
    """
    
    # 1. Helper zum ID lesen
    def _extract_id(text):
        match = re.search(r"\(ID:\s*([a-f0-9\-]+)\)", text)
        return match.group(1) if match else None

    # 2. Die Wrapper (Closures)
    def create_contact_wrapper(name: str, email: str, phone: Optional[str] = None) -> str:
        """Erstellt Kontakt."""
        res = create_contact_func(name, email, phone)
        if pid := _extract_id(res): save_undo_context(user_id, "person", pid)
        return res

    def create_task_wrapper(title: str, body: str = "", due_date: Optional[str] = None, target_id: Optional[str] = None) -> str:
        """
        Erstellt Task.
        WICHTIG bei target_id: 
            - Wenn du die UUID hast -> Sende UUID.
            - Wenn du KEINE UUID hast -> Sende den VOR- UND NACHNAMEN (z.B. 'Thomas Braun').
            - RATE KEINE E-MAILS!
        """
        res = create_task_func(title, body, due_date, target_id)
        if tid := _extract_id(res): save_undo_context(user_id, "task", tid)
        return res

    def create_note_wrapper(title: str, content: str, target_id: str) -> str:
        """
        Erstellt Notiz.
        WICHTIG bei target_id: 
            - Wenn du die UUID hast -> Sende UUID.
            - Wenn du KEINE UUID hast -> Sende den VOR- UND NACHNAMEN (z.B. 'Thomas Braun').
            - RATE KEINE E-MAILS!
        """

        res = create_note_func(title, content, target_id)
        if nid := _extract_id(res): save_undo_context(user_id, "note", nid)
        return res
        
    def undo_wrapper() -> str:
        """Macht letzte Aktion rückgängig."""
        typ, iid = get_undo_context(user_id)
        if not iid: return "⚠️ Nichts zum Rückgängigmachen gefunden."
        if not adapter: return "⚠️ Undo geht nur im Live-Modus."
        
        res = adapter.delete_item(typ, iid)
        if "✅" in res: clear_undo_context(user_id)
        return res

    # 3. Liste zurückgeben
    return [
        StructuredTool.from_function(search_func, name="search_contacts", description="Sucht Kontakte"),
        StructuredTool.from_function(create_contact_wrapper, name="create_contact", description="Erstellt Kontakt"),
        StructuredTool.from_function(create_task_wrapper, name="create_task", description="Erstellt Task (Datum ISO)"),
        StructuredTool.from_function(create_note_wrapper, name="create_note", description="Erstellt Notiz"),
        StructuredTool.from_function(undo_wrapper, name="undo_last_action", description="Macht die letzte Erstellung RÜCKGÄNGIG (Löschen).")
    ]