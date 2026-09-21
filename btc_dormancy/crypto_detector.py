"""Detecteert welke bankregels naar een bekende crypto-dienst gingen.

Matcht op vrije-tekst patronen (case-insensitive substring) uit
config/crypto_companies.json tegen de omschrijving van een bankregel. Dit is
breder dan de éne-dienst-per-run flow van de rest van de pipeline (bv.
'bitonic'): hiermee kan één CSV in één keer gescand worden op meerdere
bekende crypto-bedrijven tegelijk (zoals in het Streamlit-dashboard).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .models import BankRow


@dataclass
class CryptoCompany:
    naam: str
    patronen: List[str]

    def matches(self, tekst: str) -> bool:
        tekst_lower = tekst.lower()
        return any(patroon.lower() in tekst_lower for patroon in self.patronen)


@dataclass
class DetectedTransaction:
    bank_row: BankRow
    bedrijf: str


def load_crypto_companies(path: Optional[Path] = None) -> List[CryptoCompany]:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config" / "crypto_companies.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Bestand met crypto-bedrijven niet gevonden: {path}. "
            "Kopieer config/crypto_companies.example.json naar config/crypto_companies.json."
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        CryptoCompany(naam=c["naam"], patronen=c["patronen"])
        for c in data.get("companies", [])
    ]


def detect_crypto_transactions(
    bank_rows: List[BankRow], companies: List[CryptoCompany]
) -> List[DetectedTransaction]:
    """Voor elke bankregel: het eerst-matchende bedrijf uit de lijst (indien
    meerdere patronen matchen, telt de eerste treffer in volgorde van de
    configuratie)."""

    detected: List[DetectedTransaction] = []
    for row in bank_rows:
        for company in companies:
            if company.matches(row.omschrijving):
                detected.append(DetectedTransaction(bank_row=row, bedrijf=company.naam))
                break
    return detected
