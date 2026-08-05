import httpx


class ProviderError(Exception):
    pass


async def _call_anthropic(api_key: str, model: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return "".join(
            block["text"] for block in data["content"] if block["type"] == "text"
        )


async def _call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _call_gemini(api_key: str, model: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_ollama(base_url: str, model: str, prompt: str) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        data = response.json()
        return data["response"]


async def get_model_response(
    provider: str, model: str, prompt: str, api_key: str | None, base_url: str | None
) -> str:
    if provider == "anthropic":
        if not api_key:
            raise ProviderError("missing api key for anthropic")
        return await _call_anthropic(api_key, model, prompt)
    if provider == "openai":
        if not api_key:
            raise ProviderError("missing api key for openai")
        return await _call_openai_compatible(
            "https://api.openai.com/v1/chat/completions", api_key, model, prompt
        )
    if provider == "gemini":
        if not api_key:
            raise ProviderError("missing api key for gemini")
        return await _call_gemini(api_key, model, prompt)
    if provider == "groq":
        if not api_key:
            raise ProviderError("missing api key for groq")
        return await _call_openai_compatible(
            "https://api.groq.com/openai/v1/chat/completions", api_key, model, prompt
        )
    if provider == "ollama":
        return await _call_ollama(base_url or "http://localhost:11434", model, prompt)
    raise ProviderError(f"unknown provider: {provider}")
