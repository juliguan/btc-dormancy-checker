"""Fase A: alleen bank-CSV -> geschatte BTC-bedragen per regel (geen blockchain-lookup).

Dit is een tussenstap zodat de bankdata + koersconversie zelfstandig getest kan
worden voordat de Bitonic-adressen en de blockchain-explorer erbij komen.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .bank_csv import load_bank_rows
from .historical_price import HistoricalPriceClient
from .config import PROJECT_ROOT, load_settings
from .estimator import estimate_btc_amounts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fase A: bank-CSV -> BTC-schattingen")
    parser.add_argument("--input", type=Path, default=PROJECT_ROOT / "data" / "voorbeeld_transacties.csv")
    parser.add_argument("--service", type=str, default="bitonic")
    parser.add_argument("--margin", type=float, default=0.05)
    args = parser.parse_args()

    settings = load_settings()
    rows = load_bank_rows(args.input, service_filter=args.service)
    print(f"{len(rows)} bankregel(s) gevonden die '{args.service}' bevatten.\n")

    price_client = HistoricalPriceClient(
        requests_per_minute=settings.requests_per_minute_coingecko,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        fallback_csv_path=PROJECT_ROOT / "config" / "btc_price_fallback.csv",
    )

    estimates = estimate_btc_amounts(rows, price_client, margin=args.margin)

    for est in estimates:
        print(
            f"{est.bank_row.datum} | {est.bank_row.bedrag_eur:>10.2f} EUR | "
            f"koers: {est.eur_per_btc_op_datum:>12.2f} EUR/BTC | "
            f"geschat: {est.btc_geschat:.8f} BTC "
            f"(range {est.btc_min:.8f} - {est.btc_max:.8f})"
        )

    if len(estimates) < len(rows):
        print(f"\nLET OP: {len(rows) - len(estimates)} regel(s) overgeslagen door ontbrekende koersdata.")


if __name__ == "__main__":
    main()
