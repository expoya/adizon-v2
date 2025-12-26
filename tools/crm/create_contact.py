"""
Create Contact Tool
Erstellt einen neuen Kontakt in Zoho CRM
"""

from langchain.tools import tool
from typing import Optional


@tool
def create_contact(name: str, email: str, phone: Optional[str] = None) -> str:
    """
    Erstellt einen neuen Kontakt im CRM.
    
    Args:
        name: Vollständiger Name des Kontakts (Pflichtfeld)
        email: E-Mail-Adresse (Pflichtfeld - Zoho Requirement)
        phone: Telefonnummer (optional)
        
    Returns:
        Bestätigungsnachricht mit Kontakt-Details
    """
    
    print(f"🔧 Tool: create_contact")
    print(f"   Name: {name}")
    print(f"   Email: {email}")
    print(f"   Phone: {phone}")
    
    # TODO: Zoho API Integration
    # Aktuell: Dummy Response
    
    contact_data = {
        "name": name,
        "email": email,
        "phone": phone or "Nicht angegeben",
        "id": "DEMO_12345"
    }
    
    return f"""✅ Kontakt erfolgreich erstellt!

📋 Details:
- Name: {contact_data['name']}
- Email: {contact_data['email']}
- Phone: {contact_data['phone']}
- ID: {contact_data['id']}

Der Kontakt wurde im CRM gespeichert."""