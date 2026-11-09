"""Small polite HTTP client (no API key; sends a descriptive User-Agent)."""
from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ApiError(Exception):
    pass


class BlockedError(ApiError):
    """HTTP 403/429: the server refused us (rate limit, or a missing/blocked User-Agent)."""


class Client:
    def __init__(self, user_agent: str, delay: float = 0.25, timeout: int = 90):
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=2, status_forcelist=(500, 502, 503, 504),
                      allowed_methods=("GET",), raise_on_status=False)
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers["User-Agent"] = user_agent
        self.delay, self.timeout = delay, timeout

    def _get(self, url: str):
        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ApiError(f"request failed: {type(exc).__name__}: {exc}") from None
        time.sleep(self.delay)
        if resp.status_code in (403, 429):
            raise BlockedError(
                f"HTTP {resp.status_code} from {url}. The server refused the request: rate limit, "
                "or the User-Agent / contact email was rejected."
            )
        if resp.status_code >= 400:
            raise ApiError(f"HTTP {resp.status_code} from {url}")
        return resp

    def get_json(self, url: str):
        resp = self._get(url)
        try:
            return resp.json()
        except ValueError:
            raise ApiError(f"Response from {url} was not JSON.") from None

    def get_text(self, url: str) -> str:
        resp = self._get(url)
        try:
            return resp.content.decode("utf-8-sig")
        except UnicodeDecodeError:
            return resp.content.decode("latin-1")
