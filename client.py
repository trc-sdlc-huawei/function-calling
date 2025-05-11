import asyncio
from typing import Optional, List, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession, ListToolsResult, StdioServerParameters
from mcp.client.stdio import stdio_client


from dotenv import load_dotenv

from converter import openai_converter
import os
from openai import OpenAI
import json
import my_logger as mylog
import response_model as respmod

logger = mylog.setup_logger("client_logger", mylog.logging.DEBUG, log_to_console=False, log_to_file="client.log")
load_dotenv()  # load environment variables from .env

class MCPClient:
    def __init__(self):
        print("\n>>>>>>the __init__ method of MCPClient")


        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            mylog.log_error(logger, "OPENAI_API_KEY environment variable not set.")
            raise RuntimeError("OPENAI_API_KEY environment variable not set.")

        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai = OpenAI()

    async def connect_to_server(self, server_script_path: str, command: str = None, args: list = None, env: dict = None):
        """Connect to an MCP server, optionally with custom command/args/env (for config file support)
        Args:
            server_script_path: Path to the server script (.py or .js) (legacy)
            command: Command to launch server (e.g. 'node', 'python3', 'docker', etc.)
            args: List of arguments for the command
            env: Environment variables dict
        """
        print("\n>>>>>the connect_to_server method of MCPClient")
        if command is not None:
            launch_command = command
        else:
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")
            launch_command = "python" if is_python else "node"
        launch_args = args if args is not None else [server_script_path]
        # Store launch details for metadata endpoint
        self.command = launch_command
        self.launch_args = launch_args
        self.env = env
        server_params = StdioServerParameters(
            command=launch_command,
            args=launch_args,
            env=env
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()
        # List available tools
        self.raw_tools = await self.session.list_tools()
        print("\nConnected to server with tools:", [tool.name for tool in self.raw_tools.tools])

        self.openai_tools = openai_converter.convert_tools(self.raw_tools.tools)




    async def _execute_tool_by_name_and_args(self, tool_name, tool_args):
        for tool in self.openai_tools:
            if tool["name"] == tool_name:
                return await self.session.call_tool(tool_name, tool_args)
        return None

    async def cleanup(self):
        """Clean up resources"""
        print("\n>>>>>Cleaning up resources...")
        await self.exit_stack.aclose()

# async def main():
#     if len(sys.argv) < 2:
#         print("Usage: python client.py <path_to_server_script>")
#         sys.exit(1)
        
#     client = MCPClient()
#     try:
#         await client.connect_to_server(sys.argv[1])
#     finally:
#         await client.cleanup()

# if __name__ == "__main__":
#     import sys
#     asyncio.run(main())
