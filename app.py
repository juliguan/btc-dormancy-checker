"""Streamlit-dashboard: upload een bank-CSV en zie welke transacties naar een
bekende crypto-dienst (Bitonic, LiteBit, Bitvavo, ...) gingen.

Start met:
    streamlit run app.py
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from btc_dormancy.bank_csv import load_bank_rows
from btc_dormancy.crypto_detector import detect_crypto_transactions, load_crypto_companies

PROJECT_ROOT = Path(__file__).resolve().parent
EXAMPLE_CSV = PROJECT_ROOT / "data" / "voorbeeld_transacties.csv"

st.set_page_config(
    page_title="BTC Dormancy Checker",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stMetric {
        background-color: #171B24;
        border: 1px solid #262B36;
        border-radius: 10px;
        padding: 16px 16px 8px 16px;
    }
    div[data-testid="stMetricValue"] {
        color: #F7931A;
    }
    .company-pill {
        display: inline-block;
        background-color: #262B36;
        color: #F7931A;
        border-radius: 999px;
        padding: 2px 12px;
        font-size: 0.85em;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("₿ BTC Dormancy Checker")
st.caption("Vind bankregels die naar een bekende crypto-dienst gingen.")
st.info(
    "🔒 **Open-source hulpmiddel om je eigen (mogelijk vergeten) bitcoin-wallet "
    "terug te vinden** — geen dienst waar je bankdata naartoe gestuurd wordt. "
    "Deze app draait volledig lokaal op jouw computer: een geüploade CSV blijft "
    "in het geheugen van dit proces, wordt nergens naar een server gestuurd en "
    "komt nooit in de GitHub-repository terecht. Bekijk de broncode gerust voor "
    "je 'm met echte data gebruikt.",
    icon="🔒",
)

with st.sidebar:
    st.header("Invoer")
    uploaded_file = st.file_uploader("Bank-CSV (datum, bedrag_eur, omschrijving)", type=["csv"])
    use_example = st.button("Gebruik voorbeeld-CSV", use_container_width=True)
    st.caption(
        "Alleen lokale verwerking — zie de privacy-uitleg hierboven en in de README."
    )

    st.divider()
    st.header("Filters")

    try:
        all_companies = load_crypto_companies()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()

    company_names = [c.naam for c in all_companies]
    selected_names = st.multiselect(
        "Crypto-bedrijven", company_names, default=company_names
    )

    st.divider()
    st.caption(
        "Bedrijvenlijst en herkenningspatronen zijn instelbaar in "
        "`config/crypto_companies.json`."
    )


def _resolve_input_path() -> Path | None:
    if uploaded_file is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        tmp.write(uploaded_file.getvalue())
        tmp.close()
        return Path(tmp.name)
    if use_example:
        return EXAMPLE_CSV
    return None


input_path = _resolve_input_path()

if input_path is None:
    st.info(
        "Upload links een bank-CSV, of klik op **Gebruik voorbeeld-CSV** om de "
        "dashboard meteen te proberen.\n\n"
        "Verwacht formaat:\n```csv\ndatum,bedrag_eur,omschrijving\n"
        "2013-11-15,50.00,Bitonic BTC aankoop\n```"
    )
    st.stop()

try:
    bank_rows = load_bank_rows(input_path, service_filter=None)
except Exception as exc:
    st.error(f"Kan CSV niet inlezen: {exc}")
    st.stop()

active_companies = [c for c in all_companies if c.naam in selected_names]
detected = detect_crypto_transactions(bank_rows, active_companies)

st.subheader("Resultaat")

if not detected:
    st.warning(
        f"Geen van de {len(bank_rows)} bankregel(s) matcht een geselecteerd crypto-bedrijf."
    )
    st.stop()

df = pd.DataFrame(
    [
        {
            "Datum": d.bank_row.datum,
            "Bedrag (EUR)": d.bank_row.bedrag_eur,
            "Omschrijving": d.bank_row.omschrijving,
            "Bedrijf": d.bedrijf,
        }
        for d in detected
    ]
).sort_values("Datum")

col1, col2, col3 = st.columns(3)
col1.metric("Gedetecteerde transacties", len(df))
col2.metric("Totaalbedrag", f"€ {df['Bedrag (EUR)'].sum():,.2f}")
col3.metric("Unieke bedrijven", df["Bedrijf"].nunique())

st.markdown("#### Bedrag per bedrijf")
per_bedrijf = df.groupby("Bedrijf")["Bedrag (EUR)"].sum().sort_values(ascending=False)
st.bar_chart(per_bedrijf, color="#F7931A")

st.markdown("#### Transacties over tijd")
per_datum = df.groupby("Datum")["Bedrag (EUR)"].sum()
st.area_chart(per_datum, color="#F7931A")

st.markdown("#### Alle gedetecteerde transacties")
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Bedrag (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
        "Datum": st.column_config.DateColumn(format="YYYY-MM-DD"),
    },
)

st.download_button(
    "Download als CSV",
    df.to_csv(index=False).encode("utf-8"),
    file_name="gedetecteerde_crypto_transacties.csv",
    mime="text/csv",
    use_container_width=False,
)

st.caption(
    "Dit is een herkenning op basis van tekstpatronen in de omschrijving, "
    "geen definitieve match. Wil je ook zien welk bitcoin-adres een aankoop "
    "ontving en of dat adres nog dormant is? Gebruik de volledige pipeline "
    "via `python -m btc_dormancy.cli` (zie README)."
)
