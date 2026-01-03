import httpx
import json
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()


class LLMClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def generate(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate text using the LLM"""
        # Try OpenAI-compatible endpoint first (works with llama-server)
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except (httpx.HTTPStatusError, KeyError):
                # Try Ollama-style endpoint as fallback
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                }
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")

    async def generate_json(self, prompt: str, max_tokens: int = 2000) -> Optional[Dict[str, Any]]:
        """Generate JSON response from LLM"""
        full_prompt = f"{prompt}\n\nRespond ONLY with valid JSON, no other text."

        response = await self.generate(full_prompt, max_tokens)

        # Try to extract JSON from response
        try:
            # Find JSON in response (may have markdown code blocks)
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Try to find any JSON-like content
            import re
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            return None

    async def health_check(self) -> bool:
        """Check if LLM is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try health endpoint
                response = await client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    return True

                # Try models endpoint
                response = await client.get(f"{self.base_url}/v1/models")
                return response.status_code == 200
        except Exception:
            return False


def get_llm_client() -> LLMClient:
    return LLMClient()
