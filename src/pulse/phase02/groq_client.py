"""Groq API client wrapper (DEC-011).

Thin adapter around the openai-compatible Groq REST API.
Keeps all HTTP concerns here so callers (themer, drafter) stay clean.

Auth: GROQ_API_KEY — read from environment variable or .env file in the
project root. Never read from config files or committed to the repo.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def _load_dotenv() -> None:
    """
    Load key=value pairs from .env (project root) into os.environ.

    Only sets variables that are not already set — existing env vars win.
    Skips lines that are blank or start with #.
    Uses no third-party libraries.
    """
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.is_file():
        return
    with env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Strip optional surrounding quotes.
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


def _parse_retry_after(error_body: str) -> float | None:
    """Extract seconds to wait from a Groq rate-limit error message."""
    m = re.search(r"try again in ([0-9.]+)s", error_body)
    if m:
        return float(m.group(1))
    return None


class GroqAPIError(Exception):
    """Raised when the Groq API returns an error or unexpected response."""


class GroqRateLimitError(GroqAPIError):
    """Raised on 429 rate-limit responses. Carries retry_after seconds."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class GroqClient:
    """Minimal OpenAI-compatible client pointed at Groq."""

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str | None = None) -> None:
        _load_dotenv()
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        if not self._api_key:
            raise GroqAPIError(
                "GROQ_API_KEY is not set. "
                "Add it to .env (copy .env.example) or export it as an environment variable."
            )

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        response_format: dict[str, str] | None = None,
        max_tpm_retries: int = 3,
        tpm_backoff_extra: float = 2.0,
    ) -> str:
        """
        Call /chat/completions and return the assistant message content.

        On 429 rate-limit responses, waits the retry-after window (plus
        *tpm_backoff_extra* seconds of padding) and retries up to
        *max_tpm_retries* times before raising GroqRateLimitError.

        Raises GroqAPIError on other HTTP errors or unexpected response shape.
        """
        import urllib.error
        import urllib.request

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "weekly-review-pulse/0.1",
        }

        for attempt in range(max_tpm_retries + 1):
            req = urllib.request.Request(
                f"{self.BASE_URL}/chat/completions",
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    raw = resp.read().decode("utf-8")
                break  # success — exit retry loop
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < max_tpm_retries:
                    wait = (_parse_retry_after(detail) or 10.0) + tpm_backoff_extra
                    log.warning(
                        "TPM rate limit hit (attempt %d/%d). Waiting %.1fs…",
                        attempt + 1, max_tpm_retries, wait,
                    )
                    time.sleep(wait)
                    continue
                if exc.code == 429:
                    retry_after = _parse_retry_after(detail)
                    raise GroqRateLimitError(
                        f"Groq HTTP {exc.code}: {detail[:400]}", retry_after
                    ) from exc
                raise GroqAPIError(
                    f"Groq HTTP {exc.code}: {detail[:400]}"
                ) from exc
            except OSError as exc:
                raise GroqAPIError(f"Network error calling Groq: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GroqAPIError(f"Non-JSON response from Groq: {raw[:200]}") from exc

        try:
            content: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise GroqAPIError(
                f"Unexpected Groq response shape: {str(data)[:200]}"
            ) from exc

        return content
