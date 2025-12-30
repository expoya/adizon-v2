"""
Custom Output Parser for Ministral LLM
Tolerant parser that handles Ministral's output format variations
"""
import re
import json
from typing import Union
from langchain.agents.agent import AgentOutputParser
from langchain.schema import AgentAction, AgentFinish, OutputParserException


class MinistralOutputParser(AgentOutputParser):
    """
    Custom parser for Ministral that's more lenient than the default StructuredChatOutputParser.
    
    Handles common Ministral output variations:
    - Missing newlines between sections
    - Markdown formatting (**text**)
    - Numbered lists before Final Answer
    - Extra whitespace
    """
    
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        """Parse Ministral's output into AgentAction or AgentFinish"""
        
        # Clean up common issues
        text = text.strip()
        
        # Check for Final Answer (case-insensitive, flexible formatting)
        final_answer_match = re.search(
            r'(?:^|\n)\s*(?:\*\*)?Final\s+Answer(?:\*\*)?\s*:\s*(.+?)(?:\n|$)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if final_answer_match:
            # Extract final answer text
            answer = final_answer_match.group(1).strip()
            
            # Remove leading numbering (e.g., "1. ", "2. ")
            answer = re.sub(r'^\d+\.\s+', '', answer)
            
            # Remove markdown bold
            answer = re.sub(r'\*\*(.+?)\*\*', r'\1', answer)
            
            return AgentFinish(
                return_values={"output": answer},
                log=text
            )
        
        # Look for Action block with JSON
        action_match = re.search(
            r'Action\s*:\s*```(?:json)?\s*(\{.+?\})\s*```',
            text,
            re.IGNORECASE | re.DOTALL
        )
        
        if action_match:
            try:
                json_str = action_match.group(1).strip()
                action_dict = json.loads(json_str)
                
                action_name = action_dict.get("action")
                action_input = action_dict.get("action_input", "")
                
                if not action_name:
                    raise OutputParserException(f"Missing 'action' in JSON: {json_str}")
                
                return AgentAction(
                    tool=action_name,
                    tool_input=action_input,
                    log=text
                )
            except json.JSONDecodeError as e:
                raise OutputParserException(f"Invalid JSON in Action block: {e}")
        
        # If we get here, output doesn't match expected format
        # Try to extract any coherent answer as Final Answer
        if "thought:" in text.lower() and len(text) > 50:
            # Extract text after last "Thought:"
            parts = re.split(r'(?:^|\n)\s*Thought\s*:', text, flags=re.IGNORECASE)
            if len(parts) > 1:
                last_thought = parts[-1].strip()
                # Remove markdown and numbering
                last_thought = re.sub(r'\*\*(.+?)\*\*', r'\1', last_thought)
                last_thought = re.sub(r'^\d+\.\s+', '', last_thought, flags=re.MULTILINE)
                
                # If it looks like a reasonable answer, use it
                if len(last_thought) > 20:
                    return AgentFinish(
                        return_values={"output": last_thought},
                        log=text
                    )
        
        # Last resort: treat entire output as answer
        if len(text) > 20:
            clean_text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
            return AgentFinish(
                return_values={"output": clean_text},
                log=text
            )
        
        raise OutputParserException(
            f"Could not parse LLM output: `{text}`"
        )
    
    def get_format_instructions(self) -> str:
        """Instructions for the LLM on how to format output"""
        return """WICHTIG: Nutze EXAKT dieses Format:

Thought: [Deine Überlegung]
Action:
```json
{"action": "tool_name", "action_input": "value"}
```

ODER (ohne Tools):

Thought: [Überlegung]
Final Answer: [Antwort auf Deutsch]

REGELN:
- KEINE Markdown-Formatierung (**text**)
- KEINE nummerierten Listen
- JSON muss valid sein"""
    
    @property
    def _type(self) -> str:
        return "ministral-structured-chat"

