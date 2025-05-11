from openai import OpenAI
from dotenv import load_dotenv
import json

from openai.types.responses import ResponseOutputItemAddedEvent
load_dotenv()
client = OpenAI()


from enum import Enum


# response.
class StreamingEvent(Enum):
    ResponseCreatedEvent = "ResponseCreatedEvent" # response.created, response=Response
    ResponseInProgressEvent = "ResponseInProgressEvent" # response.in_progress
    ResponseFailedEvent = "ResponseFailedEvent" 
    ResponseCompletedEvent = "ResponseCompletedEvent" # response.completed

    ResponseOutputItemAddedEvent = "ResponseOutputItemAddedEvent" # response.output_item.added item=ResponseFunctionToolCall/ResponseOutputMessage, output_index
    ResponseOutputItemDoneEvent = "ResponseOutputItemDoneEvent" # response.output_item.done 

    ResponseContentPartAddedEvent = "ResponseContentPartAddedEvent" # response.content_part.added, part=ResponseOutputText, output_index
    ResponseContentPartDoneEvent = "ResponseContentPartDoneEvent" # response.content_part.done

    ResponseOutputTextDeltaEvent = "ResponseOutputTextDeltaEvent" # response.output_text.delta. delta, output_index
    ResponseOutputTextDoneEvent = "ResponseOutputTextDoneEvent" # response.output_text.done

    ResponseOutputTextAnnotationAddedEvent = "ResponseOutputTextAnnotationAddedEvent"
    ResponseTextDoneEvent = "ResponseTextDoneEvent"
    ResponseRefusalDeltaEvent = "ResponseRefusalDeltaEvent"
    ResponseRefusalDoneEvent = "ResponseRefusalDoneEvent"
    ResponseFunctionCallArgumentsDeltaEvent = "ResponseFunctionCallArgumentsDeltaEvent" # response.function_call_arguments.delta. delta, output_index
    ResponseFunctionCallArgumentsDoneEvent = "ResponseFunctionCallArgumentsDoneEvent" # response.function_call_arguments.done
    ResponseFileSearchCallInProgressEvent = "ResponseFileSearchCallInProgressEvent"
    ResponseFileSearchCallSearchingEvent = "ResponseFileSearchCallSearchingEvent"
    ResponseFileSearchCallCompletedEvent = "ResponseFileSearchCallCompletedEvent"
    ResponseCodeInterpreterInProgressEvent = "ResponseCodeInterpreterInProgressEvent"
    ResponseCodeInterpreterCallCodeDeltaEvent = "ResponseCodeInterpreterCallCodeDeltaEvent"
    ResponseCodeInterpreterCallCodeDoneEvent = "ResponseCodeInterpreterCallCodeDoneEvent"
    ResponseCodeInterpreterCallIntepretingEvent = "ResponseCodeInterpreterCallIntepretingEvent"
    ResponseCodeInterpreterCallCompletedEvent = "ResponseCodeInterpreterCallCompletedEvent"
    Error = "Error"


tools= [{
            "type": "function",
            "name": "get-alerts",
            "description": "Get weather alerts for a state",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Two-letter state code (e.g. CA, NY)"
                    }
                },
                "required": [
                    "state"
                ],
                "additionalProperties": False
            }
        },
        {
            "type": "function",
            "name": "get-forecast",
            "description": "Get weather forecast for a location",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {
                        "type": "number",
                        "description": "Latitude of the location"
                    },
                    "longitude": {
                        "type": "number",
                        "description": "Longitude of the location"
                    }
                },
                "required": [
                    "latitude",
                    "longitude"
                ],
                "additionalProperties": False
            }
        }
    ]

from pygments import highlight, lexers, formatters

def to_json(obj):
    try:
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump(), indent=2)
        elif hasattr(obj, "__dict__"):
            return json.dumps(vars(obj), indent=2, default=str)
        else:
            return json.dumps(obj, indent=2, default=str)
    except Exception as e:
        return f"<<Unable to convert to JSON: {e}>>"

def print_colored_json(obj):
    json_str = to_json(obj)
    colorful = highlight(json_str, lexers.JsonLexer(), formatters.TerminalFormatter())
    print(colorful)


should_stream=True  

# stream = client.responses.create(
#     model="gpt-4.1",
#     input=[
#         {
#             "role": "user",
#             "content": "what is the weather in london,paris?",
#             # "content": "count to 10",
#         },
#     ],
#     tools=tools,
#     stream= should_stream,
# )
# if should_stream:
#     for event in stream:
#         # if event.type == "response.output_item.added" and hasattr(event.item,"name"):
#         #     print(event.item.name,flush=True,end="") 
#         # if event.type == "response.function_call_arguments.delta":
#         #     print(event.delta,flush=True,end="") 
#         print("="*100)
#         print(event)
#         print_colored_json(event)
#         print(event.type)
# else:
#     print(stream)      
        
# print()




stream = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": "count to 10",
        },
    ],
    tools=tools,
    stream= should_stream,
)


if should_stream:
    for event in stream:
        # if event.type == "response.output_item.added" and hasattr(event.item,"name"):
        #     print(event.item.name,flush=True,end="") 
        # if event.type == "response.function_call_arguments.delta":
        #     print(event.delta,flush=True,end="") 
        print("="*100)
        print(event)
        print_colored_json(event)
        print(event.type)
else:
    print(stream)    
        
print()