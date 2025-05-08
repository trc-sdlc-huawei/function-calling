from fastapi import FastAPI
from pydantic import BaseModel
from client import MCPClient
import asyncio

app = FastAPI()


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
    # global mcp_client
    mcp_client = MCPClient()
    # TODO: Replace 'path_to_server_script.py' with your actual server script path
    try:
        await mcp_client.connect_to_server(r'C:\\Users\\user1\\work\\git-repo\\quickstart-resources\\weather-server-python\\weather.py')
        # await client.chat_loop()
    finally:
        await mcp_client.cleanup()

# Query endpoint
# @app.post("/query")
# async def handle_query(req: QueryRequest):
#     # global mcp_client
#     # if mcp_client is None:
#     #     return {"error": "MCPClient not initialized"}
#     # response = await mcp_client.process_query(req.query, llm_choice=req.llm_choice)
#     response = "Hello, World!"
#     return {
#         "llm_choice": req.llm_choice,
#         "query": req.query,
#         "response": response
#     }

async def connect():
    client = MCPClient()
    try:
        await client.connect_to_server(r'C:\\Users\\user1\\work\\git-repo\\quickstart-resources\\weather-server-python\\weather.py')
        # await client.chat_loop()
    finally:
        await client.cleanup()


# if __name__ == "__main__":
#     asyncio.run(main())
