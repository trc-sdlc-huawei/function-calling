from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ToolCall(BaseModel):
    tool_name: str
    tool_args: Dict[str, Any]
    tool_response: Any

class LLMCall(BaseModel):
    llm: str
    request: Dict[str, Any]
    response: Any

class Interaction(BaseModel):
    type: str  # 'llm_api_call' or 'tool_call'
    details: Dict[str, Any]

class QueryResponse(BaseModel):
    names_of_tools_used: Optional[List[str]] = None
    flow: List[Interaction]
    final_answer: str
