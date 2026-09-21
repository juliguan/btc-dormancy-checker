"""Gedeelde HTTP-laag met simpele rate limiting en retry/backoff voor 429/5xx."""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping

import requests

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simpele rate limiter: max N requests per 60 seconden, per client-instantie."""

    def __init__(self, requests_per_minute: int) -> None:
        self.min_interval = 60.0 / max(requests_per_minute, 1)
        self._last_call = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_call
        remaining = self.min_interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_call = time.monotonic()


class ApiClient:
    """Kleine wrapper rond requests met rate limiting en exponential backoff
    op 429 (rate limited) en 5xx (server error) responses."""

    def __init__(
        self,
        base_url: str,
        requests_per_minute: int = 30,
        timeout: float = 15.0,
        max_retries: int = 5,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = dict(default_headers or {})
        self._limiter = RateLimiter(requests_per_minute)
        self._session = requests.Session()

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        attempt = 0
        backoff = 1.0

        while True:
            self._limiter.wait()
            try:
                response = self._session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers=self.default_headers,
                )
            except requests.RequestException as exc:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                logger.warning(
                    "Netwerkfout bij %s (poging %d/%d): %s. Wacht %.1fs.",
                    url, attempt, self.max_retries, exc, backoff,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            if response.status_code == 429 or response.status_code >= 500:
                attempt += 1
                if attempt > self.max_retries:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after else backoff
                logger.warning(
                    "HTTP %s bij %s (poging %d/%d). Wacht %.1fs.",
                    response.status_code, url, attempt, self.max_retries, wait_time,
                )
                time.sleep(wait_time)
                backoff *= 2
                continue

            response.raise_for_status()

            if response.status_code == 204 or not response.content:
                return None
            return response.json()
