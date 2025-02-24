import os
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from typing import AsyncGenerator, List, Optional
from fastapi.responses import StreamingResponse,JSONResponse

from file_processing import upload_files

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatbot-react-teal.vercel.app"],
    # allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq client
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Request model to store conversation history
class ChatRequest(BaseModel):
    messages: List[dict] = []  # Chat history
    model: Optional[str] = "llama-3.3-70b-versatile"  # Model selection

def stream_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    try:
        if not request.messages:
            yield "Error: No messages provided."
            return

        stream = client.chat.completions.create(
            messages=request.messages,
            model=request.model,
            temperature=0.5,
            max_completion_tokens=1024,
            top_p=1,
            stop=None,
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content is None:
                content = ""
            yield content
    except Exception as e:
        yield f"Error: {str(e)}"

@app.post("/chat/")
def chat(request: ChatRequest):
    return StreamingResponse(stream_response(request), media_type="text/plain")


@app.post("/upload/")
async def upload(files: list[UploadFile] = File(...)):
    try:
        if not files:
            return JSONResponse(content={"error": "No files received"}, status_code=400)

        result = await upload_files(files)  # ✅ Call the function from file_processing.py
        return JSONResponse(content=result)  # ✅ Directly return JSONResponse
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
@app.get("/")
def root():
    return {"message": "FastAPI Groq API is running!"}
