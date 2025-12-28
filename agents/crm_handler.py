"""
Adizon - CRM Handler
"""
from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate

# Importiert nur die Factory!
from tools.crm import get_crm_tools_for_user

from agents.session_guard import check_session_status
from utils.memory import get_conversation_memory, set_session_state
from utils.agent_config import load_agent_config
import os
from datetime import datetime

def handle_crm(message: str, user_name: str, user_id: str) -> str:
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
        
        # Tools & Memory
        tools = get_crm_tools_for_user(user_id)
        memory = get_conversation_memory(user_id, session_id="main")
        current_date = datetime.now().strftime("%A, %Y-%m-%d")

        # System Prompt aus YAML mit Template-Variablen
        system_prompt = config.get_system_prompt(
            user_name=user_name,
            current_date=current_date
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Agent Config aus YAML
        agent_config = config.get_agent_config()
        
        agent = create_tool_calling_agent(llm, tools, prompt)
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