import os
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from core.conversation_manager import ConversationManager

app = FastAPI(title="Naheed Chat API")

# Initialize the conversation manager once for the whole app
conversation_manager = ConversationManager()

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ClearRequest(BaseModel):
    session_id: str

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not req.session_id or not req.message:
        raise HTTPException(status_code=400, detail="Missing session_id or message")
    
    try:
        response_text, debug_data = conversation_manager.process_message_with_debug(req.message, req.session_id)
        return {
            "response": response_text,
            "debug": debug_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/clear")
async def clear_endpoint(req: ClearRequest):
    if not req.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    try:
        conversation_manager.state_manager.clear_state(req.session_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    try:
        os.makedirs("static/uploads", exist_ok=True)
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join("static", "uploads", unique_filename)
        
        with open(file_path, "wb") as f:
            f.write(await file.read())
            
        return {"url": f"/static/uploads/{unique_filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to upload file")

@app.get("/api/version")
async def get_version():
    return {"version": "1.0.0", "name": "Naheed Chat API"}

# Mount the static directory to serve the frontend (HTML, CSS, JS)
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
