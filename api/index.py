from fastapi import FastAPI
from pydantic import BaseModel
from query import ask

app = FastAPI(title="80,000 Hours AI API")

class ChatRequest(BaseModel):
    message: str

import re

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not request.message or not request.message.strip():
        return {"response": ""}
    
    import traceback
    try:
        result = ask(request.message, show_context=False)
        response = result["answer"]
        citations = result.get("citations", [])
    except Exception as e:
        error_msg = f"Exception: {str(e)}\n\nTraceback: {traceback.format_exc()}"
        return {"response": error_msg, "citations": []}
    
    # Replace [1], [2] with markdown links [1](citation:1)
    if citations:
        for cit in citations:
            cid = cit.get("citation_id")
            if cid:
                # Use regex to replace exactly [1], avoiding things like [10] when cid=1
                response = re.sub(rf'\[{cid}\]', f'[{cid}](citation:{cid})', response)
            
    return {"response": response, "citations": citations}
