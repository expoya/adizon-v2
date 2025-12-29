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
update_entity_func = None  # Nur im Live-Modus verfügbar
get_details_func = None  # Nur im Live-Modus verfügbar

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
        search_func = adapter.search_leads  # Zoho nutzt Leads statt contacts
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

# === DIE FACTORY (Das Profi-Teil) ===

def get_crm_tools_for_user(user_id: str) -> list:
    """
    Erstellt ein Tool-Set speziell für diesen User.
    Damit landen Undo-Infos im richtigen Redis-Key.
    """
    
    # 1. Helper zum ID lesen (unterstützt UUID und numerische IDs)
    def _extract_id(text):
        # Versuche UUID Format (Twenty: abc-123-def-456)
        match = re.search(r"\(ID:\s*([a-f0-9\-]+)\)", text)
        if match:
            return match.group(1)
        
        # Versuche numerische ID (Zoho: 1234567890123456)
        match = re.search(r"\(ID:\s*(\d+)\)", text)
        if match:
            return match.group(1)
        
        return None

    # 2. Die Wrapper (Closures)
    def create_contact_wrapper(first_name: str, last_name: str, company: str, email: str, phone: Optional[str] = None) -> str:
        """
        Erstellt neuen Kontakt/Lead im CRM.
        
        PFLICHTFELDER (Agent muss ALLE abfragen):
        - first_name: Vorname des Kontakts
        - last_name: Nachname des Kontakts
        - company: Firmenname (wenn unbekannt: "Unbekannt" oder "-")
        - email: E-Mail Adresse
        
        OPTIONAL:
        - phone: Telefonnummer
        
        WICHTIG: Frage den User IMMER nach allen Pflichtfeldern, bevor du dieses Tool nutzt!
        
        Beispiel:
        User: "Erstelle Lead für Max"
        Agent: "Gerne! Ich brauche noch: Nachname, Firma und E-Mail von Max."
        """
        res = create_contact_func(first_name, last_name, company, email, phone)
        # Bei Zoho: "lead", bei Twenty: "person"
        entity_type = "lead" if crm_system == "ZOHO" else "person"
        if pid := _extract_id(res): save_undo_context(user_id, entity_type, pid)
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
    
    def update_entity_wrapper(target: str, entity_type: str, fields: str) -> str:
        """
        Aktualisiert Felder eines CRM-Eintrags.
        
        Args:
            target: Name, Email oder ID des Eintrags
            entity_type: "person"/"company" (Twenty) oder "lead" (Zoho)
            fields: JSON string mit Feldern, z.B. '{"website": "expoya.com", "size": 50}'
            
        Verfügbare Felder (Twenty):
            Person: job, linkedin, city, birthday
            Company: website, size, industry, address, roof_area
        
        Verfügbare Felder (Zoho):
            Lead: email, phone, mobile, job, linkedin, company, website, size, 
                  industry, revenue, street, city, state, zip, country, 
                  lead_source, notes, roof_area
        
        Beispiele (Twenty):
            update_entity("Thomas Braun", "person", '{{"job": "CEO", "linkedin": "linkedin.com/in/thomas"}}')
            update_entity("Expoya", "company", '{{"website": "expoya.com", "size": 50}}')
        
        Beispiele (Zoho):
            update_entity("Max Mustermann", "lead", '{{"job": "CEO", "company": "Expoya", "website": "expoya.com"}}')
        """
        if not update_entity_func:
            return "❌ Update-Feature nicht verfügbar (nur im Live-Modus mit CRM-Adapter)."
        
        # Parse JSON string zu dict
        import json
        try:
            fields_dict = json.loads(fields) if isinstance(fields, str) else fields
        except json.JSONDecodeError:
            return f"❌ Ungültiges JSON-Format für fields: {fields}"
        
        return update_entity_func(target, entity_type, fields_dict)
    
    def get_contact_details_wrapper(contact_id: str) -> str:
        """
        Ruft alle Details eines Kontakts ab (inkl. Phone, Custom Fields, etc.).
        
        Args:
            contact_id: CRM ID des Kontakts (UUID für Twenty, numerisch für Zoho)
            
        Returns:
            Formatierte Details mit allen verfügbaren Feldern
            
        Nutze dieses Tool, wenn:
        - User nach spezifischen Feldern fragt (z.B. "Welche Telefonnummer hat X?")
        - Du mehr Details brauchst als search_contacts liefert
        - Du bereits die ID eines Kontakts hast
        """
        if not get_details_func:
            return "❌ Get-Details-Feature nicht verfügbar (nur im Live-Modus mit CRM-Adapter)."
        
        return get_details_func(contact_id)

    # 3. Liste zurückgeben
    tools = [
        StructuredTool.from_function(search_func, name="search_contacts", description="Sucht Kontakte und Firmen im CRM"),
        StructuredTool.from_function(
            create_contact_wrapper, 
            name="create_contact", 
            description="Erstellt neuen Kontakt/Lead. WICHTIG: Frage IMMER nach first_name, last_name, company und email, bevor du dieses Tool nutzt! Nur phone ist optional."
        ),
        StructuredTool.from_function(create_task_wrapper, name="create_task", description="Erstellt Task (Datum im ISO-Format)"),
        StructuredTool.from_function(create_note_wrapper, name="create_note", description="Erstellt Notiz"),
        StructuredTool.from_function(undo_wrapper, name="undo_last_action", description="Löscht den zuletzt erstellten Eintrag (Lead/Task/Note). Nutze wenn User sagt: 'rückgängig', 'lösch das', 'undo'")
    ]
    
    # Update-Tool nur hinzufügen, wenn verfügbar
    if update_entity_func:
        tools.append(
            StructuredTool.from_function(
                update_entity_wrapper, 
                name="update_entity",
                description="Aktualisiert Felder eines CRM-Eintrags (Person: job, linkedin, city, birthday | Company: website, size, industry, address)"
            )
        )
    
    # Get-Details-Tool nur hinzufügen, wenn verfügbar
    if get_details_func:
        tools.append(
            StructuredTool.from_function(
                get_contact_details_wrapper,
                name="get_contact_details",
                description="Ruft ALLE Details eines Kontakts ab (Phone, Birthday, Custom Fields, etc.). Nutze wenn User nach spezifischen Feldern fragt oder du mehr Details brauchst."
            )
        )
    
    return tools