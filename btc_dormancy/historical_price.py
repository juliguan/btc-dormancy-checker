"""Historische EUR/BTC-koers per datum.

BELANGRIJKE AFWIJKING VAN DE OORSPRONKELIJKE OPZET:
CoinGecko's publieke API beperkt historische data (sinds een recente
beleidswijziging) tot de laatste 365 dagen — "Public API users are limited to
querying historical data within the past 365 days" (geverifieerd via een
live call, 2026-09-21). Voor de 2010-2015 doelperiode is dat dus onbruikbaar,
niet alleen voor het pre-2013 deel.

Als vervanging combineert deze module twee gratis, key-loze bronnen die wél
verifieerbaar historische data teruggeven:
  1. blockchain.info /charts/market-price  -> dagelijkse gemiddelde USD/BTC-koers
     (data vanaf medio 2010; vóór de eerste echte handel staat de waarde op 0.0)
  2. frankfurter.app (ECB-koersen)         -> historische USD->EUR wisselkoers
     (op weekend/feestdagen wordt de dichtstbijzijnde eerdere handelsdag gebruikt)

eur_per_btc = usd_per_btc(datum) * eur_per_usd(datum)

Dit is een keten van twee losse bronnen, dus de resulterende koers is een
benadering (vandaar ook de ±5%-marge in de rest van de pipeline). Een lokale
fallback (config/btc_price_fallback.csv) blijft mogelijk om een datum handmatig
te overschrijven met een koers uit een andere bron.
"""

from __future__ import annotations

import csv
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from .http_client import ApiClient

logger = logging.getLogger(__name__)

BLOCKCHAIN_INFO_BASE_URL = "https://api.blockchain.info"
FRANKFURTER_BASE_URL = "https://api.frankfurter.app"


class PriceNotAvailableError(Exception):
    pass


class HistoricalPriceClient:
    def __init__(
        self,
        requests_per_minute: int = 30,
        timeout: float = 15.0,
        max_retries: int = 5,
        fallback_csv_path: Optional[Path] = None,
    ) -> None:
        self._btc_usd_client = ApiClient(
            base_url=BLOCKCHAIN_INFO_BASE_URL,
            requests_per_minute=requests_per_minute,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._fx_client = ApiClient(
            base_url=FRANKFURTER_BASE_URL,
            requests_per_minute=requests_per_minute,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._fallback_path = fallback_csv_path
        self._fallback_cache: Optional[Dict[date, float]] = None

    def _load_fallback(self) -> Dict[date, float]:
        if self._fallback_cache is not None:
            return self._fallback_cache

        prices: Dict[date, float] = {}
        if self._fallback_path and self._fallback_path.exists():
            with open(self._fallback_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    d = date.fromisoformat(row["datum"])
                    prices[d] = float(row["eur_per_btc"])
        self._fallback_cache = prices
        return prices

    def _get_usd_per_btc(self, target_date: date) -> float:
        data = self._btc_usd_client.get(
            "/charts/market-price",
            params={
                "start": target_date.isoformat(),
                "timespan": "2days",
                "format": "json",
            },
        )
        for point in (data or {}).get("values", []):
            point_date = datetime.fromtimestamp(point["x"], tz=timezone.utc).date()
            if point_date == target_date:
                if point["y"] <= 0:
                    raise PriceNotAvailableError(
                        f"blockchain.info heeft geen handelsdata voor {target_date.isoformat()} "
                        "(waarde is 0, dit ligt waarschijnlijk vóór het ontstaan van liquide "
                        "bitcoin-markten). Vul een koers in via config/btc_price_fallback.csv."
                    )
                return float(point["y"])
        raise PriceNotAvailableError(
            f"Geen USD/BTC-datapunt gevonden voor {target_date.isoformat()} bij blockchain.info."
        )

    def _get_usd_to_eur_rate(self, target_date: date) -> float:
        data = self._fx_client.get(
            f"/{target_date.isoformat()}",
            params={"from": "USD", "to": "EUR"},
        )
        rate = (data or {}).get("rates", {}).get("EUR")
        if rate is None:
            raise PriceNotAvailableError(
                f"Geen USD->EUR wisselkoers gevonden voor {target_date.isoformat()} bij frankfurter.app."
            )
        actual_date = data.get("date")
        if actual_date and actual_date != target_date.isoformat():
            logger.info(
                "frankfurter.app had geen koers voor %s (weekend/feestdag), "
                "gebruikt dichtstbijzijnde eerdere handelsdag %s.",
                target_date.isoformat(), actual_date,
            )
        return float(rate)

    def get_eur_per_btc_on_date(self, target_date: date) -> float:
        fallback = self._load_fallback()
        if target_date in fallback:
            return fallback[target_date]

        usd_per_btc = self._get_usd_per_btc(target_date)
        usd_to_eur = self._get_usd_to_eur_rate(target_date)
        return usd_per_btc * usd_to_eur
