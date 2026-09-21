"""Zet bankregels om naar geschatte BTC-bedragen met een marge voor intraday-schommeling."""

from __future__ import annotations

import logging
from typing import List

from .historical_price import HistoricalPriceClient
from .models import BankRow, BtcEstimate

logger = logging.getLogger(__name__)


def estimate_btc_amounts(
    bank_rows: List[BankRow],
    price_client: HistoricalPriceClient,
    margin: float = 0.05,
) -> List[BtcEstimate]:
    """Berekent per bankregel het geschatte BTC-bedrag o.b.v. de koers op die
    datum, met een ±margin band (standaard 5%) voor intraday-schommeling."""

    estimates: List[BtcEstimate] = []
    for row in bank_rows:
        try:
            eur_per_btc = price_client.get_eur_per_btc_on_date(row.datum)
        except Exception as exc:
            logger.error(
                "Kan koers voor %s (regel %d, %.2f EUR) niet ophalen: %s",
                row.datum.isoformat(), row.row_index, row.bedrag_eur, exc,
            )
            continue

        btc_geschat = row.bedrag_eur / eur_per_btc
        estimates.append(
            BtcEstimate(
                bank_row=row,
                eur_per_btc_op_datum=eur_per_btc,
                btc_geschat=btc_geschat,
                btc_min=btc_geschat * (1 - margin),
                btc_max=btc_geschat * (1 + margin),
            )
        )
    return estimates
