import datetime
from pathlib import Path

from psx import stocks

from .symbols import SYMBOLS

START = datetime.date(2000, 1, 1)
END = datetime.date.today()
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "historical"


def fetch_one(symbol: str):
    print(f"\n=== {symbol} ===")
    try:
        data = stocks(symbol, start=START, end=END)
    except Exception as exc:
        print(f"  FAILED: {exc}")
        return

    if data.empty:
        print("  no rows returned")
        return

    data = data.reset_index()
    data.insert(0, "Symbol", symbol)
    out = OUTPUT_DIR / f"{symbol.lower()}.json"
    data.to_json(out, orient="records", date_format="iso", indent=2)
    print(
        f"  saved {len(data)} rows to {out} "
        f"({data['Date'].min().date()} to {data['Date'].max().date()})"
    )


if __name__ == "__main__":
    for symbol in SYMBOLS:
        fetch_one(symbol)
