"""Zoekt kandidaat-ontvangstadressen voor elke BTC-schatting en scoort ze."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import List, Optional

from .mempool_client import MempoolClient
from .models import BtcEstimate, Candidate

logger = logging.getLogger(__name__)


def _bedrag_score(tx_btc: float, btc_geschat: float, btc_min: float, btc_max: float) -> float:
    """1.0 = exact op de geschatte hoeveelheid, lineair aflopend naar 0 aan de
    randen van de ±marge-band."""

    half_width = max((btc_max - btc_min) / 2, 1e-12)
    afwijking = abs(tx_btc - btc_geschat)
    return max(0.0, 1.0 - afwijking / half_width)


def _tijd_score(dag_offset: int, venster_dagen: int) -> float:
    """1.0 = exact dezelfde dag als de bankregel, lineair aflopend binnen het venster."""

    if venster_dagen <= 0:
        return 1.0 if dag_offset == 0 else 0.0
    return max(0.0, 1.0 - abs(dag_offset) / venster_dagen)


def find_candidates_for_estimate(
    estimate: BtcEstimate,
    hot_wallets: List[str],
    mempool_client: MempoolClient,
    huidige_eur_per_btc: Optional[float],
    date_window_days: int = 1,
    top_n: int = 5,
) -> List[Candidate]:
    """Doorzoekt de geconfigureerde hot-wallet adressen op uitgaande
    transacties rond de banktransactiedatum met een bedrag binnen de
    geschatte BTC-range, en scoort/rangschikt de resultaten."""

    candidates: List[Candidate] = []
    bank_row = estimate.bank_row

    for hot_wallet in hot_wallets:
        for dag_offset in range(-date_window_days, date_window_days + 1):
            zoek_datum = bank_row.datum + timedelta(days=dag_offset)

            try:
                txs = list(
                    mempool_client.iter_address_txs_on_date(hot_wallet, zoek_datum)
                )
            except Exception as exc:
                logger.error(
                    "Kan transacties voor %s op %s niet ophalen: %s",
                    hot_wallet, zoek_datum.isoformat(), exc,
                )
                continue

            for tx in txs:
                for output in tx.outputs:
                    if output.address is None or output.address == hot_wallet:
                        continue  # geen adres (bv. OP_RETURN) of wisselgeld terug naar zichzelf
                    if not (estimate.btc_min <= output.value_btc <= estimate.btc_max):
                        continue

                    try:
                        addr_info = mempool_client.get_address_info(output.address)
                    except Exception as exc:
                        logger.error(
                            "Kan adresinfo voor %s niet ophalen: %s", output.address, exc
                        )
                        continue

                    huidige_waarde_eur = (
                        addr_info.balance_btc * huidige_eur_per_btc
                        if huidige_eur_per_btc is not None
                        else None
                    )

                    candidates.append(
                        Candidate(
                            bank_row=bank_row,
                            hot_wallet=hot_wallet,
                            tx_hash=tx.txid,
                            tx_datum=zoek_datum,
                            tx_btc_bedrag=output.value_btc,
                            ontvangst_adres=output.address,
                            huidig_saldo_btc=addr_info.balance_btc,
                            huidige_waarde_eur=huidige_waarde_eur,
                            is_dormant=addr_info.is_dormant,
                            bedrag_score=_bedrag_score(
                                output.value_btc, estimate.btc_geschat,
                                estimate.btc_min, estimate.btc_max,
                            ),
                            tijd_score=_tijd_score(dag_offset, date_window_days),
                        )
                    )

    candidates.sort(key=lambda c: c.totaal_score, reverse=True)
    return candidates[:top_n]
