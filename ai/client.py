import os
from typing import Optional
from openai import OpenAI
from config import OPENROUTER_API_KEY

def get_ai_client() -> Optional[OpenAI]:
    api_key = OPENROUTER_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        return OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1" if OPENROUTER_API_KEY else None,
        )
    except Exception:
        return None
