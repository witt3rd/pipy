"""Tests for OpenAI Codex OAuth helpers."""

from pipy_ai.oauth.openai_codex import (
    _parse_authorization_input,
    _decode_jwt_payload,
    _get_account_id,
)
import base64
import json


class TestParseAuthorizationInput:
    def test_empty_input(self):
        assert _parse_authorization_input("") == {}
        assert _parse_authorization_input("  ") == {}

    def test_code_hash_state(self):
        result = _parse_authorization_input("mycode#mystate")
        assert result["code"] == "mycode"
        assert result["state"] == "mystate"

    def test_bare_code(self):
        result = _parse_authorization_input("just-a-code")
        assert result["code"] == "just-a-code"

    def test_url_with_code_and_state(self):
        url = "http://localhost:1455/auth/callback?code=abc123&state=xyz789"
        result = _parse_authorization_input(url)
        assert result["code"] == "abc123"
        assert result["state"] == "xyz789"

    def test_query_string(self):
        result = _parse_authorization_input("code=foo&state=bar")
        assert result["code"] == "foo"
        assert result["state"] == "bar"


class TestJWTDecode:
    def _make_jwt(self, payload: dict) -> str:
        header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        sig = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()
        return f"{header}.{body}.{sig}"

    def test_decode_valid_jwt(self):
        jwt = self._make_jwt({"sub": "user123"})
        result = _decode_jwt_payload(jwt)
        assert result == {"sub": "user123"}

    def test_decode_invalid_jwt(self):
        assert _decode_jwt_payload("not.a.jwt") is None
        assert _decode_jwt_payload("invalid") is None

    def test_get_account_id(self):
        jwt = self._make_jwt({
            "https://api.openai.com/auth": {
                "chatgpt_account_id": "acct_abc123"
            }
        })
        assert _get_account_id(jwt) == "acct_abc123"

    def test_get_account_id_missing(self):
        jwt = self._make_jwt({"sub": "user"})
        assert _get_account_id(jwt) is None
