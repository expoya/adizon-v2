"""
Twenty CRM Adapter - PRODUCTION GRADE
Strict Filtering, Real Relations, Scalable, Fuzzy-Search, Dynamic Field Enrichment.
"""
import os
import requests
import json
import traceback
from typing import Optional, Dict, List, Tuple
from rapidfuzz import fuzz
from .field_mapping_loader import load_field_mapping

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
        
        # Field Mapping Loader
        try:
            self.field_mapper = load_field_mapping("twenty")
            field_count = sum(len(self.field_mapper.get_allowed_fields(e)) for e in self.field_mapper.get_entities())
            print(f"✅ Field Mapping loaded: {field_count} fields across {len(self.field_mapper.get_entities())} entities")
        except Exception as e:
            print(f"⚠️ Field Mapping konnte nicht geladen werden: {e}")
            self.field_mapper = None
        
        print(f"🔗 Twenty Production-Adapter connected to: {self.base_url}")

    def _fuzzy_match(self, query: str, target: str, threshold: int = 70) -> Tuple[bool, float]:
        """
        Fuzzy-Matching mit rapidfuzz.
        
        Strategien:
        1. Token Sort Ratio - Wort-Reihenfolge egal ("Braun Thomas" = "Thomas Braun")
        2. Partial Ratio - Findet Teilstrings mit Toleranz ("Thomas" in "Thomas Braun")
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

    def _resolve_target_id(self, target: str, entity_type: str = "person") -> Optional[str]:
        """
        Sucht intelligent nach UUIDs mit Fuzzy-Matching.
        Unterstützt: People und Companies
        
        Strategie:
        1. Ist es schon eine UUID? -> Return.
        2. Ist es eine E-Mail (@)? -> Fuzzy-Suche nach E-Mail (nur bei person).
        3. Ist es ein Name? -> Fuzzy-Suche nach Namen (sortiert nach Score).
        
        Args:
            target: Name, Email oder UUID
            entity_type: "person" oder "company"
        """
        if not target: return None
        target = target.strip()
        
        # 1. UUID Check (einfache Heuristik: lang, keine Leerzeichen, kein @)
        if len(target) > 20 and " " not in target and "@" not in target:
            return target  # Wir vertrauen, dass es eine ID ist

        print(f"🔍 Fuzzy-Resolve UUID für {entity_type}: '{target}'...")
        
        try:
            # Endpoint basierend auf entity_type
            if entity_type == "company":
                endpoint = "companies"
                data = self._request("GET", endpoint, params={"limit": 200}) or {}
                items = data.get('companies', [])
            else:  # person
                endpoint = "people"
                data = self._request("GET", endpoint, params={"limit": 500}) or {}
                items = data.get('people', [])
            
            # Kandidaten mit Scores sammeln
            candidates = []
            
            # 2. Suche mit Fuzzy-Matching
            for item in items:
                item_id = item.get('id')
                
                if entity_type == "company":
                    # Company: Nur nach Name suchen
                    company_name = item.get('name', '').strip()
                    
                    if company_name:
                        is_match, score = self._fuzzy_match(target, company_name, threshold=70)
                        if is_match:
                            candidates.append({
                                'id': item_id, 
                                'score': score, 
                                'matched': company_name, 
                                'type': 'company_name'
                            })
                
                else:  # person
                    # A) E-Mail Match
                    if "@" in target:
                        emails = item.get('emails') or []
                        p_mail = ""
                        if isinstance(emails, list) and emails: 
                            p_mail = emails[0].get('primaryEmail', '')
                        elif isinstance(emails, dict): 
                            p_mail = emails.get('primaryEmail', '')
                        
                        if p_mail:
                            is_match, score = self._fuzzy_match(target, p_mail, threshold=80)
                            if is_match:
                                candidates.append({
                                    'id': item_id, 
                                    'score': score, 
                                    'matched': p_mail, 
                                    'type': 'email'
                                })

                    # B) Name Match (Fuzzy)
                    else:
                        name_obj = item.get('name') or {}
                        full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
                        
                        if full_name:
                            is_match, score = self._fuzzy_match(target, full_name, threshold=70)
                            if is_match:
                                candidates.append({
                                    'id': item_id, 
                                    'score': score, 
                                    'matched': full_name, 
                                    'type': 'person_name'
                                })
            
            # 3. Besten Kandidaten wählen (höchster Score)
            if candidates:
                best = max(candidates, key=lambda x: x['score'])
                print(f"✅ UUID gefunden (via {best['type']} '{best['matched']}', Score: {best['score']:.0f}%): {best['id']}")
                return best['id']
            
            print(f"⚠️ Nichts gefunden für '{target}' im {entity_type}-Index.")
            return None
            
        except Exception as e:
            print(f"❌ Resolve Fehler: {e}")
            return None

    def search_contacts(self, query: str) -> str:
        """
        Smart-Fuzzy-Search mit Scoring & Sortierung:
        1. Findet Firmen via Fuzzy-Match.
        2. Lädt Mitarbeiter dieser Firmen (Relation).
        3. Findet Personen via Fuzzy-Match (Name + Email).
        4. Sortiert nach Relevanz-Score (beste Matches zuerst).
        """
        print(f"🕵️ Smart-Fuzzy-Search für: '{query}'")
        results = []
        
        # --- STRATEGIE 1: FIRMEN FINDEN (FUZZY) ---
        companies_found = []
        
        raw_companies = self._request("GET", "companies", params={"limit": 50}) or {}
        company_list = raw_companies.get('companies', [])
        
        for c in company_list:
            c_name = c.get('name', '')
            if not c_name:
                continue
            
            # Fuzzy-Match für Firmennamen
            is_match, score = self._fuzzy_match(query, c_name, threshold=70)
            
            if is_match:
                companies_found.append(c)
                results.append({
                    'type': 'company',
                    'name': c_name,
                    'id': c.get('id'),
                    'score': score,
                    'display': f"🏢 FIRMA: {c_name}"
                })

        # --- STRATEGIE 2: PERSONEN FINDEN (FUZZY) ---
        raw_people = self._request("GET", "people", params={"limit": 100}) or {}
        people_list = raw_people.get('people', [])
        
        company_map = {c.get('id'): c.get('name') for c in companies_found}
        matched_person_ids = set()  # Verhindert Duplikate

        for p in people_list:
            # Parsing
            name_obj = p.get('name') or {}
            full_name = f"{name_obj.get('firstName', '')} {name_obj.get('lastName', '')}".strip()
            
            emails = p.get('emails') or []
            email = emails[0].get('primaryEmail', '') if isinstance(emails, list) and emails else ""
            if isinstance(emails, dict): email = emails.get('primaryEmail', '')
            
            pid = p.get('id')
            person_cid = p.get('companyId')

            # Fuzzy-Match auf Name & Email
            name_match, name_score = self._fuzzy_match(query, full_name, threshold=70)
            email_match, email_score = self._fuzzy_match(query, email, threshold=75) if email else (False, 0)
            
            # Bester Score gewinnt
            best_score = max(name_score, email_score)
            is_match = name_match or email_match

            # Match Check 2: Gehört zu gefundener Firma (Bonus-Score)
            is_colleague_match = person_cid in company_map
            
            if is_colleague_match and pid not in matched_person_ids:
                company_name = company_map[person_cid]
                # Kollegen bekommen Bonus-Score (damit sie oben stehen)
                colleague_score = max(best_score, 85.0)
                results.append({
                    'type': 'colleague',
                    'name': full_name,
                    'email': email,
                    'id': pid,
                    'score': colleague_score,
                    'company': company_name,
                    'display': f"👉 MITARBEITER bei {company_name}: {full_name} <{email}>"
                })
                matched_person_ids.add(pid)
            
            elif is_match and pid not in matched_person_ids:
                results.append({
                    'type': 'person',
                    'name': full_name,
                    'email': email,
                    'id': pid,
                    'score': best_score,
                    'display': f"👤 PERSON: {full_name} <{email}>"
                })
                matched_person_ids.add(pid)

        # --- SORTIERUNG nach Score (beste Matches zuerst) ---
        results.sort(key=lambda x: x['score'], reverse=True)

        if not results:
            return f"❌ Keine Einträge für '{query}' gefunden."

        # Formatierung mit Score (optional für Debug)
        formatted_results = []
        for r in results:
            # Score nur anzeigen, wenn < 100 (bei perfekten Matches weglassen)
            score_display = f" [Match: {r['score']:.0f}%]" if r['score'] < 100 else ""
            formatted_results.append(f"{r['display']}{score_display} (ID: {r['id']})")

        return "✅ Gefundene Datensätze:\n" + "\n".join(formatted_results)

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
        real_target_id = self._resolve_target_id(target_id, entity_type="person")

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
        real_target_id = self._resolve_target_id(target_id, entity_type="person")

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

    # --- DYNAMIC FIELD ENRICHMENT ---
    def update_entity(self, target: str, entity_type: str, fields: dict) -> str:
        """
        Aktualisiert beliebige Felder eines CRM-Eintrags (Dynamic Field Enrichment).
        
        Features:
        - Whitelist-basiert: Nur erlaubte Felder werden akzeptiert
        - Field Mapping: Generic Names → CRM-spezifische Namen
        - Validation: Type-Checking + Auto-Fix
        - Self-Healing: Name/Email → UUID Resolution
        
        Args:
            target: Name, Email oder UUID des Eintrags
            entity_type: "person" oder "company"
            fields: Dict mit generic field names, z.B. {"website": "expoya.com", "size": 50}
            
        Returns:
            Bestätigung mit aktualisierten Feldern
            
        Example:
            update_entity("Expoya", "company", {"website": "expoya.com", "size": 50})
            update_entity("Thomas Braun", "person", {"job": "CEO", "linkedin": "linkedin.com/in/thomas"})
        """
        print(f"📝 Update {entity_type}: '{target}' with {fields}")
        
        # 0. Field Mapper Check
        if not self.field_mapper:
            return "❌ Field Mapping nicht verfügbar. Feature deaktiviert."
        
        # 1. Target-ID auflösen (Self-Healing)
        entity_id = self._resolve_target_id(target, entity_type=entity_type)
        
        if not entity_id:
            return f"❌ {entity_type.title()} '{target}' nicht gefunden im CRM."
        
        # 2. Felder validieren und mappen (nur Whitelist + Auto-Fix)
        validated_fields = {}
        skipped_fields = []
        
        for field_name, value in fields.items():
            # Prüfe ob Feld in Whitelist
            if not self.field_mapper.is_field_allowed(entity_type, field_name):
                print(f"⚠️ Feld '{field_name}' nicht in Whitelist für {entity_type} (übersprungen)")
                skipped_fields.append(field_name)
                continue
            
            # Validiere & Auto-Fix
            is_valid, corrected_value, error = self.field_mapper.validate_field(
                entity_type, field_name, value
            )
            
            if not is_valid:
                print(f"⚠️ Validation failed für '{field_name}': {error}")
                skipped_fields.append(field_name)
                continue
            
            # Mappe zu CRM-spezifischem Feldnamen
            crm_field = self.field_mapper.get_crm_field_name(entity_type, field_name)
            if crm_field:
                validated_fields[crm_field] = corrected_value
        
        # 3. Check: Wurden Felder validiert?
        if not validated_fields:
            if skipped_fields:
                return f"⚠️ Keine gültigen Felder zum Aktualisieren. Übersprungen: {', '.join(skipped_fields)}"
            else:
                return f"⚠️ Keine Felder zum Aktualisieren übergeben."
        
        print(f"🔄 Mapped & Validated: {validated_fields}")
        
        # 4. API Call (PATCH)
        endpoint = self.field_mapper.get_endpoint(entity_type)
        data = self._request("PATCH", f"{endpoint}/{entity_id}", data=validated_fields)
        
        if not data:
            return f"❌ Fehler beim Aktualisieren von {entity_type}."
        
        # 5. Response formatieren
        updated_list = []
        for field_name, value in fields.items():
            if field_name not in skipped_fields:
                updated_list.append(f"{field_name}: {value}")
        
        response = f"✅ {entity_type.title()} aktualisiert: {', '.join(updated_list)}"
        
        if skipped_fields:
            response += f"\n⚠️ Übersprungen: {', '.join(skipped_fields)}"
        
        return response

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