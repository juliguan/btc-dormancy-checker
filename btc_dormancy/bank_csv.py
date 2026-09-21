"""Inlezen van de bank-CSV (datum, bedrag_eur, omschrijving)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import List, TextIO, Union

from .models import BankRow, DashboardRow

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y")

# Met tijd-component, voor de dashboard-charts (zie parse_datetime_flexible).
_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
)


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


def parse_datetime_flexible(raw: str) -> tuple[datetime, bool]:
    """Parseert een datumveld dat optioneel een tijd-component bevat.
    Geeft (moment, heeft_tijd) terug: heeft_tijd is False als er geen tijd in
    de brontekst stond (moment staat dan op middernacht)."""

    raw = raw.strip()
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt), True
        except ValueError:
            continue
    return datetime.combine(_parse_date(raw), datetime.min.time()), False


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


def _read_dashboard_rows(f: TextIO) -> List[DashboardRow]:
    rows: List[DashboardRow] = []
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
        moment, heeft_tijd = parse_datetime_flexible(normalized["datum"])

        rows.append(
            DashboardRow(
                row_index=i,
                moment=moment,
                heeft_tijd=heeft_tijd,
                bedrag_eur=_parse_bedrag(normalized["bedrag_eur"]),
                omschrijving=omschrijving,
            )
        )
    return rows


def load_dashboard_rows(csv_source: Union[Path, str, TextIO]) -> List[DashboardRow]:
    """Zelfde CSV-inleeslogica als load_bank_rows, maar behoudt een
    eventuele tijd-component (i.p.v. hem af te kappen tot een datum) voor
    gebruik in de dashboard-charts.

    `csv_source` mag een bestandspad zijn, of een al-geopende tekst-stream
    (bv. `io.StringIO`) — dat laatste gebruikt het Streamlit-dashboard voor
    een geüploade CSV, zodat die nooit naar schijf geschreven hoeft te
    worden en alleen in het geheugen van het proces blijft."""

    if hasattr(csv_source, "read"):
        return _read_dashboard_rows(csv_source)  # type: ignore[arg-type]

    with open(csv_source, "r", encoding="utf-8-sig", newline="") as f:
        return _read_dashboard_rows(f)
