import google.generativeai as genai
from typing import Optional, Dict, Tuple

# =========================================================
# Global Gemini initialization (RUN ONCE)
# =========================================================
_API_KEY = "sk-XXXX"

genai.configure(
    api_key=_API_KEY,
    transport="rest",
    client_options={
        "api_endpoint": "https://api.openai-proxy.org/google"
    }
)

# =========================================================
# Model cache (avoid re-init every call)
# key = (model_name, system_prompt)
# =========================================================
_MODEL_CACHE: Dict[Tuple[str, Optional[str]], genai.GenerativeModel] = {}


def _get_model(
    model_name: str,
    system_prompt: Optional[str]
) -> genai.GenerativeModel:
    key = (model_name, system_prompt)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt
        )
    return _MODEL_CACHE[key]


# =========================================================
# Optimized LLM call (drop-in replacement)
# =========================================================
def call_llm_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
) -> str:
    """
    Optimized Gemini LLM call.
    - No repeated configure()
    - Model instance cached
    - Lower latency
    - Same output behavior
    """

    model = _get_model(
        model_name or "gemini-3-pro-preview",
        system_prompt
    )

    generation_config = genai.GenerationConfig(
        temperature=temperature if temperature is not None else 0.7,
        top_p=top_p if top_p is not None else 0.95,
        response_mime_type="text/plain"
    )

    response = model.generate_content(
        prompt,
        generation_config=generation_config
    )

    return (getattr(response, "text", "") or "").strip()
