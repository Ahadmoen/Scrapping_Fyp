from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import requests

from .symbols import SYMBOLS

TZ = ZoneInfo("Asia/Karachi")
BASE_URL = "https://dps.psx.com.pk/timeseries/int"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "live"


def fetch_today_ticks(symbol: str) -> pd.DataFrame:
    response = requests.get(f"{BASE_URL}/{symbol}", timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != 1 or not payload.get("data"):
        return pd.DataFrame()

    df = pd.DataFrame(payload["data"], columns=["ts", "Price", "Volume"])
    df["Datetime"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.tz_convert(TZ)
    return df.set_index("Datetime").sort_index()[["Price", "Volume"]]


def to_hourly_bars(ticks: pd.DataFrame) -> pd.DataFrame:
    ohlc = ticks["Price"].resample("1h").ohlc()
    volume = ticks["Volume"].resample("1h").sum()
    bars = ohlc.join(volume).dropna(subset=["open"])
    bars.columns = ["Open", "High", "Low", "Close", "Volume"]
    bars.index.name = "Date"
    return bars


def merge_with_existing(path: Path, new_bars: pd.DataFrame) -> pd.DataFrame:
    if not path.exists():
        return new_bars
    prev = pd.read_json(path, orient="records", convert_dates=["Date"])
    if prev.empty:
        return new_bars
    prev["Date"] = pd.to_datetime(prev["Date"], utc=True).dt.tz_convert(TZ)
    combined = pd.concat([prev, new_bars], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Symbol", "Date"], keep="last")
    return combined.sort_values("Date").reset_index(drop=True)


def process(symbol: str, today_pkt) -> None:
    try:
        ticks = fetch_today_ticks(symbol)
    except Exception as exc:
        print(f"{symbol}: fetch failed: {exc}")
        return

    if ticks.empty:
        print(f"{symbol}: endpoint returned no data")
        return

    session_date = ticks.index[-1].date()
    if session_date != today_pkt:
        print(f"{symbol}: stale session ({session_date}), skipping — market closed")
        return

    bars = to_hourly_bars(ticks).reset_index()
    bars.insert(0, "Symbol", symbol)

    out = OUTPUT_DIR / f"{symbol.lower()}_live.json"
    merged = merge_with_existing(out, bars)
    merged.to_json(out, orient="records", date_format="iso", indent=2)
    print(f"{symbol}: saved {len(merged)} hourly bars → {out} (latest {merged['Date'].iloc[-1]})")


def main() -> None:
    today_pkt = datetime.now(TZ).date()
    print(f"PKT today: {today_pkt}")
    for symbol in SYMBOLS:
        process(symbol, today_pkt)


if __name__ == "__main__":
    main()
