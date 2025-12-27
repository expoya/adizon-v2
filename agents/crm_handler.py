"""
Adizon - CRM Handler mit LangChain Tools
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate
from tools.crm import create_contact, search_contacts
from agents.session_guard import check_session_status
from utils.memory import get_conversation_memory, set_session_state
import os

def handle_crm(message: str, user_name: str, user_id: str) -> str:
    """
    Adizon's CRM-Funktion mit Tool Calling
    """
    
    try:
        print(f"🏢 Adizon (CRM) processing: {message[:50]}...")
        
        # LLM initialisieren
        llm = ChatOpenAI(
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model=os.getenv("MODEL_NAME"),
            top_p=0.9,
            temperature=0.4 
        )
        
        # Tools Liste
        tools = [create_contact, search_contacts]
        
        memory = get_conversation_memory(user_id, session_id="main")
        
        # Prompt Template - Strikter & Handlungsorientierter
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"""Du bist Adizon, ein freundlicher, hilfreicher CRM-Assistent.

USER INFO:
- Name: {user_name}
- ID: {user_id}

REGELN:
1. TOOL-FIRST: Wenn der User was will und die Daten da sind -> MACH ES SOFORT. 
2. MEMORY: Nutze Wissen aus dem Chatverlauf.
3. Wenn du einen Kontakt erstellen willst oder sollst, aber dir Daten fehlen, frage direkt nach fehlenden Daten. SEHR WICHTIG: Stelle auf keinen Fall Fragen wie "Brauche ich die Email?"!   
4. Deine Sprache: Kurz & knackig, aber charmant.

VERFÜGBARE TOOLS:
- create_contact(name, email, phone): Erfordert ZWINGEND Name UND Email.
- search_contacts(query): Suche nach Namen, Firmen oder E-Mails.

Beispiel:
User: "Suche Michael" -> [Rufe Tool search_contacts auf] -> "Hier sind die Ergebnisse..."
"""),
            ("placeholder", "{chat_history}"),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])
        
        # Agent erstellen
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            memory=memory,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True
        )
        
        # Agent ausführen
        response = agent_executor.invoke({"input": message})
        final_output = response['output']

        # === NEU: GUARD CHECK ===
        # Wir prüfen: Muss die Session offen bleiben?
        new_state = check_session_status(final_output, message)
        
        # Speichern in Redis
        set_session_state(user_id, new_state)
        
        print(f"🛡️ Session Guard Decision: {new_state}")
        
        return final_output
        
    except Exception as e:
        print(f"❌ CRM Handler Error: {e}")
        import traceback
        print(traceback.format_exc())
        return f"Technischer Fehler im CRM Modul: {str(e)}"