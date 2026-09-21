"""Configuratie: .env laden en de instelbare hot-wallet adressenlijst laden."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Settings:
    coingecko_api_key: str | None
    blockchair_api_key: str | None
    request_timeout: float
    max_retries: float
    requests_per_minute_coingecko: int
    requests_per_minute_mempool: int


def load_settings(env_path: Path | None = None) -> Settings:
    """Laadt instellingen uit .env (indien aanwezig). Geen enkele key is verplicht
    voor de standaard-flow (mempool.space + gratis CoinGecko-tier)."""

    load_dotenv(dotenv_path=env_path or (PROJECT_ROOT / ".env"))

    return Settings(
        coingecko_api_key=os.getenv("COINGECKO_API_KEY") or None,
        blockchair_api_key=os.getenv("BLOCKCHAIR_API_KEY") or None,
        request_timeout=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
        max_retries=int(os.getenv("MAX_RETRIES", "5")),
        requests_per_minute_coingecko=int(os.getenv("COINGECKO_RPM", "25")),
        requests_per_minute_mempool=int(os.getenv("MEMPOOL_RPM", "60")),
    )


def load_hot_wallets(service: str, addresses_path: Path | None = None) -> List[str]:
    """Laadt de lijst met bekende hot-wallet adressen voor een dienst (bv. 'bitonic')
    uit config/known_addresses.json. Zie README.md voor hoe je deze lijst aanvult."""

    path = addresses_path or (PROJECT_ROOT / "config" / "known_addresses.json")
    if not path.exists():
        raise FileNotFoundError(
            f"Adressenbestand niet gevonden: {path}. "
            "Kopieer/hernoem config/known_addresses.example.json of maak het bestand aan."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    service_key = service.lower()
    if service_key not in data:
        raise KeyError(
            f"Dienst '{service}' niet gevonden in {path}. "
            f"Beschikbare diensten: {list(data.keys())}"
        )

    addresses = data[service_key].get("hot_wallets", [])
    if not addresses:
        raise ValueError(
            f"Geen hot-wallet adressen geconfigureerd voor '{service}' in {path}. "
            "Vul de lijst aan, zie README.md."
        )
    return addresses
