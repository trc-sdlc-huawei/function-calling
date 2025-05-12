from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import random
import json

app = FastAPI()

# ------------------ Mock External API ------------------

async def mock_number_api():
    numbers = [random.randint(1, 9) for _ in range(9)] + [1]  # last is 0 or 1
    for number in numbers:
        await asyncio.sleep(0.2)
        yield number

# ------------------ Logic: Call API and Stream ------------------

async def stream_numbers():
    attempt = 0
    while True:
        attempt += 1
        yield f"data: Starting API call #{attempt}\n\n"
        last_number = None

         # here yield and update global vars   
        async for num in mock_number_api():
            yield f"data: {num}\n\n"
            last_number = num
        # take action based on the global var update
        if last_number == 0:
            yield f"data: Done.\n\n"
            # break
            break  # stop loop
        else:
            yield f"data: Last number was 1 — calling API again...\n\n"
            await asyncio.sleep(0.5)

# ------------------ FastAPI Endpoint ------------------

@app.get("/numbers")
async def get_numbers():
    return StreamingResponse(stream_numbers(), media_type="text/event-stream")
