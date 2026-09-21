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
from btc_dormancy.translations import language_selector, t

EXAMPLE_CSV = PROJECT_ROOT / "data" / "voorbeeld_transacties.csv"

st.set_page_config(page_title="Kandidaat zoeken — BTC Dormancy Checker", page_icon="₿", layout="wide")

with st.sidebar:
    language_selector()

st.title(t("candidates_title"))
st.caption(t("candidates_caption"))
st.info(t("candidates_privacy_info"), icon="🔒")
st.warning(t("custodial_warning"), icon="⚠️")

with st.sidebar:
    st.header(t("sidebar_input_header"))
    uploaded_file = st.file_uploader(t("upload_label"), type=["csv"], key="candidates_upload")
    if "candidates_csv_mode" not in st.session_state:
        st.session_state.candidates_csv_mode = None  # None | "upload" | "example"
    if uploaded_file is not None:
        st.session_state.candidates_csv_mode = "upload"
    if st.button(t("example_button"), width="stretch", key="candidates_example"):
        st.session_state.candidates_csv_mode = "example"

    st.divider()
    st.header(t("settings_header"))

    services = list_known_services()
    if not services:
        st.error(t("no_addresses_error"))
        st.stop()
    service = st.selectbox(t("service_label"), services)

    margin = st.slider(t("margin_label"), 0.01, 0.20, 0.05, step=0.01)
    date_window_days = st.slider(t("date_window_label"), 0, 5, 1)
    top_n = st.slider(t("top_n_label"), 1, 10, 5)

    st.divider()
    st.caption(t("hotwallets_caption"))


def _resolve_csv_source() -> Path | io.StringIO | None:
    if st.session_state.candidates_csv_mode == "upload" and uploaded_file is not None:
        return io.StringIO(uploaded_file.getvalue().decode("utf-8-sig"))
    if st.session_state.candidates_csv_mode == "example":
        return EXAMPLE_CSV
    return None


csv_source = _resolve_csv_source()

if csv_source is None:
    st.info(t("candidates_upload_prompt"))
    st.stop()

try:
    hot_wallets = load_hot_wallets(service)
except Exception as exc:
    st.error(str(exc))
    st.stop()

try:
    bank_rows = load_bank_rows(csv_source, service_filter=service)
except Exception as exc:
    st.error(t("csv_read_error", exc=exc))
    st.stop()

st.write(t("rows_found", n=len(bank_rows), service=service))

if not bank_rows:
    st.stop()

if not st.button(t("search_button"), type="primary"):
    st.stop()

settings = load_settings()

with st.spinner(t("price_spinner")):
    price_client = HistoricalPriceClient(
        requests_per_minute=settings.requests_per_minute_coingecko,
        timeout=settings.request_timeout,
        max_retries=settings.max_retries,
        fallback_csv_path=PROJECT_ROOT / "config" / "btc_price_fallback.csv",
    )
    estimates = estimate_btc_amounts(bank_rows, price_client, margin=margin)

if len(estimates) < len(bank_rows):
    st.warning(t("price_skip_warning", n=len(bank_rows) - len(estimates), total=len(bank_rows)))

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

progress = st.progress(0.0)
rows_for_table = []

for idx, estimate in enumerate(estimates):
    progress.progress(
        (idx) / max(len(estimates), 1),
        text=t("search_progress", i=idx + 1, n=len(estimates), datum=estimate.bank_row.datum.isoformat()),
    )
    candidates = find_candidates_for_estimate(
        estimate, hot_wallets, mempool_client,
        huidige_eur_per_btc=huidige_eur_per_btc,
        date_window_days=date_window_days,
        top_n=top_n,
    )
    for rang, c in enumerate(candidates, start=1):
        rows_for_table.append({
            t("col_bank_date"): c.bank_row.datum,
            t("col_bank_amount"): c.bank_row.bedrag_eur,
            t("col_rank"): rang,
            t("col_hotwallet"): c.hot_wallet,
            t("col_txhash"): c.tx_hash,
            t("col_txdate"): c.tx_datum,
            t("col_txbtc"): c.tx_btc_bedrag,
            t("col_receive_address"): c.ontvangst_adres,
            t("col_balance"): c.huidig_saldo_btc,
            t("col_value"): c.huidige_waarde_eur,
            t("col_dormant"): c.is_dormant,
            t("col_score"): c.totaal_score,
        })

progress.progress(1.0, text=t("search_done"))
progress.empty()

st.subheader(t("result_header"))

if not rows_for_table:
    st.warning(t("zero_candidates_warning"))
    st.stop()

result_df = pd.DataFrame(rows_for_table)
st.dataframe(
    result_df,
    width="stretch",
    hide_index=True,
    column_config={
        t("col_bank_amount"): st.column_config.NumberColumn(format="€ %.2f"),
        t("col_txbtc"): st.column_config.NumberColumn(format="%.8f"),
        t("col_balance"): st.column_config.NumberColumn(format="%.8f"),
        t("col_value"): st.column_config.NumberColumn(format="€ %.2f"),
        t("col_score"): st.column_config.NumberColumn(format="%.3f"),
    },
)

st.download_button(
    t("download_button"),
    result_df.to_csv(index=False).encode("utf-8"),
    file_name="kandidaten.csv",
    mime="text/csv",
)

st.caption(t("candidates_footer_caption"))
