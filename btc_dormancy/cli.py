"""Volledige pipeline: bank-CSV -> BTC-schatting -> kandidaat-adressen -> CSV-output.

LET OP: dit levert een SHORTLIST van kandidaten op, geen definitieve match.
Handmatige verificatie (tx op een block explorer bekijken, bedrag/tijd
dubbelchecken) blijft noodzakelijk voordat je een adres als "de" ontvanger
van een specifieke aankoop beschouwt.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .bank_csv import load_bank_rows
from .coingecko import CoinGeckoClient
from .config import PROJECT_ROOT, load_hot_wallets, load_settings
from .estimator import estimate_btc_amounts
from .historical_price import HistoricalPriceClient
from .matcher import find_candidates_for_estimate
from .mempool_client import MempoolClient
from .output_writer import write_candidates_csv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zoek kandidaat-adressen voor historische bitcoin-aankopen o.b.v. bankregels."
    )
    parser.add_argument("--input", type=Path, required=True, help="Pad naar bank-CSV")
    parser.add_argument("--service", type=str, default="bitonic", help="Naam van de dienst (moet voorkomen in config/known_addresses.json)")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "output" / "kandidaten.csv")
    parser.add_argument("--margin", type=float, default=0.05, help="Marge rond de geschatte BTC-hoeveelheid (default 0.05 = ±5%%)")
    parser.add_argument("--date-window-days", type=int, default=1, help="Aantal dagen rond de bankdatum om op de blockchain te doorzoeken (default 1)")
    parser.add_argument("--top-n", type=int, default=5, help="Maximum aantal kandidaten per bankregel in de output")
    parser.add_argument("--addresses-file", type=Path, default=None, help="Override voor config/known_addresses.json")
    args = parser.parse_args()

    settings = load_settings()

    bank_rows = load_bank_rows(args.input, service_filter=args.service)
    logger.info("%d bankregel(s) gevonden die '%s' bevatten.", len(bank_rows), args.service)
    if not bank_rows:
        logger.warning("Geen bankregels gevonden, niets te doen.")
        return

    hot_wallets = load_hot_wallets(args.service, addresses_path=args.addresses_file)
    logger.info("%d hot-wallet adres(sen) geconfigureerd voor '%s'.", len(hot_wallets), args.service)

    price_client = HistoricalPriceClient(
        requests_per_minute=settings.requests_per_minute_coingecko,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        fallback_csv_path=PROJECT_ROOT / "config" / "btc_price_fallback.csv",
    )
    estimates = estimate_btc_amounts(bank_rows, price_client, margin=args.margin)
    logger.info("%d/%d bankregel(s) hebben een geldige BTC-schatting.", len(estimates), len(bank_rows))

    current_price_client = CoinGeckoClient(
        api_key=settings.coingecko_api_key,
        requests_per_minute=settings.requests_per_minute_coingecko,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
    )
    try:
        huidige_eur_per_btc = current_price_client.get_current_eur_per_btc()
    except Exception as exc:
        logger.warning("Kan huidige BTC-koers niet ophalen (%s), huidige_waarde_eur blijft leeg.", exc)
        huidige_eur_per_btc = None

    mempool_client = MempoolClient(
        requests_per_minute=settings.requests_per_minute_mempool,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
    )

    all_candidates = []
    for estimate in estimates:
        logger.info(
            "Zoek kandidaten voor bankregel %s (%.2f EUR, ~%.8f BTC)...",
            estimate.bank_row.datum.isoformat(), estimate.bank_row.bedrag_eur, estimate.btc_geschat,
        )
        candidates = find_candidates_for_estimate(
            estimate, hot_wallets, mempool_client,
            huidige_eur_per_btc=huidige_eur_per_btc,
            date_window_days=args.date_window_days,
            top_n=args.top_n,
        )
        logger.info("  -> %d kandidaat/kandidaten gevonden.", len(candidates))
        all_candidates.append(candidates)

    write_candidates_csv(all_candidates, args.output)
    logger.info("Output geschreven naar %s", args.output)
    print(
        "\nLET OP: dit is een shortlist van kandidaten op basis van bedrag- en "
        "tijd-heuristieken, GEEN definitieve match. Verifieer handmatig via een "
        "block explorer voordat je conclusies trekt."
    )


if __name__ == "__main__":
    main()
