"""Client voor mempool.space: adres-transacties opzoeken + dormancy-check.

Endpoints (publieke, key-loze mempool.space REST API):
  - GET /api/address/{address}
        -> {"chain_stats": {"funded_txo_sum": <sats>, "spent_txo_sum": <sats>,
                              "tx_count": <int>, ...}, "mempool_stats": {...}}
    Dormancy volgt direct hieruit: spent_txo_sum == 0 (en mempool_stats leeg)
    betekent dat er nog nooit vanaf dit adres is uitgegeven.

  - GET /api/address/{address}/txs/chain[/{last_seen_txid}]
        -> array van bevestigde transacties (max 25 per pagina, nieuwste eerst).
           Elke tx heeft o.a. txid, status.block_time (unix ts), vin[], vout[]
           met per output scriptpubkey_address en value (in satoshis).
    Voor oudere transacties pagineer je met de txid van de laatst ontvangen
    (dus oudste) transactie in de vorige batch als {last_seen_txid}.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Iterator, List, Optional

from .http_client import ApiClient

logger = logging.getLogger(__name__)

MEMPOOL_BASE_URL = "https://mempool.space/api"
SATS_PER_BTC = 100_000_000


@dataclass
class AddressInfo:
    address: str
    funded_sats: int
    spent_sats: int
    tx_count: int
    has_unconfirmed_activity: bool

    @property
    def balance_sats(self) -> int:
        return self.funded_sats - self.spent_sats

    @property
    def balance_btc(self) -> float:
        return self.balance_sats / SATS_PER_BTC

    @property
    def is_dormant(self) -> bool:
        """True als er sinds ontvangst nooit vanaf dit adres is uitgegeven
        (ook niet als onbevestigde/mempool-transactie)."""
        return self.spent_sats == 0 and not self.has_unconfirmed_activity


@dataclass
class TxOutput:
    address: Optional[str]
    value_sats: int

    @property
    def value_btc(self) -> float:
        return self.value_sats / SATS_PER_BTC


@dataclass
class Transaction:
    txid: str
    block_time: Optional[int]
    outputs: List[TxOutput]

    @property
    def date_utc(self) -> Optional[date]:
        if self.block_time is None:
            return None
        return datetime.fromtimestamp(self.block_time, tz=timezone.utc).date()


class MempoolClient:
    def __init__(
        self,
        requests_per_minute: int = 60,
        timeout: float = 15.0,
        max_retries: int = 5,
        base_url: str = MEMPOOL_BASE_URL,
    ) -> None:
        self._client = ApiClient(
            base_url=base_url,
            requests_per_minute=requests_per_minute,
            timeout=timeout,
            max_retries=max_retries,
        )

    def get_address_info(self, address: str) -> AddressInfo:
        data = self._client.get(f"/address/{address}")
        chain = data["chain_stats"]
        mempool = data.get("mempool_stats", {})
        has_unconfirmed = bool(mempool.get("funded_txo_sum") or mempool.get("spent_txo_sum"))
        return AddressInfo(
            address=address,
            funded_sats=int(chain["funded_txo_sum"]),
            spent_sats=int(chain["spent_txo_sum"]),
            tx_count=int(chain["tx_count"]),
            has_unconfirmed_activity=has_unconfirmed,
        )

    def iter_address_txs_on_date(
        self, address: str, target_date: date, max_pages: int = 400
    ) -> Iterator[Transaction]:
        """Itereert (nieuwste-eerst, gepagineerd per 25) door de bevestigde
        transacties van een adres en levert alleen transacties op `target_date`
        op. Stopt zodra transacties ouder zijn dan `target_date`, of na
        `max_pages` pagina's als veiligheidsgrens tegen zeer actieve adressen."""

        last_seen_txid: Optional[str] = None
        pages_fetched = 0

        while pages_fetched < max_pages:
            path = f"/address/{address}/txs/chain"
            if last_seen_txid:
                path += f"/{last_seen_txid}"

            page = self._client.get(path)
            pages_fetched += 1

            if not page:
                return

            for raw_tx in page:
                status = raw_tx.get("status", {})
                block_time = status.get("block_time")
                tx = Transaction(
                    txid=raw_tx["txid"],
                    block_time=block_time,
                    outputs=[
                        TxOutput(
                            address=vout.get("scriptpubkey_address"),
                            value_sats=int(vout.get("value", 0)),
                        )
                        for vout in raw_tx.get("vout", [])
                    ],
                )

                tx_date = tx.date_utc
                if tx_date is None:
                    # onbevestigd, sla over (we zoeken historische, bevestigde txs)
                    continue
                if tx_date == target_date:
                    yield tx
                elif tx_date < target_date:
                    # nieuwste-eerst volgorde: alles hierna is nog ouder -> stoppen
                    return

            last_seen_txid = page[-1]["txid"]
            if len(page) < 25:
                # laatste pagina bereikt
                return
