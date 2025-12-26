"""
Quick Qwen Test
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url=os.getenv("OPENROUTER_BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# TEST 1: Einfache Frage
# TEST 1: Einfache Frage
print("=== TEST 1: Volle Response ===")
response = client.chat.completions.create(
    model="qwen/qwen3-8b",
    messages=[
        {"role": "user", "content": "Hallo! Wie geht's?"}
    ],
    temperature=0.7,
    max_tokens=500
)

print(f"Full Response Object:")
print(response)
print()

# Schaue nach allen möglichen Content-Teilen
message = response.choices[0].message
print(f"Message Content: '{message.content}'")

# Reasoning/Thinking könnte hier sein:
if hasattr(message, 'reasoning'):
    print(f"Reasoning: {message.reasoning}")

if hasattr(message, 'thinking'):
    print(f"Thinking: {message.thinking}")

# Oder in usage
if hasattr(response, 'usage'):
    print(f"Usage: {response.usage}")

# TEST 2: Intent Classification (unser Prompt)
print("=== TEST 2: Intent Classification ===")
response = client.chat.completions.create(
    model="qwen/qwen3-4b:free",
    messages=[
        {
            "role": "system",
            "content": "Antworte NUR mit: CHAT oder CRM"
        },
        {
            "role": "user",
            "content": "Erstelle einen Kontakt für Max"
        }
    ],
    temperature=0.0,
    max_tokens=10
)
print(f"Response: '{response.choices[0].message.content}'")
print(f"Length: {len(response.choices[0].message.content)}")
print()

# TEST 3: Verschiedene Prompts
print("=== TEST 3: Alternativer Prompt ===")
response = client.chat.completions.create(
    model="qwen/qwen3-4b:free",
    messages=[
        {
            "role": "user",
            "content": "Klassifiziere diese Nachricht als CHAT oder CRM: 'Erstelle einen Kontakt'"
        }
    ],
    temperature=0.0,
    max_tokens=10
)
print(f"Response: '{response.choices[0].message.content}'")