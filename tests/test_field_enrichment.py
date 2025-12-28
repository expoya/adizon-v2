"""
Test: Dynamic Field Enrichment
Testet das neue update_entity Feature für flexible CRM-Feld-Befüllung.

Kategorien:
1. Field Mapping Loader Tests
2. Field Validation Tests
3. Adapter Integration Tests (Mock-basiert)
4. Tool Factory Tests
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Path Setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.crm.field_mapping_loader import FieldMappingLoader, load_field_mapping


# ============================================================================
# KATEGORIE 1: FIELD MAPPING LOADER TESTS
# ============================================================================

class TestFieldMappingLoader:
    """Tests für den Field Mapping Loader"""
    
    def test_loader_initialization(self):
        """Test: Loader lädt Twenty Mapping korrekt"""
        loader = load_field_mapping("twenty")
        
        assert loader.crm_system == "twenty"
        assert loader.mapping is not None
        assert "entities" in loader.mapping
        assert loader.mapping.get("version") == "1.0"
    
    def test_get_entities(self):
        """Test: Gibt Liste der Entities zurück"""
        loader = load_field_mapping("twenty")
        entities = loader.get_entities()
        
        assert "person" in entities
        assert "company" in entities
        assert len(entities) == 2
    
    def test_get_allowed_fields_person(self):
        """Test: Person Fields werden korrekt geladen"""
        loader = load_field_mapping("twenty")
        fields = loader.get_allowed_fields("person")
        
        assert "job" in fields
        assert "linkedin" in fields
        assert "city" in fields
        assert "birthday" in fields
        
        # Check Structure
        assert fields["job"]["crm_field"] == "jobTitle"
        assert fields["job"]["type"] == "string"
    
    def test_get_allowed_fields_company(self):
        """Test: Company Fields werden korrekt geladen"""
        loader = load_field_mapping("twenty")
        fields = loader.get_allowed_fields("company")
        
        assert "website" in fields
        assert "size" in fields
        assert "industry" in fields
        assert "address" in fields
        
        # Check Mapping
        assert fields["website"]["crm_field"] == "domainName"
        assert fields["size"]["crm_field"] == "employees"
    
    def test_field_mapping_person(self):
        """Test: Generic → CRM Field Mapping (Person)"""
        loader = load_field_mapping("twenty")
        
        assert loader.get_crm_field_name("person", "job") == "jobTitle"
        assert loader.get_crm_field_name("person", "linkedin") == "linkedIn"
        assert loader.get_crm_field_name("person", "invalid_field") is None
    
    def test_field_mapping_company(self):
        """Test: Generic → CRM Field Mapping (Company)"""
        loader = load_field_mapping("twenty")
        
        assert loader.get_crm_field_name("company", "website") == "domainName"
        assert loader.get_crm_field_name("company", "size") == "employees"
        assert loader.get_crm_field_name("company", "industry") == "idealCustomerProfile"
    
    def test_is_field_allowed(self):
        """Test: Whitelist Check"""
        loader = load_field_mapping("twenty")
        
        # Erlaubt
        assert loader.is_field_allowed("person", "job") is True
        assert loader.is_field_allowed("company", "website") is True
        
        # Nicht erlaubt
        assert loader.is_field_allowed("person", "hacker_field") is False
        assert loader.is_field_allowed("company", "invalid") is False
    
    def test_map_fields_with_whitelist(self):
        """Test: Mapping filtert nicht-erlaubte Felder"""
        loader = load_field_mapping("twenty")
        
        input_fields = {
            "website": "expoya.com",
            "size": 50,
            "hacker_field": "malicious",  # Nicht in Whitelist
            "invalid": "test"               # Nicht in Whitelist
        }
        
        mapped = loader.map_fields("company", input_fields)
        
        # Nur erlaubte Felder gemappt
        assert "domainName" in mapped
        assert "employees" in mapped
        assert "hacker_field" not in mapped
        assert "invalid" not in mapped
        
        assert mapped["domainName"] == "expoya.com"
        assert mapped["employees"] == 50


# ============================================================================
# KATEGORIE 2: FIELD VALIDATION TESTS
# ============================================================================

class TestFieldValidation:
    """Tests für Field Validation & Auto-Fix"""
    
    def test_validate_number_field(self):
        """Test: Number Field Validation"""
        loader = load_field_mapping("twenty")
        
        # Valid
        is_valid, value, error = loader.validate_field("company", "size", 50)
        assert is_valid is True
        assert value == 50
        assert error is None
        
        # String → Number Conversion
        is_valid, value, error = loader.validate_field("company", "size", "100")
        assert is_valid is True
        assert value == 100
    
    def test_validate_url_with_autofix(self):
        """Test: URL Auto-Fix"""
        loader = load_field_mapping("twenty")
        
        # Ohne https:// → Auto-Fix
        is_valid, value, error = loader.validate_field("company", "website", "expoya.com")
        assert is_valid is True
        assert value == "https://expoya.com"  # Auto-Fixed!
        
        # Mit https:// → Unverändert
        is_valid, value, error = loader.validate_field("company", "website", "https://test.com")
        assert is_valid is True
        assert value == "https://test.com"
    
    def test_validate_linkedin_pattern(self):
        """Test: LinkedIn Pattern Validation"""
        loader = load_field_mapping("twenty")
        
        # Valid LinkedIn URL
        is_valid, value, error = loader.validate_field(
            "person", "linkedin", "https://linkedin.com/in/max"
        )
        assert is_valid is True
        
        # Invalid (kein linkedin.com)
        is_valid, value, error = loader.validate_field(
            "person", "linkedin", "https://facebook.com/max"
        )
        assert is_valid is False
        assert "linkedin.com" in error.lower()
    
    def test_validate_date_format(self):
        """Test: Date Format Validation (Basic)"""
        loader = load_field_mapping("twenty")
        
        # Valid
        is_valid, value, error = loader.validate_field("person", "birthday", "1990-05-15")
        assert is_valid is True
        
        # Invalid
        is_valid, value, error = loader.validate_field("person", "birthday", "15.05.1990")
        assert is_valid is False
    
    def test_validate_string_field(self):
        """Test: String Field Validation"""
        loader = load_field_mapping("twenty")
        
        is_valid, value, error = loader.validate_field("person", "city", "Wien")
        assert is_valid is True
        assert value == "Wien"
    
    def test_validate_min_value(self):
        """Test: Min Value Check für Numbers"""
        loader = load_field_mapping("twenty")
        
        # Valid (über Minimum)
        is_valid, value, error = loader.validate_field("company", "size", 50)
        assert is_valid is True
        
        # Invalid (unter Minimum = 1)
        is_valid, value, error = loader.validate_field("company", "size", 0)
        assert is_valid is False
        assert "mindestens" in error.lower()


# ============================================================================
# KATEGORIE 3: ADAPTER INTEGRATION TESTS (MOCK)
# ============================================================================

class TestTwentyAdapterIntegration:
    """Tests für Twenty Adapter update_entity() mit Mocks"""
    
    @patch('tools.crm.twenty_adapter.requests.request')
    def test_update_entity_person(self, mock_request):
        """Test: Person Update mit Field Enrichment"""
        from tools.crm.twenty_adapter import TwentyCRM
        
        # Mock API Responses
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {"data": {"id": "person-123"}}
        )
        
        adapter = TwentyCRM()
        
        # Simuliere: Person existiert (mock _resolve_target_id)
        with patch.object(adapter, '_resolve_target_id', return_value='person-123'):
            result = adapter.update_entity(
                target="Thomas Braun",
                entity_type="person",
                fields={"job": "CEO", "linkedin": "linkedin.com/in/thomas"}
            )
        
        assert "✅" in result
        assert "CEO" in result
        assert "linkedin" in result
    
    @patch('tools.crm.twenty_adapter.requests.request')
    def test_update_entity_company(self, mock_request):
        """Test: Company Update mit Field Enrichment"""
        from tools.crm.twenty_adapter import TwentyCRM
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {"data": {"id": "company-456"}}
        )
        
        adapter = TwentyCRM()
        
        with patch.object(adapter, '_resolve_target_id', return_value='company-456'):
            result = adapter.update_entity(
                target="Expoya",
                entity_type="company",
                fields={"website": "expoya.com", "size": 50}
            )
        
        assert "✅" in result
        assert "website" in result
        assert "size" in result
    
    @patch('tools.crm.twenty_adapter.requests.request')
    def test_update_entity_with_invalid_fields(self, mock_request):
        """Test: Ungültige Felder werden gefiltert"""
        from tools.crm.twenty_adapter import TwentyCRM
        
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {"data": {"id": "company-789"}}
        )
        
        adapter = TwentyCRM()
        
        with patch.object(adapter, '_resolve_target_id', return_value='company-789'):
            result = adapter.update_entity(
                target="Test Company",
                entity_type="company",
                fields={
                    "website": "test.com",
                    "hacker_field": "malicious",  # Nicht in Whitelist
                    "invalid": "data"             # Nicht in Whitelist
                }
            )
        
        # Sollte warnen über übersprungene Felder
        assert "⚠️" in result or "Übersprungen" in result
    
    @patch('tools.crm.twenty_adapter.requests.request')
    def test_update_entity_target_not_found(self, mock_request):
        """Test: Target nicht gefunden"""
        from tools.crm.twenty_adapter import TwentyCRM
        
        adapter = TwentyCRM()
        
        # Simuliere: Target nicht gefunden
        with patch.object(adapter, '_resolve_target_id', return_value=None):
            result = adapter.update_entity(
                target="NonExistent Company",
                entity_type="company",
                fields={"website": "test.com"}
            )
        
        assert "❌" in result
        assert "nicht gefunden" in result.lower()
    
    @patch('tools.crm.twenty_adapter.requests.request')
    def test_resolve_target_company(self, mock_request):
        """Test: _resolve_target_id für Companies"""
        from tools.crm.twenty_adapter import TwentyCRM
        
        # Mock: Company List Response
        mock_request.return_value = Mock(
            status_code=200,
            json=lambda: {
                "data": {
                    "companies": [
                        {"id": "comp-123", "name": "Expoya GmbH"},
                        {"id": "comp-456", "name": "Test AG"}
                    ]
                }
            }
        )
        
        adapter = TwentyCRM()
        result = adapter._resolve_target_id("Expoya", entity_type="company")
        
        # Sollte Company finden (Fuzzy Match)
        assert result == "comp-123"


# ============================================================================
# KATEGORIE 4: TOOL FACTORY TESTS
# ============================================================================

class TestToolFactory:
    """Tests für Tool Factory Integration"""
    
    @patch.dict(os.environ, {"CRM_SYSTEM": "TWENTY"})
    @patch('tools.crm.twenty_adapter.TwentyCRM')
    def test_factory_includes_update_entity_tool(self, mock_adapter_class):
        """Test: Factory registriert update_entity Tool"""
        # Mock Adapter
        mock_adapter = Mock()
        mock_adapter.update_entity = Mock(return_value="✅ Updated")
        mock_adapter_class.return_value = mock_adapter
        
        # Reload Factory (um Mock zu nutzen)
        import importlib
        import tools.crm
        importlib.reload(tools.crm)
        
        from tools.crm import get_crm_tools_for_user
        
        tools = get_crm_tools_for_user("test_user")
        
        # Check: update_entity Tool ist dabei
        tool_names = [tool.name for tool in tools]
        assert "update_entity" in tool_names
    
    def test_update_entity_tool_description(self):
        """Test: Tool hat korrekte Description"""
        from tools.crm import get_crm_tools_for_user
        
        tools = get_crm_tools_for_user("test_user")
        
        update_tool = next((t for t in tools if t.name == "update_entity"), None)
        
        if update_tool:  # Nur wenn CRM-Adapter verfügbar
            assert "person" in update_tool.description.lower()
            assert "company" in update_tool.description.lower()


# ============================================================================
# KATEGORIE 5: INTEGRATION TESTS (FULL FLOW)
# ============================================================================

class TestFullIntegration:
    """End-to-End Tests (soweit möglich ohne echtes CRM)"""
    
    def test_field_mapping_loader_cached(self):
        """Test: Loader wird gecached"""
        loader1 = load_field_mapping("twenty")
        loader2 = load_field_mapping("twenty")
        
        # Sollte dasselbe Objekt sein (Cache)
        assert loader1 is loader2
    
    def test_generate_llm_field_list(self):
        """Test: LLM Field List Generation"""
        loader = load_field_mapping("twenty")
        
        person_list = loader.generate_llm_field_list("person")
        assert "job" in person_list
        assert "linkedin" in person_list
        assert "PERSON FELDER" in person_list
        
        company_list = loader.generate_llm_field_list("company")
        assert "website" in company_list
        assert "size" in company_list
        assert "COMPANY FELDER" in company_list
    
    def test_custom_field_in_mapping(self):
        """Test: Custom Fields (z.B. roof_area) sind verfügbar"""
        loader = load_field_mapping("twenty")
        fields = loader.get_allowed_fields("company")
        
        assert "roof_area" in fields
        assert fields["roof_area"]["custom"] is True
        assert fields["roof_area"]["customer"] == "voltage_solutions"


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    print("🧪 Running Field Enrichment Tests...\n")
    pytest.main([__file__, "-v", "--tb=short"])

