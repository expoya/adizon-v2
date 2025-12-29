"""
Tests für Zoho Adapter get_lead_details Methode
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestZohoGetLeadDetails:
    """Tests für ZohoCRM.get_lead_details()"""
    
    @patch('tools.crm.zoho_adapter.requests')
    @patch('tools.crm.zoho_adapter.load_field_mapping')
    def test_get_lead_details_success(self, mock_load_mapping, mock_requests):
        """Test: Erfolgreicher Abruf mit allen Feldern"""
        # Setup Mocks
        mock_load_mapping.return_value = Mock()
        
        # Mock OAuth Token Refresh
        token_response = Mock()
        token_response.json.return_value = {"access_token": "test_token", "expires_in": 3600}
        token_response.raise_for_status = Mock()
        
        # Mock Lead Details Response
        lead_response = Mock()
        lead_response.json.return_value = {
            "data": [{
                "id": "506156000055855023",
                "First_Name": "David",
                "Last_Name": "Alaba",
                "Email": "david@fcb.com",
                "Phone": "+43 650 1234567",
                "Mobile": "+43 660 7654321",
                "Company": "FC Bayern AG",
                "Designation": "Player",
                "Street": "Säbener Straße 51",
                "City": "München",
                "State": "Bayern",
                "Zip_Code": "81547",
                "Country": "Deutschland",
                "Website": "fcbayern.com",
                "LinkedIn": "linkedin.com/in/david-alaba",
                "Lead_Source": "Website",
                "Industry": "Sports",
                "No_of_Employees": 500,
                "Annual_Revenue": 750000000,
                "Roof_Area": 150,
                "Description": "Top player"
            }]
        }
        lead_response.raise_for_status = Mock()
        
        mock_requests.post.return_value = token_response
        mock_requests.request.return_value = lead_response
        
        # Import after mocking
        with patch.dict(os.environ, {
            'ZOHO_CLIENT_ID': 'test_id',
            'ZOHO_CLIENT_SECRET': 'test_secret',
            'ZOHO_REFRESH_TOKEN': 'test_refresh'
        }):
            from tools.crm.zoho_adapter import ZohoCRM
            
            adapter = ZohoCRM()
            result = adapter.get_lead_details("506156000055855023")
            
            # Assertions
            assert "David Alaba" in result
            assert "Player" in result
            assert "david@fcb.com" in result
            assert "+43 650 1234567" in result
            assert "+43 660 7654321" in result
            assert "FC Bayern AG" in result
            assert "Säbener Straße 51" in result
            assert "München" in result
            assert "fcbayern.com" in result
            assert "linkedin.com/in/david-alaba" in result
            assert "Website" in result  # Lead Source
            assert "Sports" in result  # Industry
            assert "500" in result  # Employees
            assert "150 m²" in result  # Roof Area
            assert "Top player" in result  # Description
            assert "506156000055855023" in result  # ID
            
            # Verify API Call
            mock_requests.request.assert_called()
            call_args = mock_requests.request.call_args
            assert "Leads/506156000055855023" in call_args[0][1]
    
    @patch('tools.crm.zoho_adapter.requests')
    @patch('tools.crm.zoho_adapter.load_field_mapping')
    def test_get_lead_details_not_found(self, mock_load_mapping, mock_requests):
        """Test: Lead nicht gefunden"""
        mock_load_mapping.return_value = Mock()
        
        # Mock OAuth
        token_response = Mock()
        token_response.json.return_value = {"access_token": "test_token", "expires_in": 3600}
        token_response.raise_for_status = Mock()
        
        # Mock Empty Response
        lead_response = Mock()
        lead_response.json.return_value = {}  # Keine 'data'
        lead_response.raise_for_status = Mock()
        
        mock_requests.post.return_value = token_response
        mock_requests.request.return_value = lead_response
        
        with patch.dict(os.environ, {
            'ZOHO_CLIENT_ID': 'test_id',
            'ZOHO_CLIENT_SECRET': 'test_secret',
            'ZOHO_REFRESH_TOKEN': 'test_refresh'
        }):
            from tools.crm.zoho_adapter import ZohoCRM
            
            adapter = ZohoCRM()
            result = adapter.get_lead_details("99999")
            
            assert "❌" in result
            assert "nicht gefunden" in result
    
    @patch('tools.crm.zoho_adapter.requests')
    @patch('tools.crm.zoho_adapter.load_field_mapping')
    def test_get_lead_details_minimal_fields(self, mock_load_mapping, mock_requests):
        """Test: Lead mit Minimal-Feldern (nur Name + Email)"""
        mock_load_mapping.return_value = Mock()
        
        token_response = Mock()
        token_response.json.return_value = {"access_token": "test_token", "expires_in": 3600}
        token_response.raise_for_status = Mock()
        
        # Minimal Lead Data
        lead_response = Mock()
        lead_response.json.return_value = {
            "data": [{
                "id": "123",
                "First_Name": "John",
                "Last_Name": "Doe",
                "Email": "john@example.com"
                # Keine anderen Felder
            }]
        }
        lead_response.raise_for_status = Mock()
        
        mock_requests.post.return_value = token_response
        mock_requests.request.return_value = lead_response
        
        with patch.dict(os.environ, {
            'ZOHO_CLIENT_ID': 'test_id',
            'ZOHO_CLIENT_SECRET': 'test_secret',
            'ZOHO_REFRESH_TOKEN': 'test_refresh'
        }):
            from tools.crm.zoho_adapter import ZohoCRM
            
            adapter = ZohoCRM()
            result = adapter.get_lead_details("123")
            
            # Should still work with minimal data
            assert "John Doe" in result
            assert "john@example.com" in result
            assert "123" in result
            # Should not crash on missing fields


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

