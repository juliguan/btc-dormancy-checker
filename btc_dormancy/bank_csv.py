"""Inlezen van de bank-CSV.

Ondersteunt twee formaten:
- Generiek: kolommen `datum`, `bedrag_eur`, `omschrijving` (zie
  data/voorbeeld_transacties.csv).
- ING-export: de standaard CSV-download uit de ING-app/mijn.ing.nl, met
  kolommen als `Datum`, `Naam / Omschrijving`, `Af Bij`, `Bedrag (EUR)`,
  `Mededelingen`. Wordt automatisch gedetecteerd aan de kolomkoppen.

Wil je een ander bank-formaat toevoegen? Stuur de kolomkoppen (headerregel,
geen echte transacties nodig) en er kan een extra `_extract_...`-functie bij.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, TextIO, Tuple, Union

from .models import BankRow, DashboardRow

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y%m%d")

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

_GENERIC_COLUMNS = {"datum", "bedrag_eur", "omschrijving"}
_ING_COLUMNS = {"datum", "naam / omschrijving", "af bij", "bedrag (eur)"}


def _parse_date(raw: str) -> date:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"Kan datum '{raw}' niet parsen. Ondersteunde formaten: "
        "YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, YYYYMMDD."
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
    return abs(float(raw))


def _extract_generic(normalized: Dict[str, str]) -> Tuple[str, str, str]:
    omschrijving = (normalized.get("omschrijving") or "").strip()
    return normalized["datum"], normalized["bedrag_eur"], omschrijving


def _extract_ing(normalized: Dict[str, str]) -> Tuple[str, str, str]:
    # ING geeft het bedrag altijd als positief getal en de richting apart via
    # 'Af Bij' ('Af' = uitgaand, 'Bij' = inkomend). Voor deze tool (bedragen
    # matchen op crypto-aankopen) is de richting zelf niet nodig, alleen de
    # herkenning in de tekst — dus 'Naam / Omschrijving' en 'Mededelingen'
    # samenvoegen geeft de beste kans om bv. 'Bitonic' of 'LiteBit' te vinden,
    # ongeacht in welk van de twee velden ING dat zet.
    naam = (normalized.get("naam / omschrijving") or "").strip()
    mededelingen = (normalized.get("mededelingen") or "").strip()
    omschrijving = f"{naam} {mededelingen}".strip()
    return normalized["datum"], normalized["bedrag (eur)"], omschrijving


def _detect_format(fieldnames: List[str] | None) -> str:
    cols = set(h.strip().lower() for h in (fieldnames or []))
    if _GENERIC_COLUMNS <= cols:
        return "generic"
    if _ING_COLUMNS <= cols:
        return "ing"
    raise ValueError(
        f"Onbekend CSV-formaat. Verwacht ofwel de kolommen {sorted(_GENERIC_COLUMNS)} "
        f"(generiek), ofwel een ING-export met kolommen als {sorted(_ING_COLUMNS)}. "
        f"Gevonden kolommen: {fieldnames}"
    )


_EXTRACTORS = {"generic": _extract_generic, "ing": _extract_ing}


def _read_bank_rows(f: TextIO, service_filter: str | None) -> List[BankRow]:
    rows: List[BankRow] = []
    reader = csv.DictReader(f)
    extract = _EXTRACTORS[_detect_format(reader.fieldnames)]

    for i, raw_row in enumerate(reader):
        normalized = {k.strip().lower(): v for k, v in raw_row.items()}
        datum_str, bedrag_str, omschrijving = extract(normalized)

        if service_filter and service_filter.lower() not in omschrijving.lower():
            continue

        rows.append(
            BankRow(
                row_index=i,
                datum=_parse_date(datum_str),
                bedrag_eur=_parse_bedrag(bedrag_str),
                omschrijving=omschrijving,
            )
        )
    return rows


def load_bank_rows(
    csv_source: Union[Path, str, TextIO], service_filter: str | None = None
) -> List[BankRow]:
    """Leest de bank-CSV in (generiek of ING-formaat, zie module-docstring).
    Als service_filter is opgegeven, worden alleen regels behouden waarvan de
    omschrijving die naam bevat (case-insensitive).

    `csv_source` mag een bestandspad zijn, of een al-geopende tekst-stream
    (bv. `io.StringIO`) — zie load_dashboard_rows voor waarom (een upload in
    het dashboard hoeft zo nooit naar schijf geschreven te worden)."""

    if hasattr(csv_source, "read"):
        return _read_bank_rows(csv_source, service_filter)  # type: ignore[arg-type]

    with open(csv_source, "r", encoding="utf-8-sig", newline="") as f:
        return _read_bank_rows(f, service_filter)


def _read_dashboard_rows(f: TextIO) -> List[DashboardRow]:
    rows: List[DashboardRow] = []
    reader = csv.DictReader(f)
    extract = _EXTRACTORS[_detect_format(reader.fieldnames)]

    for i, raw_row in enumerate(reader):
        normalized = {k.strip().lower(): v for k, v in raw_row.items()}
        datum_str, bedrag_str, omschrijving = extract(normalized)
        moment, heeft_tijd = parse_datetime_flexible(datum_str)

        rows.append(
            DashboardRow(
                row_index=i,
                moment=moment,
                heeft_tijd=heeft_tijd,
                bedrag_eur=_parse_bedrag(bedrag_str),
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
