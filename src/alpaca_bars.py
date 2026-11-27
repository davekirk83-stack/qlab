"""Data only (no orders): 15-min bars for US stocks and commodity ETFs from DK's free Alpaca account (doc 274), for testing DK's long
method on stocks and commodities. Keys come from GitHub secrets ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY (never printed).
Tries the consolidated 'sip' feed (free for history older than 15 minutes on the basic plan), falls back to 'iex'."""
import os, sys, time, json, gzip, urllib.request, urllib.parse
import pandas as pd
KEY, SEC = os.environ["ALPACA_API_KEY_ID"], os.environ["ALPACA_API_SECRET_KEY"]
SYMS = (os.environ.get("SYMS") or "SPY,QQQ,IWM,AAPL,MSFT,NVDA,AMZN,META,GOOGL,TSLA,AMD,NFLX,JPM,XOM,COIN,MSTR,GLD,SLV,USO,UNG,CPER,DBA,GDX").split(",")
START, END = os.environ.get("START", "2021-01-01T00:00:00Z"), pd.Timestamp.utcnow() - pd.Timedelta("1h")
def get(sym, feed):
    rows, tok = [], None
    while True:
        q = {"symbols": sym, "timeframe": "15Min", "start": START, "end": END.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": 10000, "adjustment": "all", "feed": feed}
        if tok: q["page_token"] = tok
        req = urllib.request.Request("https://data.alpaca.markets/v2/stocks/bars?" + urllib.parse.urlencode(q), headers={"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SEC})
        r = json.load(urllib.request.urlopen(req, timeout=60)); rows += r.get("bars", {}).get(sym, []) or []
        tok = r.get("next_page_token")
        if not tok: return rows
        time.sleep(0.35)
os.makedirs("data_alpaca", exist_ok=True)
for s in SYMS:
    for feed in ("sip", "iex"):
        try:
            b = get(s, feed)
            if b:
                d = pd.DataFrame(b).rename(columns={"t": "ts", "o": "open", "h": "high", "l": "low", "c": "close", "v": "vol"})[["ts", "open", "high", "low", "close", "vol"]]
                d.to_csv(f"data_alpaca/{s}_15m.csv.gz", index=False, compression="gzip"); print(s, feed, len(d), d.ts.iloc[0], d.ts.iloc[-1], flush=True); break
        except Exception as e: print(s, feed, "failed:", str(e)[:120], flush=True)
