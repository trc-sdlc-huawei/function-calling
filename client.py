import asyncio
from typing import Optional, List, Tuple
from contextlib import AsyncExitStack

from mcp import ClientSession, ListToolsResult, StdioServerParameters
from mcp.client.streamable_http import streamablehttp_client

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

    async def connect_to_server_stdio(self, command: str = None, args: list = None, env: dict = None):
        """Connect to an MCP server, optionally with custom command/args/env (for config file support)
        Args:
            server_script_path: Path to the server script (.py or .js) (legacy)
            command: Command to launch server (e.g. 'node', 'python3', 'docker', etc.)
            args: List of arguments for the command
            env: Environment variables dict
        """
        print("\n>>>>>the connect_to_server method of MCPClient")

        launch_args = args
        # Store launch details for metadata endpoint
        self.command = command
        self.launch_args = launch_args
        self.env = env
        
        server_params = StdioServerParameters(
            command=command,
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

   
    async def _spawn_process(self, command: str, args: list, env: dict):
        """Spawn a process with command/args/env"""
        process = await asyncio.create_subprocess_exec(
            command, *args,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        return process

     

    async def connect_to_server_streamablehttp(self, command: str = None, args: list = None, env: dict = None):
        """Connect to an MCP server, optionally with custom command/args/env (for config file support)
        Args:
            server_script_path: Path to the server script (.py or .js) (legacy)
            command: Command to launch server (e.g. 'node', 'python3', 'docker', etc.)
            args: List of arguments for the command
            env: Environment variables dict
        """
        print("\n>>>>>the connect_to_server method of MCPClient")
        # Store launch details for metadata endpoint
        self.command = command
        self.launch_args = args
        self.env = env
        # self.process = await  self._spawn_process(command, args, env)

        async with streamablehttp_client("http://localhost:3001/mcp") as ( read_stream, write_stream,_,):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()
                tool_result = await session.list_tools()
                self.session = session
                self.raw_tools = await session.list_tools()
                print("\nConnected to server with tools:", [tool.name for tool in self.raw_tools.tools])

                self.openai_tools = openai_converter.convert_tools(self.raw_tools.tools)
                # Call a tool

        # List available tools
       
        




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
