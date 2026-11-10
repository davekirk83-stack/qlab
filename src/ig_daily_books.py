"""Daily books on the IG DEMO account (doc 204). DEMO ONLY: this file refuses to run with IG_MODE=live.

The books that passed the standard test (docs 200-203), with the SAME rules as their backtests (src/fifty_ideas.py, fifty_ideas_2.py,
market_search_6.py, ladder_daily_tps.py). One or two per family, so they don't all buy the same dip:
  RSI2   #51  close > 200-day, RSI(2) < 5, close < 5-day avg -> buy at the close; sell at the close above the 5-day avg; max 10 days; stop 3 ATR
  TPS         close > 200-day, RSI(2) < 25 two closes running -> ladder in on lower closes (rungs 1:2:3:4); out when RSI(2) > 70,
              30 days, or a close 15% below the average price
  TOQ  #39    last business day of a quarter -> buy at the close, hold 3 days, stop 5 ATR
  SANTA #37   first trading day of 22-24 Dec -> buy at the close, hold 7 days, stop 5 ATR
  HALLO       month-end before Nov..Apr -> buy at the close, hold 21 days, stop 8 ATR (Halloween / sell in May)
  USCL #47    US 500 closed in the top 10% of its range and up 1% -> buy Germany 40 and FTSE 100 at the European open, sell at the close; stop 2 ATR

Jobs (one GitHub Actions run each, .github/workflows/ig-daily.yml):
  eu_open   08:05 London   USCL entries
  eu_close  16:10 London   Germany 40 + FTSE 100: exits, then entries; USCL exits
  us_close  15:40 New York US 500, US Tech 100, Wall Street, gold: exits, then entries
"At the close" = about 20 minutes before the cash close, using IG's live price as today's close (the backtest used the official close;
the difference is part of what the demo measures). History comes from Yahoo daily bars; today's bar is Yahoo's previous close scaled by
IG's own change on the day, so IG's price level never mixes with Yahoo's.

Sizing: each trade risks 1% of the £500 sub-book at its stop (min IG stake 0.01/pt); TPS: the whole ladder loses 2% at the 15% kill.
Total open notional capped at 5x the sub-book. Ledger: runs/ig_daily/trades.csv; state: runs/ig_daily/state.json.
"""
import os, sys, json, math, datetime as dt, traceback
import numpy as np, pandas as pd

if os.environ.get("IG_MODE", "demo").strip().lower() != "demo":
    sys.exit("ig_daily_books.py is DEMO ONLY")
OUT = os.environ.get("IG_OUT", "runs/ig_daily"); os.makedirs(OUT, exist_ok=True)
STATE = f"{OUT}/state.json"; LEDGER = f"{OUT}/trades.csv"
START_EQ = float(os.environ.get("IG_DAILY_START_EQ", "500"))
RISK = 0.01; TPS_RISK = 0.02; EXPO = 5.0

MKT = {   # name: (yahoo ticker, IG spread-bet epic, group)
    "US500":  ("^GSPC", "IX.D.SPTRD.DAILY.IP", "us"),
    "NQ":     ("^NDX", "IX.D.NASDAQ.CASH.IP", "us"),
    "WALLST": ("^DJI", "IX.D.DOW.DAILY.IP", "us"),
    "GOLD":   ("GC=F", "CS.D.USCGC.TODAY.IP", "us"),
    "DAX":    ("^GDAXI", "IX.D.DAX.DAILY.IP", "eu"),
    "FTSE":   ("^FTSE", "IX.D.FTSE.DAILY.IP", "eu"),
}
LOCAL = {"US500": "SPX", "NQ": "NDX", "WALLST": "DJI", "GOLD": "GOLD", "DAX": "DAX", "FTSE": "FTSE"}   # data_daily/ names (offline check)
IDX = ["US500", "NQ", "WALLST", "DAX", "FTSE"]
BOOKS = {"RSI2": IDX + ["GOLD"], "TPS": IDX + ["GOLD"], "TOQ": IDX, "SANTA": IDX, "HALLO": IDX}

def utcnow(): return dt.datetime.now(dt.timezone.utc)
LOG = []
def log(*a):
    s = utcnow().strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.append(s)

# ------------------------------------------------------------------ indicators (identical to the backtests)
def rsi(c, n=2):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
def add_ind(d):
    tr = np.maximum(d.high - d.low, np.maximum((d.high - d.close.shift()).abs(), (d.low - d.close.shift()).abs()))
    d["atr"] = tr.rolling(20).mean(); d["ma200"] = d.close.rolling(200).mean(); d["ma5"] = d.close.rolling(5).mean(); d["r2"] = rsi(d.close, 2)
    return d

def entries(d, name):
    """Entry flags for every bar (used live on the last bar, and offline to check against the backtests)."""
    t = d.index; up = d.close > d.ma200
    bme = pd.Series(t == (t + pd.offsets.BMonthEnd(0)), index=t); bqe = pd.Series(t == (t + pd.offsets.BQuarterEnd(0)), index=t)
    s = pd.Series((t.month == 12) & (t.day >= 22) & (t.day <= 24) & (t.dayofweek < 5), index=t); santa = s & ~s.shift(1, fill_value=False)
    nxt = (t + pd.offsets.BDay(1)).month
    return {"RSI2": up & (d.r2 < 5) & (d.close < d.ma5),
            "TPS": up & (d.r2 < 25) & (d.r2.shift(1) < 25),
            "TOQ": bqe, "SANTA": santa,
            "HALLO": bme & pd.Series(np.isin(nxt, [11, 12, 1, 2, 3, 4]), index=t)}[name]
STOP_ATR = {"RSI2": 3, "TOQ": 5, "SANTA": 5, "HALLO": 8, "USCL": 2}
MAXD = {"RSI2": 10, "TPS": 30, "TOQ": 3, "SANTA": 7, "HALLO": 21}

# ------------------------------------------------------------------ data
def yahoo(tk):
    import yfinance as yf
    d = yf.download(tk, period="3y", interval="1d", auto_adjust=False, progress=False)
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d = d.rename(columns=str.lower)[["open", "high", "low", "close"]].dropna(); d.index = pd.to_datetime(d.index).tz_localize(None).normalize()
    return d[~d.index.duplicated(keep="last")].astype(float)
def local(name):
    d = pd.read_csv(f"data_daily/{LOCAL[name]}.csv", index_col=0); d.index = pd.to_datetime(d.index, utc=True).tz_convert(None).normalize()
    return d[~d.index.duplicated(keep="last")][["open", "high", "low", "close"]].astype(float)

def today_bar(hist, snap, day):
    """Yahoo history to yesterday + today's bar from IG's change on the day (scaled to Yahoo's level)."""
    h = hist[hist.index < day]
    bid, off = float(snap["bid"]), float(snap["offer"]); mid = (bid + off) / 2; prev_ig = mid - float(snap["netChange"])
    k = h.close.iloc[-1] / prev_ig
    row = pd.DataFrame({"open": np.nan, "high": max(float(snap["high"]), mid) * k, "low": min(float(snap["low"]), mid) * k, "close": mid * k}, index=[day])
    return add_ind(pd.concat([h, row])), k, mid

# ------------------------------------------------------------------ IG
class IG:
    def __init__(self, dry):
        from trading_ig import IGService
        u, p, key = (os.environ[x].strip() for x in ("IG_USERNAME", "IG_PASSWORD", "IG_API_KEY"))
        self.ig = IGService(u, p, key, acc_type="demo", return_dataframe=False); self.ig.create_session(); self.dry = dry
        sb = [a for a in self.ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"]
        if not sb: raise RuntimeError("no SPREADBET demo account")
        try: self.ig.switch_account(sb[0]["accountId"], True)
        except Exception as e:
            if "same" not in str(e).lower(): log("switch_account:", e)
        self.m = {}
    def market(self, epic):
        if epic not in self.m: self.m[epic] = self.ig.fetch_market_by_epic(epic)
        return self.m[epic]
    def snap(self, epic): self.m.pop(epic, None); return self.market(epic)["snapshot"]
    def min_size(self, epic): return float(self.market(epic)["dealingRules"]["minDealSize"]["value"])
    def open_ids(self):
        return {p["position"]["dealId"] for p in self.ig.fetch_open_positions()["positions"]}
    def buy(self, epic, size, stop_dist=None, stop_level=None):
        if self.dry: return {"dealStatus": "DRY", "dealId": f"dry-{epic}-{utcnow():%H%M%S}", "level": None}
        mk = self.market(epic); cc = [c["code"] for c in mk["instrument"]["currencies"]]
        return self.ig.create_open_position(currency_code="GBP" if "GBP" in cc else cc[0], direction="BUY", epic=epic, expiry=mk["instrument"]["expiry"],
                                            force_open=True, guaranteed_stop=False, level=None, limit_distance=None, limit_level=None, order_type="MARKET",
                                            quote_id=None, size=size, stop_distance=stop_dist, stop_level=stop_level, trailing_stop=False, trailing_stop_increment=None)
    def closed_level(self, p):
        """Exit level of a position IG closed itself (stop or limit), from the transaction history (matched on the opening level)."""
        try:
            now = utcnow(); tx = self.ig.fetch_transaction_history(trans_type="ALL", from_date=(now - dt.timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%S"),
                                                                    to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=200)
            rows = tx.get("transactions", tx) if isinstance(tx, dict) else tx
            for t in rows:
                if str(t.get("transactionType", "")).upper() != "DEAL": continue
                try: ol, cl = float(t.get("openLevel")), float(t.get("closeLevel"))
                except Exception: continue
                if abs(ol - p["entry_ig"]) <= 1e-6 * max(1.0, abs(ol)) + 0.05:
                    return cl, ("IG stop" if p.get("side", 1) * (cl - ol) < 0 else "IG limit") + f" (IG P&L {t.get('profitAndLoss')})"
        except Exception as e: log("transactions:", e)
        return None, None
    def sell(self, deal_id, size, direction="SELL"):
        if self.dry or str(deal_id).startswith("dry-"): return {"dealStatus": "DRY", "level": None, "profit": None}
        return self.ig.close_open_position(deal_id=deal_id, direction=direction, epic=None, expiry=None, level=None, order_type="MARKET", quote_id=None, size=size)

# ------------------------------------------------------------------ book
def load_state():
    s = json.load(open(STATE)) if os.path.exists(STATE) else {}
    s.setdefault("eq", START_EQ); s.setdefault("start", utcnow().strftime("%Y-%m-%d")); s.setdefault("pos", []); return s
def save_state(s): json.dump(s, open(STATE, "w"), indent=1, default=str)
def ledger(row):
    new = not os.path.exists(LEDGER)
    with open(LEDGER, "a") as f:
        if new: f.write("closed,book,market,entered,entry,exit,size,pnl_gbp,days,why\n")
        f.write(",".join(str(row[k]) for k in ("closed", "book", "market", "entered", "entry", "exit", "size", "pnl_gbp", "days", "why")) + "\n")
def notional(s): return sum(p.get("want", p["size"]) * p["entry_ig"] for p in s["pos"] if p.get("entry_ig"))
def size_for(eq, risk_frac, stop_pts, mn):
    """(stake actually placed, stake the rules intend). IG's minimum is often bigger than 1% of £500 allows, so the demo places the
    minimum and the sub-book counts the result at the INTENDED size (pnl x intended/placed) - the demo measures fills, not luck of size."""
    want = risk_frac * eq / stop_pts; return max(mn, math.floor(want * 100) / 100), want

def close_pos(ig, s, p, mid, why, day):
    r = ig.sell(p["deal_id"], p["size"]); lvl = r.get("level") or mid
    pnl = r.get("profit"); pnl = float(pnl) if pnl not in (None, "") else (float(lvl) - p["entry_ig"]) * p["size"]
    pnl = pnl * p.get("want", p["size"]) / p["size"]; s["eq"] += pnl; s["pos"].remove(p)
    ledger({"closed": day, "book": p["book"], "market": p["market"], "entered": p["entered"], "entry": p["entry_ig"], "exit": round(float(lvl), 2),
            "size": p["size"], "pnl_gbp": round(pnl, 2), "days": p.get("days", 0), "why": why})
    log(f"CLOSE {p['book']} {p['market']} {why}: {p['size']}/pt {p['entry_ig']} -> {float(lvl):.1f} = £{pnl:+.2f} (book £{s['eq']:.2f})")

def reconcile(ig, s, day):
    """Positions IG closed at their stop since the last run."""
    if ig.dry: return
    live = ig.open_ids()
    for p in [p for p in s["pos"] if p["deal_id"] not in live]:
        lvl, how = ig.closed_level(p); side = p.get("side", 1)
        if lvl is None: lvl, how = p["stop_ig"], "IG stop (level estimated; check IG history)"
        pnl = side * (lvl - p["entry_ig"]) * p.get("want", p["size"]); s["eq"] += pnl; s["pos"].remove(p)
        ledger({"closed": day, "book": p["book"], "market": p["market"], "entered": p["entered"], "entry": p["entry_ig"], "exit": round(lvl, 2),
                "size": p["size"], "pnl_gbp": round(pnl, 2), "days": p.get("days", 0), "why": how})
        log(f"CLOSED by IG ({how}): {p['book']} {p['market']} £{pnl:+.2f}")

def open_pos(ig, s, book, name, epic, size, mid, k, stop_pts=None, stop_level=None, extra=None, want=None):
    want = size if want is None else want
    if notional(s) + want * mid > EXPO * s["eq"]: log(f"SKIP {book} {name}: exposure cap 5x"); return None
    r = ig.buy(epic, size, stop_dist=stop_pts, stop_level=stop_level)
    if r.get("dealStatus") not in ("ACCEPTED", "DRY"): log(f"REJECTED {book} {name}: {r.get('reason')}"); return None
    lvl = float(r["level"]) if r.get("level") else mid
    p = {"book": book, "market": name, "deal_id": r["dealId"], "size": size, "entry_ig": lvl, "entered": utcnow().strftime("%Y-%m-%d"), "days": 0,
         "stop_ig": stop_level if stop_level else lvl - stop_pts, "k": k, "want": want}
    if extra: p.update(extra)
    s["pos"].append(p); log(f"OPEN {book} {name} {size}/pt (counted at {want:.4f}/pt) at {lvl:.1f} stop {p['stop_ig']:.1f}"); return p

# ------------------------------------------------------------------ jobs
def job_close(ig, s, group, hist_fn):
    day = pd.Timestamp(utcnow().date())
    for name, (tk, epic, g) in MKT.items():
        if g != group: continue
        try:
            snap = ig.snap(epic)
            if snap.get("marketStatus") != "TRADEABLE": log(f"{name}: market {snap.get('marketStatus')} — skipped"); continue
            d, k, mid = today_bar(hist_fn(name), snap, day); b = d.iloc[-1]; atr_ig = b.atr / k
            log(f"{name}: close~{b.close:.1f} RSI2 {b.r2:.1f} 5d {b.ma5:.1f} 200d {b.ma200:.1f} ATR {b.atr:.1f} | IG mid {mid:.1f}")
            # exits first
            for p in [p for p in s["pos"] if p["market"] == name and p["book"] != "USCL"]:
                p["days"] = int((d.index > pd.Timestamp(p["entered"])).sum())
                bk = p["book"]; why = None
                if bk == "RSI2" and b.close > b.ma5: why = "close above 5-day avg"
                if bk == "TPS":
                    rungs = [q for q in s["pos"] if q["book"] == "TPS" and q["market"] == name]
                    avg = sum(q["entry_ig"] * q["size"] for q in rungs) / sum(q["size"] for q in rungs)
                    if b.r2 > 70: why = "RSI2 > 70"
                    elif mid <= avg * 0.85: why = "15% below avg"
                if why is None and p["days"] >= MAXD.get(bk, 99): why = f"{p['days']} days"
                if why: close_pos(ig, s, p, mid, why, day.date())
            # TPS: add a rung on a lower close
            tps = [q for q in s["pos"] if q["book"] == "TPS" and q["market"] == name]
            if tps and len(tps) < 4:
                last = tps[-1]["entry_ig"]
                if mid < last:
                    n_ = len(tps) + 1; mn = ig.min_size(epic)
                    open_pos(ig, s, "TPS", name, epic, max(mn, round(tps[0]["unit"] * n_, 2)), mid, k, stop_level=tps[0]["stop_ig"], extra={"unit": tps[0]["unit"]}, want=tps[0]["unitw"] * n_)
            # entries
            for bk, mk in BOOKS.items():
                if name not in mk or any(q["book"] == bk and q["market"] == name for q in s["pos"]): continue
                if not bool(entries(d, bk).iloc[-1]): continue
                mn = ig.min_size(epic)
                if bk == "TPS":   # whole ladder (1+2+3+4 = 10 units) loses 2% of the book at the 15% kill
                    unitw = TPS_RISK * s["eq"] / (10 * 0.15 * mid); unit = max(mn, math.floor(unitw * 100) / 100)
                    open_pos(ig, s, "TPS", name, epic, unit, mid, k, stop_level=round(mid * 0.80, 1), extra={"unit": unit, "unitw": unitw}, want=unitw)   # disaster stop below the kill
                else:
                    stop_pts = round(STOP_ATR[bk] * atr_ig, 1); sz, w = size_for(s["eq"], RISK, stop_pts, mn); open_pos(ig, s, bk, name, epic, sz, mid, k, stop_pts=stop_pts, want=w)
        except Exception: log(f"{name} failed:", traceback.format_exc())
    if group == "eu":
        for p in [p for p in s["pos"] if p["book"] == "USCL"]:
            try: close_pos(ig, s, p, (lambda sn: (float(sn["bid"]) + float(sn["offer"])) / 2)(ig.snap(MKT[p["market"]][1])), "European close", day.date())
            except Exception: log("USCL close failed:", traceback.format_exc())

def job_eu_open(ig, s, hist_fn):
    spx = add_ind(hist_fn("US500")); spx = spx[spx.index < pd.Timestamp(utcnow().date())]; y = spx.iloc[-1]; prev = spx.close.iloc[-2]
    strong = (y.close - y.low) / (y.high - y.low) > 0.9 and y.close / prev - 1 > 0.01
    log(f"US 500 {spx.index[-1].date()}: close in range {(y.close - y.low) / (y.high - y.low):.2f}, change {100 * (y.close / prev - 1):+.2f}% -> {'SIGNAL' if strong else 'no signal'}")
    if not strong: return
    for name in ("DAX", "FTSE"):
        try:
            epic = MKT[name][1]; snap = ig.snap(epic); d, k, mid = today_bar(hist_fn(name), snap, pd.Timestamp(utcnow().date()))
            stop_pts = round(STOP_ATR["USCL"] * d.atr.iloc[-2] / k, 1)
            if not any(q["book"] == "USCL" and q["market"] == name for q in s["pos"]):
                sz, w = size_for(s["eq"], RISK, stop_pts, ig.min_size(epic)); open_pos(ig, s, "USCL", name, epic, sz, mid, k, stop_pts=stop_pts, want=w)
        except Exception: log(f"USCL {name} failed:", traceback.format_exc())

# ------------------------------------------------------------------ gold London breakout (doc 197/198: WEAK, n104, +8 pts/trade)
GOLD_EPIC = MKT["GOLD"][1]
def num(x):
    try: return float("".join(ch for ch in str(x) if ch in "0123456789.-"))
    except Exception: return 0.0
def job_gold_ldn(ig, s):
    """06:00 UTC: Asian range 01:00-06:00 UTC on IG's own 5-min mid bars; width 0.3-1.6% of price; stop-entry 0.02% beyond the side nearer
    the price; stop at the other side (capped at 0.6%); target 2.5x risk; flat at 19:00 UTC (job gold_flat). Same rules as market_search_3."""
    today = utcnow().strftime("%Y-%m-%d")
    if s.get("gold", {}).get("day") == today: log("gold: already placed today"); return
    try:
        h = ig.ig.fetch_historical_prices_by_epic(GOLD_EPIC, resolution="5Min", numpoints=80)["prices"]
        rows = []
        for b in h:
            t = pd.Timestamp(b.get("snapshotTimeUTC") or b["snapshotTime"].replace("/", "-"), tz="UTC" if b.get("snapshotTimeUTC") else None)
            mid = lambda k: (float(b[k]["bid"]) + float(b[k]["ask"])) / 2
            rows.append((t, mid("highPrice"), mid("lowPrice"), mid("closePrice")))
        d = pd.DataFrame(rows, columns=["t", "high", "low", "close"]).set_index("t")
        if d.index.tz is None: d.index = d.index.tz_localize("Europe/London").tz_convert("UTC")
    except Exception as e:   # the demo account's weekly price-history allowance is shared with the 5-min runner
        log(f"gold: IG history unavailable ({e}) — using Yahoo gold futures 5-min bars scaled to IG's price")
        import yfinance as yf
        y = yf.download("GC=F", period="2d", interval="5m", progress=False)
        if isinstance(y.columns, pd.MultiIndex): y.columns = y.columns.get_level_values(0)
        y = y.rename(columns=str.lower)[["high", "low", "close"]].dropna(); y.index = pd.to_datetime(y.index).tz_convert("UTC")
        sn = ig.snap(GOLD_EPIC); k = ((float(sn["bid"]) + float(sn["offer"])) / 2) / float(y.close.iloc[-1]); d = y * k
    a = d[(d.index.strftime("%Y-%m-%d") == today) & (d.index.hour >= 1) & (d.index.hour < 6)]
    if len(a) < 48: log(f"gold: only {len(a)} Asian bars — no trade"); return
    hi, lo = a.high.max(), a.low.min(); C = float(d.close.iloc[-1]); w = (hi - lo) / C
    log(f"gold: Asian range {lo:.1f}-{hi:.1f} ({100 * w:.2f}% of {C:.1f}), {len(a)} bars")
    if w < 0.003 or w > 0.016: log("gold: range outside 0.3-1.6% — no trade"); s["gold"] = {"day": today, "none": True}; return
    buf = 0.0002 * C
    L = (1, hi + buf, max(lo, hi * (1 - 0.006))); S = (-1, lo - buf, min(hi, lo * (1 + 0.006)))
    side, lvl, st = min((L, S), key=lambda x: abs(x[1] - C)); risk = abs(lvl - st); tgt = lvl + side * 2.5 * risk
    sz, want = size_for(s["eq"], RISK, risk, ig.min_size(GOLD_EPIC))
    log(f"gold: {'BUY' if side == 1 else 'SELL'} STOP at {lvl:.1f}, stop {st:.1f} ({risk:.1f} pts), target {tgt:.1f}; {sz}/pt (counted at {want:.4f})")
    o = {"day": today, "side": side, "level": round(lvl, 1), "stop": round(st, 1), "target": round(tgt, 1), "size": sz, "want": want, "deal_id": None}
    if not ig.dry:
        mk = ig.market(GOLD_EPIC); cc = [c["code"] for c in mk["instrument"]["currencies"]]
        r = ig.ig.create_working_order(currency_code="GBP" if "GBP" in cc else cc[0], direction="BUY" if side == 1 else "SELL", epic=GOLD_EPIC,
                                       expiry=mk["instrument"]["expiry"], guaranteed_stop=False, level=o["level"], size=sz, time_in_force="GOOD_TILL_CANCELLED",
                                       order_type="STOP", force_open=True, stop_level=o["stop"], limit_level=o["target"])
        if r.get("dealStatus") != "ACCEPTED": log("gold: order rejected:", r.get("reason")); return
        o["deal_id"] = r.get("dealId"); log("gold: working order placed", o["deal_id"])
    s["gold"] = o

def job_gold_flat(ig, s):
    """19:00 UTC: cancel the unfilled order, close an open position at market, book the day's real IG P&L on gold."""
    o = s.get("gold") or {}
    if o.get("day") != utcnow().strftime("%Y-%m-%d") or o.get("none") or o.get("booked"): log("gold: nothing to flatten today"); return
    if ig.dry: log("gold: dry — would cancel/close"); return
    try:
        if o.get("deal_id") in {x["workingOrderData"]["dealId"] for x in ig.ig.fetch_working_orders().get("workingOrders", [])}:
            ig.ig.delete_working_order(o["deal_id"]); log("gold: order never filled — cancelled"); o["booked"] = True; return
    except Exception as e: log("gold: working orders:", e)
    for x in ig.ig.fetch_open_positions()["positions"]:
        if x["market"]["epic"] == GOLD_EPIC:
            q = x["position"]; r = ig.sell(q["dealId"], float(q["size"]), direction="SELL" if q["direction"] == "BUY" else "BUY"); log("gold: closed at 19:00", r.get("level"))
    import time; time.sleep(5)
    now = utcnow(); tx = ig.ig.fetch_transaction_history(trans_type="ALL", from_date=now.strftime("%Y-%m-%dT05:50:00"), to_date=now.strftime("%Y-%m-%dT%H:%M:%S"), page_size=50)
    rows = [t for t in (tx.get("transactions", tx) if isinstance(tx, dict) else tx) if str(t.get("transactionType", "")).upper() == "DEAL" and "gold" in str(t.get("instrumentName", "")).lower()]
    pnl_ig = sum(num(t.get("profitAndLoss")) for t in rows); pnl = pnl_ig * o["want"] / o["size"]; s["eq"] += pnl; o["booked"] = True
    ledger({"closed": now.date(), "book": "GOLDLDN", "market": "GOLD", "entered": o["day"], "entry": o["level"], "exit": "", "size": o["size"],
            "pnl_gbp": round(pnl, 2), "days": 0, "why": f"day's IG gold P&L £{pnl_ig:.2f} x intended/placed"})
    log(f"gold: day's IG P&L £{pnl_ig:+.2f} -> counted £{pnl:+.2f} (book £{s['eq']:.2f})")

def main():
    global STATE, LEDGER
    job = sys.argv[1]; dry = "--dry" in sys.argv
    if job.startswith("gold"): STATE, LEDGER = f"{OUT}/gold_state.json", f"{OUT}/trades_gold.csv"   # own file: runs in its own concurrency group
    hist_fn = (lambda n: local(n)) if "--local" in sys.argv else (lambda n, c={}: c.setdefault(n, yahoo(MKT[n][0])))
    s = load_state(); log(f"job {job}{' (dry)' if dry else ''}; daily sub-book £{s['eq']:.2f}, open positions {len(s['pos'])}")
    tag = f"{job}:{utcnow():%Y-%m-%d}"
    if not dry and tag in s.setdefault("done", []): log(f"{job} already ran today — exit (backup cron)"); return
    ig = IG(dry); reconcile(ig, s, utcnow().date())
    if job == "eu_open": job_eu_open(ig, s, hist_fn)
    elif job in ("eu_close", "us_close"): job_close(ig, s, job[:2], hist_fn)
    elif job == "gold_ldn": job_gold_ldn(ig, s)
    elif job == "gold_flat": job_gold_flat(ig, s)
    if not dry: s["done"] = (s["done"] + [tag])[-30:]
    save_state(s); log(f"done; book £{s['eq']:.2f}, open {[(p['book'], p['market'], p['size']) for p in s['pos']]}")
    open(f"{OUT}/last_{job}.log", "w").write("\n".join(LOG) + "\n")

if __name__ == "__main__":
    main()
