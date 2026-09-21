# BTC Dormancy Checker

CLI-tool die op basis van je bankafschrift (aankopen bij een Nederlandse
niet-custodial dienst zoals Bitonic, 2010-2015) een **shortlist van
kandidaat-ontvangstadressen** genereert: adressen die mogelijk het bitcoin uit
die aankoop hebben ontvangen, en die sindsdien nooit zijn leeggehaald
("dormant").

**Dit is expliciet geen definitieve match.** De tool matcht op bedrag- en
tijd-heuristieken; het resultaat is een geordende lijst kandidaten die je zelf
handmatig moet verifiëren (bv. via een block explorer) voordat je concludeert
dat een adres "het" adres is.

## Hoe het werkt (pipeline)

1. **Bank-CSV inlezen** (`datum,bedrag_eur,omschrijving`), gefilterd op de
   naam van de dienst (bv. "bitonic") in de omschrijving.
2. **Historische EUR/BTC-koers per datum ophalen**, en het bankbedrag omzetten
   naar een geschat BTC-bedrag met een ±5%-marge (instelbaar) voor
   intraday-schommeling.
3. **Uitgaande transacties zoeken** op die datum (± een instelbaar aantal
   dagen) vanaf de geconfigureerde Bitonic hot-wallet adressen, met een
   output-bedrag binnen de geschatte BTC-range.
4. **Dormancy-check**: voor elk kandidaat-ontvangstadres wordt gecontroleerd
   of er ooit vanaf dat adres is uitgegeven.
5. **Scoring & ranking**: kandidaten worden gescoord op bedrag-match en
   tijd-match (dichter bij de bankdatum = hogere score) en de top 3-5 per
   bankregel gaat naar de output.
6. **Output**: een CSV met per bankregel de kandidaten, hun huidige saldo,
   huidige EUR-waarde en dormancy-status.

## Belangrijke afwijking t.o.v. de oorspronkelijke opzet: koersbron

CoinGecko's publieke API is recent gewijzigd en geeft nu een `401` op elke
historische aanvraag ouder dan 365 dagen:

> "Public API users are limited to querying historical data within the past
> 365 days. Upgrade to a paid plan to enjoy full historical data access."

Dat maakt `/coins/bitcoin/history` onbruikbaar voor de 2010-2015 doelperiode
(dit is dus niet alleen een pre-2013-probleem zoals in de oorspronkelijke
opzet werd verwacht — het geldt voor de hele periode). CoinGecko wordt in deze
tool alleen nog gebruikt voor de **huidige** koers (`/simple/price`), die wel
gratis en zonder key beschikbaar blijft.

Voor **historische** koersen combineert de tool twee gratis, key-loze bronnen
(zie [`btc_dormancy/historical_price.py`](btc_dormancy/historical_price.py)):

- **blockchain.info** `/charts/market-price` — dagelijkse gemiddelde USD/BTC-koers
  (data vanaf medio 2010; vóór de eerste liquide markt staat de waarde op 0.0)
- **frankfurter.app** (ECB-koersen) — historische USD→EUR wisselkoers
  (op weekend-/feestdagen wordt de dichtstbijzijnde eerdere handelsdag gebruikt)

Dit is een keten van twee losse bronnen, dus een benadering — vandaar ook de
marge in stap 2. Klopt een datum niet, of wil je een koers uit een andere bron
gebruiken? Vul `config/btc_price_fallback.csv` aan (kolommen: `datum,eur_per_btc`);
die waarde krijgt altijd voorrang.

Beide bronnen zijn met een live call geverifieerd te werken tijdens het bouwen
van deze tool (geen verzonnen endpoints).

## Blockchain-explorer: mempool.space

Voor het zoeken naar transacties en de dormancy-check gebruikt de tool
[mempool.space](https://mempool.space)'s publieke REST API (gratis, geen key
nodig):

- `GET /api/address/{address}` — saldo/ontvangen/uitgegeven totalen →
  dormancy volgt direct uit `spent_txo_sum == 0`.
- `GET /api/address/{address}/txs/chain[/{last_seen_txid}]` — bevestigde
  transacties, 25 per pagina, nieuwste eerst; gepagineerd tot de gezochte
  datum bereikt is.

Beide endpoints zijn tijdens het bouwen tegen echte on-chain data getest
(zie `btc_dormancy/mempool_client.py`).

Een Blockchair-implementatie is bewust **niet** toegevoegd: de exacte
JSON-structuur en paginering van hun `/dashboards/address/{address}`-endpoint,
en de rate limits van de gratis tier, waren niet met zekerheid vast te stellen
zonder een API-key. mempool.space dekt dezelfde functionaliteit (adres-info +
transactiegeschiedenis) volledig en gratis. Wil je alsnog Blockchair
gebruiken (bv. als mempool.space rate-limits gaat opleveren bij zeer actieve
adressen), lever dan een voorbeeld-response van hun address-dashboard endpoint
aan en dan bouw ik die integratie erbij.

**Let op bij zeer actieve hot-wallet adressen**: de tool pagineert
achterwaarts (nieuwste → oudste) tot de gezochte datum. Een adres met
duizenden transacties na de gezochte datum kan dus veel API-calls kosten. Er
zit een veiligheidslimiet op (`max_pages`, standaard 400 pagina's = 10.000
tx's) om dit te begrenzen.

## Installatie

```bash
cd btc_dormancy_checker
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Geen van de `.env`-variabelen is verplicht voor de standaardflow.

## De Bitonic-adressenlijst aanvullen

Bewerk `config/known_addresses.json`:

```json
{
  "bitonic": {
    "hot_wallets": [
      "1EchtBekendBitonicAdresHier...",
      "bc1qNogEenAdres..."
    ]
  }
}
```

Deze lijst begint met placeholder-waarden en moet je zelf aanvullen met
werkelijke Bitonic hot-wallet adressen uit de periode 2010-2015. Manieren om
die te achterhalen:

- **Eigen bankafschrift + oude e-mailbevestigingen van Bitonic**: als je nog
  een orderbevestiging hebt met een tx-hash of het adres waar Bitonic vandaan
  stuurde, kun je dat adres direct opzoeken op [mempool.space](https://mempool.space)
  en het cluster van bijbehorende adressen (via "vaak samen uitgegeven"
  heuristieken op explorers als [walletexplorer.com](https://www.walletexplorer.com))
  aan de lijst toevoegen.
- **walletexplorer.com**: doorzoekbaar op walletlabels; sommige oude
  Nederlandse exchange-wallets zijn daar gelabeld.
- **Eigen chain-analyse**: als je zelf een bekend adres hebt (bv. uit een oude
  transactie-ontvangstbevestiging), kun je met `mempool_client.py` de
  transactiegeschiedenis van dat adres inspecteren en gerelateerde
  hot-wallet-adressen identificeren.

Je kunt ook een ander bestand gebruiken via `--addresses-file`.

## Gebruik

**Fase A — alleen bankdata + koersconversie** (handig om te testen zonder de
blockchain-lookup):

```bash
.venv/bin/python -m btc_dormancy.phase_a --input data/voorbeeld_transacties.csv --service bitonic
```

**Volledige pipeline:**

```bash
.venv/bin/python -m btc_dormancy.cli \
  --input data/voorbeeld_transacties.csv \
  --service bitonic \
  --output output/kandidaten.csv \
  --margin 0.05 \
  --date-window-days 1 \
  --top-n 5
```

### CLI-opties

| Optie | Default | Betekenis |
|---|---|---|
| `--input` | *(verplicht)* | Pad naar bank-CSV |
| `--service` | `bitonic` | Naam van de dienst; filtert bankregels op omschrijving en kiest de adressenlijst |
| `--output` | `output/kandidaten.csv` | Pad naar output-CSV |
| `--margin` | `0.05` | Marge rond het geschatte BTC-bedrag (±5%) |
| `--date-window-days` | `1` | Aantal dagen rond de bankdatum om te doorzoeken (bankverwerkingsdatum ≠ blockchain-datum) |
| `--top-n` | `5` | Max. aantal kandidaten per bankregel in de output |
| `--addresses-file` | `config/known_addresses.json` | Override voor de adressenlijst |

## Input-CSV formaat

Zie [`data/voorbeeld_transacties.csv`](data/voorbeeld_transacties.csv) voor een
werkend voorbeeld:

```csv
datum,bedrag_eur,omschrijving
2013-11-15,50.00,Bitonic BTC aankoop
```

- `datum`: `YYYY-MM-DD`, `DD-MM-YYYY` of `DD/MM/YYYY`
- `bedrag_eur`: `.` of `,` als decimaalteken
- `omschrijving`: vrije tekst; moet de servicenaam bevatten om meegenomen te worden

## Output-CSV formaat

Eén rij per kandidaat (dus meerdere rijen per bankregel), gesorteerd op score:

| Kolom | Betekenis |
|---|---|
| `bank_datum`, `bank_bedrag_eur`, `bank_omschrijving` | Herkomst-bankregel |
| `kandidaat_rang` | 1 = beste match voor deze bankregel |
| `hot_wallet` | Bitonic-adres waar de tx vandaan kwam |
| `tx_hash`, `tx_datum`, `tx_btc_bedrag` | De gevonden on-chain transactie |
| `ontvangst_adres` | Kandidaat-adres dat het bedrag ontving |
| `huidig_saldo_btc`, `huidige_waarde_eur` | Huidig saldo op dat adres |
| `is_dormant` | `True` = nooit meer uitgegeven sinds ontvangst |
| `bedrag_score`, `tijd_score`, `totaal_score` | 0-1, hoger = betere match |

## Rate limiting & retries

Alle externe API-calls (blockchain.info, frankfurter.app, mempool.space,
CoinGecko) lopen via [`btc_dormancy/http_client.py`](btc_dormancy/http_client.py):
een simpele rate limiter (instelbaar per bron via `.env`) plus exponential
backoff op HTTP 429/5xx en netwerkfouten, met `Retry-After` support.

## Projectstructuur

```
btc_dormancy_checker/
├── btc_dormancy/
│   ├── bank_csv.py          # CSV inlezen
│   ├── historical_price.py  # historische EUR/BTC-koers
│   ├── coingecko.py         # huidige EUR/BTC-koers
│   ├── estimator.py         # bedrag -> geschat BTC-bereik
│   ├── mempool_client.py    # mempool.space client
│   ├── matcher.py           # kandidaten zoeken + scoren
│   ├── output_writer.py     # CSV wegschrijven
│   ├── config.py            # .env + adressenlijst laden
│   ├── http_client.py       # rate limiting + retries
│   ├── phase_a.py           # losse test: bank -> BTC-schatting
│   └── cli.py               # volledige pipeline
├── config/
│   ├── known_addresses.json         # Bitonic hot-wallets (zelf aanvullen)
│   └── btc_price_fallback.csv       # handmatige koers-overrides
├── data/voorbeeld_transacties.csv   # dummy testdata
└── output/                          # gegenereerde CSV's
```
