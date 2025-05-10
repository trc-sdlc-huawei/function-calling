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

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        print("\n>>>>>the connect_to_server method of MCPClient")
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
        list_tools_response = await self.session.list_tools()
        tools = list_tools_response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

        self.openai_tools = openai_converter.convert_tools(tools)



    async def process_query(self, query: str, llm_choice: str = "openai", tool_choice=None):
        """Process a query using OpenAI and available tools, returning a structured JSON response"""
        print("\n>>>>>the process_query method of MCPClient")
        mylog.log_event(logger, "process_query_start", {"llm_choice": llm_choice, "query": query, "tool_choice": tool_choice})
        try:
            if llm_choice.lower() == "openai":
                return await self._process_query_openai(query, tool_choice=tool_choice)
            else:
                mylog.log_warning(logger, f"Invalid LLM choice: {llm_choice}")
                return {"error": "Invalid LLM choice. Please select 'openai'."}
        except Exception as e:
            mylog.log_exception(logger, f"Error in process_query: {e}")
            raise

    async def _process_query_openai(self, user_query: str, tool_choice=None):
        """Handle user query processing for OpenAI LLM."""
        flow = []
        openai_query_messages = [{"role": "user", "content": user_query}]
        mylog.log_event(logger, "OpenAI: Start conversation", {"messages": openai_query_messages})
        need_query_openai: bool = True
        add_tools_to_next_openai_query: bool = True
        answer_text = ""
        overall_tool_use_names: List[str] = []
        
        while need_query_openai:
            # call openai api, with tools or without tools
            if add_tools_to_next_openai_query:
                openai_response = await self._call_openai_api(openai_query_messages, self.openai_tools, tool_choice=tool_choice)
                llm_interaction = respmod.LLMCall(llm="gpt-4.1", request={"messages": openai_query_messages, "tools": self.openai_tools, "tool_choice": tool_choice}, response=[item.model_dump() for item in openai_response.output])
                flow.append(respmod.Interaction(type="llm_api_call", details=llm_interaction.model_dump()))
                add_tools_to_next_openai_query = any([output_item.type == "function_call" for output_item in openai_response.output])  
                need_query_openai = add_tools_to_next_openai_query
            else:
                openai_response = await self._call_openai_api(openai_query_messages,self.openai_tools, tool_choice="auto")
                llm_interaction = respmod.LLMCall(llm="gpt-4.1", request={"messages": openai_query_messages, "tools": self.openai_tools, "tool_choice": "auto"}, response=[item.model_dump() for item in openai_response.output])
                flow.append(respmod.Interaction(type="llm_api_call", details=llm_interaction.model_dump()))
            mylog.log_info(logger, f"OpenAI: Response output: {openai_response.output}")

            
            # process openai response, with function call or without function call
            if any([output_item.type == "function_call" for output_item in openai_response.output]):
                # function call, and continue the loop
                # add the output of function call to the openai query messages
                openai_query_messages.extend(response_output_item for response_output_item in openai_response.output if response_output_item.type == "function_call")
                current_tool_use_names, tool_calls_results = await self.process_openai_function_call_response(openai_response, flow)
                overall_tool_use_names.extend(current_tool_use_names)
                # add the tool call results to the openai query messages
                openai_query_messages.extend([
                    {"type": "function_call_output", "output": tool_call_result, "call_id": call_id}
                    for call_id, tool_call_result in tool_calls_results
                ])
            else:
                # no function call, just return the answer
                openai_answer_text = await self.process_openai_message_response(openai_response)
                answer_text = openai_answer_text
            
            mylog.log_event(logger, "process_query_end", {"llm_choice": "openai"})
        
        
        
        
        
        
        response_obj = respmod.QueryResponse(
            names_of_tools_used=overall_tool_use_names,
            flow=flow,
            final_answer=answer_text
        )
        return response_obj.model_dump()



    async def process_openai_function_call_response(self, openai_response, flow)-> List[Tuple[str, str]]:
        """ 
        Handle OpenAI responses that contain function/tool calls.
        - Extracts the function call
        - Executes the tool
        - Updates the flow
        - returns overall tool use names and tool call results
        """
        overall_tool_use_names: List[str]= []
        tool_calls_results: List[Tuple[str, str]] = []
        for item in openai_response.output:
            mylog.log_debug(logger, f"OpenAI output item: {item}")
            if item.type == "function_call":
                func_name = item.name
                func_args = json.loads(item.arguments)
                mylog.log_event(logger, "OpenAI tool_call", {"tool_name": func_name, "tool_args": func_args})
                tool_result = None
                tool_result = await self._execute_tool_by_name_and_args(func_name, func_args)
                if tool_result is None:
                    tool_result = f"Tool {func_name} not found."
                overall_tool_use_names.append(func_name)    
                mylog.log_info(logger, f"OpenAI tool result: {tool_result}")
                tool_use = respmod.ToolCall(tool_name=func_name, tool_args=func_args, tool_response=tool_result)
                flow.append(respmod.Interaction(type="tool_call", details=tool_use.model_dump()))
                tool_calls_results.append((item.call_id,str(tool_result)))
        return overall_tool_use_names, tool_calls_results


    async def _execute_tool_by_name_and_args(self, tool_name, tool_args):
        for tool in self.openai_tools:
            if tool["name"] == tool_name:
                return await self.session.call_tool(tool_name, tool_args)
        return None

    async def process_openai_message_response(self, openai_response):
        """
        Handle OpenAI responses that are plain messages (no function/tool call).
        Extracts the answer text from the message content.
        """
        answer_text = ""
        for item in openai_response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        answer_text+=content.text+"\n"
        return answer_text




        
    async def chat_loop(self):
        """Run an interactive chat loop (always uses OpenAI, supports tool_choice)."""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        print("Available tool_choice options: auto (default), required, none, function:<function_name>")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                tool_choice = input("Choose tool_choice [auto/required/none/function:<name>]: ").strip()
                if tool_choice.startswith("function:"):
                    func_name = tool_choice[len("function:"):].strip()
                    tool_choice_param = {"type": "function", "name": func_name}
                elif tool_choice == "required":
                    tool_choice_param = "required"
                elif tool_choice == "none":
                    tool_choice_param = "none"
                else:
                    tool_choice_param = "auto"
                response = await self.process_query(query, llm_choice="openai", tool_choice=tool_choice_param)
                print("\n" + str(response))
            except Exception as e:
                print(f"\nError: {str(e)}")


    async def _call_openai_api(self, messages, tools=None, tool_choice="auto"):
        """Helper to call the OpenAI API with the given client, messages, and optional tools and tool_choice."""
        params = {
            "model": "gpt-4.1",
            "input": messages
        }
        if tools is not None:
            params["tools"] = tools
        if tool_choice is not None:
            params["tool_choice"] = tool_choice
        return self.openai.responses.create(**params)


    async def cleanup(self):
        """Clean up resources"""
        print("\n>>>>>Cleaning up resources...")
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
