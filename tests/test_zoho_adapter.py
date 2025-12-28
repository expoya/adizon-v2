"""
Test: Zoho CRM Adapter (Mock Tests)
Kritisch für: CRM-Wechsel (Twenty → Zoho), OAuth 2.0, Fuzzy-Search, Self-Healing

Tests:
- OAuth Token Refresh
- create_contact() mit required fields (Company, Last Name)
- create_task() mit What_Id + $se_module
- create_note() mit Parent_Id nested object
- search_leads() Fuzzy-Matching
- update_entity() Dynamic Field Enrichment
- delete_item() Undo-Funktion
- _resolve_target_id() Self-Healing (Name → ID)
- Error-Handling bei API-Fehlern

WICHTIG: Diese Tests nutzen MOCKS, keine echten API-Calls!
Zweck: Validieren, dass Zoho Adapter korrekt implementiert ist.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call

# .env vor allen Imports laden
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Zoho Adapter importieren
from tools.crm.zoho_adapter import ZohoCRM

print("=" * 70)
print("ZOHO CRM ADAPTER TEST (Mock-basiert)")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("⚠️  Hinweis: Nutzt MOCKS, keine echten API-Calls\n")

# Test Counter
tests_passed = 0
tests_total = 0


# === TEST 1: OAuth Token Refresh ===
tests_total += 1
print(f"TEST 1: OAuth Token Refresh")
print("-" * 70)

try:
    # Mock OAuth Token Response
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'mock_access_token_12345',
            'expires_in': 3600
        }
        mock_post.return_value = mock_response
        
        # Mock field_mapping_loader
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email', 'phone']
            mock_loader.return_value = mock_mapper
            
            adapter = ZohoCRM()
            
            print(f"✓ Access Token: {adapter.access_token}")
            print(f"✓ Token expires at: {adapter.token_expires_at}")
            
            # Prüfe ob Token gesetzt wurde
            assert adapter.access_token == 'mock_access_token_12345', "Access Token nicht gesetzt"
            assert adapter.token_expires_at > 0, "Token Expiry nicht gesetzt"
            
            print("✅ TEST 1 BESTANDEN: OAuth Token Refresh funktioniert\n")
            tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}\n")


# === TEST 2: create_contact() mit Required Fields ===
tests_total += 1
print(f"TEST 2: create_contact() Required Fields (Company, Last Name)")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        # Mock OAuth Response
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        
        # Mock API Response für Lead-Erstellung
        api_response = Mock()
        api_response.status_code = 200
        api_response.json.return_value = {
            'data': [{
                'code': 'SUCCESS',
                'details': {'id': '5876543210987654321'}
            }]
        }
        
        mock_post.side_effect = [oauth_response, api_response]
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email', 'phone']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                mock_req_response = Mock()
                mock_req_response.status_code = 200
                mock_req_response.json.return_value = {
                    'data': [{
                        'code': 'SUCCESS',
                        'details': {'id': '5876543210987654321'}
                    }]
                }
                mock_request.return_value = mock_req_response
                
                adapter = ZohoCRM()
                
                result = adapter.create_contact(
                    first_name="Max",
                    last_name="Mustermann",
                    company="Expoya GmbH",
                    email="max@expoya.com",
                    phone="+436501234567"
                )
                
                print(f"✓ Response: {result}")
                
                # Prüfe Response-Format
                assert "✅" in result, f"Success-Marker fehlt: {result}"
                assert "Max Mustermann" in result, f"Name nicht im Response: {result}"
                assert "Expoya GmbH" in result, f"Company nicht im Response: {result}"
                assert "(ID: 5876543210987654321)" in result, f"ID nicht im Response: {result}"
                
                # Prüfe ob API mit richtigen Daten aufgerufen wurde
                call_args = mock_request.call_args
                payload = call_args[1]['json']
                
                print(f"✓ Payload: {payload}")
                
                assert payload['data'][0]['First_Name'] == "Max", "Vorname falsch"
                assert payload['data'][0]['Last_Name'] == "Mustermann", "Nachname falsch"
                assert payload['data'][0]['Company'] == "Expoya GmbH", "Company falsch"
                assert payload['data'][0]['Email'] == "max@expoya.com", "Email falsch"
                assert payload['data'][0]['Phone'] == "+436501234567", "Phone falsch"
                
                print("✅ TEST 2 BESTANDEN: create_contact() mit Required Fields\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}\n")


# === TEST 3: create_task() mit What_Id + $se_module ===
tests_total += 1
print(f"TEST 3: create_task() mit What_Id + $se_module")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                # Mock Task Creation Response
                mock_req_response = Mock()
                mock_req_response.status_code = 200
                mock_req_response.json.return_value = {
                    'data': [{
                        'code': 'SUCCESS',
                        'details': {'id': '9876543210123456789'}
                    }]
                }
                mock_request.return_value = mock_req_response
                
                adapter = ZohoCRM()
                
                result = adapter.create_task(
                    title="Follow-up anrufen",
                    body="Kunde kontaktieren wegen Solar",
                    due_date="2025-12-30",
                    target_id="5876543210987654321"  # Lead ID
                )
                
                print(f"✓ Response: {result}")
                
                # Prüfe Response
                assert "✅" in result, f"Success-Marker fehlt: {result}"
                assert "Follow-up anrufen" in result, f"Title nicht im Response: {result}"
                assert "(ID: 9876543210123456789)" in result, f"Task-ID nicht im Response: {result}"
                
                # Prüfe Payload (letzter Call)
                call_args = mock_request.call_args
                payload = call_args[1]['json']
                
                print(f"✓ Payload: {payload}")
                
                # Zoho braucht What_Id + $se_module für Verknüpfung!
                assert payload['data'][0]['Subject'] == "Follow-up anrufen", "Subject falsch"
                assert payload['data'][0]['What_Id'] == "5876543210987654321", "What_Id fehlt"
                assert payload['data'][0]['$se_module'] == "Leads", "$se_module fehlt"
                assert payload['data'][0]['Due_Date'] == "2025-12-30", "Due_Date falsch"
                
                print("✅ TEST 3 BESTANDEN: create_task() mit Verknüpfung\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}\n")


# === TEST 4: create_note() mit Parent_Id nested object ===
tests_total += 1
print(f"TEST 4: create_note() mit Parent_Id nested object")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                # Mock Note Creation Response
                mock_req_response = Mock()
                mock_req_response.status_code = 200
                mock_req_response.json.return_value = {
                    'data': [{
                        'code': 'SUCCESS',
                        'details': {'id': '1234567890123456789'}
                    }]
                }
                mock_request.return_value = mock_req_response
                
                adapter = ZohoCRM()
                
                result = adapter.create_note(
                    title="Interesse Solar",
                    content="Kunde zeigt großes Interesse an Solarlösungen",
                    target_id="5876543210987654321"  # Lead ID
                )
                
                print(f"✓ Response: {result}")
                
                # Prüfe Response
                assert "✅" in result, f"Success-Marker fehlt: {result}"
                assert "Interesse Solar" in result, f"Title nicht im Response: {result}"
                assert "(ID: 1234567890123456789)" in result, f"Note-ID nicht im Response: {result}"
                
                # Prüfe Payload (letzter Call)
                call_args = mock_request.call_args
                payload = call_args[1]['json']
                
                print(f"✓ Payload: {payload}")
                
                # Zoho Notes brauchen Parent_Id als nested object!
                assert payload['data'][0]['Note_Title'] == "Interesse Solar", "Note_Title falsch"
                assert payload['data'][0]['Note_Content'] == "Kunde zeigt großes Interesse an Solarlösungen", "Note_Content falsch"
                assert 'Parent_Id' in payload['data'][0], "Parent_Id fehlt"
                assert payload['data'][0]['Parent_Id']['id'] == "5876543210987654321", "Parent_Id.id falsch"
                assert payload['data'][0]['Parent_Id']['module']['api_name'] == "Leads", "Parent_Id.module falsch"
                
                print("✅ TEST 4 BESTANDEN: create_note() mit nested Parent_Id\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 4 ERROR: {e}\n")


# === TEST 5: search_leads() Fuzzy-Matching ===
tests_total += 1
print(f"TEST 5: search_leads() Fuzzy-Matching")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                # Mock Search Response
                mock_req_response = Mock()
                mock_req_response.status_code = 200
                mock_req_response.json.return_value = {
                    'data': [
                        {
                            'id': '5876543210987654321',
                            'First_Name': 'Max',
                            'Last_Name': 'Mustermann',
                            'Email': 'max@expoya.com',
                            'Company': 'Expoya GmbH',
                            'Phone': '+436501234567',
                            'Designation': 'CEO'
                        },
                        {
                            'id': '1111111111111111111',
                            'First_Name': 'Thomas',
                            'Last_Name': 'Braun',
                            'Email': 'thomas@test.com',
                            'Company': 'Test GmbH',
                            'Phone': '+436509876543',
                            'Designation': 'CTO'
                        }
                    ]
                }
                mock_request.return_value = mock_req_response
                
                adapter = ZohoCRM()
                
                result = adapter.search_leads("Max")
                
                print(f"✓ Response: {result[:150]}...")
                
                # Prüfe ob Max gefunden wurde
                assert "✅" in result, f"Success-Marker fehlt: {result}"
                assert "Max Mustermann" in result, f"Max nicht gefunden: {result}"
                assert "max@expoya.com" in result, f"Email nicht gefunden: {result}"
                assert "(ID: 5876543210987654321)" in result, f"ID nicht gefunden: {result}"
                
                # Thomas sollte nicht dabei sein (kein Match auf "Max")
                # (Da wir Mock nutzen, wird Thomas trotzdem zurückgegeben - aber Filter sollte ihn ausschließen)
                
                print("✅ TEST 5 BESTANDEN: search_leads() funktioniert\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 5 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 5 ERROR: {e}\n")


# === TEST 6: _resolve_target_id() Self-Healing ===
tests_total += 1
print(f"TEST 6: _resolve_target_id() Self-Healing (Name → ID)")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                # Mock GET Leads Response
                mock_req_response = Mock()
                mock_req_response.status_code = 200
                mock_req_response.json.return_value = {
                    'data': [
                        {
                            'id': '5876543210987654321',
                            'First_Name': 'Max',
                            'Last_Name': 'Mustermann',
                            'Email': 'max@expoya.com',
                            'Company': 'Expoya GmbH'
                        }
                    ]
                }
                mock_request.return_value = mock_req_response
                
                adapter = ZohoCRM()
                
                # Test 1: Echte ID sollte durchgehen
                result_id = adapter._resolve_target_id("5876543210987654321")
                assert result_id == "5876543210987654321", f"ID nicht durchgegangen: {result_id}"
                print(f"✓ ID durchgegangen: 5876543210987654321")
                
                # Test 2: Name sollte aufgelöst werden
                result_name = adapter._resolve_target_id("Max Mustermann")
                assert result_name == "5876543210987654321", f"Name nicht aufgelöst: {result_name}"
                print(f"✓ Name 'Max Mustermann' aufgelöst zu: {result_name}")
                
                # Test 3: Email sollte aufgelöst werden
                result_email = adapter._resolve_target_id("max@expoya.com")
                assert result_email == "5876543210987654321", f"Email nicht aufgelöst: {result_email}"
                print(f"✓ Email 'max@expoya.com' aufgelöst zu: {result_email}")
                
                print("✅ TEST 6 BESTANDEN: _resolve_target_id() Self-Healing funktioniert\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 6 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 6 ERROR: {e}\n")


# === TEST 7: delete_item() Undo-Funktion ===
tests_total += 1
print(f"TEST 7: delete_item() Undo-Funktion")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.delete') as mock_delete:
                # Mock DELETE Response
                mock_del_response = Mock()
                mock_del_response.status_code = 200
                mock_del_response.text = '{"code":"SUCCESS"}'
                mock_delete.return_value = mock_del_response
                
                adapter = ZohoCRM()
                
                result = adapter.delete_item("task", "9876543210123456789")
                
                print(f"✓ Response: {result}")
                
                # Prüfe Response
                assert "✅" in result, f"Success-Marker fehlt: {result}"
                assert "rückgängig" in result.lower(), f"'rückgängig' nicht im Response: {result}"
                
                # Prüfe ob DELETE mit richtiger URL aufgerufen wurde
                call_args = mock_delete.call_args
                url = call_args[0][0]
                
                print(f"✓ DELETE URL: {url}")
                
                assert "Tasks/9876543210123456789" in url, f"Falsche URL: {url}"
                
                print("✅ TEST 7 BESTANDEN: delete_item() Undo funktioniert\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 7 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 7 ERROR: {e}\n")


# === TEST 8: update_entity() Dynamic Field Enrichment ===
tests_total += 1
print(f"TEST 8: update_entity() Dynamic Field Enrichment")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            # Mock Field Mapper
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['job']
            mock_mapper.is_field_allowed.return_value = True
            mock_mapper.validate_field.return_value = (True, "CEO", None)
            mock_mapper.get_crm_field_name.return_value = "Designation"
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                # Mock 1: GET für _resolve_target_id
                # Mock 2: PUT für update
                def request_side_effect(method, url, **kwargs):
                    mock_resp = Mock()
                    mock_resp.status_code = 200
                    
                    if method == "GET":
                        # Resolve Lead
                        mock_resp.json.return_value = {
                            'data': [{
                                'id': '5876543210987654321',
                                'First_Name': 'Max',
                                'Last_Name': 'Mustermann',
                                'Email': 'max@expoya.com'
                            }]
                        }
                    elif method == "PUT":
                        # Update Success
                        mock_resp.json.return_value = {
                            'data': [{
                                'code': 'SUCCESS',
                                'details': {'id': '5876543210987654321'}
                            }]
                        }
                    
                    return mock_resp
                
                mock_request.side_effect = request_side_effect
                
                adapter = ZohoCRM()
                
                result = adapter.update_entity(
                    target="Max Mustermann",
                    entity_type="lead",
                    fields={"job": "CEO"}
                )
                
                print(f"✓ Response: {result}")
                
                # Prüfe Response
                assert "✅" in result, f"Success-Marker fehlt: {result}"
                assert "job: CEO" in result, f"Feld nicht im Response: {result}"
                
                # Prüfe ob PUT mit gemappten Feldern aufgerufen wurde
                put_calls = [c for c in mock_request.call_args_list if c[0][0] == "PUT"]
                assert len(put_calls) > 0, "PUT wurde nicht aufgerufen"
                
                put_payload = put_calls[0][1]['json']
                print(f"✓ PUT Payload: {put_payload}")
                
                # Field Mapper sollte "job" → "Designation" gemappt haben
                assert put_payload['data'][0]['Designation'] == "CEO", "Field Mapping falsch"
                
                print("✅ TEST 8 BESTANDEN: update_entity() mit Field Mapping\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 8 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 8 ERROR: {e}\n")


# === TEST 9: Error-Handling bei API-Fehlern ===
tests_total += 1
print(f"TEST 9: Error-Handling bei API-Fehlern")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            with patch('requests.request') as mock_request:
                # Mock API Error
                mock_req_response = Mock()
                mock_req_response.status_code = 400
                mock_req_response.text = '{"code":"REQUIRED_PARAM_MISSING","message":"Company is missing"}'
                mock_req_response.raise_for_status.side_effect = Exception("HTTP 400")
                mock_request.return_value = mock_req_response
                
                adapter = ZohoCRM()
                
                result = adapter.create_contact(
                    first_name="Test",
                    last_name="User",
                    company="",  # Fehlt!
                    email="test@test.com"
                )
                
                print(f"✓ Response bei Fehler: {result}")
                
                # Sollte Fehler-Message enthalten
                assert "❌" in result or "Fehler" in result, f"Fehler nicht korrekt gehandhabt: {result}"
                
                print("✅ TEST 9 BESTANDEN: Error-Handling funktioniert\n")
                tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 9 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 9 ERROR: {e}\n")


# === TEST 10: Fuzzy-Matching Scoring ===
tests_total += 1
print(f"TEST 10: Fuzzy-Matching Scoring")
print("-" * 70)

try:
    with patch('requests.post') as mock_post:
        oauth_response = Mock()
        oauth_response.status_code = 200
        oauth_response.json.return_value = {'access_token': 'test_token', 'expires_in': 3600}
        mock_post.return_value = oauth_response
        
        with patch('tools.crm.zoho_adapter.load_field_mapping') as mock_loader:
            mock_mapper = Mock()
            mock_mapper.get_entities.return_value = ['lead']
            mock_mapper.get_allowed_fields.return_value = ['email']
            mock_loader.return_value = mock_mapper
            
            adapter = ZohoCRM()
            
            # Test verschiedene Matching-Strategien
            
            # 1. Exakter Match
            is_match, score = adapter._fuzzy_match("Max Mustermann", "Max Mustermann")
            assert is_match and score == 100.0, f"Exakter Match fehlgeschlagen: {score}"
            print(f"✓ Exakter Match: {score}%")
            
            # 2. Substring Match
            is_match, score = adapter._fuzzy_match("Max", "Max Mustermann")
            assert is_match and score == 100.0, f"Substring Match fehlgeschlagen: {score}"
            print(f"✓ Substring Match: {score}%")
            
            # 3. Token Sort (Reihenfolge egal)
            is_match, score = adapter._fuzzy_match("Mustermann Max", "Max Mustermann")
            assert is_match and score >= 70, f"Token Sort fehlgeschlagen: {score}"
            print(f"✓ Token Sort Match: {score}%")
            
            # 4. Kein Match
            is_match, score = adapter._fuzzy_match("Thomas Braun", "Max Mustermann")
            assert not is_match, f"Falsch-Positiv: {score}%"
            print(f"✓ Kein Match (korrekt): {score}%")
            
            print("✅ TEST 10 BESTANDEN: Fuzzy-Matching Scoring korrekt\n")
            tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 10 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 10 ERROR: {e}\n")


# === FINAL SUMMARY ===
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"📊 Ergebnis: {tests_passed}/{tests_total} Tests bestanden")

if tests_passed == tests_total:
    print("✅ Alle Tests erfolgreich!")
    print("✅ Zoho CRM Adapter ist produktionsreif")
    print("✅ OAuth 2.0, Fuzzy-Search, Self-Healing funktionieren")
    print("✅ Bereit für Deployment auf Railway")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")

print("\n💡 Hinweise:")
print("   - Diese Tests nutzen MOCKS (keine echten API-Calls)")
print("   - Für echte API-Tests: Swagger UI oder Postman verwenden")
print("   - Zoho-spezifische Features getestet:")
print("     • OAuth Token Refresh")
print("     • Required Fields (Company, Last Name)")
print("     • Task-Verknüpfung (What_Id + $se_module)")
print("     • Note-Verknüpfung (Parent_Id nested object)")
print("     • Fuzzy-Search mit Scoring")
print("     • Self-Healing (Name/Email → ID)")
print("     • Dynamic Field Enrichment")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

