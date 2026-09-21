"""Kleine i18n-laag voor het Streamlit-dashboard (Nederlands/Engels).

Gebruik: `from btc_dormancy.translations import t, language_selector` en roep
`language_selector()` één keer aan (bovenaan de sidebar) en `t("key")` overal
waar je vroeger een Nederlandse string had staan.
"""

from __future__ import annotations

import streamlit as st

TRANSLATIONS: dict[str, dict[str, str]] = {
    "nl": {
        # Algemeen / hoofdpagina
        "app_title": "₿ BTC Dormancy Checker",
        "app_caption": "Vind bankregels die naar een bekende crypto-dienst gingen.",
        "privacy_info": (
            "🔒 **Open-source hulpmiddel om je eigen (mogelijk vergeten) bitcoin-wallet "
            "terug te vinden** — geen dienst waar je bankdata naartoe gestuurd wordt. "
            "Deze app draait volledig lokaal op jouw computer: een geüploade CSV blijft "
            "in het geheugen van dit proces, wordt nergens naar een server gestuurd en "
            "komt nooit in de GitHub-repository terecht. Bekijk de broncode gerust voor "
            "je 'm met echte data gebruikt."
        ),
        "sidebar_input_header": "Invoer",
        "upload_label": "Bank-CSV (datum, bedrag_eur, omschrijving)",
        "example_button": "Gebruik voorbeeld-CSV",
        "local_only_caption": "Alleen lokale verwerking — zie de privacy-uitleg hierboven en in de README.",
        "filters_header": "Filters",
        "companies_label": "Crypto-bedrijven",
        "companies_config_caption": (
            "Bedrijvenlijst en herkenningspatronen zijn instelbaar in "
            "`config/crypto_companies.json`."
        ),
        "upload_prompt": (
            "Upload links een bank-CSV, of klik op **Gebruik voorbeeld-CSV** om de "
            "dashboard meteen te proberen.\n\n"
            "Verwacht formaat:\n```csv\ndatum,bedrag_eur,omschrijving\n"
            "2013-11-15,50.00,Bitonic BTC aankoop\n```\n\n"
            "Bevat je `datum`-kolom ook een tijd (bv. `2013-11-15 14:32`)? Dan "
            "wordt die getoond in de grafieken — handig om transacties exact te "
            "kunnen natrekken."
        ),
        "csv_read_error": "Kan CSV niet inlezen: {exc}",
        "result_header": "Resultaat",
        "no_match_warning": "Geen van de {n} bankregel(s) matcht een geselecteerd crypto-bedrijf.",
        "metric_detected": "Gedetecteerde transacties",
        "metric_total": "Totaalbedrag",
        "metric_unique": "Unieke bedrijven",
        "no_time_caption": (
            "ℹ️ Geen tijd-component gevonden in de `datum`-kolom — punten hieronder "
            "staan op middernacht. Voeg een tijd toe aan je CSV (bv. "
            "`2013-11-15 14:32`) voor preciezere weergave."
        ),
        "chart_per_company": "#### Bedrag per bedrijf",
        "chart_over_time": "#### Transacties over tijd",
        "table_header": "#### Alle gedetecteerde transacties",
        "download_button": "Download als CSV",
        "footer_caption": (
            "Dit is een herkenning op basis van tekstpatronen in de omschrijving, "
            "geen definitieve match. Wil je ook zien welk bitcoin-adres een aankoop "
            "ontving en of dat adres nog dormant is? Gebruik de pagina **Kandidaat "
            "zoeken** in de sidebar."
        ),
        "col_datetime": "Datum & tijd",
        "col_amount": "Bedrag (EUR)",
        "col_description": "Omschrijving",
        "col_company": "Bedrijf",
        "avg_label": "gemiddeld",
        # Pagina 2: kandidaat zoeken
        "candidates_title": "🔎 Kandidaat-adressen zoeken",
        "candidates_caption": (
            "Zoekt op de blockchain naar uitgaande transacties die bij je "
            "bankregels passen, en checkt of het ontvangstadres nog dormant is."
        ),
        "candidates_privacy_info": (
            "🔒 Zelfde als de hoofdpagina: dit draait volledig lokaal, je CSV blijft "
            "in het geheugen. De enige uitgaande verzoeken gaan naar mempool.space, "
            "blockchain.info, frankfurter.app en CoinGecko — die krijgen alleen "
            "datums, BTC-bedragen en de door jou ingevulde adressen te zien."
        ),
        "custodial_warning": (
            "⚠️ Dit werkt alleen voor **non-custodial** aankopen, waarbij de dienst de "
            "bitcoin rechtstreeks naar een adres van jou stuurde (zoals Bitonic in "
            "2010-2015). Bij een **custodial** exchange (Coinbase, Binance, Bitvavo, "
            "Kraken, ...) blijft gekochte crypto meestal gewoon op je account bij die "
            "dienst staan — er is dan geen aparte blockchain-transactie naar een eigen "
            "adres om te vinden, en deze zoekactie zal terecht 0 kandidaten opleveren. "
            "Log in dat geval gewoon in bij die dienst om je saldo te zien."
        ),
        "settings_header": "Instellingen",
        "no_addresses_error": (
            "Geen `config/known_addresses.json` gevonden. Zie README voor hoe "
            "je die aanmaakt."
        ),
        "service_label": "Dienst",
        "margin_label": "Marge rond geschat BTC-bedrag",
        "date_window_label": "Zoekvenster rond bankdatum (dagen)",
        "top_n_label": "Max. kandidaten per bankregel",
        "hotwallets_caption": (
            "Hot-wallet adressen voor elke dienst staan in "
            "`config/known_addresses.json` — vul die aan met echte adressen."
        ),
        "candidates_upload_prompt": "Upload links een bank-CSV, of klik op **Gebruik voorbeeld-CSV**.",
        "rows_found": "**{n}** bankregel(s) gevonden die '{service}' bevatten.",
        "search_button": "🔍 Zoek kandidaten",
        "price_spinner": "Historische koersen ophalen...",
        "price_skip_warning": (
            "{n} van de {total} bankregel(s) overgeslagen door ontbrekende "
            "koersdata (zie terminal/logs voor details)."
        ),
        "search_progress": "Bankregel {i}/{n}: {datum}...",
        "search_done": "Klaar.",
        "zero_candidates_warning": (
            "0 kandidaten gevonden. Mogelijke oorzaken: de hot-wallet adressen in "
            "config/known_addresses.json zijn nog placeholders, de dienst is "
            "custodial (zie waarschuwing hierboven), of er zat geen matchende "
            "transactie binnen de bedrag-/tijdmarge."
        ),
        "candidates_footer_caption": (
            "Dit is een shortlist op basis van bedrag- en tijd-heuristieken, GEEN "
            "definitieve match. Verifieer handmatig via een block explorer."
        ),
        "col_bank_date": "Bank datum",
        "col_bank_amount": "Bank bedrag (EUR)",
        "col_rank": "Rang",
        "col_hotwallet": "Hot wallet",
        "col_txhash": "Tx hash",
        "col_txdate": "Tx datum",
        "col_txbtc": "Tx BTC",
        "col_receive_address": "Ontvangstadres",
        "col_balance": "Huidig saldo (BTC)",
        "col_value": "Huidige waarde (EUR)",
        "col_dormant": "Dormant",
        "col_score": "Score",
    },
    "en": {
        "app_title": "₿ BTC Dormancy Checker",
        "app_caption": "Find bank transactions that went to a known crypto company.",
        "privacy_info": (
            "🔒 **Open-source tool to find your own (possibly forgotten) bitcoin "
            "wallet** — not a service you hand your bank data to. This app runs "
            "entirely on your own computer: an uploaded CSV stays in this "
            "process's memory, is never sent to a server, and never ends up in "
            "the GitHub repository. Feel free to check the source before using "
            "it with real data."
        ),
        "sidebar_input_header": "Input",
        "upload_label": "Bank CSV (date, amount_eur, description)",
        "example_button": "Use example CSV",
        "local_only_caption": "Local processing only — see the privacy note above and in the README.",
        "filters_header": "Filters",
        "companies_label": "Crypto companies",
        "companies_config_caption": (
            "The company list and matching patterns can be edited in "
            "`config/crypto_companies.json`."
        ),
        "upload_prompt": (
            "Upload a bank CSV on the left, or click **Use example CSV** to try "
            "the dashboard right away.\n\n"
            "Expected format:\n```csv\ndate,amount_eur,description\n"
            "2013-11-15,50.00,Bitonic BTC purchase\n```\n\n"
            "Does your `date` column also include a time (e.g. `2013-11-15 14:32`)? "
            "It'll show up in the charts — handy for cross-checking transactions "
            "exactly."
        ),
        "csv_read_error": "Could not read CSV: {exc}",
        "result_header": "Result",
        "no_match_warning": "None of the {n} bank row(s) matched a selected crypto company.",
        "metric_detected": "Detected transactions",
        "metric_total": "Total amount",
        "metric_unique": "Unique companies",
        "no_time_caption": (
            "ℹ️ No time component found in the `date` column — points below sit "
            "at midnight. Add a time to your CSV (e.g. `2013-11-15 14:32`) for a "
            "more precise view."
        ),
        "chart_per_company": "#### Amount per company",
        "chart_over_time": "#### Transactions over time",
        "table_header": "#### All detected transactions",
        "download_button": "Download as CSV",
        "footer_caption": (
            "This is a text-pattern match on the description, not a definitive "
            "match. Want to see which bitcoin address a purchase went to, and "
            "whether it's still dormant? Use the **Kandidaat zoeken** page in "
            "the sidebar."
        ),
        "col_datetime": "Date & time",
        "col_amount": "Amount (EUR)",
        "col_description": "Description",
        "col_company": "Company",
        "avg_label": "average",
        "candidates_title": "🔎 Find candidate addresses",
        "candidates_caption": (
            "Searches the blockchain for outgoing transactions that match your "
            "bank rows, and checks whether the receiving address is still dormant."
        ),
        "candidates_privacy_info": (
            "🔒 Same as the main page: this runs entirely locally, your CSV stays "
            "in memory. The only outgoing requests go to mempool.space, "
            "blockchain.info, frankfurter.app and CoinGecko — they only ever see "
            "dates, BTC amounts, and the addresses you entered yourself."
        ),
        "custodial_warning": (
            "⚠️ This only works for **non-custodial** purchases, where the service "
            "sent the bitcoin straight to an address of your own (like Bitonic in "
            "2010-2015). With a **custodial** exchange (Coinbase, Binance, "
            "Bitvavo, Kraken, ...) purchased crypto usually just stays in your "
            "account there — there's no separate blockchain transaction to an "
            "address of yours to find, and this search will correctly return 0 "
            "candidates. In that case, just log in to that service to see your "
            "balance."
        ),
        "settings_header": "Settings",
        "no_addresses_error": (
            "No `config/known_addresses.json` found. See the README for how to "
            "create one."
        ),
        "service_label": "Service",
        "margin_label": "Margin around estimated BTC amount",
        "date_window_label": "Search window around bank date (days)",
        "top_n_label": "Max. candidates per bank row",
        "hotwallets_caption": (
            "Hot-wallet addresses for each service live in "
            "`config/known_addresses.json` — fill it in with real addresses."
        ),
        "candidates_upload_prompt": "Upload a bank CSV on the left, or click **Use example CSV**.",
        "rows_found": "**{n}** bank row(s) found containing '{service}'.",
        "search_button": "🔍 Search candidates",
        "price_spinner": "Fetching historical prices...",
        "price_skip_warning": (
            "{n} of {total} bank row(s) skipped due to missing price data (see "
            "terminal/logs for details)."
        ),
        "search_progress": "Bank row {i}/{n}: {datum}...",
        "search_done": "Done.",
        "zero_candidates_warning": (
            "0 candidates found. Possible causes: the hot-wallet addresses in "
            "config/known_addresses.json are still placeholders, the service is "
            "custodial (see warning above), or no transaction matched within the "
            "amount/time margin."
        ),
        "candidates_footer_caption": (
            "This is a shortlist based on amount and time heuristics, NOT a "
            "definitive match. Verify manually via a block explorer."
        ),
        "col_bank_date": "Bank date",
        "col_bank_amount": "Bank amount (EUR)",
        "col_rank": "Rank",
        "col_hotwallet": "Hot wallet",
        "col_txhash": "Tx hash",
        "col_txdate": "Tx date",
        "col_txbtc": "Tx BTC",
        "col_receive_address": "Receiving address",
        "col_balance": "Current balance (BTC)",
        "col_value": "Current value (EUR)",
        "col_dormant": "Dormant",
        "col_score": "Score",
    },
}


def t(key: str, **kwargs: object) -> str:
    lang = st.session_state.get("lang", "nl")
    text = TRANSLATIONS.get(lang, TRANSLATIONS["nl"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


def language_selector() -> None:
    """Rendert een NL/EN-keuzeknop. Roep dit als eerste in de sidebar aan."""

    if "lang" not in st.session_state:
        st.session_state.lang = "nl"

    options = {"Nederlands": "nl", "English": "en"}
    labels = list(options.keys())
    current_label = "Nederlands" if st.session_state.lang == "nl" else "English"

    choice = st.radio(
        "Language / Taal",
        labels,
        index=labels.index(current_label),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.lang = options[choice]
