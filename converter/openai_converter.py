from typing import List, Dict, Any

def convert_tools(tools: List):
    """
    Converts server tool objects to the format required by OpenAI LLM.
    Each OpenAI tool should be a dict with keys: type, function (with name, description, parameters).
    """
    converted = []
    for tool in tools:
        openai_tool = {
            "type": "function",
            "name": tool.name,
            "description": tool.description or "",
            "strict": True,
            "parameters": {
                "type": tool.inputSchema.get("type", "object"),
                "properties": {},
                "required": tool.inputSchema.get("required", []),
                "additionalProperties": False
            }
        }

        for prop_name, prop_schema in tool.inputSchema.get("properties", {}).items():
            param = {
                "type": prop_schema.get("type", "string")
            }
            # Optional: Add 'description' or 'title' if present
            if "description" in prop_schema:
                param["description"] = prop_schema["description"]
            elif "title" in prop_schema:
                param["title"] = prop_schema["title"]
            openai_tool["parameters"]["properties"][prop_name] = param

        converted.append(openai_tool)

    return converted

