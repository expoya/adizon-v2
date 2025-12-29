"""
Zoho CRM Adapter - PRODUCTION GRADE
OAuth 2.0 Token Management, Fuzzy-Search, Dynamic Field Enrichment, Self-Healing.
"""
import os
import requests
import json
import time
from typing import Optional, Dict, List, Tuple
from rapidfuzz import fuzz
from .field_mapping_loader import load_field_mapping


class ZohoCRM:
    def __init__(self):
        # --- OAUTH CONFIG ---
        self.client_id = os.getenv("ZOHO_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("ZOHO_CLIENT_SECRET", "").strip()
        self.refresh_token = os.getenv("ZOHO_REFRESH_TOKEN", "").strip()
        
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("CRITICAL: ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, and ZOHO_REFRESH_TOKEN must be set in .env")
        
        # --- API URLS (Region-specific) ---
        self.api_url = os.getenv("ZOHO_API_URL", "https://www.zohoapis.eu").strip().rstrip("/")
        self.accounts_url = os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.eu").strip().rstrip("/")
        
        # --- TOKEN STATE ---
        self.access_token = None
        self.token_expires_at = 0  # Unix timestamp
        
        # Field Mapping Loader
        try:
            self.field_mapper = load_field_mapping("zoho")
            field_count = sum(len(self.field_mapper.get_allowed_fields(e)) for e in self.field_mapper.get_entities())
            print(f"✅ Field Mapping loaded: {field_count} fields across {len(self.field_mapper.get_entities())} entities")
        except Exception as e:
            print(f"⚠️ Field Mapping konnte nicht geladen werden: {e}")
            self.field_mapper = None
        
        # Initial Token Refresh
        self._refresh_access_token()
        
        print(f"🔗 Zoho Production-Adapter connected to: {self.api_url}")
    
    def _refresh_access_token(self):
        """
        Erneuert Access Token mit Refresh Token.
        Access Token ist 1 Stunde gültig, wird automatisch erneuert.
        """
        print("🔄 Refreshing Zoho Access Token...")
        
        token_url = f"{self.accounts_url}/oauth/v2/token"
        
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }
        
        try:
            response = requests.post(token_url, data=payload, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)  # Default: 1 Stunde
            
            # Token läuft ab in X Sekunden - wir erneuern 5 Min früher
            self.token_expires_at = time.time() + expires_in - 300
            
            print(f"✅ Access Token refreshed (expires in {expires_in}s)")
            
        except Exception as e:
            print(f"❌ Token Refresh Error: {e}")
            raise ValueError("Failed to refresh Zoho Access Token. Check credentials!")
    
    def _is_token_expired(self) -> bool:
        """Prüft, ob Access Token abgelaufen ist"""
        return time.time() >= self.token_expires_at
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Gibt Headers mit aktuellem Access Token zurück.
        Erneuert Token automatisch wenn nötig.
        """
        if self._is_token_expired():
            self._refresh_access_token()
        
        return {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def _fuzzy_match(self, query: str, target: str, threshold: int = 70) -> Tuple[bool, float]:
        """
        Fuzzy-Matching mit rapidfuzz.
        
        Strategien:
        1. Token Sort Ratio - Wort-Reihenfolge egal ("Braun Thomas" = "Thomas Braun")
        2. Partial Ratio - Findet Teilstrings mit Toleranz
        3. Ratio - Gesamtähnlichkeit
        
        Args:
            query: Suchbegriff
            target: Zu vergleichender Text
            threshold: Minimaler Score (0-100)
            
        Returns:
            (is_match, score)
        """
        if not query or not target:
            return (False, 0.0)
        
        q = query.lower().strip()
        t = target.lower().strip()
        
        # Strategie 1: Exaktes Substring-Match (schnellster Weg)
        if q in t:
            return (True, 100.0)
        
        # Strategie 2: Token Sort (Reihenfolge egal)
        token_score = fuzz.token_sort_ratio(q, t)
        
        # Strategie 3: Partial Ratio (Substring mit Fuzzy)
        partial_score = fuzz.partial_ratio(q, t)
        
        # Strategie 4: Standard Ratio (Gesamtähnlichkeit)
        simple_score = fuzz.ratio(q, t)
        
        # Bester Score gewinnt
        best_score = max(token_score, partial_score, simple_score)
        
        return (best_score >= threshold, float(best_score))
    
    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None):
        """Zentraler Request-Handler mit Error-Management"""
        url = f"{self.api_url}/crm/v8/{endpoint}"
        
        try:
            response = requests.request(
                method, 
                url, 
                headers=self._get_headers(), 
                params=params, 
                json=data, 
                timeout=10
            )
            response.raise_for_status()
            
            # Zoho kapselt Daten in {'data': [...]}
            json_resp = response.json()
            return json_resp
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ API Error {e.response.status_code} at {endpoint}: {e.response.text}")
            return None
        except Exception as e:
            print(f"❌ Network Error at {endpoint}: {e}")
            return None
    
    def _resolve_target_id(self, target: str) -> Optional[str]:
        """
        Sucht intelligent nach Lead IDs mit Fuzzy-Matching.
        
        Strategie:
        1. Ist es schon eine ID? -> Return.
        2. Ist es eine E-Mail (@)? -> Fuzzy-Suche nach E-Mail.
        3. Ist es ein Name? -> Fuzzy-Suche nach Namen (sortiert nach Score).
        
        Args:
            target: Name, Email oder ID
            
        Returns:
            Lead ID oder None
        """
        if not target:
            return None
        
        target = target.strip()
        
        # 1. ID Check (Zoho IDs sind numerisch, 16-19 Stellen)
        if target.isdigit() and len(target) >= 16:
            return target
        
        print(f"🔍 Fuzzy-Resolve Lead ID für: '{target}'...")
        
        try:
            # Hole Leads (max 200) - Zoho braucht explizite Fields!
            fields = "id,First_Name,Last_Name,Email,Company,Phone,Mobile,Designation"
            response = self._request("GET", "Leads", params={"per_page": 200, "fields": fields})
            
            if not response or "data" not in response:
                print("⚠️ Keine Leads gefunden")
                return None
            
            leads = response.get("data", [])
            candidates = []
            
            # 2. Suche mit Fuzzy-Matching
            for lead in leads:
                lead_id = lead.get("id")
                
                # A) E-Mail Match
                if "@" in target:
                    email = lead.get("Email", "")
                    if email:
                        is_match, score = self._fuzzy_match(target, email, threshold=80)
                        if is_match:
                            candidates.append({
                                'id': lead_id,
                                'score': score,
                                'matched': email,
                                'type': 'email'
                            })
                
                # B) Name Match (Fuzzy)
                else:
                    first_name = lead.get("First_Name", "")
                    last_name = lead.get("Last_Name", "")
                    full_name = f"{first_name} {last_name}".strip()
                    
                    if full_name:
                        is_match, score = self._fuzzy_match(target, full_name, threshold=70)
                        if is_match:
                            candidates.append({
                                'id': lead_id,
                                'score': score,
                                'matched': full_name,
                                'type': 'name'
                            })
                    
                    # Auch Company-Name checken
                    company = lead.get("Company", "")
                    if company:
                        is_match, score = self._fuzzy_match(target, company, threshold=70)
                        if is_match:
                            candidates.append({
                                'id': lead_id,
                                'score': score,
                                'matched': company,
                                'type': 'company'
                            })
            
            # 3. Besten Kandidaten wählen (höchster Score)
            if candidates:
                best = max(candidates, key=lambda x: x['score'])
                print(f"✅ Lead ID gefunden (via {best['type']} '{best['matched']}', Score: {best['score']:.0f}%): {best['id']}")
                return best['id']
            
            print(f"⚠️ Nichts gefunden für '{target}'")
            return None
            
        except Exception as e:
            print(f"❌ Resolve Fehler: {e}")
            return None
    
    def search_leads(self, query: str) -> str:
        """
        Smart-Fuzzy-Search für Leads:
        1. Findet Leads via Fuzzy-Match (Name, Email, Company).
        2. Sortiert nach Relevanz-Score (beste Matches zuerst).
        """
        print(f"🕵️ Smart-Fuzzy-Search für: '{query}'")
        results = []
        
        try:
            # Hole Leads - Zoho braucht explizite Fields!
            fields = "id,First_Name,Last_Name,Email,Company,Phone,Mobile,Designation"
            response = self._request("GET", "Leads", params={"per_page": 100, "fields": fields})
            
            if not response or "data" not in response:
                return f"❌ Keine Leads gefunden."
            
            leads = response.get("data", [])
            
            for lead in leads:
                # Parsing
                first_name = lead.get("First_Name", "")
                last_name = lead.get("Last_Name", "")
                full_name = f"{first_name} {last_name}".strip()
                
                email = lead.get("Email", "")
                company = lead.get("Company", "")
                phone = lead.get("Phone", "")
                designation = lead.get("Designation", "")
                
                lead_id = lead.get("id")
                
                # Fuzzy-Match auf Name, Email, Company
                name_match, name_score = self._fuzzy_match(query, full_name, threshold=70)
                email_match, email_score = self._fuzzy_match(query, email, threshold=75) if email else (False, 0)
                company_match, company_score = self._fuzzy_match(query, company, threshold=70) if company else (False, 0)
                
                # Bester Score gewinnt
                best_score = max(name_score, email_score, company_score)
                is_match = name_match or email_match or company_match
                
                if is_match:
                    # Formatierung
                    display_parts = [f"👤 {full_name}"]
                    if designation:
                        display_parts.append(f"({designation})")
                    if company:
                        display_parts.append(f"@ {company}")
                    if email:
                        display_parts.append(f"<{email}>")
                    if phone:
                        display_parts.append(f"📞 {phone}")
                    
                    results.append({
                        'name': full_name,
                        'email': email,
                        'company': company,
                        'phone': phone,
                        'id': lead_id,
                        'score': best_score,
                        'display': " ".join(display_parts)
                    })
            
            # Sortierung nach Score (beste Matches zuerst)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            if not results:
                return f"❌ Keine Einträge für '{query}' gefunden."
            
            # Formatierung mit Score (optional für Debug)
            formatted_results = []
            for r in results:
                score_display = f" [Match: {r['score']:.0f}%]" if r['score'] < 100 else ""
                formatted_results.append(f"{r['display']}{score_display} (ID: {r['id']})")
            
            return "✅ Gefundene Leads:\n" + "\n".join(formatted_results)
            
        except Exception as e:
            print(f"❌ Search Error: {e}")
            return f"❌ Fehler bei der Suche: {str(e)}"
    
    def create_contact(self, first_name: str, last_name: str, company: str, email: str, phone: Optional[str] = None) -> str:
        """
        Erstellt neuen Lead in Zoho CRM.
        
        WICHTIG: Alle Parameter außer phone sind PFLICHTFELDER!
        
        Args:
            first_name: Vorname (REQUIRED)
            last_name: Nachname (REQUIRED)
            company: Firmenname (REQUIRED - auch wenn unbekannt, dann "-" oder "Unbekannt")
            email: E-Mail Adresse (REQUIRED)
            phone: Telefonnummer (OPTIONAL)
            
        Returns:
            Erfolgsmeldung mit Lead ID
        """
        payload = {
            "data": [{
                "First_Name": first_name,
                "Last_Name": last_name,
                "Company": company,
                "Email": email,
                "Lead_Source": "AI Assistant"
            }]
        }
        
        if phone:
            payload["data"][0]["Phone"] = phone
        
        print(f"📝 Creating Lead: {first_name} {last_name} @ {company} <{email}>")
        
        response = self._request("POST", "Leads", data=payload)
        
        # Besseres Error-Handling
        if not response:
            return "❌ Fehler beim Erstellen des Leads (API Error)."
        
        if "data" in response:
            lead_data = response["data"][0]
            
            # Prüfe ob erfolgreich
            code = lead_data.get("code")
            if code == "SUCCESS":
                lead_id = lead_data.get("details", {}).get("id")
                full_name = f"{first_name} {last_name}"
                return f"✅ Lead erstellt: {full_name} @ {company} (ID: {lead_id})"
            else:
                # API hat Error zurückgegeben
                message = lead_data.get("message", "Unknown error")
                return f"❌ Lead konnte nicht erstellt werden: {message}"
        
        return "❌ Fehler beim Erstellen des Leads (Unerwartete Response)."
    
    def create_task(self, title: str, body: str = "", due_date: str = None, target_id: str = None) -> str:
        """
        Erstellt Task in Zoho CRM.
        Löst Names/Emails automatisch in IDs auf (Self-Healing).
        """
        print(f"📝 Zoho: Task '{title}' (Datum: {due_date}, Target: {target_id})")
        
        # --- PHASE 0: ID REPARATUR (Self-Healing) ---
        real_target_id = None
        if target_id:
            real_target_id = self._resolve_target_id(target_id)
        
        # --- PHASE 1: TASK ERSTELLEN ---
        # Subject ist PFLICHTFELD!
        payload = {
            "data": [{
                "Subject": title,  # REQUIRED
                "Status": "Not Started",
                "Priority": "Normal"
            }]
        }
        
        if body:
            payload["data"][0]["Description"] = body
        
        if due_date:
            # Zoho erwartet Format: YYYY-MM-DD
            payload["data"][0]["Due_Date"] = due_date
        
        # Verknüpfung mit Lead (What_Id + $se_module sind REQUIRED für Verknüpfung!)
        if real_target_id:
            payload["data"][0]["What_Id"] = real_target_id
            payload["data"][0]["$se_module"] = "Leads"  # Gibt an, mit welchem Modul verknüpft
        
        print(f"📝 Task Payload: Subject='{title}', What_Id={real_target_id}, Module=Leads")
        
        response = self._request("POST", "Tasks", data=payload)
        
        # Besseres Error-Handling
        if not response:
            return "❌ Fehler: Task konnte nicht erstellt werden (API Error)."
        
        if "data" in response:
            task_data = response["data"][0]
            
            # Prüfe ob erfolgreich
            code = task_data.get("code")
            if code == "SUCCESS":
                task_id = task_data.get("details", {}).get("id")
                output = f"✅ Aufgabe '{title}' erstellt (ID: {task_id})"
                
                if real_target_id:
                    output += " 🔗 Verknüpft mit Lead!"
                elif target_id:
                    output += " ⚠️ Verknüpfung fehlgeschlagen (Lead nicht gefunden)."
                
                return output
            else:
                # API hat Error zurückgegeben
                message = task_data.get("message", "Unknown error")
                return f"❌ Task konnte nicht erstellt werden: {message}"
        
        return "❌ Fehler: Task konnte nicht erstellt werden (Unerwartete Response)."
    
    def create_note(self, title: str, content: str, target_id: str) -> str:
        """
        Erstellt Notiz in Zoho CRM.
        Löst Names/Emails automatisch in IDs auf (Self-Healing).
        """
        print(f"📝 Zoho: Erstelle Notiz '{title}' für Target '{target_id}'...")
        
        # --- PHASE 0: ID REPARATUR ---
        real_target_id = self._resolve_target_id(target_id)
        
        if not real_target_id:
            return f"❌ Lead '{target_id}' nicht gefunden. Notiz konnte nicht erstellt werden."
        
        # --- PHASE 1: NOTIZ ERSTELLEN ---
        # Zoho Notes API Format (laut Docs)
        payload = {
            "data": [{
                "Parent_Id": {
                    "module": {
                        "api_name": "Leads"
                    },
                    "id": real_target_id
                },
                "Note_Content": content,
                "Note_Title": title  # Optional, aber gut für UX
            }]
        }
        
        print(f"📝 Note Payload: Parent_Id={real_target_id}, Title={title}")
        
        response = self._request("POST", "Notes", data=payload)
        
        # Besseres Error-Handling
        if not response:
            return "❌ Fehler: Notiz konnte nicht erstellt werden (API Error)."
        
        if "data" in response:
            note_data = response["data"][0]
            
            # Prüfe ob erfolgreich
            code = note_data.get("code")
            if code == "SUCCESS":
                note_id = note_data.get("details", {}).get("id")
                return f"✅ Notiz '{title}' erstellt (ID: {note_id})"
            else:
                # API hat Error zurückgegeben
                message = note_data.get("message", "Unknown error")
                return f"❌ Notiz konnte nicht erstellt werden: {message}"
        
        return "❌ Fehler: Notiz konnte nicht erstellt werden (Unerwartete Response)."
    
    def update_entity(self, target: str, entity_type: str, fields: dict) -> str:
        """
        Aktualisiert beliebige Felder eines Leads (Dynamic Field Enrichment).
        
        Features:
        - Whitelist-basiert: Nur erlaubte Felder werden akzeptiert
        - Field Mapping: Generic Names → Zoho Field Names
        - Validation: Type-Checking + Auto-Fix
        - Self-Healing: Name/Email → ID Resolution
        - Auto-Mapping: "person"/"company" → "lead" (Zoho hat nur Leads)
        
        Args:
            target: Name, Email oder Lead ID
            entity_type: "lead", "person" oder "company" (wird automatisch auf "lead" gemappt)
            fields: Dict mit generic field names
            
        Returns:
            Bestätigung mit aktualisierten Feldern
            
        Example:
            update_entity("Max Mustermann", "person", {"job": "CEO"})
            → Wird automatisch auf entity_type="lead" gemappt
        """
        # 0. Auto-Mapping: Bei Zoho gibt es nur "lead" (kombiniert Person + Company)
        if entity_type in ["person", "company"]:
            print(f"🔄 Auto-Mapping: entity_type '{entity_type}' → 'lead' (Zoho Struktur)")
            entity_type = "lead"
        
        print(f"📝 Update Lead: '{target}' with {fields}")
        
        # 1. Field Mapper Check
        if not self.field_mapper:
            return "❌ Field Mapping nicht verfügbar. Feature deaktiviert."
        
        # 2. Target-ID auflösen (Self-Healing)
        lead_id = self._resolve_target_id(target)
        
        if not lead_id:
            return f"❌ Lead '{target}' nicht gefunden im CRM."
        
        # 3. Felder validieren und mappen (nur Whitelist + Auto-Fix)
        validated_fields = {}
        skipped_fields = []
        
        for field_name, value in fields.items():
            # Prüfe ob Feld in Whitelist
            if not self.field_mapper.is_field_allowed("lead", field_name):
                print(f"⚠️ Feld '{field_name}' nicht in Whitelist (übersprungen)")
                skipped_fields.append(field_name)
                continue
            
            # Validiere & Auto-Fix
            is_valid, corrected_value, error = self.field_mapper.validate_field(
                "lead", field_name, value
            )
            
            if not is_valid:
                print(f"⚠️ Validation failed für '{field_name}': {error}")
                skipped_fields.append(field_name)
                continue
            
            # Mappe zu Zoho-Feldnamen
            crm_field = self.field_mapper.get_crm_field_name("lead", field_name)
            if crm_field:
                validated_fields[crm_field] = corrected_value
        
        # 4. Check: Wurden Felder validiert?
        if not validated_fields:
            if skipped_fields:
                return f"⚠️ Keine gültigen Felder zum Aktualisieren. Übersprungen: {', '.join(skipped_fields)}"
            else:
                return f"⚠️ Keine Felder zum Aktualisieren übergeben."
        
        print(f"🔄 Mapped & Validated: {validated_fields}")
        
        # 5. API Call (PUT)
        payload = {"data": [validated_fields]}
        
        response = self._request("PUT", f"Leads/{lead_id}", data=payload)
        
        if not response or "data" not in response:
            failed_fields = ", ".join([f"{k}={v}" for k, v in fields.items()])
            return f"❌ CRM hat Update abgelehnt. Versuchte Felder: {failed_fields}"
        
        # 6. Response formatieren
        updated_list = []
        for field_name, value in fields.items():
            if field_name not in skipped_fields:
                updated_list.append(f"{field_name}: {value}")
        
        response_text = f"✅ Lead aktualisiert: {', '.join(updated_list)}"
        
        if skipped_fields:
            response_text += f"\n⚠️ Übersprungen: {', '.join(skipped_fields)}"
        
        return response_text
    
    def delete_item(self, item_type: str, item_id: str) -> str:
        """
        Löscht ein Objekt (Lead, Task, Note) anhand der ID.
        Für Undo-Funktion.
        """
        endpoint_map = {
            "lead": "Leads",
            "contact": "Leads",
            "task": "Tasks",
            "note": "Notes"
        }
        
        endpoint = endpoint_map.get(item_type)
        if not endpoint:
            return "❌ Fehler: Unbekannter Typ."
        
        print(f"🗑️ Deleting {item_type} {item_id} from {endpoint}...")
        
        try:
            url = f"{self.api_url}/crm/v8/{endpoint}/{item_id}"
            print(f"🗑️ DELETE URL: {url}")
            
            response = requests.delete(url, headers=self._get_headers(), timeout=10)
            
            print(f"🗑️ Response Status: {response.status_code}")
            print(f"🗑️ Response Body: {response.text}")
            
            if response.status_code in [200, 204]:
                return "✅ Aktion erfolgreich rückgängig gemacht."
            elif response.status_code == 404:
                return "⚠️ Element war bereits gelöscht."
            else:
                # Detaillierter Error
                try:
                    error_data = response.json()
                    message = error_data.get("message", response.text)
                    return f"❌ Fehler beim Löschen: {message}"
                except:
                    return f"❌ Fehler beim Löschen (Status {response.status_code}): {response.text}"
                
        except Exception as e:
            print(f"❌ Exception beim Löschen: {e}")
            return f"❌ Fehler: {e}"

