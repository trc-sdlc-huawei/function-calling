import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from anthropic import Anthropic
from dotenv import load_dotenv


import os
from openai import OpenAI
from huawei_tools import huawei_tools,weather_tools
import json
from my_logger import setup_logger, log_info, log_warning, log_error, log_debug, log_exception, log_separator, log_event, log_dict

logger = setup_logger("client_logger", log_to_console=False, log_to_file="client.log")
load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")
            
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str, llm_choice: str = "claude") -> str:
        """Process a query using Claude or OpenAI and available tools"""
        log_event(logger, "process_query_start", {"llm_choice": llm_choice, "query": query})
        try:
            if llm_choice.lower() == "claude":
                messages = [
                    {
                        "role": "user",
                        "content": query
                    }
                ]
                log_info(logger, f"Claude: Initial messages: {messages}")
                response = await self.session.list_tools()
                available_tools = [{ 
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                } for tool in response.tools]
                log_dict(logger, available_tools, "Claude available_tools")
                response = self.anthropic.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )
                log_info(logger, f"Claude: Initial response: {response}")
                final_text = []
                while True:
                    for content in response.content:
                        log_debug(logger, f"Claude content type: {content.type}")
                        if content.type == 'text':
                            final_text.append(content.text)
                        elif content.type == 'tool_use':
                            tool_name = content.name
                            tool_args = content.input
                            log_event(logger, "Claude tool_call", {"tool_name": tool_name, "tool_args": tool_args})
                            result = await self.session.call_tool(tool_name, tool_args)
                            log_info(logger, f"Claude tool result: {result}")
                            final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")
                            if hasattr(content, 'text') and content.text:
                                messages.append({
                                  "role": "assistant",
                                  "content": content.text
                                })
                            messages.append({
                                "role": "user", 
                                "content": result.content
                            })
                            response = self.anthropic.messages.create(
                                model="claude-3-5-sonnet-20241022",
                                max_tokens=1000,
                                messages=messages,
                            )
                            log_info(logger, f"Claude: Next response: {response}")
                            final_text.append(response.content[0].text)
                            break  # Only process one tool_use per loop
                    else:
                        break  # No tool_use found, break loop
                log_event(logger, "process_query_end", {"llm_choice": llm_choice})
                return "\n".join(final_text)
            elif llm_choice.lower() == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    log_error(logger, "OPENAI_API_KEY environment variable not set.")
                    raise RuntimeError("OPENAI_API_KEY environment variable not set.")
                client = OpenAI()
                messages = [{"role": "user", "content": query}]
                output_str = []
                log_event(logger, "OpenAI: Start conversation", {"messages": messages})
                while True:
                    response = client.responses.create(
                        model="gpt-4.1",
                        input=messages,
                        tools=weather_tools
                    )
                    log_info(logger, f"OpenAI: Response: {response}")
                    found_function_call = False
                    for item in response.output:
                        log_debug(logger, f"OpenAI output item: {item}")
                        output_str.append(str(item.type))
                        if item.type == "function_call":
                            found_function_call = True
                            func_name = item.name
                            func_args = item.arguments
                            log_event(logger, "OpenAI tool_call", {"func_name": func_name, "func_args": func_args})
                            tool_result = None
                            for tool in weather_tools:
                                if tool["name"] == func_name:
                                    tool_result = f"[Simulated call to {func_name} with {func_args}]"
                                    break
                            if tool_result is None:
                                tool_result = f"Tool {func_name} not found."
                            log_info(logger, f"OpenAI tool result: {tool_result}")
                            messages.append({
                                "role": "assistant",
                                "content": json.dumps({"function_call": {"name": func_name, "arguments": func_args}})
                            })
                            messages.append({
                                "role": "function",
                                "name": func_name,
                                "content": tool_result
                            })
                            output_str.append(f"Function call: {func_name} with {func_args}")
                            output_str.append(f"Tool result: {tool_result}")
                    if not found_function_call:
                        for item in response.output:
                            if hasattr(item, "text"):
                                output_str.append(str(item.text))
                        break
                output_str.append('=============================response output======================================================')
                output_str.append(str(response.output))
                output_str.append('===================================================================================')
                log_event(logger, "process_query_end", {"llm_choice": llm_choice})
                return "\n".join(output_str)
            else:
                log_warning(logger, f"Invalid LLM choice: {llm_choice}")
                return "Invalid LLM choice. Please select 'claude' or 'openai'."
        except Exception as e:
            log_exception(logger, f"Error in process_query: {e}")
            raise


    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        
        llm_choice = input("Which llm? (claude/openai): ").strip().lower()
        if llm_choice not in ["claude", "openai"]:
            print("Invalid LLM choice. Defaulting to 'claude'.")
            llm_choice = "claude"
        while True:
            try:
                query = input("\nQuery: ").strip()
                
                if query.lower() == 'quit':
                    break
                    
                response = await self.process_query(query, llm_choice=llm_choice)
                print("\n" + response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)
        
    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    import sys
    asyncio.run(main())
