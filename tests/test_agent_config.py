"""
Test: YAML Agent Config System
Kritisch für: Alle Agents, Prompt Management, Parameter-Tuning

Tests:
- Config laden funktioniert
- Environment Variable Substitution (${VAR})
- Template Variable Rendering ({user_name})
- Parameter Validation (temperature range)
- Caching funktioniert
- Alle 4 Configs sind valide
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# .env vor allen Imports laden
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

from dotenv import load_dotenv
load_dotenv(dotenv_path=env_path)

# Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.agent_config import load_agent_config, reload_config

print("=" * 70)
print("YAML AGENT CONFIG SYSTEM TEST")
print("=" * 70)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Test Counter
tests_passed = 0
tests_total = 0


# === TEST 1: Config laden ===
tests_total += 1
print(f"TEST 1: Config laden")
print("-" * 70)

try:
    config = load_agent_config("crm_handler")
    
    assert config is not None, "Config ist None"
    print("✓ Config erfolgreich geladen")
    
    # Metadata prüfen
    meta = config.get_metadata()
    assert meta['name'] == "CRM Handler", f"Expected 'CRM Handler', got '{meta['name']}'"
    assert 'version' in meta, "Version fehlt in Metadata"
    print(f"✓ Metadata: {meta['name']} v{meta['version']}")
    
    print("✅ TEST 1 BESTANDEN: Config laden funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 1 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 1 ERROR: {e}\n")


# === TEST 2: Environment Variable Substitution ===
tests_total += 1
print(f"TEST 2: Environment Variable Substitution")
print("-" * 70)

try:
    config = load_agent_config("crm_handler")
    model_config = config.get_model_config()
    
    # Prüfe ob ${MODEL_NAME} durch echten Wert ersetzt wurde
    model_name = model_config.get('name')
    assert model_name is not None, "Model name ist None"
    assert not model_name.startswith('${'), f"Env var nicht ersetzt: {model_name}"
    assert 'MODEL_NAME' not in model_name, f"Platzhalter noch vorhanden: {model_name}"
    
    print(f"✓ Model Name: {model_name}")
    
    # Prüfe API Key
    api_key = model_config.get('api_key')
    assert api_key is not None, "API Key ist None"
    assert not api_key.startswith('${'), f"API Key nicht ersetzt: {api_key}"
    
    print(f"✓ API Key: {'*' * 20} (gesetzt)")
    
    print("✅ TEST 2 BESTANDEN: Env Variable Substitution funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 2 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 2 ERROR: {e}\n")


# === TEST 3: Template Variable Rendering ===
tests_total += 1
print(f"TEST 3: Template Variable Rendering")
print("-" * 70)

try:
    config = load_agent_config("crm_handler")
    
    # Render mit Template-Variablen
    prompt = config.get_system_prompt(
        user_name="TestUser",
        current_date="2025-12-28"
    )
    
    assert prompt is not None, "Prompt ist None"
    assert len(prompt) > 0, "Prompt ist leer"
    
    # Prüfe ob Variablen ersetzt wurden
    assert "TestUser" in prompt, "user_name nicht gerendert"
    assert "2025-12-28" in prompt, "current_date nicht gerendert"
    assert "{user_name}" not in prompt, "Platzhalter nicht ersetzt"
    assert "{current_date}" not in prompt, "Platzhalter nicht ersetzt"
    
    print(f"✓ Prompt gerendert (Länge: {len(prompt)} Zeichen)")
    print(f"✓ 'TestUser' gefunden: ✓")
    print(f"✓ '2025-12-28' gefunden: ✓")
    
    print("✅ TEST 3 BESTANDEN: Template Rendering funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 3 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 3 ERROR: {e}\n")


# === TEST 4: Parameter Validation ===
tests_total += 1
print(f"TEST 4: Parameter Validation")
print("-" * 70)

try:
    config = load_agent_config("crm_handler")
    params = config.get_parameters()
    
    assert params is not None, "Parameters sind None"
    assert 'temperature' in params, "Temperature fehlt"
    
    # Temperature im validen Bereich?
    temp = params['temperature']
    assert 0.0 <= temp <= 2.0, f"Temperature außerhalb [0, 2]: {temp}"
    
    print(f"✓ Temperature: {temp} (valide)")
    
    # Top-P vorhanden?
    if 'top_p' in params:
        top_p = params['top_p']
        assert 0.0 <= top_p <= 1.0, f"Top-P außerhalb [0, 1]: {top_p}"
        print(f"✓ Top-P: {top_p} (valide)")
    
    # Max-Tokens vorhanden?
    if 'max_tokens' in params:
        max_tokens = params['max_tokens']
        assert max_tokens > 0, f"Max-Tokens muss positiv sein: {max_tokens}"
        print(f"✓ Max-Tokens: {max_tokens} (valide)")
    
    print("✅ TEST 4 BESTANDEN: Parameter sind valide\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 4 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 4 ERROR: {e}\n")


# === TEST 5: Caching funktioniert ===
tests_total += 1
print(f"TEST 5: Caching")
print("-" * 70)

try:
    import time
    
    # Erste Ladung (kalt)
    start1 = time.time()
    config1 = load_agent_config("crm_handler")
    time1 = (time.time() - start1) * 1000  # ms
    
    # Zweite Ladung (sollte gecacht sein)
    start2 = time.time()
    config2 = load_agent_config("crm_handler")
    time2 = (time.time() - start2) * 1000  # ms
    
    print(f"✓ Erste Ladung: {time1:.2f}ms")
    print(f"✓ Zweite Ladung: {time2:.2f}ms (Cache)")
    
    # Cache sollte schneller sein (aber nicht immer garantiert auf allen Systemen)
    # Wir prüfen nur, dass es funktioniert
    assert config1 is config2, "Cache gibt nicht dieselbe Instanz zurück"
    
    print("✅ TEST 5 BESTANDEN: Caching funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 5 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 5 ERROR: {e}\n")


# === TEST 6: Alle 4 Agent-Configs sind valide ===
tests_total += 1
print(f"TEST 6: Alle Agent-Configs validieren")
print("-" * 70)

try:
    agent_configs = [
        "crm_handler",
        "chat_handler",
        "intent_detection",
        "session_guard"
    ]
    
    for config_name in agent_configs:
        config = load_agent_config(config_name)
        
        # Basis-Checks
        assert config is not None, f"{config_name}: Config ist None"
        
        meta = config.get_metadata()
        assert meta['name'] is not None, f"{config_name}: Name fehlt"
        
        params = config.get_parameters()
        assert 'temperature' in params, f"{config_name}: Temperature fehlt"
        
        prompt = config.get_system_prompt()
        assert len(prompt) > 0, f"{config_name}: Prompt ist leer"
        
        print(f"✓ {config_name}: {meta['name']} v{meta['version']} (temp={params['temperature']})")
    
    print("✅ TEST 6 BESTANDEN: Alle 4 Configs sind valide\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 6 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 6 ERROR: {e}\n")


# === TEST 7: Agent Config für LangChain ===
tests_total += 1
print(f"TEST 7: Agent-spezifische Config (LangChain)")
print("-" * 70)

try:
    config = load_agent_config("crm_handler")
    agent_config = config.get_agent_config()
    
    # CRM Handler sollte agent_config haben
    assert agent_config is not None, "Agent Config ist None"
    assert 'verbose' in agent_config, "verbose fehlt"
    assert 'handle_parsing_errors' in agent_config, "handle_parsing_errors fehlt"
    
    print(f"✓ verbose: {agent_config['verbose']}")
    print(f"✓ handle_parsing_errors: {agent_config['handle_parsing_errors']}")
    
    # Chat Handler sollte KEINE agent_config haben (kein LangChain Agent)
    chat_config = load_agent_config("chat_handler")
    chat_agent_config = chat_config.get_agent_config()
    
    # Sollte leer sein oder nicht existieren
    print(f"✓ Chat Handler hat {'keine' if not chat_agent_config else 'optionale'} agent_config")
    
    print("✅ TEST 7 BESTANDEN: Agent Config funktioniert\n")
    tests_passed += 1
    
except AssertionError as e:
    print(f"❌ TEST 7 FEHLGESCHLAGEN: {e}\n")
except Exception as e:
    print(f"❌ TEST 7 ERROR: {e}\n")


# === FINAL SUMMARY ===
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"📊 Ergebnis: {tests_passed}/{tests_total} Tests bestanden")

if tests_passed == tests_total:
    print("✅ Alle Tests erfolgreich!")
    print("✅ YAML Config System ist production-ready")
    print("✅ Alle 4 Agent-Configs validiert")
else:
    print(f"⚠️  {tests_total - tests_passed} Test(s) fehlgeschlagen")
    print("🔍 Prüfe die Fehler oben")

print("\n💡 Hinweise:")
print("   - Env-Variablen müssen in .env gesetzt sein")
print("   - YAML-Files müssen in prompts/ existieren")
print("=" * 70)

# Exit Code für CI/CD
sys.exit(0 if tests_passed == tests_total else 1)

