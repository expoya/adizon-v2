# Adizon V2 - Troubleshooting Guide

Lessons learned from production debugging sessions.

---

## 🏗️ Twenty CRM API Quirks

### Problem: "Invalid object value" Errors

**Symptom:**
```
❌ API Error 400: "Invalid object value 'expoya.com' for field 'domainName'"
```

**Root Cause:**
Twenty CRM uses **Object structures** for many fields, NOT simple strings!

**Affected Fields:**

**Person:**
- `phones` → `{"primaryPhoneNumber": "...", "primaryPhoneCallingCode": "+43", "primaryPhoneCountryCode": "AT", "additionalPhones": []}`
- `emails` → `{"primaryEmail": "...", "additionalEmails": None}`
- `linkedinLink` → `{"primaryLinkLabel": "", "primaryLinkUrl": "...", "secondaryLinks": []}`
- `xLink` → Same structure as linkedinLink

**Company:**
- `domainName` → `{"primaryLinkLabel": "", "primaryLinkUrl": "...", "secondaryLinks": []}`
- `linkedinLink` → Same structure
- `xLink` → Same structure

**Solution:**
Implemented auto-conversion in `field_mapping_loader.py`:
- New field types: `links_object`, `phones_object`, `emails_object`
- Converts simple strings to Twenty's Object format automatically

**Example:**
```python
# Input from LLM:
"website": "expoya.com"

# Auto-converted to:
"domainName": {
    "primaryLinkLabel": "",
    "primaryLinkUrl": "https://expoya.com",
    "secondaryLinks": []
}
```

---

## 🤖 Ministral 14B Optimizations

### Problem 1: "übermorgen" Date Calculation Wrong

**Symptom:**
```
User: "Ruf Peter übermorgen an"
Agent: Due date = 2025-01-02 ❌
Correct: Due date = 2025-12-30 ✅
```

**Root Cause:**
- Ministral 14B doesn't understand German word "übermorgen" (day after tomorrow)
- Reproduced 5x in a row → NOT hallucination!
- Hypothesis: Compound word "über" + "morgen" not in training data

**Solution:**
Pre-calculate dates in Python and provide explicitly:
```python
HEUTE: Samstag, 28. Dezember 2025 (ISO: 2025-12-28)
MORGEN: Sonntag, 29. Dezember 2025 (ISO: 2025-12-29)
ÜBERMORGEN: Montag, 30. Dezember 2025 (ISO: 2025-12-30)
```

**Code:** `agents/crm_handler.py` - Uses `timedelta(days=1/2)`

---

### Problem 2: System Prompt Too Long

**Symptom:**
- Slow inference
- Inconsistent behavior
- High token costs

**Root Cause:**
- System prompt was **152 lines** (too much for 14B model!)
- Redundant examples
- Long explanations

**Solution:**
Drastically shortened prompt:
- **Before:** 152 lines
- **After:** 55 lines
- **Reduction:** 64%

**Impact:**
- ✅ Faster inference
- ✅ Lower costs
- ✅ Better focus for small models
- ✅ All features still work

---

## 🔧 LangChain Issues

### Problem 1: Template Variable Errors

**Symptom:**
```
❌ 'Input to ChatPromptTemplate is missing variables {'"size"', ...
Note: if you intended {"size"} to be part of the string and not a variable,
please escape it with double curly braces
```

**Root Cause:**
JSON syntax in system prompt (e.g., `{"size": 50}`) triggers LangChain's template engine.

**Solution:**
- Remove ALL JSON syntax from prompts
- Use verbal descriptions instead: "fields mit size=50 und website=expoya.com"
- LLM still understands (tool docstring has correct format)

---

### Problem 2: Memory Not Cleared on NEUSTART

**Symptom:**
```
User: NEUSTART
Agent: "Memory cleared" ✅
Then: "Hinweis: Telefonnummer +43 650... gespeichert" ❌
→ Agent remembers from previous session!
```

**Root Cause:**
LangChain uses **multiple Redis key formats**:
- `adizon:conversation:{user_id}:main` ✅ deleted
- `message_store:{user_id}:main` ❌ NOT deleted
- Other variations...

**Solution:**
Pattern-based deletion in `utils/memory.py`:
```python
# Delete all keys matching *{user_id}*
# But only adizon/message/conversation keys for safety
pattern = f"*{user_id}*"
keys = redis_client.keys(pattern)
for key in keys:
    if b'adizon' in key or b'message' in key or b'conversation' in key:
        redis_client.delete(key)
```

---

## 📞 Phone Number Parsing

### Problem: Wrong Country Code Extraction

**Symptom:**
```
Input:  "+436508150791"
Parsed: "+436" (calling code) ❌
API Error: "Invalid calling code +436"
```

**Root Cause:**
Regex `\+(\d{1,3})` matches **maximum length** (3 digits) → extracts "+436" instead of "+43"

**Solution:**
Check known country codes FIRST (longest to shortest):
```python
country_codes = {
    "+43": "AT", "+49": "DE", "+41": "CH",
    "+420": "CZ", ...  # 3-digit codes first
}

for code in sorted(country_codes, key=len, reverse=True):
    if phone_clean.startswith(code):
        calling_code = code
        break
```

**Test Cases:**
```
"+436508150791"   → "+43" (AT) ✅
"+4915012345678"  → "+49" (DE) ✅
"+420123456789"   → "+420" (CZ) ✅
```

---

## 🕐 Timezone Issues

### Problem: Server runs in UTC

**Symptom:**
Agent uses wrong time for Vienna users.

**Solution:**
```python
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("Europe/Vienna"))
```

**Impact:**
- Correct local time for Austrian users
- Proper date calculations
- Tasks with correct due dates

---

## 🎯 Best Practices

### When Adding New CRM Systems

1. **Check API Documentation FIRST**
   - Are fields simple strings or complex objects?
   - What's the exact structure required?

2. **Create Field Mapping YAML**
   - Use whitelist principle (explicit is better than implicit)
   - Document field types and structures
   - Add examples

3. **Test with Real API**
   - Don't assume format based on field name
   - Twenty CRM: "domainName" is NOT a string!
   - Check error messages for clues

### When Optimizing for Small LLMs (< 20B)

1. **Keep Prompts Short**
   - Max 80-100 lines for 14B models
   - Remove redundant examples
   - Use bullet points, not long explanations

2. **Pre-calculate Complex Tasks**
   - Dates, times, arithmetic
   - Don't rely on LLM for precise calculations
   - Especially for multilingual models with domain-specific terms

3. **Test Language-Specific Terms**
   - "übermorgen", "vorgestern", etc.
   - May not be in training data
   - Provide explicit values when possible

### Redis Memory Management

1. **Always Check All Key Formats**
   - LangChain uses multiple formats
   - Pattern-based deletion for safety
   - Log deleted keys for debugging

2. **Use TTLs**
   - Active sessions: 10 min
   - Idle sessions: 24 hours
   - Prevents memory leaks

---

## 🐛 Known Limitations

### Ministral 14B

- ❌ German compound time words ("übermorgen", "vorgestern")
- ❌ Long system prompts (> 150 lines)
- ✅ Good at English and simple German
- ✅ Fast inference
- ✅ Low cost

### Twenty CRM API

- ⚠️ Many fields are Objects, not Strings
- ⚠️ Error messages not always clear
- ⚠️ Documentation incomplete for some fields
- ✅ Fast API
- ✅ Good GraphQL support

---

## 📚 Version History

- **2.4.2** - Memory leak + Phone parsing fixes (2025-12-28)
- **2.4.1** - Phones & Emails Object support (2025-12-28)
- **2.4.0** - Links Object for domainName (2025-12-28)
- **3.0.2** - Date calculation pre-computation (2025-12-28)
- **3.0.1** - Remove JSON from prompt (2025-12-28)
- **3.0.0** - System prompt optimization (2025-12-28)

