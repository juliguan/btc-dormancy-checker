"""Datamodellen die door de hele pipeline heen gedeeld worden."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class BankRow:
    """Eén regel uit de bank-CSV."""

    row_index: int
    datum: date
    bedrag_eur: float
    omschrijving: str


@dataclass
class BtcEstimate:
    """Geschatte BTC-hoeveelheid voor een bankregel, met marge."""

    bank_row: BankRow
    eur_per_btc_op_datum: float
    btc_geschat: float
    btc_min: float
    btc_max: float


@dataclass
class Candidate:
    """Eén kandidaat-ontvangstadres voor een bankregel."""

    bank_row: BankRow
    hot_wallet: str
    tx_hash: str
    tx_datum: date
    tx_btc_bedrag: float
    ontvangst_adres: str
    huidig_saldo_btc: float
    huidige_waarde_eur: Optional[float]
    is_dormant: bool
    bedrag_score: float
    tijd_score: float
    totaal_score: float = field(init=False)

    def __post_init__(self) -> None:
        # Gelijk gewicht voor bedrag- en tijdmatch; kan later verfijnd worden.
        self.totaal_score = (self.bedrag_score + self.tijd_score) / 2
