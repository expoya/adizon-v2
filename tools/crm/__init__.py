"""
CRM Tools Factory
Stellt dem Agenten Tools bereit, die wissen, wer der User ist (für Attribution).

Undo-Context wird über LangGraph State gehandelt (nicht mehr Redis).
"""
import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain.tools import StructuredTool
from typing import Optional, Callable

# User Model für Attribution
try:
    from models.user import User
except ImportError:
    User = None

# .env laden
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent
load_dotenv(dotenv_path=root_dir / ".env")

# Adapter Setup
crm_system = os.getenv("CRM_SYSTEM", "MOCK").upper().strip()

# === MOCKS ===

def mock_create(first_name, last_name, company, email, phone=None): 
    return f"⚠️ Mock: Kontakt {first_name} {last_name} (ID: mock-{hash(email) % 10000})"

def mock_task(title, body="", due_date=None, target_id=None): 
    return f"⚠️ Mock: Task '{title}' (ID: mock-task-1)"

def mock_note(title, content, target_id): 
    return f"⚠️ Mock: Note '{title}' (ID: mock-note-1)"

def mock_search(query): 
    return "⚠️ Mock Search: Keine Ergebnisse (Mock Mode)"


# === ADAPTER GLOBALS ===

adapter = None
search_func = mock_search
create_contact_func = mock_create
create_task_func = mock_task
create_note_func = mock_note
update_entity_func = None
get_details_func = None


# === ADAPTER SELECTION ===

if crm_system == "TWENTY":
    from .twenty_adapter import TwentyCRM
    try:
        adapter = TwentyCRM()
        search_func = adapter.search_contacts
        create_contact_func = adapter.create_contact
        create_task_func = adapter.create_task
        create_note_func = adapter.create_note
        update_entity_func = adapter.update_entity
        get_details_func = adapter.get_person_details
        print("✅ Twenty Adapter connected")
    except Exception as e:
        print(f"❌ Twenty Adapter Error: {e}")

elif crm_system == "ZOHO":
    from .zoho_adapter import ZohoCRM
    try:
        adapter = ZohoCRM()
        search_func = adapter.search_leads
        create_contact_func = adapter.create_contact
        create_task_func = adapter.create_task
        create_note_func = adapter.create_note
        update_entity_func = adapter.update_entity
        get_details_func = adapter.get_lead_details
        print("✅ Zoho Adapter connected")
    except Exception as e:
        print(f"❌ Zoho Adapter Error: {e}")

else:
    print(f"⚠️ CRM_SYSTEM={crm_system} - Using Mock Mode (set to TWENTY or ZOHO for live mode)")


# === IN-MEMORY UNDO CONTEXT ===
# Temporärer Speicher für Undo-Context (pro User-ID)
# Wird nach jedem Turn durch LangGraph State persistiert
_undo_context: dict[str, tuple[str, str]] = {}


def _save_undo_context(user_id: str, entity_type: str, entity_id: str):
    """Speichert Undo-Context im Memory (für aktuellen Turn)"""
    _undo_context[user_id] = (entity_type, entity_id)
    print(f"💾 Undo context saved: {entity_type} -> {entity_id}")


def _get_undo_context(user_id: str) -> tuple[Optional[str], Optional[str]]:
    """Liest Undo-Context aus Memory"""
    if user_id in _undo_context:
        return _undo_context[user_id]
    return None, None


def _clear_undo_context(user_id: str):
    """Löscht Undo-Context"""
    if user_id in _undo_context:
        del _undo_context[user_id]


# === FACTORY ===

def get_crm_tools_for_user(user_id: str, user: Optional['User'] = None) -> list:
    """
    Erstellt ein Tool-Set speziell für diesen User.
    
    Args:
        user_id: Platform-spezifische User-ID
        user: Optional User-Objekt für CRM-Attribution
        
    Returns:
        Liste von StructuredTools für den CRM Agent
    """
    
    # Attribution Suffix (wird an Notes/Tasks angehängt)
    attribution = ""
    if user and hasattr(user, 'crm_display_name'):
        attribution = f"\n\n---\n_✍️ via {user.crm_display_name}_"
    
    def _extract_id(text: str) -> Optional[str]:
        """Extrahiert ID aus Tool-Output"""
        # UUID Format (Twenty: abc-123-def-456)
        match = re.search(r"\(ID:\s*([a-f0-9\-]+)\)", text)
        if match:
            return match.group(1)
        
        # Numerische ID (Zoho: 1234567890123456)
        match = re.search(r"\(ID:\s*(\d+)\)", text)
        if match:
            return match.group(1)
        
        return None

    # === TOOL WRAPPERS ===
    
    def create_contact_wrapper(
        first_name: str, 
        last_name: str, 
        company: str, 
        email: str, 
        phone: Optional[str] = None
    ) -> str:
        """
        Erstellt neuen Kontakt/Lead im CRM.
        
        PFLICHTFELDER:
        - first_name: Vorname des Kontakts
        - last_name: Nachname des Kontakts
        - company: Firmenname (wenn unbekannt: "Unbekannt" oder "-")
        - email: E-Mail Adresse
        
        OPTIONAL:
        - phone: Telefonnummer
        
        WICHTIG: Frage den User IMMER nach allen Pflichtfeldern!
        """
        res = create_contact_func(first_name, last_name, company, email, phone)
        entity_type = "lead" if crm_system == "ZOHO" else "person"
        
        if entity_id := _extract_id(res):
            _save_undo_context(user_id, entity_type, entity_id)
        
        return res

    def create_task_wrapper(
        title: str, 
        body: str = "", 
        due_date: Optional[str] = None, 
        target_id: Optional[str] = None
    ) -> str:
        """
        Erstellt Task.
        
        WICHTIG bei target_id: 
            - Wenn du die UUID hast -> Sende UUID.
            - Wenn du KEINE UUID hast -> Sende den VOR- UND NACHNAMEN.
            - RATE KEINE E-MAILS!
        """
        body_with_attribution = (body or "") + attribution
        res = create_task_func(title, body_with_attribution, due_date, target_id)
        
        if entity_id := _extract_id(res):
            _save_undo_context(user_id, "task", entity_id)
        
        return res

    def create_note_wrapper(title: str, content: str, target_id: str) -> str:
        """
        Erstellt Notiz.
        
        WICHTIG bei target_id: 
            - Wenn du die UUID hast -> Sende UUID.
            - Wenn du KEINE UUID hast -> Sende den VOR- UND NACHNAMEN.
            - RATE KEINE E-MAILS!
        """
        content_with_attribution = content + attribution
        res = create_note_func(title, content_with_attribution, target_id)
        
        if entity_id := _extract_id(res):
            _save_undo_context(user_id, "note", entity_id)
        
        return res
        
    def undo_wrapper() -> str:
        """
        Macht letzte Aktion rückgängig (Löscht den zuletzt erstellten Eintrag).
        
        Nutze wenn User sagt: 'rückgängig', 'lösch das', 'undo', 'Das war ein Fehler'
        """
        entity_type, entity_id = _get_undo_context(user_id)
        
        if not entity_id:
            return "⚠️ Nichts zum Rückgängigmachen gefunden."
        
        if not adapter:
            return "⚠️ Undo geht nur im Live-Modus (CRM-Adapter benötigt)."
        
        res = adapter.delete_item(entity_type, entity_id)
        
        if "✅" in res:
            _clear_undo_context(user_id)
        
        return res
    
    def update_entity_wrapper(target: str, entity_type: str, fields: str) -> str:
        """
        Aktualisiert Felder eines CRM-Eintrags.
        
        Args:
            target: Name, Email oder ID des Eintrags
            entity_type: "person"/"company" (Twenty) oder "lead" (Zoho)
            fields: JSON string mit Feldern
            
        Verfügbare Felder (Twenty):
            Person: job, linkedin, city, birthday
            Company: website, size, industry, address, roof_area
        
        Verfügbare Felder (Zoho):
            Lead: email, phone, mobile, job, linkedin, company, website, size, 
                  industry, revenue, street, city, state, zip, country
        """
        if not update_entity_func:
            return "❌ Update nicht verfügbar (nur im Live-Modus)."
        
        try:
            fields_dict = json.loads(fields) if isinstance(fields, str) else fields
        except json.JSONDecodeError:
            return f"❌ Ungültiges JSON-Format: {fields}"
        
        return update_entity_func(target, entity_type, fields_dict)
    
    def get_contact_details_wrapper(contact_id: str) -> str:
        """
        Ruft alle Details eines Kontakts ab (Phone, Birthday, Custom Fields, etc.).
        
        Args:
            contact_id: CRM ID des Kontakts (UUID für Twenty, numerisch für Zoho)
            
        Nutze wenn User nach spezifischen Feldern fragt oder du mehr Details brauchst.
        """
        if not get_details_func:
            return "❌ Get-Details nicht verfügbar (nur im Live-Modus)."
        
        return get_details_func(contact_id)

    # === TOOL LIST ===
    
    tools = [
        StructuredTool.from_function(
            search_func, 
            name="search_contacts", 
            description="Sucht Kontakte und Firmen im CRM"
        ),
        StructuredTool.from_function(
            create_contact_wrapper, 
            name="create_contact", 
            description="Erstellt neuen Kontakt/Lead. WICHTIG: Frage IMMER nach first_name, last_name, company und email!"
        ),
        StructuredTool.from_function(
            create_task_wrapper, 
            name="create_task", 
            description="Erstellt Task (Datum im ISO-Format)"
        ),
        StructuredTool.from_function(
            create_note_wrapper, 
            name="create_note", 
            description="Erstellt Notiz"
        ),
        StructuredTool.from_function(
            undo_wrapper, 
            name="undo_last_action", 
            description="Löscht den zuletzt erstellten Eintrag (Lead/Task/Note). Nutze bei: 'rückgängig', 'lösch das', 'undo'"
        )
    ]
    
    # Optional Tools
    if update_entity_func:
        tools.append(
            StructuredTool.from_function(
                update_entity_wrapper, 
                name="update_entity",
                description="Aktualisiert Felder eines CRM-Eintrags"
            )
        )
    
    if get_details_func:
        tools.append(
            StructuredTool.from_function(
                get_contact_details_wrapper,
                name="get_contact_details",
                description="Ruft ALLE Details eines Kontakts ab (Phone, Birthday, Custom Fields, etc.)"
            )
        )
    
    return tools


# === EXPORTS ===

__all__ = [
    "get_crm_tools_for_user",
    "adapter",
    "crm_system",
]
