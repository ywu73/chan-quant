from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .errors import ChanQuantError

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
DEFAULT_API_BASE = "http://127.0.0.1:8000"
DEFAULT_UI_BASE = "http://127.0.0.1:5173"


def _local_base(raw: str, variable: str) -> str:
    value = raw.strip().rstrip("/")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "http" or parsed.hostname not in LOCAL_HOSTS:
        raise ChanQuantError(
            "LOCAL_ADDRESS_REQUIRED",
            f"{variable} must be an http loopback address",
            status="REJECTED",
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ChanQuantError(
            "LOCAL_ADDRESS_INVALID",
            f"{variable} must not include credentials, query, or fragment",
            status="REJECTED",
        )
    return value


class ChanQuantClient:
    def __init__(self, api_base: str | None = None, ui_base: str | None = None) -> None:
        self.api_base = _local_base(
            api_base or os.getenv("CHAN_QUANT_API_BASE", DEFAULT_API_BASE),
            "CHAN_QUANT_API_BASE",
        )
        self.ui_base = _local_base(
            ui_base or os.getenv("CHAN_QUANT_UI_BASE", DEFAULT_UI_BASE),
            "CHAN_QUANT_UI_BASE",
        )
        try:
            self.timeout = float(os.getenv("CHAN_QUANT_HTTP_TIMEOUT", "10"))
        except ValueError as error:
            raise ChanQuantError(
                "HTTP_TIMEOUT_INVALID", "CHAN_QUANT_HTTP_TIMEOUT must be numeric", status="REJECTED"
            ) from error
        if not 0.1 <= self.timeout <= 60:
            raise ChanQuantError(
                "HTTP_TIMEOUT_INVALID", "CHAN_QUANT_HTTP_TIMEOUT must be between 0.1 and 60", status="REJECTED"
            )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query: list[tuple[str, str]] = []
        for key, value in (params or {}).items():
            if isinstance(value, list):
                query.extend((key, str(item)) for item in value)
            else:
                query.append((key, str(value).lower() if isinstance(value, bool) else str(value)))
        suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
        url = f"{self.api_base}{path}{suffix}"
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "chan-quant-codex-plugin/0.2"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                status = response.status
        except urllib.error.HTTPError as error:
            raw = error.read()
            self._raise_http(error.code, raw)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ChanQuantError(
                "LOCAL_SERVICE_UNAVAILABLE",
                f"cannot reach Chan Quant at {self.api_base}; start it with ./start.sh",
            ) from error
        if status != 200:
            self._raise_http(status, raw)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ChanQuantError(
                "MALFORMED_RESPONSE", f"Chan Quant returned malformed JSON for {path}"
            ) from error
        if not isinstance(payload, (dict, list)):
            raise ChanQuantError("MALFORMED_RESPONSE", f"Chan Quant returned a non-object response for {path}")
        return payload

    def health(self) -> dict[str, Any]:
        payload = self.get("/health")
        if not isinstance(payload, dict) or not {"status", "data_mode", "remote_network", "strategy"}.issubset(payload):
            raise ChanQuantError("NON_CHAN_QUANT_SERVICE", "loopback service did not return Chan Quant health fields")
        if payload.get("data_mode") not in {"synthetic", "csv", "sina", "snapshot", "invalid"}:
            raise ChanQuantError("NON_CHAN_QUANT_SERVICE", "health response contains an unknown Chan Quant data mode")
        return payload

    def url(self, path: str, params: dict[str, Any] | None = None) -> str:
        query: list[tuple[str, str]] = []
        for key, value in (params or {}).items():
            if isinstance(value, list):
                query.extend((key, str(item)) for item in value)
            else:
                query.append((key, str(value)))
        suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
        return f"{self.ui_base}{path}{suffix}"

    @staticmethod
    def _raise_http(status: int, raw: bytes) -> None:
        detail: Any = None
        try:
            detail = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = None
        code = None
        message = None
        if isinstance(detail, dict):
            candidate = detail.get("detail", detail)
            if isinstance(candidate, dict):
                code = candidate.get("code")
                message = candidate.get("message")
            elif isinstance(candidate, str):
                message = candidate
        code = code or {422: "REQUEST_REJECTED", 502: "UPSTREAM_UNAVAILABLE", 503: "SERVICE_UNAVAILABLE"}.get(status, "HTTP_ERROR")
        message = message or f"Chan Quant returned HTTP {status}"
        status_kind = "REJECTED" if status == 422 else "UNAVAILABLE"
        raise ChanQuantError(str(code), str(message), status=status_kind)
