from fastapi import FastAPI
from pydantic import BaseModel
from host import Host
import asyncio
from typing import Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow all CORS (development only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients_host = None

# Request model
class QueryRequest(BaseModel):
    query: str
    llm_choice: str = "mock-llm"
    tool_choice: Optional[str|Dict[str, Any]] = None
    parallel_tool_calls: bool = True

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Startup event to initialize MCPClient and connect to server
@app.on_event("startup")
async def startup_event():
    global clients_host
    clients_host = Host()
    # Add as many server scripts as needed here
    # await clients_host.add_client('/home/user1/work/git-repo/quickstart-resources/weather-server-python/weather.py')
    await clients_host.add_client('/home/user1/work/git-repo/quickstart-resources/weather-server-typescript/build/index.js')
    # await clients_host.add_clients_from_config('config.json')

@app.post("/query")
async def handle_query(req: QueryRequest):
    global clients_host
    response = await clients_host.process_query(
        req.query,
        tool_choice=req.tool_choice,
        parallel_tool_calls=req.parallel_tool_calls
    )
    return {
        "response": response
    }

@app.get("/openai-tools")
async def get_tools():
    global clients_host
    # Aggregate all tools from all clients (OpenAI-converted)
    all_tools = {}
    for name, client in clients_host.clients.items():
        all_tools[name] = getattr(client, "openai_tools", None)
    return all_tools

@app.get("/raw-tools")
async def get_raw_tools():
    global clients_host
    # Return client.raw_tools for each client
    all_raw_tools = {}
    for name, client in clients_host.clients.items():
        all_raw_tools[name] = getattr(client, "raw_tools", None)
    return all_raw_tools

@app.get("/metadata")
async def get_metadata():
    global clients_host
    # Return launch metadata for each client
    all_metadata = {}
    for name, client in clients_host.clients.items():
        all_metadata[name] = {
            "command": getattr(client, "command", None),
            "launch_args": getattr(client, "launch_args", None),
            "env": getattr(client, "env", None)
        }
    return all_metadata


@app.on_event("shutdown")
async def shutdown_event():
    global clients_host
    if clients_host is not None:
        await clients_host.cleanup()
