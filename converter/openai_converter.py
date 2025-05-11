from typing import List, Dict, Any

def convert_tools(tools: List):
    """
    Converts server tool objects to the format required by OpenAI LLM.
    Handles nested types (arrays of objects, nested properties) recursively.
    """
    def convert_property(prop_schema: dict, original_required=None, prop_name=None) -> dict:
        prop_type = prop_schema.get("type", "string")
        # Determine if this property is required in the original schema
        is_required = True
        if original_required is not None and prop_name is not None:
            is_required = prop_name in original_required
        # If not required, type should be [type, "null"]
        if not is_required and isinstance(prop_type, str):
            type_val = [prop_type, "null"]
        else:
            type_val = prop_type
        param = {"type": type_val}
        if "description" in prop_schema:
            param["description"] = prop_schema["description"]
        elif "title" in prop_schema:
            param["title"] = prop_schema["title"]
        # Recursively handle arrays and objects
        if prop_type == "array" and "items" in prop_schema:
            param["items"] = convert_property(prop_schema["items"])
        if prop_type == "object":
            param["properties"] = {}
            nested_properties = prop_schema.get("properties", {})
            original_nested_required = prop_schema.get("required", [])
            # All nested properties are required in OpenAI schema
            param["required"] = list(nested_properties.keys())
            for sub_name, sub_schema in nested_properties.items():
                param["properties"][sub_name] = convert_property(
                    sub_schema, original_nested_required, sub_name
                )
            param["additionalProperties"] = prop_schema.get("additionalProperties", False)
        if "enum" in prop_schema:
            param["enum"] = prop_schema["enum"]
        return param

    converted = []
    for tool in tools:
        original_required = tool.inputSchema.get("required", [])
        all_props = list(tool.inputSchema.get("properties", {}).keys())
        parameters = {
            "type": tool.inputSchema.get("type", "object"),
            "properties": {},
            "required": all_props,  # OpenAI expects all properties required
            "additionalProperties": tool.inputSchema.get("additionalProperties", False)
        }
        for prop_name, prop_schema in tool.inputSchema.get("properties", {}).items():
            parameters["properties"][prop_name] = convert_property(prop_schema, original_required, prop_name)
        openai_tool = {
            "type": "function",
            "name": tool.name,
            "description": tool.description or "",
            "strict": True,
            "parameters": parameters
        }
        converted.append(openai_tool)
    return converted

