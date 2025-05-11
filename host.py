import asyncio
from typing import Dict, Any, Optional
from client import MCPClient
from openai import OpenAI
import json
import my_logger as mylog
import response_model as respmod
from config_file_parser import ConfigFileParser
import os

logger = mylog.setup_logger("host_logger", mylog.logging.DEBUG, log_to_console=False, log_to_file="host.log")

class Host:
    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.tool_to_client: Dict[str, str] = {}  # tool_name -> client_name
        self.openai = OpenAI()
        self.tools: Dict[str, Any] = {}  # tool_name -> tool spec

    async def add_client(self, server_script_path: str, command: Optional[str]=None, args: Optional[list]=None, env: Optional[dict]=None, server_name: Optional[str]=None):
        """
        Add a client from a script path or with explicit command/args/env (for config file support).
        """
        client = MCPClient()
        # If command/args/env provided, use them for connection (assume MCPClient.connect_to_server supports them)
        if command or args or env:
            await client.connect_to_server(server_script_path, command=command, args=args, env=env)
        else:
            await client.connect_to_server(server_script_path)
        # Use provided server_name or fallback to script filename
        if server_name:
            name = server_name
        else:
            name = os.path.basename(server_script_path)
        self.clients[name] = client
        # Map tools to this client
        for tool in getattr(client, 'openai_tools', []):
            tool_name = tool.get("name")
            if tool_name:
                self.tool_to_client[tool_name] = name
                self.tools[tool_name] = tool

    async def add_clients_from_config(self, config_path: str):
        """
        Add all clients defined in a config JSON file using ConfigFileParser.
        """
        parser = ConfigFileParser(config_path)
        for server_name, server_conf in parser.iter_servers():
            command = server_conf.get("command")
            args = server_conf.get("args", [])
            env = server_conf.get("env", {})
            # For each server, add a client with explicit command/args/env
            # Use the command as the main script path (for legacy compatibility)
            script_path = args[0] if args else command
            await self.add_client(
                script_path,
                command=command,
                args=args,
                env=env,
                server_name=server_name
            )

    async def chat_loop(self):
        print("\nHost Chat Loop Started!")
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
                response = await self.process_query(query, tool_choice=tool_choice_param)
                print("\n" + str(response))
            except Exception as e:
                print(f"\nError: {str(e)}")

    async def process_query(self, query: str, tool_choice=None, parallel_tool_calls: bool = True):
        """Process a query using OpenAI and available tools, routing tool calls to the correct client. Errors from OpenAI API or tool calls are appended as error entries in the flow and returned to the user."""
        flow = []
        openai_query_messages = [{"role": "user", "content": query}]
        need_query_openai: bool = True
        add_tools_to_next_openai_query: bool = True
        answer_text = ""
        overall_tool_use_names: list = []
        error_info = None

        while need_query_openai:
            tools_list = list(self.tools.values())
            try:
                if add_tools_to_next_openai_query:
                    openai_response = await self._call_openai_api(
                        openai_query_messages,
                        tools_list,
                        tool_choice=tool_choice,
                        parallel_tool_calls=parallel_tool_calls
                    )
                    llm_interaction = respmod.LLMCall(llm="gpt-4.1", request={"messages": openai_query_messages, "tools": tools_list, "tool_choice": tool_choice, "parallel_tool_calls": parallel_tool_calls}, response=[item.model_dump() for item in openai_response.output])
                    flow.append(respmod.Interaction(type="llm_api_call", details=llm_interaction.model_dump()))
                    add_tools_to_next_openai_query = any([output_item.type == "function_call" for output_item in openai_response.output])
                    need_query_openai = add_tools_to_next_openai_query
                else:
                    openai_response = await self._call_openai_api(
                        openai_query_messages,
                        tools_list,
                        tool_choice="auto",
                        parallel_tool_calls=parallel_tool_calls
                    )
                    llm_interaction = respmod.LLMCall(llm="gpt-4.1", request={"messages": openai_query_messages, "tools": tools_list, "tool_choice": "auto", "parallel_tool_calls": parallel_tool_calls}, response=[item.model_dump() for item in openai_response.output])
                    flow.append(respmod.Interaction(type="llm_api_call", details=llm_interaction.model_dump()))
            except Exception as e:
                error_info = {"error": str(e)}
                flow.append(respmod.Interaction(type="error", details={"error": str(e), "source": "openai_api"}))
                answer_text = f"OpenAI API error: {e}"
                break

            try:
                # Handle function/tool calls
                if any([output_item.type == "function_call" for output_item in openai_response.output]):
                    # Add the output of function call to the openai query messages
                    openai_query_messages.extend(response_output_item for response_output_item in openai_response.output if response_output_item.type == "function_call")
                    current_tool_use_names, tool_calls_results, tool_errors = await self.process_openai_function_call_response(openai_response, flow)
                    overall_tool_use_names.extend(current_tool_use_names)
                    # Add the tool call results to the openai query messages
                    openai_query_messages.extend([
                        {"type": "function_call_output", "output": tool_call_result, "call_id": call_id}
                        for call_id, tool_call_result in tool_calls_results
                    ])
                    # Append any tool errors to flow
                    for tool_err in tool_errors:
                        flow.append(respmod.Interaction(type="error", details=tool_err))
                    if tool_errors and not error_info:
                        # If any tool error, set answer_text to first error
                        answer_text = f"Tool call error: {tool_errors[0].get('error')}"
                        error_info = tool_errors[0]
                else:
                    # No function call, just return the answer
                    openai_answer_text = await self.process_openai_message_response(openai_response)
                    answer_text = openai_answer_text
            except Exception as e:
                error_info = {"error": str(e)}
                flow.append(respmod.Interaction(type="error", details={"error": str(e), "source": "tool_call_processing"}))
                answer_text = f"Tool call error: {e}"
                break

        response_obj = respmod.QueryResponse(
            names_of_tools_used=overall_tool_use_names,
            flow=flow,
            final_answer=answer_text
        )
        result = response_obj.model_dump()
        if error_info:
            result["error"] = error_info["error"]
        return result


    async def process_openai_function_call_response(self, openai_response, flow):
        """
        Handle OpenAI responses that contain function/tool calls.
        - Extracts the function call
        - Executes the tool
        - Updates the flow
        - Returns overall tool use names and tool call results
        - Returns a list of error dicts for any tool call errors
        """
        overall_tool_use_names = []
        tool_calls_results = []
        tool_errors = []
        for item in openai_response.output:
            mylog.log_debug(logger, f"OpenAI output item: {item}")
            if item.type == "function_call":
                func_name = item.name
                func_args = json.loads(item.arguments)
                mylog.log_event(logger, "OpenAI tool_call", {"tool_name": func_name, "tool_args": func_args})
                tool_result = None
                error_detail = None
                client_name = self.tool_to_client.get(func_name)
                try:
                    if client_name and client_name in self.clients:
                        client = self.clients[client_name]
                        tool_result = await client._execute_tool_by_name_and_args(func_name, func_args)
                    if tool_result is None:
                        tool_result = f"Tool {func_name} not found."
                except Exception as e:
                    error_detail = {"error": str(e), "tool": func_name, "args": func_args}
                    tool_result = {"error": str(e)}
                overall_tool_use_names.append(func_name)
                mylog.log_info(logger, f"OpenAI tool result: {tool_result}")
                tool_use = respmod.ToolCall(tool_name=func_name, tool_args=func_args, tool_response=tool_result)
                flow.append(respmod.Interaction(type="tool_call", details=tool_use.model_dump()))
                tool_calls_results.append((item.call_id, str(tool_result)))
                if error_detail:
                    tool_errors.append(error_detail)
        return overall_tool_use_names, tool_calls_results, tool_errors


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
                        answer_text += content.text + "\n"
        return answer_text

    async def _call_openai_api(self, messages, tools=None, tool_choice="auto", parallel_tool_calls: bool = True):
        """Helper to call the OpenAI API with the given client, messages, and optional tools and tool_choice.
        Logs and handles errors from the OpenAI API call.
        """
        params = {
            "model": "gpt-4.1",
            "input": messages
        }
        if tools is not None:
            params["tools"] = tools
        if tool_choice is not None:
            params["tool_choice"] = tool_choice
        if parallel_tool_calls is not None:
            params["parallel_tool_calls"] = parallel_tool_calls
        mylog.log_event(logger, "OpenAI: request", {"messages": messages, "tools": tools, "tool_choice": tool_choice, "parallel_tool_calls": parallel_tool_calls})
        try:
            response = self.openai.responses.create(**params)
            mylog.log_event(logger, "OpenAI: response", {"response": response})
            return response
        except Exception as e:
            mylog.log_error(logger, f"OpenAI API call failed: {e}", exc_info=True)
            # Optionally, you can re-raise or return a special error response object
            raise
    async def cleanup(self):
        for client in self.clients.values():
            await client.cleanup()
