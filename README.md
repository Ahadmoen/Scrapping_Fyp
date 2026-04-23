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

### `news_scraper.py` — news + sentiment-prep
Fetches news via **Google News RSS** for each symbol (using company name + aliases) plus a set of macro / world queries. Extracts per-article: date, heading, link, matched keywords, sentence context around those keywords, market/industry tag, and publisher platform. Leaves the `Sentiment` field null for later NLP labelling (excellent / good / neutral / bad / worst).

```bash
python news_scraper.py
```

Output: `{symbol}_news.json` per company + `general_news.json` for macro/world news. Re-runnable; dedupes by article link.

Row format:
```json
{
  "Symbol": "OGDC",
  "Date": "2026-04-23T04:04:00Z",
  "Heading": "OGDC revives Attock's Jand-1 well, output triples",
  "Link": "https://news.google.com/rss/articles/...",
  "Keywords": ["oil", "gas", "well", "exploration"],
  "KeywordContext": ["OGDC revives Attock's Jand-1 well, output triples"],
  "Market": "Oil & Gas",
  "Platform": "Mettis Global",
  "Sentiment": null
}
```

## Automating hourly runs (cron)

Runs at `:05` past every hour, Monday–Friday, 9 AM–4 PM PKT, plus a daily news pull at 6 PM:

```
5 9-16 * * 1-5  cd ~/Scrapping_Fyp && /usr/bin/python3 live_scraper.py >> live.log 2>&1
0 18   * * *    cd ~/Scrapping_Fyp && /usr/bin/python3 news_scraper.py >> news.log 2>&1
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
- News: `https://news.google.com/rss/search` (Google News RSS — aggregates BBC, Profit, Dawn, Business Recorder, Reuters, Bloomberg, Mettis, ProPakistani, etc.)

PSX DPS endpoints are public. There is no official intraday history API — accumulated hourly bars across days only exist once the scraper has been running. Google News RSS returns ~100 items per query and covers the last few weeks.
