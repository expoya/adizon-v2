from typing import Protocol, List, Dict, Optional

class CRMInterface(Protocol):
    """
    Der Bauplan für alle CRM Adapter.
    Adizon Core spricht NUR mit diesem Interface.
    """
    
    def search_contacts(self, query: str) -> str:
        """Sucht Kontakte und gibt formatierten Text zurück"""
        ...
        
    def create_contact(self, name: str, email: str, phone: Optional[str] = None) -> str:
        """Erstellt Kontakt und gibt Bestätigung zurück"""
        ...