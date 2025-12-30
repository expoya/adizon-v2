"""
Adizon - CRM Handler
"""
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate

# Importiert nur die Factory!
from tools.crm import get_crm_tools_for_user

from agents.session_guard import check_session_status
from utils.memory import get_conversation_memory, set_session_state
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
        
        # Tools & Memory (mit User-Context für Attribution)
        tools = get_crm_tools_for_user(user_id, user=user)
        memory = get_conversation_memory(user_id, session_id="main")
        
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

        # ReAct Prompt Template (text-basiert, funktioniert mit jedem LLM!)
        prompt = PromptTemplate.from_template(
            system_prompt + """

Du hast Zugriff auf folgende Tools:

{tools}

Nutze dieses Format:

Question: Die Frage oder Aufgabe des Users
Thought: Überlege, was zu tun ist
Action: Das Tool, das du nutzen möchtest (eins von: [{tool_names}])
Action Input: Der Input für das Tool (als JSON)
Observation: Das Resultat des Tools
... (Thought/Action/Action Input/Observation kann sich wiederholen)
Thought: Ich weiß jetzt die Antwort
Final Answer: Die finale Antwort an den User (auf Deutsch!)

Beginne!

Question: {input}
Thought: {agent_scratchpad}"""
        )
        
        # Agent Config aus YAML
        agent_config = config.get_agent_config()
        
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            memory=memory, 
            verbose=agent_config.get('verbose', True),
            handle_parsing_errors=agent_config.get('handle_parsing_errors', True),
            max_iterations=agent_config.get('max_iterations', 5)
        )
        
        response = agent_executor.invoke({"input": message})
        final_output = response['output']

        # Session Guard
        new_state = check_session_status(final_output, message)
        set_session_state(user_id, new_state)
        
        return final_output
        
    except Exception as e:
        print(f"❌ CRM Error: {e}")
        return f"Fehler: {str(e)}"