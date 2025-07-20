"""
Backend summarization endpoint
Uses gemini-2.0-flash to summarize conversation history
"""

from fastapi import APIRouter, Body, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/summarize", tags=["summarize"])
security = HTTPBearer()

# Initialize summarization LLM
summarize_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,
)

class SummarizeRequest(BaseModel):
    messages: List[dict]

class SummarizeResponse(BaseModel):
    summary: str

@router.post("/", response_model=SummarizeResponse)
async def summarize_conversation(
    request: SummarizeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Summarize conversation history using gemini-2.0-flash
    """
    try:
        # Format messages for summarization
        messages_text = ""
        for msg in request.messages:
            role = msg['role']
            content = msg['content']
            messages_text += f"{role.upper()}: {content}\n\n"
        
        # Create summarization prompt
        summary_prompt = f"""
        Summarize the following conversation history in a concise way that would help 
        an AI agent understand the context and continue the conversation naturally.
        
        Focus on:
        - Key topics discussed
        - Important decisions or conclusions
        - Current status or pending items
        - User preferences or requirements mentioned
        
        Keep the summary concise but informative.
        
        Conversation History:
        {messages_text}
        
        Provide a clear, concise summary that captures the essential context:
        """
        
        # Get summary from LLM
        summary_response = summarize_llm.invoke(summary_prompt)
        summary = summary_response.content
        
        return SummarizeResponse(summary=summary)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}") 