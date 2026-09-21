"""CoinGecko: alleen de huidige EUR/BTC-koers (gebruikt om de huidige waarde
van een dormant adres te tonen). Voor historische koersen, zie historical_price.py
CoinGecko's publieke API beperkt historische data sinds kort tot de laatste
365 dagen, en is daarom niet bruikbaar voor de 2010-2015 doelperiode.
"""

from __future__ import annotations

from typing import Optional

from .http_client import ApiClient

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"


class CoinGeckoClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        requests_per_minute: int = 25,
        timeout: float = 15.0,
        max_retries: int = 5,
    ) -> None:
        headers = {"x-cg-demo-api-key": api_key} if api_key else None
        self._client = ApiClient(
            base_url=COINGECKO_BASE_URL,
            requests_per_minute=requests_per_minute,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=headers,
        )

    def get_current_eur_per_btc(self) -> float:
        data = self._client.get(
            "/simple/price", params={"ids": "bitcoin", "vs_currencies": "eur"}
        )
        return float(data["bitcoin"]["eur"])
