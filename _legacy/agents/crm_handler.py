"""
Adizon - CRM Handler
"""
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import RedisChatMessageHistory

# Importiert nur die Factory!
from tools.crm import get_crm_tools_for_user

from agents.session_guard import check_session_status
from utils.memory import set_session_state
from utils.agent_config import load_agent_config
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

        # ReAct Prompt (Standard LangChain Format - funktioniert mit ALLEN LLMs!)
        prompt = PromptTemplate.from_template(
            system_prompt + """

Du hast Zugriff auf folgende Tools:

{tools}

Nutze folgendes Format:

Question: Die Frage oder Anfrage des Users
Thought: Überlege was zu tun ist
Action: Der Tool-Name (einer von [{tool_names}])
Action Input: Der Input für das Tool (als String)
Observation: Das Ergebnis des Tools
... (Thought/Action/Action Input/Observation kann sich wiederholen)
Thought: Ich habe genug Informationen für die finale Antwort
Final Answer: Die finale Antwort auf Deutsch

WICHTIG:
- Bei Begrüßungen DIREKT "Final Answer:" (keine Tools nötig!)
- Action Input ist IMMER ein einfacher String (kein JSON!)
- Antworte IMMER auf Deutsch

Beginne!

Question: {input}
Thought: {agent_scratchpad}"""
        )
        
        # Agent Config aus YAML
        agent_config = config.get_agent_config()
        
        # ReAct Agent (kein Custom Parser nötig!)
        agent = create_react_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=agent_config.get('verbose', True),
            handle_parsing_errors=True,
            max_iterations=agent_config.get('max_iterations', 5),
            max_execution_time=agent_config.get('max_execution_time', 60)
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