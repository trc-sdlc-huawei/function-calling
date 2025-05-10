from typing import List, Dict, Any

def convert_tools(server_tools: List[Any]) -> List[Dict[str, Any]]:
    """
    Converts server tool objects to the format required by Claude LLM.
    Each Claude tool should be a dict with keys: name, description, input_schema.
    """
    claude_tools = []
    for tool in server_tools:
        claude_tools.append({
            "name": getattr(tool, "name", tool.get("name", None)),
            "description": getattr(tool, "description", tool.get("description", None)),
            "input_schema": getattr(tool, "inputSchema", tool.get("input_schema", None)),
        })
    return claude_tools
