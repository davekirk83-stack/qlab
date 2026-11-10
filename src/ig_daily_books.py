"""Daily books on the IG DEMO account (doc 204); since doc 210 also the LIVE core (RSI4, TPS, TOM, SANTA) behind DK's own switch.

The books that passed the standard test (docs 200-203), with the SAME rules as their backtests (src/fifty_ideas.py, fifty_ideas_2.py,
market_search_6.py, ladder_daily_tps.py). One or two per family, so they don't all buy the same dip:
  RSI4        (doc 207, replaced RSI2 #51: same family, corr 0.72, more trades) close > 200-day, RSI(4) < 25 -> buy; sell when RSI(4) > 55;
              max 10 days; stop 3 ATR. At the next open: n1262, +0.275 ATR, t 5.28, 19/26 years
  TPS         close > 200-day, RSI(2) < 25 two closes running -> ladder in on lower closes (rungs 1:2:3:4); out when RSI(2) > 70,
              30 days, or a close 15% below the average price
  TOM        last business day of every month -> buy at the close, hold 3 days, stop 5 ATR (doc 208; replaces TOQ, which it contains)
  SANTA #37   first trading day of 22-24 Dec -> buy at the close, hold 7 days, stop 5 ATR
  HALLO       month-end before Nov..Apr -> buy at the close, hold 21 days, stop 8 ATR (Halloween / sell in May)
  USCL #47    US 500 closed in the top 10% of its range and up 1% -> buy Germany 40 and FTSE 100 at the European open, sell at the close; stop 2 ATR

Jobs (one GitHub Actions run each, .github/workflows/ig-daily.yml). Since doc 206: RSI2 and TPS decide on the FINAL close and trade at the next open
(eu_open for Germany 40 / FTSE 100, us_open 09:35 New York for the US indices and gold); the calendar books stay at the close:
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

MODE = os.environ.get("IG_MODE", "demo").strip().lower()
# LIVE (doc 210, DK 10 Nov 07:27 "start making me reliable small gains on IG however small"): the daily CORE books only, on DK's £500 IG
# spread-bet book, under CAP-021 (amended 4 Nov) limits: <= 2% risk per trade (a trade IG's minimum stake would push over 2% is SKIPPED,
# never oversized), 5x exposure, -4% day stop, -15% floor. Needs IG_MODE=live AND the confirmation string, and DK's own repo switch
# IG_DAILY_LIVE_ENABLED (workflow ig-daily-live.yml). Claude never sets that switch or dispatches the live workflow.
LIVE_CONFIRM = "CAP021-AMENDED-2026-11-10-IG-DAILY-CORE-500"
if MODE not in ("demo", "live"): sys.exit(f"IG_MODE must be demo or live, not {MODE!r}")
if MODE == "live" and os.environ.get("IG_DAILY_LIVE_CONFIRMED", "") != LIVE_CONFIRM: sys.exit("live refused: IG_DAILY_LIVE_CONFIRMED does not match")
LIVE = MODE == "live"
OUT = os.environ.get("IG_OUT", "runs/ig_daily_live" if LIVE else "runs/ig_daily"); os.makedirs(OUT, exist_ok=True)
STATE = f"{OUT}/state.json"; LEDGER = f"{OUT}/trades.csv"
START_EQ = float(os.environ.get("IG_DAILY_START_EQ", "500"))
RISK = 0.01; TPS_RISK = 0.02; EXPO = 5.0
DAY_STOP, FLOOR = 0.96, 0.85
if LIVE:   # doc 212: live money rules come from config/live_pot.json (one place, fractions of the pot, shared with the intraday runner)
    import live_limits as L
    START_EQ, RISK, TPS_RISK, EXPO = L.POT, L.RISK, L.RISK, L.EXPO

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
BOOKS = {"RSI4": IDX + ["GOLD"], "TPS": IDX + ["GOLD"], "TOM": IDX + ["GOLD"], "SANTA": IDX, "HALLO": IDX,
         "TPSS": IDX,   # TPSS = TPS SHORT ladder, only while the US 500 is below its 200-day (doc 221, DK 11:21: demo only)
         "LBS": IDX,    # LBS = dormant long-bear breakdown short (doc 222, DK 11:33: demo only) — wakes only in an established long bear
         "INS": ["US500"]}   # INS = insurance short at each new ALL-TIME closing high of the US 500 (doc 223, DK 11:42: demo, 0.5% risk)
if LIVE: BOOKS = {k: v for k, v in BOOKS.items() if k in L.engines("daily")}   # live books listed in config/live_pot.json (DK-approved)

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
    d["atr"] = tr.rolling(20).mean(); d["ma200"] = d.close.rolling(200).mean(); d["ma5"] = d.close.rolling(5).mean(); d["r2"] = rsi(d.close, 2); d["r4"] = rsi(d.close, 4)
    return d

def entries(d, name):
    """Entry flags for every bar (used live on the last bar, and offline to check against the backtests)."""
    t = d.index; up = d.close > d.ma200
    bme = pd.Series(t == (t + pd.offsets.BMonthEnd(0)), index=t); bqe = pd.Series(t == (t + pd.offsets.BQuarterEnd(0)), index=t)
    s = pd.Series((t.month == 12) & (t.day >= 22) & (t.day <= 24) & (t.dayofweek < 5), index=t); santa = s & ~s.shift(1, fill_value=False)
    nxt = (t + pd.offsets.BDay(1)).month
    return {"RSI4": up & (d.r4 < 25),
            "TPS": up & (d.r2 < 25) & (d.r2.shift(1) < 25),
            "TOM": bme, "SANTA": santa,
            "HALLO": bme & pd.Series(np.isin(nxt, [11, 12, 1, 2, 3, 4]), index=t)}[name]
STOP_ATR = {"RSI4": 3, "TOM": 5, "SANTA": 5, "HALLO": 8, "USCL": 2}
MAXD = {"RSI4": 10, "TPS": 30, "TOM": 3, "SANTA": 7, "HALLO": 21, "TPSS": 30, "LBS": 60, "INS": 60}

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
        self.ig = IGService(u, p, key, acc_type="live" if LIVE else "demo", return_dataframe=False); self.ig.create_session(); self.dry = dry
        sb = [a for a in self.ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"]
        if not sb: raise RuntimeError("no SPREADBET account")
        try: self.ig.switch_account(sb[0]["accountId"], True)
        except Exception as e:
            if "same" not in str(e).lower(): log("switch_account:", e)
        self.m = {}
    def market(self, epic):
        if epic not in self.m: self.m[epic] = self.ig.fetch_market_by_epic(epic)
        return self.m[epic]
    def snap(self, epic): self.m.pop(epic, None); return self.market(epic)["snapshot"]
    def min_size(self, epic): return float(self.market(epic)["dealingRules"]["minDealSize"]["value"])
    def account_notional(self):
        """£ exposure of EVERY open position on the account (both live books), size x level."""
        if self.dry: return 0.0
        return float(sum(float(x["position"]["size"]) * float(x["position"]["level"]) for x in self.ig.fetch_open_positions()["positions"]))
    def account_equity(self):
        """Spread-bet account balance + open P&L (used only as a change from a baseline; never logged on live)."""
        a = [a for a in self.ig.fetch_accounts()["accounts"] if a["accountType"] == "SPREADBET"][0]["balance"]
        return float(a["balance"]) + float(a.get("profitLoss") or 0.0)
    def open_ids(self):
        return {p["position"]["dealId"] for p in self.ig.fetch_open_positions()["positions"]}
    def buy(self, epic, size, stop_dist=None, stop_level=None, direction="BUY", limit_dist=None):
        if self.dry: return {"dealStatus": "DRY", "dealId": f"dry-{epic}-{utcnow():%H%M%S}", "level": None}
        mk = self.market(epic); cc = [c["code"] for c in mk["instrument"]["currencies"]]
        return self.ig.create_open_position(currency_code="GBP" if "GBP" in cc else cc[0], direction=direction, epic=epic, expiry=mk["instrument"]["expiry"],
                                            force_open=True, guaranteed_stop=False, level=None, limit_distance=limit_dist, limit_level=None, order_type="MARKET",
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
    def move_stop(self, deal_id, stop_level, limit_level=None):
        """Amend an open position's stop (e.g. to breakeven), keeping its limit."""
        if self.dry or str(deal_id).startswith("dry-"): return {"dealStatus": "DRY"}
        return self.ig.update_open_position(limit_level=limit_level, stop_level=stop_level, deal_id=deal_id)
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
def size_eq(s):
    """Equity the stakes are sized from: live = the shared pot now (all books' P&L compounded) x this book's share; demo = the sub-book."""
    return s.get("pot_now", START_EQ) * L.share("daily") if LIVE else s["eq"]
def fit(s, stop_pts, atr_ig, mn, name=None):
    """Live (doc 213): (size, want, stop_pts) for a 2%-risk trade. If IG's minimum stake makes the normal stop risk more than 2%, fall back to a
    2 ATR stop (tested: same edge — RSI4 +0.288 vs +0.290, TOM +0.180 vs +0.175 ATR) and take the minimum stake if its risk is within
    max_risk_at_min_stake (config/live_pot.json; = 2% unless DK sets an exception). None = skip."""
    sz, w = size_for(size_eq(s), RISK, stop_pts, mn)
    if not LIVE or sz <= w * 1.0001: return sz, w, stop_pts
    exc = L.C.get("min_stake_exception", {}); on = size_eq(s) < float(exc.get("until_pot", 1e18))   # exceptions end automatically at that pot size
    cap = float(exc.get(name, L.C.get("max_risk_at_min_stake", RISK)) if on else L.C.get("max_risk_at_min_stake", RISK)); st2 = round(min(stop_pts, 2.0 * atr_ig), 1)
    if mn * st2 <= cap * size_eq(s): log(f"fit: minimum {mn}/pt with a 2 ATR stop ({st2} pts) risks £{mn * st2:.2f} ({mn * st2 / size_eq(s):.1%})"); return mn, mn, st2
    log(f"fit: minimum {mn}/pt risks £{mn * st2:.2f} even at 2 ATR (> {cap:.0%}) — skip"); return None
def size_for(eq, risk_frac, stop_pts, mn):
    """(stake actually placed, stake the rules intend). IG's minimum is often bigger than 1% of £500 allows, so the demo places the
    minimum and the sub-book counts the result at the INTENDED size (pnl x intended/placed) - the demo measures fills, not luck of size."""
    want = risk_frac * eq / stop_pts; return max(mn, math.floor(want * 100) / 100), want

def close_pos(ig, s, p, mid, why, day):
    side = p.get("side", 1); r = ig.sell(p["deal_id"], p["size"], direction="SELL" if side == 1 else "BUY"); lvl = r.get("level") or mid
    pnl = r.get("profit"); pnl = float(pnl) if pnl not in (None, "") else side * (float(lvl) - p["entry_ig"]) * p["size"]
    pnl = pnl * p.get("want", p["size"]) / p["size"]; s["eq"] += pnl; s["pos"].remove(p)
    if p["book"] == "TPS": s.setdefault("tps", {}); s["tps"]["realised"] = s["tps"].get("realised", 0.0) + pnl
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
        if p["book"] == "TPS": s.setdefault("tps", {}); s["tps"]["realised"] = s["tps"].get("realised", 0.0) + pnl
        ledger({"closed": day, "book": p["book"], "market": p["market"], "entered": p["entered"], "entry": p["entry_ig"], "exit": round(lvl, 2),
                "size": p["size"], "pnl_gbp": round(pnl, 2), "days": p.get("days", 0), "why": how})
        log(f"CLOSED by IG ({how}): {p['book']} {p['market']} £{pnl:+.2f}")

def open_pos(ig, s, book, name, epic, size, mid, k, stop_pts=None, stop_level=None, extra=None, want=None, risk=None, side=1, limit_pts=None):
    want = size if want is None else want
    if LIVE:
        if not s.get("entries_ok", True): log(f"SKIP {book} {name}: {s.get('stop_why')}"); return None
        if book == "TPS" and s.get("tps", {}).get("stopped"): log(f"SKIP TPS {name}: TPS stopped at its £ limit (DK restarts it)"); return None
        tps_min = book == "TPS" and L.tier(s.get("pot_now", START_EQ)).get("tps_min_stake", False)
        if size > want * 1.0001 and not tps_min: log(f"SKIP {book} {name}: IG minimum {size}/pt is more than {RISK:.0%} risk ({want:.4f}/pt)"); return None
        want = size   # live: the stake placed is the stake counted
    held = ig.account_notional() if LIVE else notional(s)   # live: every book on the account shares one cap on the pot
    if held + want * mid > EXPO * (s.get("pot_now", START_EQ) if LIVE else s["eq"]): log(f"SKIP {book} {name}: exposure cap {EXPO:g}x (whole account)"); return None
    if name in IDX and risk is not None:
        held = sum(q.get("risk", 0.0) for q in s["pos"] if q["market"] in IDX)
        if held + risk > IDX_RISK_CAP * size_eq(s): log(f"SKIP {book} {name}: equity-index risk would be £{held + risk:.2f} > {IDX_RISK_CAP:.0%} of the book"); return None
    kw = {} if side == 1 else {"direction": "SELL"}
    if limit_pts: kw["limit_dist"] = limit_pts
    r = ig.buy(epic, size, stop_dist=stop_pts, stop_level=stop_level, **kw)
    if r.get("dealStatus") not in ("ACCEPTED", "DRY"): log(f"REJECTED {book} {name}: {r.get('reason')}"); return None
    lvl = float(r["level"]) if r.get("level") else mid
    p = {"book": book, "market": name, "deal_id": r["dealId"], "size": size, "entry_ig": lvl, "entered": utcnow().strftime("%Y-%m-%d"), "days": 0,
         "stop_ig": stop_level if stop_level else lvl - side * stop_pts, "k": k, "want": want, "risk": risk or 0.0, "side": side}
    if limit_pts: p["limit_ig"] = lvl + side * limit_pts   # take-profit: above a long's entry, BELOW a short's
    if extra: p.update(extra)
    s["pos"].append(p); log(f"OPEN {'SHORT ' if side == -1 else ''}{book} {name} {size}/pt (counted at {want:.4f}/pt) at {lvl:.1f} stop {p['stop_ig']:.1f}"); return p

def tps_check(ig, s, hist_fn=None):
    """Live (doc 214, DK 10 Nov 08:22): TPS book stop. Realised + open TPS P&L <= -tps_stop (£100 while the pot is under £1,000) ->
    close every TPS position and take no new ladders until DK restarts TPS (set state tps.stopped = false)."""
    t = s.setdefault("tps", {}); today = utcnow().strftime("%Y-%m-%d"); mine = {p["deal_id"]: p for p in s["pos"] if p["book"] == "TPS"}
    bid = {x["position"]["dealId"]: float(x["market"]["bid"]) for x in ig.ig.fetch_open_positions()["positions"] if x["position"]["dealId"] in mine}
    t["open"] = round(sum((bid[d] - p["entry_ig"]) * p["size"] for d, p in mine.items() if d in bid), 2)
    tot = t.get("realised", 0.0) + t["open"]
    if t.get("day") != today: t["day"], t["day_start"] = today, tot
    if t.get("stopped") and L.C.get("risk_tiers", {}).get("tps_auto_restart", False) and hist_fn is not None:
        h = hist_fn("US500"); h = h[h.index < pd.Timestamp(utcnow().date())]
        if len(h) > 200 and h.close.iloc[-1] > h.close.rolling(200).mean().iloc[-1]:
            t["stopped"], t["base"] = False, tot; log(f"TPS RESTART: US 500 back above its 200-day average — fresh £ limit from TPS £{tot:+.2f}")
    tot = tot - t.get("base", 0.0)   # the stop counts from the last (re)start
    lim = L.tps_stop(s.get("pot_now", START_EQ)); log(f"TPS book £{tot:+.2f} (realised {t.get('realised', 0.0):+.2f}, open {t['open']:+.2f}); stop at -£{lim:.0f}{' — STOPPED' if t.get('stopped') else ''}")
    if not t.get("stopped") and tot <= -lim:
        t["stopped"] = True; log(f"TPS STOP: £{tot:.2f} <= -£{lim:.0f} — closing every TPS position; no new ladders until DK restarts TPS")
        for d, p in mine.items():
            try: close_pos(ig, s, p, bid.get(d, p["entry_ig"]), "TPS book stop", utcnow().date())
            except Exception: log("TPS stop close failed:", traceback.format_exc())

# ------------------------------------------------------------------ jobs
OPEN_BOOKS = ("RSI4", "TPS")            # price-based signals: decided on the FINAL daily close, traded at the next open (doc 206 review)
CLOSE_BOOKS = ("TOM", "SANTA", "HALLO")  # date-based signals (known in advance): traded about 20 min before the close
TPS_RUNGS = int(L.C.get("tps_rungs", 4)) if LIVE else 4   # doc 216: 3 rungs keeps ~77% of the profit, halves the worst loss
IDX_RISK_CAP = L.IDX_CAP if LIVE else 0.06   # total risk on the five equity indices at once (they move together: ~2-3 independent bets)

def job_close(ig, s, group, hist_fn):
    """Calendar books: exits after their fixed number of days, entries on their known dates; USCL exits at the European close."""
    day = pd.Timestamp(utcnow().date())
    for name, (tk, epic, g) in MKT.items():
        if g != group: continue
        try:
            snap = ig.snap(epic)
            if snap.get("marketStatus") != "TRADEABLE": log(f"{name}: market {snap.get('marketStatus')} — skipped"); continue
            d, k, mid = today_bar(hist_fn(name), snap, day); b = d.iloc[-1]; atr_ig = b.atr / k
            for p in [p for p in s["pos"] if p["market"] == name and p["book"] in CLOSE_BOOKS]:
                p["days"] = int((d.index > pd.Timestamp(p["entered"])).sum())
                if p["days"] >= MAXD[p["book"]]: close_pos(ig, s, p, mid, f"{p['days']} days", day.date())
            for bk in CLOSE_BOOKS:
                if bk not in BOOKS or name not in BOOKS[bk] or any(q["book"] == bk and q["market"] == name for q in s["pos"]): continue
                if not bool(entries(d, bk).iloc[-1]): continue
                f_ = fit(s, round(STOP_ATR[bk] * atr_ig, 1), atr_ig, ig.min_size(epic), name)
                if f_: sz, w, stop_pts = f_; open_pos(ig, s, bk, name, epic, sz, mid, k, stop_pts=stop_pts, want=w, risk=w * stop_pts)
        except Exception: log(f"{name} failed:", traceback.format_exc())
    if group == "eu":
        for p in [p for p in s["pos"] if p["book"] == "USCL"]:
            try: close_pos(ig, s, p, (lambda sn: (float(sn["bid"]) + float(sn["offer"])) / 2)(ig.snap(MKT[p["market"]][1])), "European close", day.date())
            except Exception: log("USCL close failed:", traceback.format_exc())

def job_open(ig, s, group, hist_fn):
    """Dip books (RSI2, TPS): every decision uses the last FINAL daily bar (yesterday's close); exits, ladder rungs and entries are all
    traded now, at the open. Backtest of exactly this (doc 206): RSI2 t 4.14, 19/26 years; TPS t 4.85, 21/26 years."""
    day = pd.Timestamp(utcnow().date())
    # doc 220 (regime layer, reviewer 2 sec. 4): no NEW dip-book positions (RSI4, TPS first rung) while the US 500 closed below its 200-day.
    # Out of sample 2008-26: RSI4 +303 -> +323 (Sharpe 0.88 -> 0.97), TPS +178 -> +189 (0.51 -> 0.57); exits and open ladders unaffected.
    bear = False
    try:
        sp = hist_fn("US500"); sp = sp[sp.index < day]; bear = bool(sp.close.iloc[-1] < sp.close.rolling(200).mean().iloc[-1])
        if bear: log(f"REGIME: US 500 {sp.close.iloc[-1]:.1f} below its 200-day {sp.close.rolling(200).mean().iloc[-1]:.1f} — no new dip-book entries today")
    except Exception as e: log("regime check failed (no filter today):", e)
    for name, (tk, epic, g) in MKT.items():
        if g != group: continue
        try:
            snap = ig.snap(epic)
            if snap.get("marketStatus") != "TRADEABLE": log(f"{name}: market {snap.get('marketStatus')} — skipped"); continue
            h = hist_fn(name); d = add_ind(h[h.index < day].copy()); b = d.iloc[-1]
            mid = (float(snap["bid"]) + float(snap["offer"])) / 2; k = b.close / mid; atr_ig = b.atr / k
            log(f"{name}: final close {d.index[-1].date()} {b.close:.1f} RSI2 {b.r2:.1f} RSI4 {b.r4:.1f} 5d {b.ma5:.1f} 200d {b.ma200:.1f} ATR {b.atr:.1f} | IG open {mid:.1f}")
            for p in [p for p in s["pos"] if p["market"] == name and p["book"] in OPEN_BOOKS + ("TPSS", "LBS", "INS")]:
                p["days"] = int((d.index >= pd.Timestamp(p["entered"])).sum()); why = None
                if p["book"] in ("RSI4", "RSI2") and b.r4 > 55: why = "RSI(4) > 55"
                if p["book"] == "TPS":
                    rungs = [q for q in s["pos"] if q["book"] == "TPS" and q["market"] == name]
                    avg = sum(q["entry_ig"] * q["size"] for q in rungs) / sum(q["size"] for q in rungs)
                    if b.r2 > 70: why = "RSI2 > 70"
                    elif b.close / k <= avg * 0.85: why = "15% below avg"
                if p["book"] == "TPSS":
                    rungs = [q for q in s["pos"] if q["book"] == "TPSS" and q["market"] == name]
                    avg = sum(q["entry_ig"] * q["size"] for q in rungs) / sum(q["size"] for q in rungs)
                    if b.r2 < 30: why = "RSI2 < 30"
                    elif b.close / k >= avg * 1.15: why = "15% above avg"
                if p["book"] == "LBS" and b.close > d.close.rolling(10).max().shift(1).iloc[-1]: why = "close above the 10-day high"
                if p["book"] == "INS" and not p.get("be") and b.close / k <= p["entry_ig"] - p.get("atr_ig", atr_ig):   # dropped back 1 ATR -> stop to breakeven
                    try: ig.move_stop(p["deal_id"], round(p["entry_ig"], 1), p.get("limit_ig")); p["be"] = True; p["stop_ig"] = p["entry_ig"]; log(f"INS {name}: dropped back 1 ATR — stop moved to breakeven {p['entry_ig']:.1f}")
                    except Exception as e: log("INS breakeven move failed (will close at breakeven instead):", e); p["be"] = True; p["stop_ig"] = p["entry_ig"]
                if p["book"] == "INS" and p.get("be") and mid >= p["entry_ig"]: why = "back to breakeven"
                if why is None and p["days"] >= MAXD[p["book"]]: why = f"{p['days']} days"
                if why: close_pos(ig, s, p, mid, why, day.date())
            tps = [q for q in s["pos"] if q["book"] == "TPS" and q["market"] == name]
            if tps and len(tps) < TPS_RUNGS and b.close < tps[-1].get("sig_close", 1e18):
                n_ = len(tps) + 1
                open_pos(ig, s, "TPS", name, epic, max(ig.min_size(epic), round(tps[0]["unit"] * n_, 2)), mid, k, stop_level=tps[0]["stop_ig"],
                         extra={"unit": tps[0]["unit"], "unitw": tps[0]["unitw"], "sig_close": float(b.close)}, want=tps[0]["unitw"] * n_, risk=0.15 * tps[0]["unitw"] * n_ * mid)
            # TPSS (doc 221, demo only): short ladder mirror of TPS — the market below its 200-day AND the US 500 below its 200-day, RSI(2) > 75 on two
            # closes -> short 10% of the budget; each HIGHER close adds 20/30/40%; exit RSI(2) < 30, 30 days, or 15% above the average short price.
            if "TPSS" in BOOKS and name in BOOKS["TPSS"]:
                ss = [q for q in s["pos"] if q["book"] == "TPSS" and q["market"] == name]
                if ss and len(ss) < TPS_RUNGS and b.close > ss[-1].get("sig_close", -1e18):
                    n_ = len(ss) + 1
                    open_pos(ig, s, "TPSS", name, epic, max(ig.min_size(epic), round(ss[0]["unit"] * n_, 2)), mid, k, stop_level=ss[0]["stop_ig"], side=-1,
                             extra={"unit": ss[0]["unit"], "unitw": ss[0]["unitw"], "sig_close": float(b.close)}, want=ss[0]["unitw"] * n_, risk=0.15 * ss[0]["unitw"] * n_ * mid)
                elif not ss and bear and b.close < b.ma200 and b.r2 > 75 and d.r2.iloc[-2] > 75:
                    mn = ig.min_size(epic); unitw = TPS_RISK * size_eq(s) / (sum(range(1, TPS_RUNGS + 1)) * 0.15 * mid); unit = max(mn, math.floor(unitw * 100) / 100)
                    open_pos(ig, s, "TPSS", name, epic, unit, mid, k, stop_level=round(mid * 1.20, 1), side=-1,
                             extra={"unit": unit, "unitw": unitw, "sig_close": float(b.close)}, want=unitw, risk=0.15 * unitw * mid)
            # LBS (doc 222, demo only): an ESTABLISHED long bear in this market — its 200-day average lower than 60 days ago AND the close >= 15% below the
            # 1-year high — plus close below the 200-day and below the prior 20-day low -> short at the open; exit close above the 10-day high, 60 days; stop 2 ATR.
            if "LBS" in BOOKS and name in BOOKS["LBS"] and not any(q["book"] == "LBS" and q["market"] == name for q in s["pos"]):
                m200 = d.close.rolling(200).mean(); est = m200.iloc[-1] < m200.iloc[-61] and b.close <= 0.85 * d.close.rolling(252).max().iloc[-1]
                if est and b.close < b.ma200 and b.close < d.low.rolling(20).min().shift(1).iloc[-1]:
                    log(f"LBS {name}: established long bear (200-day falling, {100 * (1 - b.close / d.close.rolling(252).max().iloc[-1]):.0f}% below the 1-year high) + 20-day breakdown")
                    sp_ = round(2.0 * atr_ig, 1); sz, w = size_for(size_eq(s), RISK, sp_, ig.min_size(epic))
                    open_pos(ig, s, "LBS", name, epic, sz, mid, k, stop_pts=sp_, want=w, risk=w * sp_, side=-1)
            # INS (doc 223, demo only, DK 11:42-11:47): the US 500 closed at a new ALL-TIME high -> short at the next open, stop 1.5 ATR; once it drops back 1 ATR
            # the stop moves to breakeven; take-profit 3 ATR (IG limit); out after 60 days. With INTRADAY stops, S&P 1962-2026: -6 ATR in 65 years (about free),
            # since 2001 +5, worst year -12; pays a little at most tops (1973 +3, 2007 +6, 2020 +7, 2022 +1). Risk 0.5% of the book.
            if "INS" in BOOKS and name in BOOKS["INS"] and not any(q["book"] == "INS" and q["market"] == name for q in s["pos"]):
                ref = d.close.iloc[:-1].max()
                try:   # long history, only dates BEFORE today's final bar (no look-ahead in replays)
                    hh = pd.read_csv("data_hist/SPX_yahoo.csv", index_col=0, parse_dates=True).Close; ref = max(ref, float(hh[hh.index < d.index[-1]].max())) if name == "US500" else ref
                except Exception: pass
                if b.close > ref:
                    sp_ = round(1.5 * atr_ig, 1); sz, w = size_for(size_eq(s), 0.005, sp_, ig.min_size(epic))
                    log(f"INS {name}: new all-time closing high {b.close:.1f} (previous {ref:.1f}) — insurance short, stop {sp_} pts")
                    open_pos(ig, s, "INS", name, epic, sz, mid, k, stop_pts=sp_, want=w, risk=w * sp_, side=-1, limit_pts=round(3.0 * atr_ig, 1), extra={"atr_ig": float(atr_ig)})
            for bk in OPEN_BOOKS:
                if bear: break
                if bk not in BOOKS or name not in BOOKS[bk] or any(q["book"] == bk and q["market"] == name for q in s["pos"]): continue
                if not bool(entries(d, bk).iloc[-1]): continue
                mn = ig.min_size(epic)
                if bk == "TPS":   # whole ladder (1+2+3+4 = 10 units) loses 2% of the book at the 15% kill
                    unitw = TPS_RISK * size_eq(s) / (sum(range(1, TPS_RUNGS + 1)) * 0.15 * mid); unit = max(mn, math.floor(unitw * 100) / 100)
                    open_pos(ig, s, "TPS", name, epic, unit, mid, k, stop_level=round(mid * 0.80, 1), extra={"unit": unit, "unitw": unitw, "sig_close": float(b.close)},
                             want=unitw, risk=0.15 * unitw * mid)
                else:
                    f_ = fit(s, round(STOP_ATR[bk] * atr_ig, 1), atr_ig, mn, name)
                    if f_: sz, w, stop_pts = f_; open_pos(ig, s, bk, name, epic, sz, mid, k, stop_pts=stop_pts, want=w, risk=w * stop_pts)
        except Exception: log(f"{name} failed:", traceback.format_exc())

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
                sz, w = size_for(size_eq(s), RISK, stop_pts, ig.min_size(epic)); open_pos(ig, s, "USCL", name, epic, sz, mid, k, stop_pts=stop_pts, want=w, risk=w * stop_pts)
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
    sz, want = size_for(size_eq(s), RISK, risk, ig.min_size(GOLD_EPIC))
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
    global STATE, LEDGER, RISK
    job = sys.argv[1]; dry = "--dry" in sys.argv
    if job.startswith("gold"): STATE, LEDGER = f"{OUT}/gold_state.json", f"{OUT}/trades_gold.csv"   # own file: runs in its own concurrency group
    hist_fn = (lambda n: local(n)) if "--local" in sys.argv else (lambda n, c={}: c.setdefault(n, yahoo(MKT[n][0])))
    s = load_state(); log(f"job {job}{' (dry)' if dry else ''}; daily sub-book £{s['eq']:.2f}, open positions {len(s['pos'])}")
    tag = f"{job}:{utcnow():%Y-%m-%d}"
    if not dry and tag in s.setdefault("done", []): log(f"{job} already ran today — exit (backup cron)"); return
    ig = IG(dry); reconcile(ig, s, utcnow().date())
    if LIVE:
        today = utcnow().strftime("%Y-%m-%d")
        if s.get("day") != today: s["day"], s["day_eq"] = today, s["eq"]
        s["entries_ok"], s["stop_why"] = True, ""
        # doc 212: every live book shares the pot (config/live_pot.json): day stop, floor and exposure on the WHOLE account
        if not dry:
            try:
                pot = L.Pot(ig.ig, s, daily_state=s).refresh(); s["pot_now"] = pot.pot; s["entries_ok"], s["stop_why"] = pot.entries_ok()
                RISK = float(L.tier(pot.pot)["risk_per_trade"]); tps_check(ig, s, hist_fn)
                log(f"pot £{pot.pot:.2f} (start £{L.POT:.0f}, all books {pot.change:+.2f}); entries {'on' if s['entries_ok'] else 'OFF: ' + s['stop_why']}")
            except Exception as e: log("account check failed — no new entries this run:", e); s["entries_ok"], s["stop_why"] = False, "account check failed"
        if job.startswith("gold"): log("live: gold London book is demo-only — exit"); return
    if job == "eu_open":
        # USCL removed 10 Nov (doc 209): its edge came from Yahoo's stale FTSE opens (look-ahead); on real DAX prices it loses
        job_open(ig, s, "eu", hist_fn)
    elif job == "us_open": job_open(ig, s, "us", hist_fn)
    elif job in ("eu_close", "us_close"): job_close(ig, s, job[:2], hist_fn)
    elif job == "gold_ldn": job_gold_ldn(ig, s)
    elif job == "gold_flat": job_gold_flat(ig, s)
    if not dry: s["done"] = (s["done"] + [tag])[-30:]
    save_state(s); log(f"done; book £{s['eq']:.2f}, open {[(p['book'], p['market'], p['size']) for p in s['pos']]}")
    open(f"{OUT}/last_{job}.log", "w").write("\n".join(LOG) + "\n")

if __name__ == "__main__":
    main()
