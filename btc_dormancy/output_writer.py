"""Schrijft de kandidatenlijst weg als CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List

from .models import Candidate

FIELDNAMES = [
    "bank_datum",
    "bank_bedrag_eur",
    "bank_omschrijving",
    "kandidaat_rang",
    "hot_wallet",
    "tx_hash",
    "tx_datum",
    "tx_btc_bedrag",
    "ontvangst_adres",
    "huidig_saldo_btc",
    "huidige_waarde_eur",
    "is_dormant",
    "bedrag_score",
    "tijd_score",
    "totaal_score",
]


def write_candidates_csv(rows: List[List[Candidate]], output_path: Path) -> None:
    """`rows` is een lijst van kandidatenlijsten (één sublijst per bankregel,
    al gesorteerd op score, hoogste eerst)."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for candidates in rows:
            for rang, c in enumerate(candidates, start=1):
                writer.writerow(
                    {
                        "bank_datum": c.bank_row.datum.isoformat(),
                        "bank_bedrag_eur": f"{c.bank_row.bedrag_eur:.2f}",
                        "bank_omschrijving": c.bank_row.omschrijving,
                        "kandidaat_rang": rang,
                        "hot_wallet": c.hot_wallet,
                        "tx_hash": c.tx_hash,
                        "tx_datum": c.tx_datum.isoformat(),
                        "tx_btc_bedrag": f"{c.tx_btc_bedrag:.8f}",
                        "ontvangst_adres": c.ontvangst_adres,
                        "huidig_saldo_btc": f"{c.huidig_saldo_btc:.8f}",
                        "huidige_waarde_eur": (
                            f"{c.huidige_waarde_eur:.2f}"
                            if c.huidige_waarde_eur is not None else ""
                        ),
                        "is_dormant": c.is_dormant,
                        "bedrag_score": f"{c.bedrag_score:.3f}",
                        "tijd_score": f"{c.tijd_score:.3f}",
                        "totaal_score": f"{c.totaal_score:.3f}",
                    }
                )
