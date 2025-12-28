"""
Tests für Fuzzy-Search Funktionalität
WICHTIG: Diese Tests erfordern rapidfuzz Installation!
"""

import pytest
import sys
import os

# Path Setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importiere nach Path-Setup
from unittest.mock import MagicMock, patch
from tools.crm.twenty_adapter import TwentyCRM


# === UNIT TESTS: _fuzzy_match() ===

def test_fuzzy_match_exact():
    """Exakte Matches sollten 100% Score haben"""
    adapter = TwentyCRM()
    
    is_match, score = adapter._fuzzy_match("Thomas Braun", "Thomas Braun")
    
    assert is_match is True
    assert score == 100.0


def test_fuzzy_match_typo():
    """Tippfehler sollten erkannt werden"""
    adapter = TwentyCRM()
    
    # "Tomas" statt "Thomas" (1 Buchstabe fehlt)
    is_match, score = adapter._fuzzy_match("Tomas Braun", "Thomas Braun")
    
    assert is_match is True  # Über Threshold
    assert score >= 85  # Hoher Score trotz Tippfehler


def test_fuzzy_match_word_order():
    """Wort-Reihenfolge sollte egal sein"""
    adapter = TwentyCRM()
    
    is_match, score = adapter._fuzzy_match("Braun Thomas", "Thomas Braun")
    
    assert is_match is True
    assert score >= 90  # Token-Sort erkennt das


def test_fuzzy_match_partial():
    """Teilstrings sollten gefunden werden"""
    adapter = TwentyCRM()
    
    # "Thomas" findet "Thomas Braun"
    is_match, score = adapter._fuzzy_match("Thomas", "Thomas Braun")
    
    assert is_match is True
    assert score >= 70


def test_fuzzy_match_case_insensitive():
    """Groß-/Kleinschreibung sollte egal sein"""
    adapter = TwentyCRM()
    
    is_match, score = adapter._fuzzy_match("THOMAS BRAUN", "thomas braun")
    
    assert is_match is True
    assert score == 100.0


def test_fuzzy_match_below_threshold():
    """Zu unterschiedliche Strings sollten nicht matchen"""
    adapter = TwentyCRM()
    
    is_match, score = adapter._fuzzy_match("Thomas Braun", "Max Mustermann")
    
    assert is_match is False
    assert score < 70


def test_fuzzy_match_empty_strings():
    """Leere Strings sollten gracefully gehandhabt werden"""
    adapter = TwentyCRM()
    
    is_match1, score1 = adapter._fuzzy_match("", "Thomas Braun")
    is_match2, score2 = adapter._fuzzy_match("Thomas", "")
    
    assert is_match1 is False
    assert is_match2 is False
    assert score1 == 0.0
    assert score2 == 0.0


def test_fuzzy_match_custom_threshold():
    """Custom Threshold sollte respektiert werden"""
    adapter = TwentyCRM()
    
    # Mit hohem Threshold (98%) - Muss sehr unterschiedlich sein
    is_match, score = adapter._fuzzy_match("Tom Braun", "Thomas Braun", threshold=98)
    
    # Score ist ~85-90%, also unter 98%
    assert is_match is False
    assert score < 98


# === INTEGRATION TESTS: _resolve_target_id() ===

@patch.object(TwentyCRM, '_request')
def test_resolve_target_id_fuzzy_name(mock_request):
    """Fuzzy Name-Match sollte UUID zurückgeben"""
    # Mock API Response
    mock_request.return_value = {
        'people': [
            {
                'id': 'abc-123',
                'name': {'firstName': 'Thomas', 'lastName': 'Braun'},
                'emails': []
            }
        ]
    }
    
    adapter = TwentyCRM()
    
    # Suche mit Tippfehler
    result = adapter._resolve_target_id("Tomas Braun")
    
    assert result == 'abc-123'
    mock_request.assert_called_once()


@patch.object(TwentyCRM, '_request')
def test_resolve_target_id_fuzzy_email(mock_request):
    """Fuzzy Email-Match sollte UUID zurückgeben"""
    mock_request.return_value = {
        'people': [
            {
                'id': 'def-456',
                'name': {'firstName': 'Max', 'lastName': 'Müller'},
                'emails': [{'primaryEmail': 'max.mueller@firma.de'}]
            }
        ]
    }
    
    adapter = TwentyCRM()
    
    # Suche mit ähnlicher Email (ue statt ü)
    result = adapter._resolve_target_id("max.muller@firma.de")
    
    # Sollte trotzdem gefunden werden (Fuzzy Match)
    assert result == 'def-456'


@patch.object(TwentyCRM, '_request')
def test_resolve_target_id_best_match_wins(mock_request):
    """Bei mehreren Matches sollte der beste Score gewinnen"""
    mock_request.return_value = {
        'people': [
            {
                'id': 'exact-match',
                'name': {'firstName': 'Thomas', 'lastName': 'Braun'},
                'emails': []
            },
            {
                'id': 'partial-match',
                'name': {'firstName': 'Tom', 'lastName': 'Braun'},
                'emails': []
            }
        ]
    }
    
    adapter = TwentyCRM()
    
    result = adapter._resolve_target_id("Thomas Braun")
    
    # Exakter Match sollte gewinnen
    assert result == 'exact-match'


@patch.object(TwentyCRM, '_request')
def test_resolve_target_id_no_match(mock_request):
    """Wenn kein Match gefunden wird, sollte None zurückkommen"""
    mock_request.return_value = {
        'people': [
            {
                'id': 'abc-123',
                'name': {'firstName': 'Thomas', 'lastName': 'Braun'},
                'emails': []
            }
        ]
    }
    
    adapter = TwentyCRM()
    
    result = adapter._resolve_target_id("Völlig Anderer Name")
    
    assert result is None


# === INTEGRATION TESTS: search_contacts() ===

@patch.object(TwentyCRM, '_request')
def test_search_contacts_fuzzy_person(mock_request):
    """Fuzzy-Search sollte Personen mit Tippfehlern finden"""
    
    def mock_response(method, endpoint, params=None, data=None):
        if endpoint == "companies":
            return {'companies': []}
        elif endpoint == "people":
            return {
                'people': [
                    {
                        'id': 'person-1',
                        'name': {'firstName': 'Thomas', 'lastName': 'Braun'},
                        'emails': [{'primaryEmail': 'thomas.braun@firma.de'}],
                        'companyId': None
                    }
                ]
            }
    
    mock_request.side_effect = mock_response
    
    adapter = TwentyCRM()
    
    # Suche mit Tippfehler
    result = adapter.search_contacts("Tomas Braun")
    
    assert "✅ Gefundene Datensätze:" in result
    assert "Thomas Braun" in result
    assert "person-1" in result


@patch.object(TwentyCRM, '_request')
def test_search_contacts_sorted_by_score(mock_request):
    """Results sollten nach Score sortiert sein (beste zuerst)"""
    
    def mock_response(method, endpoint, params=None, data=None):
        if endpoint == "companies":
            return {'companies': []}
        elif endpoint == "people":
            return {
                'people': [
                    {
                        'id': 'partial',
                        'name': {'firstName': 'Tom', 'lastName': 'Braun'},
                        'emails': [],
                        'companyId': None
                    },
                    {
                        'id': 'exact',
                        'name': {'firstName': 'Thomas', 'lastName': 'Braun'},
                        'emails': [],
                        'companyId': None
                    }
                ]
            }
    
    mock_request.side_effect = mock_response
    
    adapter = TwentyCRM()
    
    result = adapter.search_contacts("Thomas Braun")
    
    # "exact" sollte vor "partial" kommen (höherer Score)
    lines = result.split('\n')
    exact_line = next(i for i, line in enumerate(lines) if 'exact' in line)
    partial_line = next(i for i, line in enumerate(lines) if 'partial' in line)
    
    assert exact_line < partial_line


@patch.object(TwentyCRM, '_request')
def test_search_contacts_company_fuzzy(mock_request):
    """Fuzzy-Search sollte auch Firmen mit Tippfehlern finden"""
    
    def mock_response(method, endpoint, params=None, data=None):
        if endpoint == "companies":
            return {
                'companies': [
                    {
                        'id': 'company-1',
                        'name': 'Acme Corporation'
                    }
                ]
            }
        elif endpoint == "people":
            return {'people': []}
    
    mock_request.side_effect = mock_response
    
    adapter = TwentyCRM()
    
    # Suche mit Tippfehler
    result = adapter.search_contacts("Acm Corporation")
    
    assert "✅ Gefundene Datensätze:" in result
    assert "Acme Corporation" in result


@patch.object(TwentyCRM, '_request')
def test_search_contacts_no_results(mock_request):
    """Bei keinen Matches sollte Fehlermeldung kommen"""
    
    mock_request.return_value = {'companies': [], 'people': []}
    
    adapter = TwentyCRM()
    result = adapter.search_contacts("XYZ Nicht Existent")
    
    assert "❌ Keine Einträge" in result


# === PERFORMANCE TESTS ===

def test_fuzzy_match_performance():
    """Fuzzy-Match sollte schnell sein (< 1ms pro Call)"""
    import time
    
    adapter = TwentyCRM()
    
    start = time.time()
    
    for _ in range(1000):
        adapter._fuzzy_match("Thomas Braun", "Thomas Braun Test GmbH")
    
    duration = time.time() - start
    
    # 1000 Matches in < 100ms (= < 0.1ms pro Match)
    assert duration < 0.1, f"Zu langsam: {duration}s für 1000 Matches"


# === EDGE CASES ===

def test_fuzzy_match_special_characters():
    """Sonderzeichen sollten nicht crashen"""
    adapter = TwentyCRM()
    
    # Umlaute, Bindestriche, Punkte
    is_match, score = adapter._fuzzy_match("Müller-Schmidt", "Mueller Schmidt")
    
    # Sollte matchen (ähnliche Schreibweise)
    assert is_match is True


def test_fuzzy_match_very_long_strings():
    """Sehr lange Strings sollten gehandhabt werden"""
    adapter = TwentyCRM()
    
    long_string = "Thomas " * 100
    
    is_match, score = adapter._fuzzy_match("Thomas", long_string)
    
    assert isinstance(score, float)
    assert 0 <= score <= 100


if __name__ == "__main__":
    print("🧪 Running Fuzzy-Search Tests...")
    print("\nHinweis: Tests erfordern 'rapidfuzz' Installation:")
    print("  pip install rapidfuzz\n")
    
    # Quick Smoke Test
    try:
        from rapidfuzz import fuzz
        print("✅ rapidfuzz ist installiert\n")
        
        # Run pytest
        pytest.main([__file__, "-v"])
    except ImportError:
        print("❌ rapidfuzz ist NICHT installiert!")
        print("   Bitte installieren: pip install rapidfuzz")

