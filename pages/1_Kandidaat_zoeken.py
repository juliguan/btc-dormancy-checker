"""Streamlit-pagina: zoekt op de blockchain naar kandidaat-ontvangstadressen
voor bankregels, via dezelfde pipeline als `python -m btc_dormancy.cli`.

Dit is de stap die echte netwerkverzoeken doet (mempool.space, blockchain.info,
frankfurter.app, CoinGecko) en dus langzamer is dan de crypto-bedrijf-detectie
op de hoofdpagina — vandaar een expliciete "Zoek kandidaten"-knop i.p.v.
automatisch bij elke wijziging.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from btc_dormancy.bank_csv import load_bank_rows
from btc_dormancy.coingecko import CoinGeckoClient
from btc_dormancy.config import PROJECT_ROOT, list_known_services, load_hot_wallets, load_settings
from btc_dormancy.estimator import estimate_btc_amounts
from btc_dormancy.historical_price import HistoricalPriceClient
from btc_dormancy.matcher import find_candidates_for_estimate
from btc_dormancy.mempool_client import MempoolClient

EXAMPLE_CSV = PROJECT_ROOT / "data" / "voorbeeld_transacties.csv"

st.set_page_config(page_title="Kandidaat zoeken — BTC Dormancy Checker", page_icon="₿", layout="wide")

st.title("🔎 Kandidaat-adressen zoeken")
st.caption(
    "Zoekt op de blockchain naar uitgaande transacties die bij je bankregels "
    "passen, en checkt of het ontvangstadres nog dormant is."
)
st.info(
    "🔒 Zelfde als de hoofdpagina: dit draait volledig lokaal, je CSV blijft in "
    "het geheugen. De enige uitgaande verzoeken gaan naar mempool.space, "
    "blockchain.info, frankfurter.app en CoinGecko — die krijgen alleen "
    "datums, BTC-bedragen en de door jou ingevulde adressen te zien.",
    icon="🔒",
)
st.warning(
    "⚠️ Dit werkt alleen voor **non-custodial** aankopen, waarbij de dienst de "
    "bitcoin rechtstreeks naar een adres van jou stuurde (zoals Bitonic in "
    "2010-2015). Bij een **custodial** exchange (Coinbase, Binance, Bitvavo, "
    "Kraken, ...) blijft gekochte crypto meestal gewoon op je account bij die "
    "dienst staan — er is dan geen aparte blockchain-transactie naar een eigen "
    "adres om te vinden, en deze zoekactie zal terecht 0 kandidaten opleveren. "
    "Log in dat geval gewoon in bij die dienst om je saldo te zien.",
    icon="⚠️",
)

with st.sidebar:
    st.header("Invoer")
    uploaded_file = st.file_uploader("Bank-CSV", type=["csv"], key="candidates_upload")
    if "candidates_csv_mode" not in st.session_state:
        st.session_state.candidates_csv_mode = None  # None | "upload" | "example"
    if uploaded_file is not None:
        st.session_state.candidates_csv_mode = "upload"
    if st.button("Gebruik voorbeeld-CSV", width="stretch", key="candidates_example"):
        st.session_state.candidates_csv_mode = "example"

    st.divider()
    st.header("Instellingen")

    services = list_known_services()
    if not services:
        st.error(
            "Geen `config/known_addresses.json` gevonden. Zie README voor hoe "
            "je die aanmaakt."
        )
        st.stop()
    service = st.selectbox("Dienst", services)

    margin = st.slider("Marge rond geschat BTC-bedrag", 0.01, 0.20, 0.05, step=0.01)
    date_window_days = st.slider("Zoekvenster rond bankdatum (dagen)", 0, 5, 1)
    top_n = st.slider("Max. kandidaten per bankregel", 1, 10, 5)

    st.divider()
    st.caption(
        "Hot-wallet adressen voor elke dienst staan in "
        "`config/known_addresses.json` — vul die aan met echte adressen."
    )


def _resolve_csv_source() -> Path | io.StringIO | None:
    if st.session_state.candidates_csv_mode == "upload" and uploaded_file is not None:
        return io.StringIO(uploaded_file.getvalue().decode("utf-8-sig"))
    if st.session_state.candidates_csv_mode == "example":
        return EXAMPLE_CSV
    return None


csv_source = _resolve_csv_source()

if csv_source is None:
    st.info("Upload links een bank-CSV, of klik op **Gebruik voorbeeld-CSV**.")
    st.stop()

try:
    hot_wallets = load_hot_wallets(service)
except Exception as exc:
    st.error(str(exc))
    st.stop()

try:
    bank_rows = load_bank_rows(csv_source, service_filter=service)
except Exception as exc:
    st.error(f"Kan CSV niet inlezen: {exc}")
    st.stop()

st.write(f"**{len(bank_rows)}** bankregel(s) gevonden die '{service}' bevatten.")

if not bank_rows:
    st.stop()

if not st.button("🔍 Zoek kandidaten", type="primary"):
    st.stop()

settings = load_settings()

with st.spinner("Historische koersen ophalen..."):
    price_client = HistoricalPriceClient(
        requests_per_minute=settings.requests_per_minute_coingecko,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        fallback_csv_path=PROJECT_ROOT / "config" / "btc_price_fallback.csv",
    )
    estimates = estimate_btc_amounts(bank_rows, price_client, margin=margin)

if len(estimates) < len(bank_rows):
    st.warning(
        f"{len(bank_rows) - len(estimates)} van de {len(bank_rows)} bankregel(s) "
        "overgeslagen door ontbrekende koersdata (zie terminal/logs voor details)."
    )

try:
    huidige_eur_per_btc = CoinGeckoClient(
        api_key=settings.coingecko_api_key,
        requests_per_minute=settings.requests_per_minute_coingecko,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
    ).get_current_eur_per_btc()
except Exception:
    huidige_eur_per_btc = None

mempool_client = MempoolClient(
    requests_per_minute=settings.requests_per_minute_mempool,
    timeout=settings.request_timeout,
    max_retries=settings.max_retries,
)

progress = st.progress(0.0, text="Kandidaten zoeken op de blockchain...")
rows_for_table = []

for idx, estimate in enumerate(estimates):
    progress.progress(
        (idx) / max(len(estimates), 1),
        text=f"Bankregel {idx + 1}/{len(estimates)}: {estimate.bank_row.datum.isoformat()}...",
    )
    candidates = find_candidates_for_estimate(
        estimate, hot_wallets, mempool_client,
        huidige_eur_per_btc=huidige_eur_per_btc,
        date_window_days=date_window_days,
        top_n=top_n,
    )
    for rang, c in enumerate(candidates, start=1):
        rows_for_table.append({
            "Bank datum": c.bank_row.datum,
            "Bank bedrag (EUR)": c.bank_row.bedrag_eur,
            "Rang": rang,
            "Hot wallet": c.hot_wallet,
            "Tx hash": c.tx_hash,
            "Tx datum": c.tx_datum,
            "Tx BTC": c.tx_btc_bedrag,
            "Ontvangstadres": c.ontvangst_adres,
            "Huidig saldo (BTC)": c.huidig_saldo_btc,
            "Huidige waarde (EUR)": c.huidige_waarde_eur,
            "Dormant": c.is_dormant,
            "Score": c.totaal_score,
        })

progress.progress(1.0, text="Klaar.")
progress.empty()

st.subheader("Resultaat")

if not rows_for_table:
    st.warning(
        "0 kandidaten gevonden. Mogelijke oorzaken: de hot-wallet adressen in "
        "config/known_addresses.json zijn nog placeholders, de dienst is "
        "custodial (zie waarschuwing hierboven), of er zat geen matchende "
        "transactie binnen de bedrag-/tijdmarge."
    )
    st.stop()

result_df = pd.DataFrame(rows_for_table)
st.dataframe(
    result_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Bank bedrag (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
        "Tx BTC": st.column_config.NumberColumn(format="%.8f"),
        "Huidig saldo (BTC)": st.column_config.NumberColumn(format="%.8f"),
        "Huidige waarde (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
        "Score": st.column_config.NumberColumn(format="%.3f"),
    },
)

st.download_button(
    "Download als CSV",
    result_df.to_csv(index=False).encode("utf-8"),
    file_name="kandidaten.csv",
    mime="text/csv",
)

st.caption(
    "Dit is een shortlist op basis van bedrag- en tijd-heuristieken, GEEN "
    "definitieve match. Verifieer handmatig via een block explorer."
)
