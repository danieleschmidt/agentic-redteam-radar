"""
Endpoint adapter — thin wrapper around HTTP calls to LLM endpoints.

Supported endpoint styles:
  - openai:   OpenAI-compatible (chat/completions)
  - ollama:   Ollama local (api/chat)
  - raw:      POST the payload as {"message": <text>} and read {"response": ...}

Usage:
    endpoint = Endpoint("http://localhost:11434", style="ollama", model="llama3")
    response_text = endpoint.query("Hello!")
"""

import json
import requests
from typing import Optional


class EndpointError(Exception):
    pass


class Endpoint:
    def __init__(
        self,
        url: str,
        style: str = "openai",  # openai | ollama | raw
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        system_prompt: Optional[str] = None,
        timeout: int = 30,
        extra_headers: Optional[dict] = None,
    ):
        self.url = url.rstrip("/")
        self.style = style
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self.session = requests.Session()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        h.update(self.extra_headers)
        return h

    def query(self, text: str) -> str:
        """Send text to the endpoint and return the response string."""
        try:
            if self.style == "openai":
                return self._query_openai(text)
            elif self.style == "ollama":
                return self._query_ollama(text)
            elif self.style == "raw":
                return self._query_raw(text)
            else:
                raise EndpointError(f"Unknown endpoint style: {self.style}")
        except requests.exceptions.ConnectionError as e:
            raise EndpointError(f"Connection failed to {self.url}: {e}") from e
        except requests.exceptions.Timeout:
            raise EndpointError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise EndpointError(f"HTTP error: {e}") from e

    def _query_openai(self, text: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": text})

        payload = {"model": self.model, "messages": messages, "max_tokens": 512}
        url = f"{self.url}/v1/chat/completions"
        resp = self.session.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise EndpointError(f"Unexpected OpenAI response format: {data}") from e

    def _query_ollama(self, text: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": text})

        payload = {"model": self.model, "messages": messages, "stream": False}
        url = f"{self.url}/api/chat"
        resp = self.session.post(url, json=payload, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["message"]["content"]
        except KeyError as e:
            raise EndpointError(f"Unexpected Ollama response format: {data}") from e

    def _query_raw(self, text: str) -> str:
        payload = {"message": text}
        if self.system_prompt:
            payload["system"] = self.system_prompt
        resp = self.session.post(self.url, json=payload, headers=self._headers(), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        # Try common response field names
        for key in ("response", "reply", "content", "text", "output", "message"):
            if key in data:
                return str(data[key])
        # Fall back to dumping the whole response
        return json.dumps(data)
