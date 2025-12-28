"""
CRM Field Mapping Loader
Lädt Field-Mappings aus YAML-Files und stellt sie bereit.

Konzept:
- Whitelist-Prinzip: Nur explizit definierte Felder werden akzeptiert
- CRM-agnostisch: Generic Field Names → CRM-spezifische Namen
- Validation: Type-Checking + Auto-Fix
- Custom Fields: Unterstützung für kundenspezifische Felder
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache


class FieldMappingLoader:
    """
    Lädt und verwaltet CRM Field-Mappings aus YAML-Files.
    
    Features:
    - Whitelist-basierte Feld-Kontrolle
    - Type-Validation
    - Auto-Fix für URLs, etc.
    - Custom Field Support
    """
    
    def __init__(self, crm_system: str):
        """
        Args:
            crm_system: Name des CRM-Systems (z.B. 'twenty', 'zoho')
        """
        self.crm_system = crm_system.lower()
        self.mapping = self._load_mapping()
        self._validate_mapping()
    
    def _load_mapping(self) -> Dict:
        """Lädt Mapping-File für CRM-System"""
        mapping_dir = Path(__file__).parent / "field_mappings"
        mapping_file = mapping_dir / f"{self.crm_system}.yaml"
        
        if not mapping_file.exists():
            raise FileNotFoundError(
                f"❌ Mapping nicht gefunden: {mapping_file}\n"
                f"Verfügbare Mappings: {self._list_available_mappings()}"
            )
        
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mapping = yaml.safe_load(f)
                print(f"✅ Field Mapping geladen: {self.crm_system} (Version {mapping.get('version')})")
                return mapping
        except Exception as e:
            raise ValueError(f"❌ Fehler beim Laden von {mapping_file}: {e}")
    
    def _list_available_mappings(self) -> List[str]:
        """Listet verfügbare Mapping-Files auf"""
        mapping_dir = Path(__file__).parent / "field_mappings"
        if mapping_dir.exists():
            return [f.stem for f in mapping_dir.glob("*.yaml") if f.stem != "template"]
        return []
    
    def _validate_mapping(self):
        """Validiert Mapping-Struktur"""
        required_keys = ['crm_system', 'version', 'entities']
        for key in required_keys:
            if key not in self.mapping:
                raise ValueError(f"❌ Mapping-File ungültig: '{key}' fehlt")
    
    def get_entities(self) -> List[str]:
        """Gibt Liste aller verfügbaren Entity-Types zurück"""
        return list(self.mapping.get('entities', {}).keys())
    
    def get_allowed_fields(self, entity_type: str) -> Dict:
        """
        Gibt erlaubte Felder für Entity zurück (Whitelist).
        
        Args:
            entity_type: "person" oder "company"
            
        Returns:
            Dict mit erlaubten Feldern und deren Config
        """
        entities = self.mapping.get('entities', {})
        entity = entities.get(entity_type, {})
        return entity.get('fields', {})
    
    def get_crm_field_name(self, entity_type: str, generic_name: str) -> Optional[str]:
        """
        Mappt generic field name zu CRM-spezifischem Namen.
        
        Args:
            entity_type: "person" oder "company"
            generic_name: Generic Feldname (z.B. "job", "website")
            
        Returns:
            CRM-spezifischer Feldname (z.B. "jobTitle", "domainName") oder None
        """
        fields = self.get_allowed_fields(entity_type)
        field_config = fields.get(generic_name)
        
        if not field_config:
            return None  # Feld nicht in Whitelist
        
        return field_config.get('crm_field')
    
    def is_field_allowed(self, entity_type: str, generic_name: str) -> bool:
        """Prüft, ob Feld in Whitelist ist"""
        return generic_name in self.get_allowed_fields(entity_type)
    
    def map_fields(self, entity_type: str, fields: Dict) -> Dict:
        """
        Mappt alle Felder und filtert nicht-erlaubte raus.
        
        Args:
            entity_type: "person" oder "company"
            fields: Dict mit generic field names
            
        Returns:
            Dict mit CRM-spezifischen Feldnamen
        """
        mapped = {}
        allowed = self.get_allowed_fields(entity_type)
        
        for generic_name, value in fields.items():
            if generic_name in allowed:
                crm_field = allowed[generic_name]['crm_field']
                mapped[crm_field] = value
            else:
                print(f"⚠️ Feld '{generic_name}' nicht in Whitelist für {entity_type} (ignoriert)")
        
        return mapped
    
    def validate_field(self, entity_type: str, field_name: str, value: Any) -> Tuple[bool, Any, Optional[str]]:
        """
        Validiert Feld-Wert und führt Auto-Fix durch.
        
        Args:
            entity_type: "person" oder "company"
            field_name: Generic Feldname
            value: Wert zum Validieren
            
        Returns:
            (is_valid, corrected_value, error_message)
        """
        fields = self.get_allowed_fields(entity_type)
        field_config = fields.get(field_name, {})
        
        if not field_config:
            return (False, value, f"Feld '{field_name}' nicht erlaubt")
        
        field_type = field_config.get('type')
        validation_rule = field_config.get('validation')
        auto_fix = field_config.get('auto_fix', False)
        
        # === TYPE CHECKING ===
        
        # Number
        if field_type == 'number':
            try:
                value = int(value) if isinstance(value, str) else value
                if not isinstance(value, (int, float)):
                    return (False, value, f"'{field_name}' muss eine Zahl sein")
                
                # Min-Wert prüfen
                min_val = field_config.get('min')
                if min_val is not None and value < min_val:
                    return (False, value, f"'{field_name}' muss mindestens {min_val} sein")
                    
            except (ValueError, TypeError):
                return (False, value, f"'{field_name}' muss eine Zahl sein")
        
        # Date
        elif field_type == 'date':
            date_format = field_config.get('format', 'YYYY-MM-DD')
            # Basic validation (könnte erweitert werden)
            if not isinstance(value, str) or len(value) != 10 or value.count('-') != 2:
                return (False, value, f"'{field_name}' muss im Format {date_format} sein")
        
        # URL + Auto-Fix
        elif field_type == 'url':
            if not isinstance(value, str):
                return (False, value, f"'{field_name}' muss eine URL (String) sein")
            
            # Auto-Fix: Ergänze https://
            if auto_fix == True and not value.startswith(('http://', 'https://')):
                value = f"https://{value}"
                print(f"🔧 Auto-Fix: '{field_name}' → {value}")
        
        # Links Object (für Twenty CRM: domainName, linkedinLink, xLink)
        elif field_type == 'links_object':
            if not isinstance(value, str):
                return (False, value, f"'{field_name}' muss eine URL (String) sein")
            
            # Auto-Fix: Konvertiere String zu Links-Object
            if auto_fix:
                # Ergänze https:// falls fehlt
                if not value.startswith(('http://', 'https://')):
                    value = f"https://{value}"
                
                # Konvertiere zu Twenty CRM Links-Object Format
                value = {
                    "primaryLinkLabel": "",
                    "primaryLinkUrl": value,
                    "secondaryLinks": []
                }
                print(f"🔧 Auto-Fix: '{field_name}' → Links-Object (primaryLinkUrl: {value['primaryLinkUrl']})")
        
        # Phones Object (für Twenty CRM: phones)
        elif field_type == 'phones_object':
            if not isinstance(value, str):
                return (False, value, f"'{field_name}' muss eine Telefonnummer (String) sein")
            
            # Auto-Fix: Konvertiere String zu Phones-Object
            if auto_fix:
                # Extrahiere Country Code aus +43... Format
                import re
                phone_clean = value.strip().replace(' ', '').replace('-', '')
                
                # Versuche +XX Format zu parsen (max 2-stellige Country Codes bevorzugt)
                # Prüfe zuerst bekannte Country Codes
                country_codes = {
                    "+43": "AT", "+49": "DE", "+41": "CH",
                    "+33": "FR", "+39": "IT", "+44": "GB",
                    "+1": "US", "+34": "ES", "+31": "NL",
                    "+32": "BE", "+48": "PL", "+420": "CZ"
                }
                
                calling_code = None
                phone_number = phone_clean
                country_code = "AT"  # Default
                
                # Versuche bekannte Country Codes zu matchen (längste zuerst)
                for code, country in sorted(country_codes.items(), key=lambda x: len(x[0]), reverse=True):
                    if phone_clean.startswith(code):
                        calling_code = code
                        country_code = country
                        phone_number = phone_clean[len(code):]
                        break
                
                # Fallback: Wenn kein Match, versuche generisches Pattern
                if not calling_code:
                    country_match = re.match(r'\+(\d{1,3})', phone_clean)
                    if country_match:
                        calling_code = f"+{country_match.group(1)}"
                        phone_number = phone_clean[len(calling_code):]
                    else:
                        # Kein + gefunden, nehme AT default
                        calling_code = "+43"
                        country_code = "AT"
                        phone_number = phone_clean.lstrip('+')
                
                value = {
                    "primaryPhoneNumber": phone_number,
                    "primaryPhoneCallingCode": calling_code,
                    "primaryPhoneCountryCode": country_code,
                    "additionalPhones": []
                }
                print(f"🔧 Auto-Fix: '{field_name}' → Phones-Object ({calling_code} {phone_number})")
        
        # Emails Object (für Twenty CRM: emails)
        elif field_type == 'emails_object':
            if not isinstance(value, str):
                return (False, value, f"'{field_name}' muss eine E-Mail (String) sein")
            
            # Auto-Fix: Konvertiere String zu Emails-Object
            if auto_fix:
                value = {
                    "primaryEmail": value,
                    "additionalEmails": None
                }
                print(f"🔧 Auto-Fix: '{field_name}' → Emails-Object (primaryEmail: {value['primaryEmail']})")
        
        # String
        elif field_type == 'string':
            if not isinstance(value, str):
                value = str(value)
            
            # Auto-Fix: Strip Protocol (für CRMs die nur Domain wollen, z.B. Twenty)
            if auto_fix == "strip_protocol" and isinstance(value, str):
                if value.startswith(('http://', 'https://')):
                    value = value.replace('https://', '').replace('http://', '')
                    print(f"🔧 Auto-Fix: '{field_name}' → {value} (Protokoll entfernt)")
        
        # === CUSTOM VALIDATION ===
        
        # Validation Pattern (z.B. "linkedin.com" muss enthalten sein)
        if validation_rule and isinstance(validation_rule, str):
            if validation_rule not in str(value):
                validation_info = self.mapping.get('validation', {}).get(validation_rule, {})
                message = validation_info.get('message', f"Muss {validation_rule} enthalten")
                return (False, value, f"'{field_name}': {message}")
        
        return (True, value, None)
    
    def get_field_description(self, entity_type: str, field_name: str) -> str:
        """Gibt Beschreibung für LLM zurück"""
        fields = self.get_allowed_fields(entity_type)
        field_config = fields.get(field_name, {})
        return field_config.get('description', field_name)
    
    def get_llm_hint(self, entity_type: str, field_name: str) -> str:
        """Gibt LLM-Hint zurück"""
        fields = self.get_allowed_fields(entity_type)
        field_config = fields.get(field_name, {})
        return field_config.get('llm_hint', '')
    
    def get_endpoint(self, entity_type: str) -> str:
        """Gibt API-Endpoint für Entity zurück"""
        entities = self.mapping.get('entities', {})
        entity = entities.get(entity_type, {})
        return entity.get('endpoint', entity_type)
    
    def generate_llm_field_list(self, entity_type: str) -> str:
        """
        Generiert formatierte Liste aller Felder für System-Prompt.
        
        Returns:
            Formatierter String für LLM
        """
        fields = self.get_allowed_fields(entity_type)
        
        if not fields:
            return f"Keine Felder für {entity_type} definiert"
        
        lines = [f"**{entity_type.upper()} FELDER:**"]
        
        for generic_name, config in fields.items():
            description = config.get('description', '')
            llm_hint = config.get('llm_hint', '')
            example = config.get('example', '')
            custom = config.get('custom', False)
            
            line = f"- `{generic_name}`: {description}"
            
            if custom:
                customer = config.get('customer', '')
                line += f" [CUSTOM: {customer}]" if customer else " [CUSTOM]"
            
            if llm_hint:
                line += f" ({llm_hint})"
            
            if example:
                line += f" - Beispiel: {example}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_all_generic_field_names(self, entity_type: str) -> List[str]:
        """Gibt Liste aller Generic Field Names zurück"""
        return list(self.get_allowed_fields(entity_type).keys())
    
    def __repr__(self):
        entities = ", ".join(self.get_entities())
        return f"FieldMappingLoader(crm='{self.crm_system}', entities=[{entities}])"


# === CACHED LOADER ===

@lru_cache(maxsize=5)
def load_field_mapping(crm_system: str) -> FieldMappingLoader:
    """
    Cached Field Mapping Loader.
    
    Args:
        crm_system: Name des CRM-Systems (z.B. 'twenty')
        
    Returns:
        FieldMappingLoader Instanz
    """
    return FieldMappingLoader(crm_system)


# === TESTING ===

if __name__ == "__main__":
    print("🧪 Testing Field Mapping Loader...\n")
    
    try:
        # Load Twenty Mapping
        loader = load_field_mapping("twenty")
        print(f"✅ Loaded: {loader}\n")
        
        # Show Entities
        print(f"📁 Entities: {loader.get_entities()}\n")
        
        # Show Person Fields
        print("👤 Person Fields:")
        person_fields = loader.get_allowed_fields("person")
        for name, config in person_fields.items():
            print(f"  - {name} → {config['crm_field']} ({config['type']})")
        
        print("\n🏢 Company Fields:")
        company_fields = loader.get_allowed_fields("company")
        for name, config in company_fields.items():
            print(f"  - {name} → {config['crm_field']} ({config['type']})")
        
        # Test Mapping
        print("\n🔄 Test Mapping:")
        test_fields = {"website": "expoya.com", "size": 50, "invalid_field": "test"}
        mapped = loader.map_fields("company", test_fields)
        print(f"Input:  {test_fields}")
        print(f"Output: {mapped}")
        
        # Test Validation
        print("\n✅ Test Validation:")
        is_valid, fixed_value, error = loader.validate_field("company", "website", "expoya.com")
        print(f"website='expoya.com' → valid={is_valid}, fixed='{fixed_value}', error={error}")
        
        # Test LLM Field List
        print("\n📝 LLM Field List (Person):")
        print(loader.generate_llm_field_list("person"))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

