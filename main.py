from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    prompt: str

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    # Return mock response
    return {
        "response": f"Mock response to: '{request.prompt}'"
    }



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
