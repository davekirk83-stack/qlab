"""Data only (no orders), doc 276: QQQ trades from DK's free Alpaca account -> 5-min buy/sell volume by the tick rule (each trade is a buy
if it prints above the last different price, a sell if below), to test whether a feed we can get LIVE for free reproduces the CME true
order flow that AuclairsDad's divergence path needs. FEED=iex is what the free plan streams in real time; FEED=sip (all exchanges) is
free for history older than 15 minutes and is the benchmark. Raw trades are not stored, only the 5-min aggregate."""
import os, time, json, urllib.request, urllib.parse
import numpy as np, pandas as pd
KEY, SEC = os.environ["ALPACA_API_KEY_ID"], os.environ["ALPACA_API_SECRET_KEY"]
SYM = os.environ.get("SYM") or "QQQ"; FEED = os.environ.get("FEED") or "iex"
START = os.environ.get("START") or "2026-04-01"; END = os.environ.get("END") or "2026-11-20"
MAXP = int(os.environ.get("MAXPAGES") or "40000")
out = f"data_alpaca/{SYM}_{FEED}_delta_5m.csv.gz"; os.makedirs("data_alpaca", exist_ok=True)
agg = {}; last_px = None; last_dir = 0; pages = 0
for day in pd.bdate_range(START, END):
    tok = None
    s = day.strftime("%Y-%m-%dT00:00:00Z"); e = (day + pd.Timedelta("1D")).strftime("%Y-%m-%dT00:00:00Z")
    while True:
        q = {"symbols": SYM, "start": s, "end": e, "limit": 10000, "feed": FEED}
        if tok: q["page_token"] = tok
        req = urllib.request.Request("https://data.alpaca.markets/v2/stocks/trades?" + urllib.parse.urlencode(q), headers={"APCA-API-KEY-ID": KEY, "APCA-API-SECRET-KEY": SEC})
        for attempt in range(5):
            try: r = json.load(urllib.request.urlopen(req, timeout=60)); break
            except Exception as ex: time.sleep(2 + 3 * attempt); r = None
        if r is None: break
        for tr in (r.get("trades", {}).get(SYM) or []):
            px, sz = tr["p"], tr["s"]
            if last_px is not None and px != last_px: last_dir = 1 if px > last_px else -1
            last_px = px
            b = pd.Timestamp(tr["t"]).floor("5min"); a = agg.setdefault(b, [0, 0, 0, px, px, px, px])
            if last_dir > 0: a[0] += sz
            elif last_dir < 0: a[1] += sz
            a[2] += sz; a[4] = max(a[4], px); a[5] = min(a[5], px); a[6] = px
        tok = r.get("next_page_token"); pages += 1
        if not tok or pages >= MAXP: break
        time.sleep(0.31)
    if day.day == 1 or day == pd.Timestamp(END): print(day.date(), "pages", pages, "bars", len(agg), flush=True)
    if pages >= MAXP: print("page cap reached"); break
d = pd.DataFrame.from_dict(agg, orient="index", columns=["buy", "sell", "vol", "open", "high", "low", "close"]).sort_index()
d["delta"] = d.buy - d.sell; d.index.name = "ts"; d.to_csv(out, compression="gzip"); print("wrote", out, len(d), "bars,", pages, "pages")
