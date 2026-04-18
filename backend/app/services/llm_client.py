# llm_app/llm_client.py

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import os
from openai import OpenAI


# DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_MODEL = "gpt-4.1-mini"


def get_openai_client() -> OpenAI:
    """
    Create and return OpenAI client using API key from environment.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment")
    return OpenAI(api_key=api_key)


def extract_text(resp) -> str:
    """
    Robustly extract text output from OpenAI Responses API response.
    """
    text = (getattr(resp, "output_text", None) or "").strip()
    if text:
        return text

    chunks = []
    for item in getattr(resp, "output", []) or []:
        for c in getattr(item, "content", []) or []:
            t = getattr(c, "text", None)
            if t:
                chunks.append(t)

    return "".join(chunks).strip()


def run_llm(
    messages,
    max_new_tokens: int = 16,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    client: OpenAI | None = None,
) -> str:
    """
    Low-level OpenAI call.

    messages: list of dicts, e.g.
      [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]

    Returns raw text output (not JSON-parsed).
    """
    # Responses API constraint: max_output_tokens must be >= 16
    max_out = int(max_new_tokens) if max_new_tokens is not None else 16
    if max_out < 16:
        max_out = 16

    if client is None:
        client = get_openai_client()

    resp = client.responses.create(
        model=model,
        input=messages,
        max_output_tokens=max_out,
        temperature=temperature,
        store=False,
    )

    return extract_text(resp)


def llm_call(messages, max_new_tokens: int = 16, **kwargs) -> str:
    """
    Project-wide canonical LLM callable.

    Keeps a stable signature expected by parsers:
      llm_call(messages, max_new_tokens=N) -> str

    You can still pass optional kwargs (model, temperature, client) when needed.
    """
    return run_llm(messages, max_new_tokens=max_new_tokens, **kwargs)
