"""HTTP client for the MCP server (Phase 3 + 4).

Thin adapter that calls the deployed MCP server at MCP_SERVER_URL.
All requests are fire-and-check: we inspect the returned status field
and raise McpError on any non-success outcome.

URL and target doc/email config come from environment variables (.env).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# .env loading (same pattern as groq_client)
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[3] / ".env"
    if not env_path.is_file():
        return
    import os
    with env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            if key:
                __import__("os").environ[key] = value


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------

class McpError(Exception):
    """Raised when the MCP server returns an error or is unreachable."""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class McpClient:
    """
    Minimal HTTP client for the deployed MCP server.

    Reads MCP_SERVER_URL from the environment (or .env).
    Supports automatic retries with backoff on transient 5xx errors.
    """

    DEFAULT_URL = "https://saksham-mcp-server-production-6213.up.railway.app"

    def __init__(self, base_url: str | None = None) -> None:
        import os
        _load_dotenv()
        self._base_url = (
            base_url
            or os.environ.get("MCP_SERVER_URL", self.DEFAULT_URL)
        ).rstrip("/")

    def _post(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ) -> dict[str, Any]:
        """
        POST JSON to *path* on the MCP server.

        Retries up to *max_retries* times on transient 5xx errors with
        exponential backoff. Raises McpError on persistent failure or 4xx.
        """
        url = f"{self._base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "weekly-review-pulse/0.1",
        }

        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read().decode("utf-8")
                    return json.loads(raw)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code >= 500 and attempt < max_retries:
                    wait = backoff_base ** (attempt + 1)
                    log.warning(
                        "MCP server %s error (attempt %d/%d). Retrying in %.1fs…",
                        exc.code, attempt + 1, max_retries, wait,
                    )
                    time.sleep(wait)
                    last_exc = exc
                    continue
                raise McpError(
                    f"MCP server HTTP {exc.code} at {path}: {detail[:300]}"
                ) from exc
            except (urllib.error.URLError, OSError) as exc:
                if attempt < max_retries:
                    wait = backoff_base ** (attempt + 1)
                    log.warning(
                        "MCP network error (attempt %d/%d). Retrying in %.1fs: %s",
                        attempt + 1, max_retries, wait, exc,
                    )
                    time.sleep(wait)
                    last_exc = exc
                    continue
                raise McpError(f"Network error calling MCP server: {exc}") from exc

        raise McpError(f"MCP server unreachable after {max_retries} retries") from last_exc

    def append_to_doc(self, doc_id: str, content: str) -> dict[str, Any]:
        """
        Call POST /append_to_doc on the MCP server.

        Returns the server response dict on success.
        Raises McpError if the server returns status != 'success'.
        """
        if not doc_id:
            raise McpError("doc_id is required for append_to_doc")
        if not content:
            raise McpError("content is required for append_to_doc")

        log.info("MCP append_to_doc: doc_id=%s (%d chars)", doc_id, len(content))
        result = self._post("/append_to_doc", {"doc_id": doc_id, "content": content})

        status = result.get("status")
        if status != "success":
            raise McpError(
                f"append_to_doc returned status={status!r}: "
                f"{result.get('message', '')} {result.get('details', '')}"
            )
        return result

    def create_email_draft(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> dict[str, Any]:
        """
        Call POST /create_email_draft on the MCP server.

        Returns the server response dict on success.
        Raises McpError if the server returns status != 'success'.
        """
        if not to or not subject or not body:
            raise McpError("to, subject, and body are all required")

        log.info("MCP create_email_draft: to=%s subject=%r", to, subject[:60])
        result = self._post(
            "/create_email_draft",
            {"to": to, "subject": subject, "body": body},
        )

        status = result.get("status")
        if status != "success":
            raise McpError(
                f"create_email_draft returned status={status!r}: "
                f"{result.get('message', '')} {result.get('details', '')}"
            )
        return result
