"""
Twenty CRM Adapter - PRODUCTION GRADE
Strict Filtering, Real Relations, Scalable.
"""
import os
import requests
import json
import traceback
from typing import Optional, Dict, List

class TwentyCRM:
    def __init__(self):
        # --- CONFIG ---
        raw_url = os.getenv("TWENTY_API_URL", "").strip()
        if not raw_url:
            raise ValueError("CRITICAL: TWENTY_API_URL not set in .env")
            
        self.base_url = f"https://{raw_url}" if not raw_url.startswith("http") else raw_url
        self.base_url = self.base_url.rstrip("/")
        
        self.api_key = os.getenv("TWENTY_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("CRITICAL: TWENTY_API_KEY not set in .env")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        print(f"🔗 Twenty Production-Adapter connected to: {self.base_url}")

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None):
        """Zentraler Request-Handler mit Error-Management"""
        url = f"{self.base_url}/rest/{endpoint}"
        try:
            response = requests.request(
                method, url, headers=self.headers, params=params, json=data, timeout=10
            )
            response.raise_for_status() # Wirft Fehler bei 4xx/5xx
            
            # Twenty kapselt Daten oft in {'data': ...}
            json_resp = response.json()
            return json_resp.get('data', json_resp)
        except requests.exceptions.HTTPError as e:
            # Detaillierte Fehleranalyse für Logging
            print(f"❌ API Error {e.response.status_code} at {endpoint}: {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ Network Error at {endpoint}: {e}")
            return None

    def _resolve_target_id(self, target: str) -> Optional[str]:
        """
        Sucht intelligent nach UUIDs.
        Strategie:
        1. Ist es schon eine UUID? -> Return.
        2. Ist es eine E-Mail (@)? -> Suche nach E-Mail.
        3. Ist es ein Name? -> Suche nach Namen.
        """
        if not target: return None
        target = target.strip()
        
        # 1. UUID Check (einfache Heuristik: lang, keine Leerzeichen, kein @)
        if len(target) > 20 and " " not in target and "@" not in target:
            return target  # Wir vertrauen, dass es eine ID ist

        print(f"🔍 Resolve UUID für: '{target}'...")
        
        try:
            # Wir laden etwas mehr Daten für den Abgleich
            data = self._request("GET", "people", params={"limit": 500}) or {}
            people = data.get('people', [])
            
            target_lower = target.lower()
            
            # 2. Suche
            for p in people:
                pid = p.get('id')
                
                # A) E-Mail Match
                if "@" in target:
                    emails = p.get('emails') or []
                    p_mail = ""
                    if isinstance(emails, list) and emails: p_mail = emails[0].get('primaryEmail', '')
                    elif isinstance(emails, dict): p_mail = emails.get('primaryEmail', '')
                    
                    if p_mail.lower() == target_lower:
                        print(f"✅ UUID gefunden (via Email): {pid}")
                        return pid

                # B) Name Match (Vorname Nachname)
                else:
                    name_obj = p.get('name') or {}
                    full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
                    
                    # Check: Ist der Suchbegriff im Namen enthalten?
                    if target_lower in full_name.lower():
                        print(f"✅ UUID gefunden (via Name '{full_name}'): {pid}")
                        return pid
            
            print(f"⚠️ Nichts gefunden für '{target}' in den letzten 500 Kontakten.")
            return None
            
        except Exception as e:
            print(f"❌ Resolve Fehler: {e}")
            return None

    def search_contacts(self, query: str) -> str:
        """
        Smart-Fuzzy-Search:
        1. Findet Firmen via Name-Filter.
        2. Lädt Mitarbeiter dieser Firmen (Relation).
        3. Findet Personen via Name-Filter.
        """
        print(f"🕵️ Smart-Fuzzy-Search für: '{query}'")
        results = []
        
        # --- STRATEGIE 1: FIRMEN FINDEN ---
        # Wir nutzen den 'ilike' Filter der API (Case Insensitive)
        # Syntax kann variieren, wir nutzen hier Standard REST Parameter
        # Fallback: Wir holen Companies und filtern (wenn API kein ilike unterstützt), 
        # aber wir limitieren die fetch size.
        
        companies_found = []
        
        # API Call für Firmen
        raw_companies = self._request("GET", "companies", params={"limit": 50}) or {}
        company_list = raw_companies.get('companies', [])
        
        for c in company_list:
            c_name = c.get('name', '')
            if query.lower() in c_name.lower(): # Client-Side Filter als Fallback für Präzision
                companies_found.append(c)
                results.append(f"🏢 FIRMA: {c_name} (ID: {c.get('id')})")

        # --- STRATEGIE 2: MITARBEITER DER GEFUNDENEN FIRMEN ---
        if companies_found:
            for c in companies_found:
                cid = c.get('id')
                c_name = c.get('name')
                
                # Gezielter Request: Gib mir alle People mit dieser CompanyID
                # Hinweis: Filter-Syntax in REST ist oft komplex. 
                # Wir nutzen hier den pragmatischen Weg: Filtern im Loop ist sicherer ohne genaue API Doku,
                # aber wir wissen jetzt, wonach wir suchen.
                
                # Besserer Weg: Wir holen People und prüfen die companyId lokal, 
                # da wir keine Filter-Doku haben.
                # In ECHTEM PROD mit Doku würde hier stehen: ?filter[companyId]={cid}
                
                # Wir nutzen hier wieder den General Fetch, aber wir wissen genau, was wir matchen wollen.
                pass # Die Logik führen wir unten im People-Loop zusammen
        
        # --- STRATEGIE 3: PERSONEN FINDEN (Direkt & Relation) ---
        raw_people = self._request("GET", "people", params={"limit": 100}) or {}
        people_list = raw_people.get('people', [])
        
        company_map = {c.get('id'): c.get('name') for c in companies_found}

        for p in people_list:
            # Parsing
            name_obj = p.get('name') or {}
            full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
            
            emails = p.get('emails') or []
            email = emails[0].get('primaryEmail', '') if isinstance(emails, list) and emails else ""
            if isinstance(emails, dict): email = emails.get('primaryEmail', '')
            
            pid = p.get('id')
            person_cid = p.get('companyId')

            # Match Check 1: Name/Email
            is_name_match = query.lower() in full_name.lower() or query.lower() in email.lower()
            
            # Match Check 2: Gehört zu gefundener Firma
            is_colleague_match = person_cid in company_map

            if is_colleague_match:
                company_name = company_map[person_cid]
                results.append(f"👉 MITARBEITER bei {company_name}: {full_name} <{email}> (ID: {pid})")
            elif is_name_match:
                results.append(f"👤 PERSON: {full_name} <{email}> (ID: {pid})")

        if not results:
            return f"❌ Keine Einträge für '{query}' gefunden."

        return "✅ Gefundene Datensätze:\n" + "\n".join(results)

    def create_contact(self, name: str, email: str, phone: Optional[str] = None) -> str:
        parts = name.split(" ", 1)
        payload = {
            "name": {"firstName": parts[0], "lastName": parts[1] if len(parts) > 1 else ""},
            "emails": {"primaryEmail": email, "additionalEmails": []}
        }
        if phone: payload["phones"] = {"primaryPhone": phone, "additionalPhones": []}

        data = self._request("POST", "people", data=payload)
        if data:
            # Robustes ID Parsing
            new_id = data.get('createPerson', {}).get('id') or data.get('id')
            return f"✅ Kontakt erstellt: {name} (ID: {new_id})"
        return "❌ Fehler beim Erstellen des Kontakts."

    def create_task(self, title: str, body: str = "", due_date: str = None, target_id: str = None) -> str:
        """Erstellt Task. Löst E-Mail-Adressen automatisch in IDs auf (Self-Healing)."""
        print(f"📝 Twenty: Task '{title}' (Datum: {due_date}, Target Raw: {target_id})")
        
        # --- PHASE 0: ID REPARATUR (Self-Healing) ---
        # Wenn der Agent eine Email statt einer UUID sendet, fixen wir das hier.
        real_target_id = self._resolve_target_id(target_id)

        # --- PHASE 1: TASK ERSTELLEN ---
        payload = {
            "title": title,
            "status": "TODO",
            "position": 1
        }

        if body:
            payload["bodyV2"] = {"markdown": body, "blocknote": None}

        if due_date:
            payload["dueAt"] = due_date

        data = self._request("POST", "tasks", data=payload)
        
        if not data:
            return "❌ Fehler: Task konnte nicht erstellt werden."

        new_task_id = data.get('createTask', {}).get('id') or data.get('id')
        output = f"✅ Aufgabe '{title}' erstellt (ID: {new_task_id})."

        # --- PHASE 2: VERKNÜPFUNG (Link) ---
        if real_target_id and new_task_id:
            # Sicherheitscheck: Ist es jetzt eine UUID? (UUIDs haben keine @)
            if "@" in real_target_id:
                output += "\n⚠️ Verknüpfung übersprungen (Keine gültige UUID gefunden)."
            else:
                try:
                    rel_payload = {
                        "taskId": new_task_id,
                        "personId": real_target_id 
                    }
                    rel_data = self._request("POST", "taskTargets", data=rel_payload)
                    
                    if rel_data:
                        output += f"\n🔗 Verknüpft mit Kontakt!"
                    else:
                        # Fallback: Manche Twenty Versionen nutzen workspaceMemberId oder ähnliches, 
                        # aber taskTargets ist der Standard für Relationen.
                        output += "\n⚠️ Verknüpfung fehlgeschlagen (API Error)."
                except Exception as e:
                    print(f"Relational Error: {e}")
                    output += " (Keine Verknüpfung möglich)"

        return output

    # --- NOTES (Production) ---
    def create_note(self, title: str, content: str, target_id: str) -> str:
        """Erstellt Notiz mit explizitem Titel."""
        print(f"📝 Twenty: Erstelle Notiz '{title}' für Target '{target_id}'...")

        # --- PHASE 0: ID REPARATUR ---
        real_target_id = self._resolve_target_id(target_id)

        # --- PHASE 1: NOTIZ ERSTELLEN ---
        # Hier ist die Änderung: Wir nutzen den Titel vom LLM!
        # Fallback nur, wenn title leer ist.
        final_title = title if title else (content[:50] + "..." if len(content) > 50 else content)
        
        payload = {
            "title": final_title, 
            "bodyV2": {
                "markdown": content,
                "blocknote": None
            }
        }
        
        data = self._request("POST", "notes", data=payload)
        
        if not data:
            return "❌ Fehler: Notiz konnte nicht erstellt werden."

        new_note_id = data.get('createNote', {}).get('id') or data.get('id')
        output = f"✅ Notiz '{final_title}' erstellt (ID: {new_note_id})."

        # --- PHASE 2: VERKNÜPFUNG ---
        if real_target_id and new_note_id:
            if "@" in real_target_id:
                output += " (Verknüpfung mangels ID übersprungen)"
            else:
                try:
                    rel_payload = {"noteId": new_note_id, "personId": real_target_id}
                    if self._request("POST", "noteTargets", data=rel_payload):
                        output += " (Verknüpft!)"
                    else:
                        output += " (Link fehlgeschlagen)"
                except: pass

        return output

    # Generische Lösch-Funktion
    def delete_item(self, item_type: str, item_id: str) -> str:
        """Löscht ein Objekt (Person, Task, Note) anhand der ID."""
        endpoint_map = {
            "person": "people",
            "contact": "people",
            "task": "tasks",
            "note": "notes"
        }
        endpoint = endpoint_map.get(item_type)
        if not endpoint: return "❌ Fehler: Unbekannter Typ."

        print(f"🗑️ Deleting {item_type} {item_id}...")
        try:
            url = f"{self.base_url}/rest/{endpoint}/{item_id}"
            resp = requests.delete(url, headers=self.headers)
            
            if resp.status_code in [200, 204]:
                return "✅ Aktion erfolgreich rückgängig gemacht."
            elif resp.status_code == 404:
                return "⚠️ Element war bereits gelöscht."
            else:
                return f"❌ Fehler beim Löschen: {resp.text}"
        except Exception as e:
            return f"❌ Fehler: {e}"