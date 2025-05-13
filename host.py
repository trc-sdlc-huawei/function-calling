import asyncio
from typing import Dict, Any, Optional

from openai.types.responses import ResponseFunctionToolCall,Response
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



    async def process_query_stream_function_calling(self, query: str, tool_choice=None, parallel_tool_calls: bool = True):
        """
        Stream OpenAI response events as they arrive, and accumulate function call deltas for function calling.
        Yields both raw events and final_tool_call objects as SSE.
        """
        import json
        # accumulated stuff
        flow = []
        openai_query_messages = [{"role": "user", "content": query}]
        need_query_openai: bool = True
        answer_text = ""
        overall_tool_use_names: list = []
        error_info = None
        all_servers_tools_list = list(self.tools.values())

        
        while need_query_openai:   
            final_tool_calls:Dict[int,ResponseFunctionToolCall] = {}
            final_openai_response: Optional[Response] = None
            async for event in self._call_openai_api_stream(
                messages=openai_query_messages,
                tools=all_servers_tools_list,
                tool_choice=tool_choice,
                parallel_tool_calls=parallel_tool_calls
            ):
                try:
                    # Always yield the raw event as well
                    import json
                    yield f"data: {json.dumps(self._serialize_event(event), default=str)}\n\n"
                    if event.type == 'response.output_item.added' and event.item.type == "function_call":
                        # ResponseFunctionToolCall
                        final_tool_calls[event.output_index] = event.item;      
                    elif event.type == "response.function_call_arguments.delta":
                        index = event.output_index
                        if final_tool_calls[index]:
                            final_tool_calls[index].arguments += event.delta
                    elif event.type == "response.completed":
                        final_openai_response = event.response
                except Exception as e:
                    mylog.log_error(logger, f"Error processing OpenAI event: {e}", exc_info=True)
                    yield f"event: error\ndata: {str(e)}\n\n"    
            # we done streaming llm response
            mylog.log_info(logger, final_tool_calls)
            mylog.log_event(logger, "OpenAI: response (stream)", {"response": final_openai_response})
            llm_interaction = respmod.LLMCall(llm="gpt-4.1", request={"messages": openai_query_messages, "tools": all_servers_tools_list, "tool_choice": tool_choice, "parallel_tool_calls": parallel_tool_calls}, response=[item.model_dump() for item in final_openai_response.output])
            flow.append(respmod.Interaction(type="llm_api_call", details=llm_interaction.model_dump()))
            try:
                if len(final_tool_calls) > 0:
                    # add the tools needed to the openai query messages
                    openai_query_messages.extend(tool_call for tool_call in final_tool_calls.values())
                    current_tool_use_names, tool_calls_results, tool_errors = await self.process_openai_function_call_response(final_tool_calls.values(), flow)
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
                    need_query_openai = False
                    answer_text = self.process_openai_message_response(final_openai_response)        
            except Exception as e:
                    error_info = {"error": str(e)}
                    flow.append(respmod.Interaction(type="error", details={"error": str(e), "source": "tool_call_processing"}))
                    answer_text = f"Tool call error: {e}"
                    mylog.log_error(logger, f"Error processing OpenAI function call response: {e}", exc_info=True)
                    break

        response_obj = respmod.QueryResponse(
                names_of_tools_used=overall_tool_use_names,
                flow=flow,
                final_answer=answer_text
            )
        result = response_obj.model_dump()
        result["type"] = "full_flow"
        if error_info:
            result["error"] = error_info["error"]
        yield f"data: {json.dumps(result)}\n\n"


                

    async def _call_openai_api_stream(self, messages, tools=None, tool_choice="auto", parallel_tool_calls: bool = True):
        """
        Helper to call OpenAI API with stream=True. Yields raw events (as text/event-stream lines).
        """
        params = {
            "model": "gpt-4.1",
            "input": messages,
            "stream": True
        }
        if tools is not None:
            params["tools"] = tools
        if tool_choice is not None:
            params["tool_choice"] = tool_choice
        if parallel_tool_calls is not None:
            params["parallel_tool_calls"] = parallel_tool_calls
        mylog.log_event(logger, "OpenAI: request (stream)", {"messages": messages, "tools": tools, "tool_choice": tool_choice, "parallel_tool_calls": parallel_tool_calls, "stream": True})
        
        stream = self.openai.responses.create(**params)
        for event in stream:
            # The event is a dict with 'type' and 'response' or other keys. Serialize to JSON and yield as SSE.
            yield event  

    def _serialize_event(self, event):
            # Try model_dump, dict, or __dict__, else fallback to str
            if hasattr(event, "model_dump"):
                return event.model_dump()
            elif hasattr(event, "dict"):
                return event.dict()
            elif hasattr(event, "__dict__"):
                return event.__dict__
            else:
                return str(event)        

    async def add_client_stdio(self, command: Optional[str]=None, args: Optional[list]=None, env: Optional[dict]=None, server_name: Optional[str]=None):
        """
        Add a client from a script path or with explicit command/args/env (for config file support).
        """
        client = MCPClient()
        # If command/args/env provided, use them for connection (assume MCPClient.connect_to_server supports them)
        await client.connect_to_server_stdio(command=command, args=args, env=env)

        # Use provided server_name or fallback to script filename
        name = server_name
        self.clients[name] = client
        # Map tools to this client
        for tool in getattr(client, 'openai_tools', []):
            tool_name = tool.get("name")
            if tool_name:
                self.tool_to_client[tool_name] = name
                self.tools[tool_name] = tool


    async def add_client_streamablehttp(self, command: Optional[str]=None, args: Optional[list]=None, env: Optional[dict]=None, server_name: Optional[str]=None):
        """
        Add a client from a script path or with explicit command/args/env (for config file support).
        """
        client = MCPClient()
        await client.connect_to_server_streamablehttp(command=command, args=args, env=env)
        # # Use provided server_name or fallback to script filename
        name = server_name
        self.clients[name] = client
        # Map tools to this client
        for tool in getattr(client, 'openai_tools', []):
            tool_name = tool.get("name")
            if tool_name:
                self.tool_to_client[tool_name] = name
                self.tools[tool_name] = tool
          

    async def add_stdio_clients_from_config(self, config_path: str):
        """
        Add all clients defined in a config JSON file using ConfigFileParser.
        """
        parser = ConfigFileParser(config_path)
        for server_name, server_conf in parser.iter_servers():
            command = server_conf.get("command")
            args = server_conf.get("args", [])
            env = server_conf.get("env", {})
            # For each server, add a client with explicit command/args/env
            await self.add_client_stdio(
                command=command,
                args=args,
                env=env,
                server_name=server_name
            )


    async def process_query(self, query: str, tool_choice=None, parallel_tool_calls: bool = True):
        """Process a query using OpenAI and available tools, routing tool calls to the correct client. Errors from OpenAI API or tool calls are appended as error entries in the flow and returned to the user."""
        flow = []
        openai_query_messages = [{"role": "user", "content": query}]
        need_query_openai: bool = True
        answer_text = ""
        overall_tool_use_names: list = []
        error_info = None
        tools_list = list(self.tools.values())

        while need_query_openai:

            try:
                openai_response = await self._call_openai_api(
                    openai_query_messages,
                    tools_list,
                    tool_choice=tool_choice,
                    parallel_tool_calls=parallel_tool_calls
                )
                llm_interaction = respmod.LLMCall(llm="gpt-4.1", request={"messages": openai_query_messages, "tools": tools_list, "tool_choice": tool_choice, "parallel_tool_calls": parallel_tool_calls}, response=[item.model_dump() for item in openai_response.output])
                flow.append(respmod.Interaction(type="llm_api_call", details=llm_interaction.model_dump()))
                need_query_openai = any([output_item.type == "function_call" for output_item in openai_response.output])
            except Exception as e:
                error_info = {"error": str(e)}
                flow.append(respmod.Interaction(type="error", details={"error": str(e), "source": "openai_api"}))
                answer_text = f"OpenAI API error: {e}"
                break

            try:
                # Handle function/tool calls
                if any([output_item.type == "function_call" for output_item in openai_response.output]):
                    # add the tools needed to the openai query messages
                    openai_query_messages.extend(response_output_item for response_output_item in openai_response.output if response_output_item.type == "function_call")
                    current_tool_use_names, tool_calls_results, tool_errors = await self.process_openai_function_call_response(openai_response.output, flow)
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
                    answer_text = self.process_openai_message_response(openai_response)
            except Exception as e:
                error_info = {"error": str(e)}
                flow.append(respmod.Interaction(type="error", details={"error": str(e), "source": "tool_call_processing"}))
                answer_text = f"Tool call error: {e}"
                mylog.log_error(logger, f"Error processing OpenAI function call response: {e}", exc_info=True)
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


    async def process_openai_function_call_response(self, function_calls:list[ResponseFunctionToolCall], flow:list[respmod.Interaction]):
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
        for function_call in function_calls:
            mylog.log_debug(logger, f"OpenAI output item: {function_call}")
            func_name = function_call.name
            func_args = json.loads(function_call.arguments)
            mylog.log_event(logger, "OpenAI tool_call", {"tool_name": func_name, "tool_args": func_args})
            tool_result = None
            error_detail = None
            try:
                tool_result = await self._run_tool(func_name, func_args)
            except Exception as e:
                error_detail = {"error": str(e), "tool": func_name, "args": func_args}
                tool_result = {"error": str(e)}
                mylog.log_event(logger, "OpenAI tool_error", error_detail)
            overall_tool_use_names.append(func_name)
            mylog.log_info(logger, f"OpenAI tool result: {tool_result}")
            tool_use = respmod.ToolCall(tool_name=func_name, tool_args=func_args, tool_response=tool_result)
            flow.append(respmod.Interaction(type="tool_call", details=tool_use.model_dump()))
            tool_calls_results.append((function_call.call_id, str(tool_result)))
            if error_detail:
                tool_errors.append(error_detail)
                mylog.log_event(logger, "OpenAI tool_error", error_detail)
        return overall_tool_use_names, tool_calls_results, tool_errors

    
    
    
    async def _run_tool(self, name, args):
        client_name = self.tool_to_client.get(name)
        if not client_name or client_name not in self.clients:
            return f"Tool '{name}' not registered"
        client = self.clients[client_name]
        return await client._execute_tool_by_name_and_args(name, args)



    def process_openai_message_response(self, openai_response):
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
