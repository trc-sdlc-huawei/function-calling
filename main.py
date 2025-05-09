from fastapi import FastAPI
from pydantic import BaseModel
from client import MCPClient
import asyncio

app = FastAPI()

mcp_client = None

# Request model
class QueryRequest(BaseModel):
    query: str
    llm_choice: str = "mock-llm"

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Startup event to initialize MCPClient and connect to server
@app.on_event("startup")
async def startup_event():
    global mcp_client
    mcp_client = MCPClient()
    # TODO: Replace 'path_to_server_script.py' with your actual server script path
    try:
        await mcp_client.connect_to_server('/home/ubuntu/work/git-repo/quickstart-resources/weather-server-python/weather.py')
        # await client.chat_loop()
    finally:
        pass
        # await mcp_client.cleanup()

@app.post("/query")
async def handle_query(req: QueryRequest):
    global mcp_client
    response = await mcp_client.process_query(req.query, llm_choice=req.llm_choice)
    return {
        "llm_choice": req.llm_choice,
        "query": req.query,
        "response": response
    }

@app.get("/tools")
async def get_tools():
    global mcp_client
    response = await mcp_client.session.list_tools()
    return response.tools


@app.on_event("shutdown")
async def shutdown_event():
    global mcp_client
    if mcp_client is not None:
        await mcp_client.cleanup()

async def connect():
    client = MCPClient()
    try:
        await client.connect_to_server('/home/ubuntu/work/git-repo/quickstart-resources/weather-server-python/weather.py')
        # await client.chat_loop()
    finally:
        await client.cleanup()


# if __name__ == "__main__":
#     asyncio.run(main())
