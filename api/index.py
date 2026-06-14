from fastapi import FastAPI
from pydantic import BaseModel
from query import ask

app = FastAPI(title="80,000 Hours AI API")

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        return {"response": ""}
    
    result = ask(request.message, show_context=False)
    
    response = result["answer"]
    
    if result["citations"]:
        response += "\n\n---\n\n**Citations:**\n\n"
        for i, citation in enumerate(result["citations"], 1):
            response += f"**[{i}]** [{citation['title']}]({citation['url']})\n\n"
            
    return {"response": response}
