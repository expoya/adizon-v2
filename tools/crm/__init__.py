"""
CRM Tools Package - The Switchboard
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain.tools import tool
from typing import Optional

# === FIX: Expliziter Pfad zur .env ===
# Wir ermitteln den Pfad dynamisch, egal von wo das Skript läuft.
# Struktur: adizon-v2/tools/crm/__init__.py
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent.parent  # Zwei Ebenen hoch zu 'adizon-v2'
env_path = root_dir / ".env"

# Debug Print (damit wir im Terminal sehen, was passiert)
print(f"🔍 Tools Init: Suche .env Datei in: {env_path}")

# Laden mit explizitem Pfad
load_success = load_dotenv(dotenv_path=env_path)
print(f"📂 .env geladen? {'JA ✅' if load_success else 'NEIN ❌'}")

# =====================================

# Welches System nutzen wir?
crm_system = os.getenv("CRM_SYSTEM", "MOCK").upper().strip() # .strip() entfernt versehentliche Leerzeichen

print(f"🔌 Loading CRM Adapter: {crm_system}")

# --- ADAPTER LOADING ---
adapter = None

if crm_system == "TWENTY":
    try:
        from .twenty_adapter import TwentyCRM
        adapter = TwentyCRM()
        
        search_contacts_func = adapter.search_contacts
        create_contact_func = adapter.create_contact
        print("✅ Twenty Adapter connected")
    except Exception as e:
        print(f"❌ Twenty Init Error: {e}")

elif crm_system == "ZOHO":
    pass # Placeholder

# --- WRAPPER ---
if adapter:
    def _search_impl(query: str):
        return adapter.search_contacts(query)
    def _create_impl(name: str, email: str, phone: Optional[str] = None):
        return adapter.create_contact(name, email, phone)
else:
    # Fallback MOCK
    print("⚠️ Fallback auf MOCK")
    from .create_contact import create_contact as mock_create
    from .search_contacts import search_contacts as mock_search
    
    def _search_impl(query: str):
        return mock_search.invoke(query)
    def _create_impl(name: str, email: str, phone: Optional[str] = None):
        return mock_create.invoke({"name": name, "email": email, "phone": phone})

# LangChain Tools Wrapper
@tool
def search_contacts(query: str) -> str:
    """Sucht nach Kontakten im CRM."""
    return search_contacts_func(query)

@tool
def create_contact(name: str, email: str, phone: Optional[str] = None) -> str:
    """
    Erstellt einen neuen Kontakt im CRM.
    Args:
        name: Vor- und Nachname
        email: E-Mail Adresse
        phone: (Optional) Telefonnummer. Wenn nicht vorhanden, ist es None.
    """
    return _create_impl(name, email, phone)

__all__ = ['search_contacts', 'create_contact']