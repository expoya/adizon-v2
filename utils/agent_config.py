"""
Agent Configuration Loader
Lädt YAML-basierte Agent-Profile mit LLM-Settings und Prompts
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache


class AgentConfig:
    """
    Lädt und verwaltet Agent-Konfigurationen aus YAML-Files.
    
    Features:
    - Environment Variable Substitution: ${VAR_NAME}
    - Template Variable Rendering: {user_name}, {current_date}
    - Caching für Performance
    - Validation
    """
    
    def __init__(self, config_name: str):
        """
        Args:
            config_name: Name der Config-Datei (ohne .yaml), z.B. 'crm_handler'
        """
        self.config_name = config_name
        self.config_path = self._get_config_path(config_name)
        self._raw_config = self._load_yaml()
        self._process_env_vars()
        
    def _get_config_path(self, config_name: str) -> Path:
        """Findet den Pfad zur Config-Datei"""
        # Von utils/ aus: ../prompts/
        current_dir = Path(__file__).resolve().parent
        prompts_dir = current_dir.parent / "prompts"
        config_file = prompts_dir / f"{config_name}.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config nicht gefunden: {config_file}")
        
        return config_file
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Lädt YAML-Datei"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise ValueError(f"Fehler beim Laden von {self.config_path}: {e}")
    
    def _process_env_vars(self):
        """Ersetzt ${VAR_NAME} durch Environment Variables"""
        self._raw_config = self._substitute_env_vars(self._raw_config)
    
    def _substitute_env_vars(self, obj: Any) -> Any:
        """Rekursive Environment Variable Substitution"""
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Ersetzt ${VAR_NAME} oder ${VAR_NAME:-default} oder ${VAR:-${OTHER_VAR}}
            def replacer(match):
                full_expr = match.group(1)
                
                # Check for default value syntax: VAR:-default or VAR:-${OTHER_VAR}
                if ":-" in full_expr:
                    var_name, default = full_expr.split(":-", 1)
                    value = os.getenv(var_name.strip())
                    if value is None or value == "":
                        # Default kann auch eine andere Env-Var sein: ${OTHER_VAR}
                        if default.startswith("${") and default.endswith("}"):
                            other_var = default[2:-1]
                            return os.getenv(other_var, default)
                        return default
                    return value
                else:
                    var_name = full_expr
                    value = os.getenv(var_name)
                    if value is None:
                        print(f"⚠️ Environment Variable nicht gefunden: {var_name}")
                        return match.group(0)  # Original beibehalten
                    return value
            
            # Pattern: ${VAR} oder ${VAR:-default} oder ${VAR:-${OTHER}}
            return re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*(?::-[^}]*)?)\}', replacer, obj)
        else:
            return obj
    
    def get_system_prompt(self, **template_vars) -> str:
        """
        Gibt den System-Prompt zurück mit gerenderten Template-Variablen.
        
        Args:
            **template_vars: Variablen für Template-Rendering (z.B. user_name="Max")
            
        Returns:
            Gerenderter System-Prompt
        """
        prompt_template = self._raw_config.get('system_prompt', '')
        
        try:
            return prompt_template.format(**template_vars)
        except KeyError as e:
            print(f"⚠️ Template Variable fehlt: {e}")
            return prompt_template
    
    def get_model_config(self) -> Dict[str, str]:
        """Gibt LLM Model Configuration zurück"""
        return self._raw_config.get('model', {})
    
    def get_parameters(self) -> Dict[str, Any]:
        """Gibt LLM Parameters zurück (temperature, top_p, etc.)"""
        params = self._raw_config.get('parameters', {})
        
        # Validation
        if 'temperature' in params:
            temp = params['temperature']
            if not (0.0 <= temp <= 2.0):
                print(f"⚠️ Temperature außerhalb des Bereichs [0, 2]: {temp}")
        
        # Entferne None-Werte (top_k: null wird zu top_k: None)
        return {k: v for k, v in params.items() if v is not None}
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Gibt Agent-spezifische Settings zurück"""
        return self._raw_config.get('agent', {})
    
    def get_metadata(self) -> Dict[str, Any]:
        """Gibt Metadaten zurück (name, version, etc.)"""
        return {
            'name': self._raw_config.get('name'),
            'description': self._raw_config.get('description'),
            'version': self._raw_config.get('version'),
            'changelog': self._raw_config.get('changelog', [])
        }
    
    def __repr__(self):
        meta = self.get_metadata()
        return f"AgentConfig(name='{meta['name']}', version={meta['version']})"


# === HELPER FUNCTIONS ===

@lru_cache(maxsize=10)
def load_agent_config(config_name: str) -> AgentConfig:
    """
    Cached Config Loader.
    
    Args:
        config_name: Name der Config (z.B. 'crm_handler')
        
    Returns:
        AgentConfig Instanz
    """
    return AgentConfig(config_name)


def reload_config(config_name: str) -> AgentConfig:
    """
    Erzwingt Reload einer Config (bypass Cache).
    Nützlich für Hot-Reloading in Development.
    """
    load_agent_config.cache_clear()
    return load_agent_config(config_name)


# === TESTING ===

if __name__ == "__main__":
    # Quick Test
    print("🧪 Testing Agent Config Loader...\n")
    
    try:
        config = load_agent_config("crm_handler")
        print(f"✅ Loaded: {config}")
        print(f"📝 Model: {config.get_model_config()['name']}")
        print(f"🎛️  Temperature: {config.get_parameters()['temperature']}")
        
        prompt = config.get_system_prompt(
            user_name="Test User",
            current_date="2025-12-28"
        )
        print(f"💬 Prompt (first 100 chars): {prompt[:100]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")

