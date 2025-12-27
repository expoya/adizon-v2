"""
Twenty CRM Adapter - ROBUST & FIXED
"""
import os
import requests
import traceback
from typing import Optional

class TwentyCRM:
    def __init__(self):
        # 1. URL Setup (HTTPS erzwingen)
        raw_url = os.getenv("TWENTY_API_URL", "").strip()
        if not raw_url:
            self.base_url = "http://MISSING_URL"
        else:
            if not raw_url.startswith("http"):
                self.base_url = f"https://{raw_url}"
            else:
                self.base_url = raw_url
            self.base_url = self.base_url.rstrip("/")

        self.api_key = os.getenv("TWENTY_API_KEY", "").strip()
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        print(f"🔗 Twenty Adapter connected to: {self.base_url}")

    def search_contacts(self, query: str) -> str:
        print(f"🕵️ Twenty: Suche nach '{query}'...")
        
        try:
            response = requests.get(
                f"{self.base_url}/rest/people", 
                headers=self.headers,
                params={"limit": 50}, # Limit erhöhen
                timeout=10
            )
            
            if response.status_code != 200:
                return f"❌ API Fehler {response.status_code}: {response.text}"
                
            data = response.json()
            people = data.get('data', {}).get('people', [])
            
            results = []
            for p in people:
                # 1. Name sicher extrahieren
                name_obj = p.get('name')
                if not name_obj: name_obj = {} # Fallback falls None
                full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
                
                # 2. Email sicher extrahieren (DER FIX FÜR KEYERROR: 0)
                emails_data = p.get('emails')
                primary_email = "Keine Email"
                
                if isinstance(emails_data, list) and len(emails_data) > 0:
                    # Es ist eine Liste -> Erstes Element nehmen
                    primary_email = emails_data[0].get('primaryEmail', '')
                elif isinstance(emails_data, dict):
                    # Es ist ein Dictionary -> Direkt zugreifen
                    primary_email = emails_data.get('primaryEmail', '')
                
                # 3. ID sicher extrahieren
                pid = p.get('id', 'No ID')

                # Matching
                if (query.lower() in full_name.lower() or 
                    query.lower() in primary_email.lower()):
                    results.append(f"- {full_name} ({primary_email}) [ID: {pid}]")
            
            if not results:
                return f"❌ Nichts in Twenty gefunden für: {query}"
                
            return f"✅ {len(results)} Treffer in Twenty:\n" + "\n".join(results)
            
        except Exception as e:
            print("❌ Fehler im Adapter:")
            traceback.print_exc()
            return f"❌ Systemfehler: {str(e)}"

    def create_contact(self, name: str, email: str, phone: Optional[str] = None) -> str:
        print(f"📝 Twenty: Erstelle '{name}'...")
        
        try:
            parts = name.split(" ", 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ""
            
            payload = {
                "name": {
                    "firstName": first_name,
                    "lastName": last_name
                },
                "emails": {
                    "primaryEmail": email,
                    "additionalEmails": []
                }
            }
            
            # Telefon nur hinzufügen, wenn vorhanden
            if phone:
                payload["phones"] = {
                    "primaryPhone": phone,
                    "additionalPhones": []
                }

            response = requests.post(
                f"{self.base_url}/rest/people",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                # ID extrahieren (manchmal data.id, manchmal data.createPerson.id)
                res_data = data.get('data', {})
                # Versuchen wir verschiedene Pfade
                new_id = res_data.get('createPerson', {}).get('id') or res_data.get('id') or 'UNKNOWN'
                
                return f"✅ Kontakt erfolgreich in Twenty erstellt!\nName: {name}\nID: {new_id}"
            else:
                return f"❌ Fehler beim Erstellen: {response.status_code} - {response.text}"
                
        except Exception as e:
            traceback.print_exc()
            return f"❌ Twenty Error: {str(e)}"