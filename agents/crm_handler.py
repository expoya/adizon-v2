"""
Adizon - CRM Handler mit LangChain Tools
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from tools.crm import create_contact, search_contacts
from utils.memory import get_conversation_memory
import os


def handle_crm(message: str, user_name: str, user_id: str) -> str:
    """
    Adizon's CRM-Funktion mit Tool Calling
    
    Args:
        message: User Nachricht
        user_name: Name des Users
        user_id: User ID
        
    Returns:
        Adizon's Antwort
    """
    
    try:
        print(f"🏢 Adizon (CRM) processing: {message[:50]}...")
        
        # LLM initialisieren
        llm = ChatOpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=os.getenv("MODEL_NAME"),
            temperature=0.3
        )
        
        # Tools Liste
        tools = [create_contact, search_contacts]
        
        memory = get_conversation_memory(user_id, session_id="crm")
        # Prompt Template
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Du bist Adizon, ein KI-Assistent für KMUs.

CRM-MODUS:
- Du kannst CRM-Tools nutzen um echte Aktionen auszuführen
- Sei professionell und präzise
- Antworte auf Deutsch
- Du duzt ({user_name})

VERFÜGBARE TOOLS:
- create_contact: Erstellt Kontakte (benötigt: name, email, optional: phone)
- search_contacts: Sucht Kontakte (benötigt: query)

WICHTIG:
- Wenn du Informationen brauchst (z.B. Email fehlt), frage nach!
- Nach Tool-Nutzung: Bestätige die Aktion kurz und freundlich
- Bei Fehlern: Erkläre was schief ging

User ID: {user_id}"""),
            ("human", "{input}"),
            ("placeholder", "{chat_history}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Agent erstellen
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,  # Zeigt Tool-Calls in Logs
            max_iterations=3,
            handle_parsing_errors=True
        )
        
        # Agent ausführen
        response = agent_executor.invoke({"input": message})
        
        return response['output']
        
    except Exception as e:
        print(f"❌ CRM Handler Error: {e}")
        import traceback
        print(traceback.format_exc())
        return f"Hi {user_name}, ich hatte gerade technische Probleme. Versuch's bitte nochmal!"