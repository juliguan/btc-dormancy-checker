"""Inlezen van de bank-CSV (datum, bedrag_eur, omschrijving)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import List

from .models import BankRow

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")


def _parse_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Kan datum '{raw}' niet parsen. Ondersteunde formaten: "
        "YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY."
    )


def _parse_bedrag(raw: str) -> float:
    raw = raw.strip().replace("€", "").replace(" ", "")
    # Ondersteun zowel '1234,56' (NL) als '1234.56' (EN) notatie.
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")
    return float(raw)


def load_bank_rows(csv_path: Path, service_filter: str | None = None) -> List[BankRow]:
    """Leest de bank-CSV in. Als service_filter is opgegeven, worden alleen
    regels behouden waarvan de omschrijving die naam bevat (case-insensitive)."""

    rows: List[BankRow] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"datum", "bedrag_eur", "omschrijving"}
        missing = required - set(h.strip().lower() for h in (reader.fieldnames or []))
        if missing:
            raise ValueError(
                f"CSV mist verplichte kolommen: {missing}. "
                f"Gevonden kolommen: {reader.fieldnames}"
            )

        for i, raw_row in enumerate(reader):
            normalized = {k.strip().lower(): v for k, v in raw_row.items()}
            omschrijving = (normalized.get("omschrijving") or "").strip()

            if service_filter and service_filter.lower() not in omschrijving.lower():
                continue

            rows.append(
                BankRow(
                    row_index=i,
                    datum=_parse_date(normalized["datum"]),
                    bedrag_eur=_parse_bedrag(normalized["bedrag_eur"]),
                    omschrijving=omschrijving,
                )
            )
    return rows
