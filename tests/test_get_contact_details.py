"""
Tests für get_contact_details Tool
Testet die Factory-Integration für Zoho und Twenty
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_zoho_adapter():
    """Mock Zoho Adapter"""
    adapter = Mock()
    adapter.get_lead_details = Mock(return_value="""📇 **Max Mustermann** (CEO)

**📧 Kontakt:**
  • Email: max@example.com
  • Phone: +43 650 1234567
  • Mobile: +43 660 7654321

**🏢 Firma:**
  • Name: Example GmbH
  • Website: example.com
  • Branche: Software
  • Mitarbeiter: 50

**📍 Adresse:**
  • Teststraße 123
  • 1010 Wien, Österreich

**🔗 LinkedIn:** linkedin.com/in/max

**📊 Lead Source:** Website

**🆔 ID:** 12345678901234567""")
    return adapter


@pytest.fixture
def mock_twenty_adapter():
    """Mock Twenty Adapter"""
    adapter = Mock()
    adapter.get_person_details = Mock(return_value="""📇 **Eva Summer** (Sales Manager)

**📧 Kontakt:**
  • Email: e.summer@bodensee-wellness.at
  • Phone: +43 650 9876543

**🏢 Firma:** Bodensee Wellness

**📍 Stadt:** Wien

**🔗 LinkedIn:** linkedin.com/in/eva-summer

**🎂 Geburtstag:** 1990-05-15

**📅 Erstellt:** 2024-01-15

**🆔 ID:** 10000000-0000-4000-8000-000000000048""")
    return adapter


class TestGetContactDetailsZoho:
    """Tests für get_lead_details (Zoho)"""
    
    @patch('tools.crm.zoho_adapter.ZohoCRM')
    def test_get_lead_details_success(self, mock_crm_class, mock_zoho_adapter):
        """Test: Erfolgreicher Abruf von Lead Details"""
        mock_crm_class.return_value = mock_zoho_adapter
        
        # Simuliere Zoho CRM Modus
        with patch.dict(os.environ, {'CRM_SYSTEM': 'ZOHO'}):
            from tools.crm import get_crm_tools_for_user
            
            tools = get_crm_tools_for_user("test_user_123")
            
            # Finde get_contact_details Tool
            details_tool = None
            for tool in tools:
                if tool.name == "get_contact_details":
                    details_tool = tool
                    break
            
            assert details_tool is not None, "get_contact_details tool nicht gefunden"
            
            # Rufe Tool auf
            result = details_tool.run(contact_id="12345678901234567")
            
            # Assertions
            assert "Max Mustermann" in result
            assert "+43 650 1234567" in result
            assert "example.com" in result
            assert "CEO" in result
            mock_zoho_adapter.get_lead_details.assert_called_once_with("12345678901234567")
    
    @patch('tools.crm.zoho_adapter.ZohoCRM')
    def test_get_lead_details_not_found(self, mock_crm_class):
        """Test: Lead nicht gefunden"""
        adapter = Mock()
        adapter.get_lead_details = Mock(return_value="❌ Lead mit ID 99999 nicht gefunden.")
        mock_crm_class.return_value = adapter
        
        with patch.dict(os.environ, {'CRM_SYSTEM': 'ZOHO'}):
            from tools.crm import get_crm_tools_for_user
            
            tools = get_crm_tools_for_user("test_user_123")
            details_tool = next(t for t in tools if t.name == "get_contact_details")
            
            result = details_tool.run(contact_id="99999")
            
            assert "❌" in result
            assert "nicht gefunden" in result


class TestGetContactDetailsTwenty:
    """Tests für get_person_details (Twenty)"""
    
    @patch('tools.crm.twenty_adapter.TwentyCRM')
    def test_get_person_details_success(self, mock_crm_class, mock_twenty_adapter):
        """Test: Erfolgreicher Abruf von Person Details"""
        mock_crm_class.return_value = mock_twenty_adapter
        
        # Simuliere Twenty CRM Modus
        with patch.dict(os.environ, {'CRM_SYSTEM': 'TWENTY'}):
            from tools.crm import get_crm_tools_for_user
            
            tools = get_crm_tools_for_user("test_user_123")
            
            # Finde get_contact_details Tool
            details_tool = None
            for tool in tools:
                if tool.name == "get_contact_details":
                    details_tool = tool
                    break
            
            assert details_tool is not None, "get_contact_details tool nicht gefunden"
            
            # Rufe Tool auf
            result = details_tool.run(contact_id="10000000-0000-4000-8000-000000000048")
            
            # Assertions
            assert "Eva Summer" in result
            assert "+43 650 9876543" in result
            assert "e.summer@bodensee-wellness.at" in result
            assert "Sales Manager" in result
            assert "1990-05-15" in result  # Birthday
            mock_twenty_adapter.get_person_details.assert_called_once()
    
    @patch('tools.crm.twenty_adapter.TwentyCRM')
    def test_get_person_details_not_found(self, mock_crm_class):
        """Test: Person nicht gefunden"""
        adapter = Mock()
        adapter.get_person_details = Mock(
            return_value="❌ Person mit ID invalid-uuid nicht gefunden."
        )
        mock_crm_class.return_value = adapter
        
        with patch.dict(os.environ, {'CRM_SYSTEM': 'TWENTY'}):
            from tools.crm import get_crm_tools_for_user
            
            tools = get_crm_tools_for_user("test_user_123")
            details_tool = next(t for t in tools if t.name == "get_contact_details")
            
            result = details_tool.run(contact_id="invalid-uuid")
            
            assert "❌" in result
            assert "nicht gefunden" in result


class TestGetContactDetailsMockMode:
    """Tests für Mock Mode (kein CRM konfiguriert)"""
    
    def test_get_contact_details_not_available_in_mock_mode(self):
        """Test: Tool nicht verfügbar im Mock Mode"""
        with patch.dict(os.environ, {'CRM_SYSTEM': 'MOCK'}):
            from tools.crm import get_crm_tools_for_user
            
            tools = get_crm_tools_for_user("test_user_123")
            
            # get_contact_details sollte NICHT in der Tool-Liste sein
            tool_names = [t.name for t in tools]
            assert "get_contact_details" not in tool_names


class TestGetContactDetailsIntegration:
    """Integration Tests für Workflow"""
    
    @patch('tools.crm.zoho_adapter.ZohoCRM')
    def test_workflow_search_then_details(self, mock_crm_class):
        """Test: Workflow search_contacts → get_contact_details"""
        # Setup Mock
        adapter = Mock()
        adapter.search_leads = Mock(return_value="""✅ Gefundene Leads:
👤 David Alaba @ FC Bayern AG <david@fcb.com> 📞 +43 650 1234567 (ID: 506156000055855023)""")
        adapter.get_lead_details = Mock(return_value="""📇 **David Alaba** (Player)

**📧 Kontakt:**
  • Email: david@fcb.com
  • Phone: +43 650 1234567

**🏢 Firma:**
  • Name: FC Bayern AG

**🆔 ID:** 506156000055855023""")
        
        mock_crm_class.return_value = adapter
        
        with patch.dict(os.environ, {'CRM_SYSTEM': 'ZOHO'}):
            from tools.crm import get_crm_tools_for_user
            
            tools = get_crm_tools_for_user("test_user_123")
            
            # 1. Suche
            search_tool = next(t for t in tools if t.name == "search_contacts")
            search_result = search_tool.run(query="David Alaba")
            
            assert "David Alaba" in search_result
            assert "506156000055855023" in search_result
            
            # 2. Details abrufen
            details_tool = next(t for t in tools if t.name == "get_contact_details")
            details_result = details_tool.run(contact_id="506156000055855023")
            
            assert "David Alaba" in details_result
            assert "+43 650 1234567" in details_result
            assert "david@fcb.com" in details_result
            
            # Verify calls
            adapter.search_leads.assert_called_once()
            adapter.get_lead_details.assert_called_once_with("506156000055855023")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

