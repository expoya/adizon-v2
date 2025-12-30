"""
Adizon - CRM Handler
"""
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langchain.agents.structured_chat.base import StructuredChatAgent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import RedisChatMessageHistory

# Importiert nur die Factory!
from tools.crm import get_crm_tools_for_user

from agents.session_guard import check_session_status
from utils.memory import set_session_state
from utils.agent_config import load_agent_config
from utils.ministral_parser import MinistralOutputParser  # Custom Parser!
from models.user import User
from typing import Optional
import os
from datetime import datetime
from zoneinfo import ZoneInfo

def handle_crm(message: str, user_name: str, user_id: str, user: Optional[User] = None) -> str:
    try:
        # Load Agent Config from YAML
        config = load_agent_config("crm_handler")
        
        # LLM Setup mit Config
        model_config = config.get_model_config()
        params = config.get_parameters()
        
        llm = ChatOpenAI(
            base_url=model_config['base_url'],
            api_key=model_config['api_key'],
            model=model_config['name'],
            **params  # temperature, top_p, max_tokens, etc.
        )
        
        # Tools (mit User-Context für Attribution)
        tools = get_crm_tools_for_user(user_id, user=user)
        
        # Redis Memory (neue LangChain API - kompatibel mit Structured Chat Agent!)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        session_key = f"adizon:conversation:{user_id}:main"
        
        def get_message_history(session_id: str):
            """Factory function für Redis Message History"""
            return RedisChatMessageHistory(
                session_id=session_id,
                url=redis_url,
                ttl=86400  # 24 Stunden TTL
            )
        
        # Aktuelles Datum für LLM (Vienna Timezone, eindeutig formatiert)
        now = datetime.now(ZoneInfo("Europe/Vienna"))
        from datetime import timedelta
        tomorrow = now + timedelta(days=1)
        day_after_tomorrow = now + timedelta(days=2)
        
        weekday_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        month_de = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
        
        current_date = now.strftime("%Y-%m-%d")
        tomorrow_date = tomorrow.strftime("%Y-%m-%d")
        day_after_tomorrow_date = day_after_tomorrow.strftime("%Y-%m-%d")
        
        current_date_full = (
            f"HEUTE: {weekday_de[now.weekday()]}, {now.day}. {month_de[now.month - 1]} {now.year} (ISO: {current_date})\n"
            f"  MORGEN: {weekday_de[tomorrow.weekday()]}, {tomorrow.day}. {month_de[tomorrow.month - 1]} {tomorrow.year} (ISO: {tomorrow_date})\n"
            f"  ÜBERMORGEN: {weekday_de[day_after_tomorrow.weekday()]}, {day_after_tomorrow.day}. {month_de[day_after_tomorrow.month - 1]} {day_after_tomorrow.year} (ISO: {day_after_tomorrow_date})"
        )

        # System Prompt aus YAML mit Template-Variablen
        system_prompt = config.get_system_prompt(
            user_name=user_name,
            current_date=current_date_full
        )

        # Optimized Prompt for Ministral (text-based reasoning)
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + """

VERFÜGBARE TOOLS: {tool_names}

{tools}

WICHTIG: Du MUSST für JEDE Anfrage ein strukturiertes Format nutzen!

FORMAT (EXAKT SO):

Thought: [Deine Überlegung was zu tun ist]
Action:
```json
{{"action": "tool_name", "action_input": "parameter"}}
```

ODER falls keine Tools nötig:

Thought: [Erklärung warum keine Tools nötig]
Final Answer: [Deine Antwort auf Deutsch]

REGELN:
1. NIEMALS Markdown-Formatierung (**text**) verwenden
2. IMMER mit "Thought:" beginnen
3. JSON MUSS valid sein (double quotes!)
4. "action_input" ist IMMER ein String
5. Bei Begrüßungen: Direkt "Final Answer:" ohne Tools

BEISPIEL (Begrüßung):
Thought: User grüßt nur, keine CRM-Aktion nötig
Final Answer: Servus Michael! Wie kann ich helfen?

BEISPIEL (Tool-Nutzung):
Thought: User möchte nach "Expoya" suchen
Action:
```json
{{"action": "search_contacts", "action_input": "Expoya"}}
```

STARTE JETZT!"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            ("ai", "{agent_scratchpad}")
        ])
        
        # Agent Config aus YAML
        agent_config = config.get_agent_config()
        
        # Custom Parser for Ministral (tolerant to format variations)
        output_parser = MinistralOutputParser()
        
        # Create agent with custom parser (using from_llm_and_tools)
        agent = StructuredChatAgent.from_llm_and_tools(
            llm=llm,
            tools=tools,
            prompt=prompt,
            output_parser=output_parser,
            handle_parsing_errors=True
        )
        
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=agent_config.get('verbose', True),
            handle_parsing_errors=True,  # Still handle edge cases
            max_iterations=3,  # Reduced iterations
            max_execution_time=60  # 60 second timeout
        )
        
        # Wrap Agent with Message History (neue Memory API!)
        agent_with_memory = RunnableWithMessageHistory(
            agent_executor,
            get_message_history,
            input_messages_key="input",
            history_messages_key="chat_history",
        )
        
        print(f"\n🤖 === CRM AGENT EXECUTION START ===")
        print(f"📝 User Input: {message}")
        print(f"🔧 Available Tools: {[tool.name for tool in tools]}")
        print(f"💾 Memory Session: {session_key}")
        
        response = agent_with_memory.invoke(
            {"input": message},
            config={"configurable": {"session_id": session_key}}
        )
        
        print(f"✅ Agent finished")
        print(f"📤 Final Output: {response.get('output', 'N/A')[:200]}...")
        print(f"🤖 === CRM AGENT EXECUTION END ===\n")
        final_output = response['output']

        # Session Guard
        new_state = check_session_status(final_output, message)
        set_session_state(user_id, new_state)
        
        return final_output
        
    except Exception as e:
        print(f"❌ CRM Error: {e}")
        return f"Fehler: {str(e)}"