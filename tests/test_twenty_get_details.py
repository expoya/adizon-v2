"""
Tests für Twenty Adapter get_person_details Methode
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTwentyGetPersonDetails:
    """Tests für TwentyCRM.get_person_details()"""
    
    @patch('tools.crm.twenty_adapter.requests')
    @patch('tools.crm.twenty_adapter.load_field_mapping')
    def test_get_person_details_success(self, mock_load_mapping, mock_requests):
        """Test: Erfolgreicher Abruf mit allen Feldern"""
        mock_load_mapping.return_value = Mock()
        
        # Mock Person Response
        person_response = Mock()
        person_response.json.return_value = {
            "data": {
                "person": {
                    "id": "10000000-0000-4000-8000-000000000048",
                    "name": {
                        "firstName": "Eva",
                        "lastName": "Summer"
                    },
                    "emails": {
                        "primaryEmail": "e.summer@bodensee-wellness.at",
                        "additionalEmails": []
                    },
                    "phones": {
                        "primaryPhoneNumber": "650 9876543",
                        "primaryPhoneCountryCode": "AT",
                        "primaryPhoneCallingCode": "+43",
                        "additionalPhones": []
                    },
                    "jobTitle": "Sales Manager",
                    "linkedinLink": {
                        "primaryLinkUrl": "linkedin.com/in/eva-summer",
                        "primaryLinkLabel": "LinkedIn",
                        "secondaryLinks": []
                    },
                    "city": "Wien",
                    "birthday": "1990-05-15",
                    "companyId": "20000000-0000-4000-8000-000000000099",
                    "createdAt": "2024-01-15T10:30:00Z",
                    "updatedAt": "2024-12-20T15:45:00Z"
                }
            }
        }
        person_response.raise_for_status = Mock()
        
        # Mock Company Response
        company_response = Mock()
        company_response.json.return_value = {
            "data": {
                "company": {
                    "id": "20000000-0000-4000-8000-000000000099",
                    "name": "Bodensee Wellness"
                }
            }
        }
        company_response.raise_for_status = Mock()
        
        mock_requests.request.side_effect = [person_response, company_response]
        
        with patch.dict(os.environ, {
            'TWENTY_API_URL': 'twenty.example.com',
            'TWENTY_API_KEY': 'test_key'
        }):
            from tools.crm.twenty_adapter import TwentyCRM
            
            adapter = TwentyCRM()
            result = adapter.get_person_details("10000000-0000-4000-8000-000000000048")
            
            # Assertions
            assert "Eva Summer" in result
            assert "Sales Manager" in result
            assert "e.summer@bodensee-wellness.at" in result
            assert "+43 650 9876543" in result  # Formatted phone
            assert "Bodensee Wellness" in result
            assert "Wien" in result
            assert "linkedin.com/in/eva-summer" in result
            assert "1990-05-15" in result  # Birthday
            assert "2024-01-15" in result  # Created date
            assert "10000000-0000-4000-8000-000000000048" in result
            
            # Verify API Calls
            assert mock_requests.request.call_count == 2
            # First call: person
            # Second call: company
    
    @patch('tools.crm.twenty_adapter.requests')
    @patch('tools.crm.twenty_adapter.load_field_mapping')
    def test_get_person_details_not_found(self, mock_load_mapping, mock_requests):
        """Test: Person nicht gefunden"""
        mock_load_mapping.return_value = Mock()
        
        # Mock 404 or empty response
        person_response = Mock()
        person_response.json.return_value = {"data": None}
        person_response.raise_for_status = Mock()
        
        mock_requests.request.return_value = person_response
        
        with patch.dict(os.environ, {
            'TWENTY_API_URL': 'twenty.example.com',
            'TWENTY_API_KEY': 'test_key'
        }):
            from tools.crm.twenty_adapter import TwentyCRM
            
            adapter = TwentyCRM()
            result = adapter.get_person_details("invalid-uuid")
            
            assert "❌" in result
            assert "nicht gefunden" in result
    
    @patch('tools.crm.twenty_adapter.requests')
    @patch('tools.crm.twenty_adapter.load_field_mapping')
    def test_get_person_details_minimal_fields(self, mock_load_mapping, mock_requests):
        """Test: Person mit Minimal-Feldern (nur Name + Email)"""
        mock_load_mapping.return_value = Mock()
        
        # Minimal Person Data
        person_response = Mock()
        person_response.json.return_value = {
            "data": {
                "person": {
                    "id": "test-uuid",
                    "name": {
                        "firstName": "Jane",
                        "lastName": "Doe"
                    },
                    "emails": {
                        "primaryEmail": "jane@example.com"
                    },
                    "phones": {},  # Empty
                    "jobTitle": "",
                    "city": "",
                    "birthday": "",
                    "companyId": None,
                    "createdAt": "2024-01-01T00:00:00Z"
                }
            }
        }
        person_response.raise_for_status = Mock()
        
        mock_requests.request.return_value = person_response
        
        with patch.dict(os.environ, {
            'TWENTY_API_URL': 'twenty.example.com',
            'TWENTY_API_KEY': 'test_key'
        }):
            from tools.crm.twenty_adapter import TwentyCRM
            
            adapter = TwentyCRM()
            result = adapter.get_person_details("test-uuid")
            
            # Should still work with minimal data
            assert "Jane Doe" in result
            assert "jane@example.com" in result
            assert "test-uuid" in result
            # Should not crash on missing/empty fields
    
    @patch('tools.crm.twenty_adapter.requests')
    @patch('tools.crm.twenty_adapter.load_field_mapping')
    def test_get_person_details_with_company_error(self, mock_load_mapping, mock_requests):
        """Test: Person abrufen, aber Company-Abruf schlägt fehl"""
        mock_load_mapping.return_value = Mock()
        
        person_response = Mock()
        person_response.json.return_value = {
            "data": {
                "person": {
                    "id": "person-uuid",
                    "name": {"firstName": "Test", "lastName": "User"},
                    "emails": {"primaryEmail": "test@example.com"},
                    "phones": {},
                    "companyId": "company-uuid",
                    "createdAt": "2024-01-01T00:00:00Z"
                }
            }
        }
        person_response.raise_for_status = Mock()
        
        # Company call fails
        company_response = Mock()
        company_response.json.return_value = {"data": None}
        company_response.raise_for_status = Mock()
        
        mock_requests.request.side_effect = [person_response, company_response]
        
        with patch.dict(os.environ, {
            'TWENTY_API_URL': 'twenty.example.com',
            'TWENTY_API_KEY': 'test_key'
        }):
            from tools.crm.twenty_adapter import TwentyCRM
            
            adapter = TwentyCRM()
            result = adapter.get_person_details("person-uuid")
            
            # Should still return person data, even if company fails
            assert "Test User" in result
            assert "test@example.com" in result
            # Company name should be empty/not shown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

