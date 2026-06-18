"""Tests for the MCP HTTP client — mocked at urllib level."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from pulse.phase03.mcp_client import McpClient, McpError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(body: dict, status: int = 200):
    """Return a context-manager mock that mimics urllib urlopen response."""
    raw = json.dumps(body).encode()
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read = MagicMock(return_value=raw)
    return mock


def _http_error(code: int, body: str = "error") -> HTTPError:
    return HTTPError(
        url="http://test", code=code, msg="error",
        hdrs=None, fp=BytesIO(body.encode()),
    )


# ---------------------------------------------------------------------------
# append_to_doc
# ---------------------------------------------------------------------------

class TestAppendToDoc:
    def test_happy_path(self):
        client = McpClient(base_url="http://mock")
        resp = {"status": "success", "message": "Content appended to document", "document_id": "doc1"}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = client.append_to_doc("doc1", "some content")
        assert result["status"] == "success"
        assert result["document_id"] == "doc1"

    def test_empty_doc_id_raises(self):
        client = McpClient(base_url="http://mock")
        with pytest.raises(McpError, match="doc_id is required"):
            client.append_to_doc("", "content")

    def test_empty_content_raises(self):
        client = McpClient(base_url="http://mock")
        with pytest.raises(McpError, match="content is required"):
            client.append_to_doc("doc1", "")

    def test_server_error_status_raises(self):
        client = McpClient(base_url="http://mock")
        resp = {"status": "error", "message": "Google Docs API error"}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            with pytest.raises(McpError, match="status="):
                client.append_to_doc("doc1", "content")

    def test_500_retries_then_raises(self):
        client = McpClient(base_url="http://mock")
        err = _http_error(500, "internal error")
        with patch("urllib.request.urlopen", side_effect=err):
            with patch("time.sleep"):  # don't actually sleep in tests
                with pytest.raises(McpError, match="HTTP 500"):
                    client.append_to_doc("doc1", "content")

    def test_network_error_retries_then_raises(self):
        client = McpClient(base_url="http://mock")
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            with patch("time.sleep"):
                with pytest.raises(McpError, match="Network error"):
                    client.append_to_doc("doc1", "content")

    def test_4xx_does_not_retry(self):
        client = McpClient(base_url="http://mock")
        err = _http_error(403, "forbidden")
        call_count = 0

        def side_effect(*a, **kw):
            nonlocal call_count
            call_count += 1
            raise err

        with patch("urllib.request.urlopen", side_effect=side_effect):
            with pytest.raises(McpError, match="HTTP 403"):
                client.append_to_doc("doc1", "content")
        # 4xx should not retry
        assert call_count == 1


# ---------------------------------------------------------------------------
# create_email_draft
# ---------------------------------------------------------------------------

class TestCreateEmailDraft:
    def test_happy_path(self):
        client = McpClient(base_url="http://mock")
        resp = {"status": "success", "message": "Draft created", "draft_id": "draft_abc"}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            result = client.create_email_draft("a@b.com", "Subject", "Body")
        assert result["status"] == "success"

    def test_missing_fields_raises(self):
        client = McpClient(base_url="http://mock")
        with pytest.raises(McpError, match="required"):
            client.create_email_draft("", "subject", "body")

    def test_server_error_raises(self):
        client = McpClient(base_url="http://mock")
        resp = {"status": "error", "message": "Gmail API error"}
        with patch("urllib.request.urlopen", return_value=_mock_response(resp)):
            with pytest.raises(McpError, match="status="):
                client.create_email_draft("a@b.com", "Subject", "Body")
