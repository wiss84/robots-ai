"""
Dynamic model configuration system for Gemini API rate limiting.
This module provides a centralized way to get the current model configuration
that all agents should use.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
import os
from rate_limiter import rate_limiter

def get_current_gemini_model(temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    """
    Get the current Gemini model instance based on rate limiting status.
    
    Args:
        temperature: Temperature setting for the model
        
    Returns:
        ChatGoogleGenerativeAI instance configured with the current model
    """
    current_model = rate_limiter.current_model
    
    return ChatGoogleGenerativeAI(
        model=current_model,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=temperature,
    )

def get_current_model_name() -> str:
    """Get the name of the currently active model."""
    return rate_limiter.current_model

def is_model_switched() -> bool:
    """Check if we're not using the primary model (indicating a switch occurred)."""
    return rate_limiter.current_model != rate_limiter.model_priority[0]