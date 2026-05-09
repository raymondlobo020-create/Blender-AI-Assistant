from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI()


storage = {
    "current_command": None,  
    "latest_result": None     
}


@app.get("/get_command")
async def get_command():
    """Blender calls this every 0.1s to see if there is work to do."""
    if storage["current_command"]: 
        cmd = storage["current_command"]
        storage["current_command"] = None
        print(f"[SERVER] Sending command to Blender: {cmd[:50]}...")
        return {"code": cmd}
    return {"code": None}

@app.post("/post_result")
async def post_result(request: Request):
    """Blender calls this after it finishes running the code."""
    data = await request.json()
    storage["latest_result"] = data
    print(f"[SERVER] Received result from Blender: {data}")
    return {"status": "acknowledged"}


@app.post("/internal/add_task")
async def add_task(request: Request):
    """The Agent calls this to 'drop off' new Python code."""
    data = await request.json()
    storage["current_command"] = data.get("code")
    storage["latest_result"] = None 
    print(f"[SERVER] Agent added new task.")
    return {"status": "queued"}

@app.get("/internal/get_result")
async def get_result():
    """The Agent calls this to see if Blender has finished the job."""
    if storage["latest_result"]:
        return storage["latest_result"]
    return {"status": "pending", "response": None}

if __name__ == "__main__":
    # server port is 8000 btw
    uvicorn.run(app, host="0.0.0.0", port=8000)