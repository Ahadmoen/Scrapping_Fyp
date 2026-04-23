# Scrapping_Fyp

PSX (Pakistan Stock Exchange) data scrapers for 20 major companies.

## Symbols tracked

SILK, OGDC, PPL, LUCK, ENGRO, HBL, UBL, MCB, NBP, FFC, HUBC, PSO, TRG, SYS, MEBL, BAHL, POL, MARI, DGKC, NESTLE

Edit [symbols.py](symbols.py) to add or remove tickers.

## Scripts

### `my_script.py` — historical (lifetime) data
Fetches end-of-day OHLCV bars from 2000 to today for every symbol, one JSON per symbol.

```bash
python my_script.py
```

Output: `silk.json`, `ogdc.json`, ... (one row per trading day).

Takes 15–20 minutes because PSX's historical endpoint is scraped month-by-month.

### `live_scraper.py` — live intraday hourly data
Fetches today's ticks from the PSX live endpoint, resamples to 1-hour OHLCV bars in PKT, and merges into per-symbol live files.

```bash
python live_scraper.py
```

Output: `silk_live.json`, `ogdc_live.json`, ...

Safe to run repeatedly — merge/dedupe logic upgrades partial bars to complete as the hour progresses. Skips writing when the market is closed (compares the endpoint's session date against today in Asia/Karachi).

## Automating hourly runs (cron)

Runs at `:05` past every hour, Monday–Friday, 9 AM–4 PM PKT:

```
5 9-16 * * 1-5  cd ~/Scrapping_Fyp && /usr/bin/python3 live_scraper.py >> live.log 2>&1
```

## Output format

Each row across all JSON files:

```json
{
  "Symbol": "OGDC",
  "Date": "2026-04-23T04:00:00.000Z",
  "Open": 320.0,
  "High": 321.2,
  "Low":  319.0,
  "Close": 320.5,
  "Volume": 228903
}
```

## Setup

```bash
pip install -r requirements.txt
```

The bundled `psx/` package is a local copy of [MuhammadAmir5670/psx-data-reader](https://github.com/MuhammadAmir5670/psx-data-reader) with a small patch to skip empty/malformed month tables.

## Data source

- Historical EOD: `https://dps.psx.com.pk/historical` (POST, HTML table)
- Live intraday ticks: `https://dps.psx.com.pk/timeseries/int/{SYMBOL}` (JSON)

Both are public PSX DPS endpoints. There is no official intraday history API — accumulated hourly bars across days only exist once the scraper has been running.
