import os
import threading
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("run:app", host="0.0.0.0", port=port, reload=False)

import g4f
from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
def chat_with_ai(request: ChatRequest):
    try:
        response = g4f.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": request.prompt}],
        )
        return {"status": "success", "reply": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}
