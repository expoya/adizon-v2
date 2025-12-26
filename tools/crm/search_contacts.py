"""
Search Contacts Tool
Sucht Kontakte in Zoho CRM
"""

from langchain.tools import tool


@tool
def search_contacts(query: str) -> str:
    """
    Sucht nach Kontakten im CRM.
    
    Args:
        query: Suchbegriff (Name, Email, Firma)
        
    Returns:
        Liste gefundener Kontakte
    """
    
    print(f"🔧 Tool: search_contacts")
    print(f"   Query: {query}")
    
    # TODO: Zoho API Integration
    # Aktuell: Dummy Data
    
    dummy_contacts = [
        {"name": "Max Mustermann", "email": "max@example.com", "id": "001"},
        {"name": "Maria Musterfrau", "email": "maria@example.com", "id": "002"},
    ]
    
    results = [c for c in dummy_contacts if query.lower() in c['name'].lower()]
    
    if not results:
        return f"❌ Keine Kontakte gefunden für: {query}"
    
    response = f"✅ {len(results)} Kontakt(e) gefunden:\n\n"
    for contact in results:
        response += f"📇 {contact['name']}\n"
        response += f"   Email: {contact['email']}\n"
        response += f"   ID: {contact['id']}\n\n"
    
    return response