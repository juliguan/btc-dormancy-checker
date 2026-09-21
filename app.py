"""Streamlit-dashboard: upload een bank-CSV en zie welke transacties naar een
bekende crypto-dienst (Bitonic, LiteBit, Bitvavo, ...) gingen.

Start met:
    streamlit run app.py
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from btc_dormancy.bank_csv import load_dashboard_rows
from btc_dormancy.crypto_detector import detect_crypto_transactions, load_crypto_companies

PROJECT_ROOT = Path(__file__).resolve().parent
EXAMPLE_CSV = PROJECT_ROOT / "data" / "voorbeeld_transacties.csv"

# CoinMarketCap-achtig kleurenpalet.
CMC_GREEN = "#16C784"
CMC_RED = "#EA3943"
CMC_GRID = "rgba(255,255,255,0.06)"
CMC_BASELINE = "rgba(255,255,255,0.35)"
CMC_TEXT = "#B0B6C3"
CMC_FONT = "'Inter', 'Segoe UI', -apple-system, sans-serif"

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
        color: #16C784;
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
    div[data-testid="stPlotlyChart"] {
        background-color: #171B24;
        border: 1px solid #262B36;
        border-radius: 10px;
        padding: 8px;
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


def _resolve_csv_source() -> Path | io.StringIO | None:
    """Geeft de bron voor load_dashboard_rows terug. Een upload wordt NOOIT
    naar schijf geschreven — alleen naar een in-memory tekst-stream, die na
    deze run gewoon door Python's garbage collector wordt opgeruimd. Alleen
    de meegeleverde voorbeeld-CSV (onderdeel van deze repo) is een echt pad
    op schijf."""

    if uploaded_file is not None:
        tekst = uploaded_file.getvalue().decode("utf-8-sig")
        return io.StringIO(tekst)
    if use_example:
        return EXAMPLE_CSV
    return None


def _base_layout(fig: go.Figure, hovermode: str = "closest") -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CMC_FONT, color=CMC_TEXT, size=13),
        margin=dict(l=10, r=10, t=10, b=10),
        hoverlabel=dict(
            bgcolor="#1E2330", font_color="#E6E6E6", bordercolor="#262B36"
        ),
        hovermode=hovermode,
        showlegend=False,
        xaxis=dict(
            gridcolor=CMC_GRID, zeroline=False, showline=False,
            tickfont=dict(color=CMC_TEXT),
        ),
        yaxis=dict(
            gridcolor=CMC_GRID, zeroline=False, showline=False,
            tickfont=dict(color=CMC_TEXT), tickprefix="€ ",
        ),
    )
    return fig


def build_timeline_chart(df_sorted: pd.DataFrame, heeft_tijd: bool) -> go.Figure:
    """Eén balk per gedetecteerde transactie, op zijn exacte moment (datum +
    tijd, als de CSV die bevat). Bewust GEEN rood/groen-onderscheid: dit zijn
    allemaal uitgaande aankopen naar een crypto-dienst, er is geen koop/verkoop
    of stijging/daling om mee te contrasteren — dat zou hier misleidend zijn.
    Een vloeiende lijn tussen de punten zou bovendien een trend suggereren die
    er niet is (het zijn losse, onregelmatig verspreide gebeurtenissen, geen
    continue reeks) — vandaar losse balken i.p.v. een lijn/vlakgrafiek."""

    x = df_sorted["Moment"]
    y = df_sorted["Bedrag (EUR)"]
    gemiddelde = float(y.mean())

    hovertemplate = (
        "<b>%{customdata[0]}</b><br>"
        "€ %{y:,.2f} — %{customdata[1]}<extra></extra>"
    )
    customdata = df_sorted[["Bedrijf", "Omschrijving"]].to_numpy()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=y, marker=dict(color=CMC_GREEN), marker_cornerradius=4,
        width=1000 * 60 * 60 * 24 * 3,  # ~3 dagen breed in ms, blijft zichtbaar over jaren
        customdata=customdata, hovertemplate=hovertemplate,
    ))
    fig.add_trace(go.Scatter(
        x=[x.min(), x.max()], y=[gemiddelde, gemiddelde], mode="lines",
        line=dict(color=CMC_BASELINE, width=1, dash="dot"),
        hoverinfo="skip",
    ))
    fig.add_annotation(
        x=x.max(), y=gemiddelde, xanchor="right", yanchor="bottom",
        text=f"gemiddeld: € {gemiddelde:,.2f}", showarrow=False,
        font=dict(color=CMC_TEXT, size=11),
    )

    fig = _base_layout(fig, hovermode="closest")
    fig.update_xaxes(hoverformat="%d %b %Y, %H:%M" if heeft_tijd else "%d %b %Y")
    return fig


def build_bar_chart(per_bedrijf: pd.Series) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=per_bedrijf.index, y=per_bedrijf.values,
        marker=dict(color=CMC_GREEN),
        marker_cornerradius=6,
        hovertemplate="<b>%{x}</b><br>€ %{y:,.2f}<extra></extra>",
    ))
    # Bij weinig categorieën een grotere bargap, anders vult 1-2 balken de
    # hele breedte van de grafiek (ziet er lomp uit); bij veel bedrijven juist
    # een kleinere gap zodat de balken niet te dun worden.
    aantal = len(per_bedrijf)
    bargap = 0.6 if aantal <= 2 else 0.4 if aantal <= 4 else 0.2
    fig.update_layout(bargap=bargap)
    return _base_layout(fig)


csv_source = _resolve_csv_source()

if csv_source is None:
    st.info(
        "Upload links een bank-CSV, of klik op **Gebruik voorbeeld-CSV** om de "
        "dashboard meteen te proberen.\n\n"
        "Verwacht formaat:\n```csv\ndatum,bedrag_eur,omschrijving\n"
        "2013-11-15,50.00,Bitonic BTC aankoop\n```\n\n"
        "Bevat je `datum`-kolom ook een tijd (bv. `2013-11-15 14:32`)? Dan "
        "wordt die getoond in de grafieken — handig om transacties exact te "
        "kunnen natrekken."
    )
    st.stop()

try:
    dashboard_rows = load_dashboard_rows(csv_source)
except Exception as exc:
    st.error(f"Kan CSV niet inlezen: {exc}")
    st.stop()

active_companies = [c for c in all_companies if c.naam in selected_names]
detected = detect_crypto_transactions(dashboard_rows, active_companies)

st.subheader("Resultaat")

if not detected:
    st.warning(
        f"Geen van de {len(dashboard_rows)} bankregel(s) matcht een geselecteerd crypto-bedrijf."
    )
    st.stop()

heeft_tijd = any(d.bank_row.heeft_tijd for d in detected)

df = pd.DataFrame(
    [
        {
            "Moment": d.bank_row.moment,
            "Bedrag (EUR)": d.bank_row.bedrag_eur,
            "Omschrijving": d.bank_row.omschrijving,
            "Bedrijf": d.bedrijf,
        }
        for d in detected
    ]
).sort_values("Moment")

col1, col2, col3 = st.columns(3)
col1.metric("Gedetecteerde transacties", len(df))
col2.metric("Totaalbedrag", f"€ {df['Bedrag (EUR)'].sum():,.2f}")
col3.metric("Unieke bedrijven", df["Bedrijf"].nunique())

if not heeft_tijd:
    st.caption(
        "ℹ️ Geen tijd-component gevonden in de `datum`-kolom — punten hieronder "
        "staan op middernacht. Voeg een tijd toe aan je CSV (bv. "
        "`2013-11-15 14:32`) voor preciezere weergave."
    )

st.markdown("#### Bedrag per bedrijf")
per_bedrijf = df.groupby("Bedrijf")["Bedrag (EUR)"].sum().sort_values(ascending=False)
st.plotly_chart(build_bar_chart(per_bedrijf), use_container_width=True, config={"displayModeBar": False})

st.markdown("#### Transacties over tijd")
st.plotly_chart(build_timeline_chart(df, heeft_tijd), use_container_width=True, config={"displayModeBar": False})

st.markdown("#### Alle gedetecteerde transacties")
tabel_df = df.rename(columns={"Moment": "Datum & tijd"})
st.dataframe(
    tabel_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Bedrag (EUR)": st.column_config.NumberColumn(format="€ %.2f"),
        "Datum & tijd": st.column_config.DatetimeColumn(
            format="YYYY-MM-DD HH:mm" if heeft_tijd else "YYYY-MM-DD"
        ),
    },
)

st.download_button(
    "Download als CSV",
    tabel_df.to_csv(index=False).encode("utf-8"),
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
