import os
import google.generativeai as genai
from typing import Optional


def call_llm_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
) -> str:
    """
    Direct Gemini LLM call aligned with LLMClient.generate_content().
    Uses proxy endpoint + unified API key.
    Returns plain text.
    """

    # Use the SAME key resolution logic as LLMClient
    api_key = 'sk-aAnti9pqSb1F28qI5C7uuxwSaoybwuUHnx16vriFw3w8XjcK'

    if not api_key:
        raise RuntimeError("No PROXY_API_KEY or GEMINI_API_KEY found")

    # Configure Gemini EXACTLY like LLMClient
    genai.configure(
        api_key=api_key,
        transport="rest",
        client_options={
            "api_endpoint": "https://api.openai-proxy.org/google"
        }
    )

    model = genai.GenerativeModel(
        model_name=model_name or "gemini-3-pro-preview",
        system_instruction=system_prompt
    )

    generation_config = {}
    if temperature is not None:
        generation_config["temperature"] = temperature
    if top_p is not None:
        generation_config["top_p"] = top_p

    response = model.generate_content(
        prompt,
        generation_config=(
            genai.GenerationConfig(**generation_config)
            if generation_config else None
        )
    )

    return (getattr(response, "text", "") or "").strip()
