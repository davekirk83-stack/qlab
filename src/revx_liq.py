"""
REVOLUT X — LIQ book: BTC liquidation-cluster ladder (doc 225; DK 10 Nov 22:20 "get things trading").
Rules = doc 225 (WEAK on the standard test: +0.23%/trade, 63% win, one position at a time) + addendum (half off at +1%, no breakeven):
  levels : DK's "Liquidations" indicator rebuilt (pivots 5 left / 2 right on 15-min bars, volume vs its 1000-bar average, leverage tiers);
           volume from Coinbase BTC-USD 15-min candles (Binance blocks US servers; Revolut X's own volume as fallback).
  setup  : the highest LIVE long-liquidation level below price that still has another live long level below it within 10%, and a live
           short level above within 10%. Only when BTC's previous daily close is above its 200-day, and not in the CPI blackout
           (08:15-10:30 New York on CPI days; any open trade is closed before 08:30).
  orders : resting limit BUYs (maker, 0% fee): half the trade budget at the level, half 1% lower.
  exits  : resting limit SELLs: half at +1%, the rest at +3% above the level; stop 4% under the level (checked every 15 min, market sell);
           3 days max (market sell). One trade at a time.
  size   : £50 per trade (10% of the £500 Revolut X book, CAP-021); book -15% from start -> halt (back to paper, DK decides).
Modes: dry = no orders, fills simulated on Revolut X 15-min bars, runs/revx_liq_dry/
       live = DK's Revolut X account, only when DK sets REVX_LIQ_LIVE_ENABLED=true (workflow revx-liq.yml); runs/revx_liq_live/
Toxicity skip from the research (needs taker buy/sell volume) is not available from these feeds — left out in v1.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, math, time, re, datetime as dt, urllib.request
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("QLAB_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TIERS = [(100, .20, .0049, .0051), (50, .10, .0147, .0155), (25, .05, .0338, .0370), (10, .025, .0467, .0511), (5, .0125, .06115, .06705)]
TRADE_GBP, USD_PER_GBP, BOOK_GBP, BOOK_STOP = 50.0, 1.27, 500.0, 0.15
RUNG2, TP1, TP2, STOP, HOLD_H = 0.01, 0.01, 0.03, 0.04, 72
MAXSLOTS = 3          # DK 11 Nov: bids at up to 3 clusters at once (doc 225 'all taps' version: ~3x the trades, same +0.23%/trade); CAP-021 allows 10 x 10%
TAKER, SLIP = 0.0009, 0.0005
SYM = "BTC-USD"

def log(*a): print(dt.datetime.utcnow().strftime("%H:%M:%S"), *a, flush=True)
def utcnow(): return pd.Timestamp.utcnow()

# ------------------------------------------------------------------ data
def _get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))
def coinbase(n=1400):
    end = utcnow().floor("15min"); out = []
    while len(out) < n:
        st = end - pd.Timedelta(minutes=15 * 300)
        r = _get(f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=900&start={st.isoformat()}&end={end.isoformat()}")
        if not r: break
        out += r; end = st; time.sleep(0.4)
    d = pd.DataFrame(out, columns=["t", "low", "high", "open", "close", "vol"]).drop_duplicates("t")
    d.index = pd.to_datetime(d.t, unit="s", utc=True); return d[["open", "high", "low", "close", "vol"]].astype(float).sort_index()
def revx15():
    import paperbook14 as B
    d = pd.DataFrame(B.rx_get(f"1.0/public/candles/{SYM}?interval=15")["data"]); d.index = pd.to_datetime(d.start, unit="ms", utc=True)
    return d[["open", "high", "low", "close", "volume"]].rename(columns={"volume": "vol"}).astype(float).sort_index()
def closed(d): return d[d.index + pd.Timedelta(minutes=15) <= utcnow()]

def levels(d):
    """Live long and short liquidation levels at the last closed bar: list of (level, leverage)."""
    H, L, V = d.high.values, d.low.values, d.vol.values; N = len(d)
    avg = pd.Series(V).rolling(1000, min_periods=400).mean().values; longs, shorts = [], []
    for i in range(5, N - 2):
        if not np.isfinite(avg[i]) or avg[i] <= 0: continue
        r = V[i] / avg[i] - 1; tier = next(((lev, lp, sp) for lev, thr, lp, sp in TIERS if r > thr), None)
        if not tier: continue
        lev, lp, sp = tier
        if L[i] == L[i - 5:i + 3].min():
            lvl = L[i] * (1 - lp)
            if not (L[i + 2:] <= lvl).any(): longs.append((lvl, lev))
        if H[i] == H[i - 5:i + 3].max():
            lvl = H[i] * (1 + sp)
            if not (H[i + 2:] >= lvl).any(): shorts.append((lvl, lev))
    return longs, shorts

def regime_ok():
    import revx_tps as R
    dd = R.daily("BTC"); ma = dd.close.rolling(200).mean()
    return bool(dd.close.iloc[-1] > ma.iloc[-1]), float(dd.close.iloc[-1]), float(ma.iloc[-1])

def cpi_times():
    s = set()
    try: s |= set(json.load(open(f"{ROOT}/runs/event_blackouts.json")).get("cpi", []))
    except Exception: pass
    try: s |= set(re.search(r'CPI = """(.*?)"""', open(f"{ROOT}/src/news_fade_test.py").read(), re.S).group(1).split())
    except Exception: pass
    return sorted(pd.Timestamp(x + " 08:30", tz="America/New_York").tz_convert("UTC") for x in s)
def cpi_state(now, cpis):
    """('block', release) from 08:15 to 10:30 NY on a CPI day; ('flat', release) if a release falls within the next 15 min of 08:15."""
    for c in cpis:
        if c - pd.Timedelta(minutes=15) <= now <= c + pd.Timedelta(hours=2): return "block", c
        if c - pd.Timedelta(minutes=30) <= now < c - pd.Timedelta(minutes=15): return "flat", c
    return None, None

def pick(price, longs, shorts, used=()):
    """The setup level: highest live long level below price with another live long level below it within 10%, and a short level above within 10%."""
    for lvl, lev in sorted(longs, reverse=True):
        if lvl >= price or round(lvl, 2) in used: continue
        below = [x for x, _ in longs if lvl * 0.90 < x < lvl]; above = [x for x, _ in shorts if lvl < x < lvl * 1.10]
        if below and above: return lvl, lev
    return None, None

# ------------------------------------------------------------------ executors
class DryEx:
    """Simulated resting orders, filled on Revolut X 15-min bars after they are placed (buy: low <= price; sell: high >= price)."""
    def __init__(s, st): s.st = st; st.setdefault("orders", {}); st.setdefault("oid", 0)
    def limit(s, side, qty, px):
        s.st["oid"] += 1; k = f"d{s.st['oid']}"; s.st["orders"][k] = {"side": side, "qty": qty, "px": px, "filled": 0.0, "placed": str(utcnow())}; return k
    def cancel(s, k): s.st["orders"].pop(k, None)
    def status(s, k):
        o = s.st["orders"].get(k); return (o["filled"], o["px"]) if o else (0.0, 0.0)
    def sim(s, bars):
        for k, o in s.st["orders"].items():
            if o["filled"] >= o["qty"]: continue
            b = bars[bars.index > pd.Timestamp(o["placed"]).floor("15min")]
            if len(b) and ((o["side"] == "buy" and b.low.min() <= o["px"]) or (o["side"] == "sell" and b.high.max() >= o["px"])): o["filled"] = o["qty"]
    def market_sell(s, qty, ref): return qty, ref * (1 - SLIP)

class LiveEx(DryEx):
    """Revolut X: GTC limit orders (maker 0%), market exits as IOC limits 1% through (taker 0.09%). Keys: DK's GitHub secrets only."""
    def __init__(s, st):
        super().__init__(st); from revx_client import RevX; s.rx = RevX()
        f = f"{ROOT}/runs/revx_live/pairs.json"; cfg = json.load(open(f)) if os.path.exists(f) else s.rx.pairs()
        s.step = float(cfg.get("BTC/USD", {}).get("base_step", "0.00000001"))
    def _q(s, q): dp = max(0, -int(math.floor(math.log10(s.step)))); v = math.floor(q / s.step + 1e-9) * s.step; return f"{v:.{dp}f}", v
    def limit(s, side, qty, px):
        qs, qv = s._q(qty)
        r = s.rx.place(SYM, side, base_size=qs, price=f"{px:.2f}", tif="gtc", post_only=True); d = r.get("data", r)
        k = d.get("venue_order_id") or d.get("id"); s.st["orders"][k] = {"side": side, "qty": qv, "px": px, "filled": 0.0, "placed": str(utcnow())}; return k
    def cancel(s, k):
        try: s.rx.cancel(k)
        except Exception as e: log("cancel", k, str(e)[:120])
        s.st["orders"].pop(k, None)
    def status(s, k):
        try: o = s.rx.order(k); o = o.get("data", o); q = float(o.get("filled_quantity") or 0); p = float(o.get("average_fill_price") or 0)
        except Exception as e: log("status", k, str(e)[:120]); return s.st["orders"].get(k, {}).get("filled", 0.0), 0.0
        if k in s.st["orders"]: s.st["orders"][k]["filled"] = q
        return q, p
    def sim(s, bars): pass
    def market_sell(s, qty, ref):
        qs, qv = s._q(qty)
        if qv <= 0: return 0.0, 0.0
        r = s.rx.place(SYM, "sell", base_size=qs, price=f"{ref * 0.99:.2f}", tif="ioc"); d = r.get("data", r); k = d.get("venue_order_id") or d.get("id")
        for _ in range(6):
            time.sleep(1.5); o = s.rx.order(k); o = o.get("data", o)
            if o.get("status") in ("filled", "cancelled", "rejected", "partially_filled"): break
        return float(o.get("filled_quantity") or 0), float(o.get("average_fill_price") or 0)

# ------------------------------------------------------------------ the book
def slot_step(st, slot, ex, px, now, new, longs, shorts, bull, cs, used):
    tr, pend = slot.get("trade"), slot.get("pending")
    # 1. pending buys: filled? -> trade
    if pend and not tr:
        q1, p1 = ex.status(pend["o1"]); q2, p2 = ex.status(pend["o2"])
        if q1 > 0 or q2 > 0:
            lvl = pend["lvl"]; tr = {"lvl": lvl, "opened": str(now), "o2": pend["o2"] if q2 < pend["q2"] else None, "q": q1 + q2,
                                     "cost": q1 * (p1 or lvl) + q2 * (p2 or lvl * (1 - RUNG2)), "rung2": q2 > 0, "tp1_done": False, "pnl": 0.0}
            if not q1: ex.cancel(pend["o1"])
            tr["tp1"] = ex.limit("sell", tr["q"] / 2, lvl * (1 + TP1)); tr["tp2"] = ex.limit("sell", tr["q"] / 2, lvl * (1 + TP2))
            log(f"FILLED at the {lvl:,.0f} cluster: {tr['q']:.6f} BTC; sells resting at {lvl * (1 + TP1):,.0f} (half) and {lvl * (1 + TP2):,.0f}; stop {lvl * (1 - STOP):,.0f}")
            pend = None
    # 2. open trade: rung 2, take-profits, stop, time, CPI
    if tr:
        lvl = tr["lvl"]
        if tr.get("o2"):
            q2, p2 = ex.status(tr["o2"])
            if q2 > 0:
                tr["q"] += q2; tr["cost"] += q2 * (p2 or lvl * (1 - RUNG2)); tr["rung2"] = True; tr["o2"] = None
                ex.cancel(tr["tp2"]); rem = tr["q"] - (tr.get("sold", 0) if tr["tp1_done"] else ex.st["orders"].get(tr["tp1"], {}).get("qty", 0))
                tr["tp2"] = ex.limit("sell", max(rem, 0), lvl * (1 + TP2)); log(f"rung 2 filled at {lvl * (1 - RUNG2):,.0f}; target order resized")
        if not tr["tp1_done"]:
            q, p = ex.status(tr["tp1"])
            if q > 0: tr["tp1_done"] = True; tr["pnl"] += q * (p or lvl * (1 + TP1)); tr["sold"] = tr.get("sold", 0) + q; log(f"half off at {lvl * (1 + TP1):,.0f}")
        q, p = ex.status(tr["tp2"]); why = None
        if q > 0 and q >= ex.st["orders"].get(tr["tp2"], {}).get("qty", q): tr["pnl"] += q * (p or lvl * (1 + TP2)); tr["sold"] = tr.get("sold", 0) + q; why = "target +3%"
        low = new.low.min() if len(new) else px
        if not why and low <= lvl * (1 - STOP): why = "stop -4%"
        if not why and now - pd.Timestamp(tr["opened"]) >= pd.Timedelta(hours=HOLD_H): why = "3 days"
        if not why and cs == "flat": why = "CPI release"
        if why:
            for k in (tr.get("tp1"), tr.get("tp2"), tr.get("o2")):
                if k and k in st["orders"]: ex.cancel(k)
            rest = tr["q"] - tr.get("sold", 0)
            if rest > 1e-9:
                ref = lvl * (1 - STOP) if why == "stop -4%" else px; qs, ps = ex.market_sell(rest, ref); tr["pnl"] += qs * ps * (1 - TAKER)
            pnl = tr["pnl"] - tr["cost"]; st["eq_usd"] += pnl
            st["closed"].append({"lvl": round(lvl, 2), "opened": tr["opened"], "closed": str(now), "rung2": tr["rung2"], "why": why,
                                 "pnl_usd": round(pnl, 2), "pnl_pct": round(100 * pnl / tr["cost"], 3)})
            log(f"EXIT ({why}): ${pnl:+.2f} ({100 * pnl / tr['cost']:+.2f}%)"); tr = None
    # 3. flat: place or move the resting buys
    if not tr:
        halted = st["eq_usd"] < st["eq0_usd"] * (1 - BOOK_STOP)
        lvl, lev = pick(px, longs, shorts, used) if (bull and not cs and not halted) else (None, None)
        if pend and (lvl is None or abs(pend["lvl"] / lvl - 1) > 1e-6):
            ex.cancel(pend["o1"]); ex.cancel(pend["o2"]); log(f"cancelled resting buys at {pend['lvl']:,.0f}"); pend = None
        if lvl and not pend:
            usd = TRADE_GBP * USD_PER_GBP; q1 = usd / 2 / lvl; q2 = usd / 2 / (lvl * (1 - RUNG2))
            pend = {"lvl": lvl, "lev": lev, "q1": q1, "q2": q2, "o1": ex.limit("buy", q1, lvl), "o2": ex.limit("buy", q2, lvl * (1 - RUNG2)), "placed": str(now)}
            log(f"resting BUYS at {lvl:,.0f} ({lev}x cluster) and {lvl * (1 - RUNG2):,.0f}, ${usd / 2:.2f} each")
        if not lvl: log("no setup" + (" (book halted)" if halted else "" if bull else " (below the 200-day)" if not cs else f" (CPI {cs})"))

    slot["trade"], slot["pending"] = tr, pend
    for x in (tr, pend):
        if x: used.add(round(x["lvl"], 2))

def run(mode):
    out = f"{ROOT}/runs/revx_liq_{mode}"; os.makedirs(out, exist_ok=True); f = f"{out}/state.json"
    st = json.load(open(f)) if os.path.exists(f) else {"start": str(utcnow()), "eq_usd": BOOK_GBP * USD_PER_GBP, "eq0_usd": BOOK_GBP * USD_PER_GBP,
                                                       "trade": None, "pending": None, "closed": [], "orders": {}}
    ex = LiveEx(st) if mode == "live" else DryEx(st)
    rx = closed(revx15()); px = float(rx.close.iloc[-1]); now = utcnow()
    try: feed = closed(coinbase()); src = "Coinbase"
    except Exception as e: log("Coinbase failed:", str(e)[:120], "— using Revolut X volume"); feed = rx; src = "Revolut X"
    longs, shorts = levels(feed); bull, dc, ma = regime_ok(); cs, crel = cpi_state(now, cpi_times())
    log(f"BTC {px:,.0f} | {src} {len(feed)} bars, live long levels {len(longs)}, short {len(shorts)} | daily close {dc:,.0f} vs 200d {ma:,.0f} -> "
        f"{'ON' if bull else 'OFF'} | CPI {cs or '-'} | book ${st['eq_usd']:.2f}")
    since = pd.Timestamp(st.get("last_bar", str(rx.index[-8]))); new = rx[rx.index > since]; ex.sim(new)
    if "slots" not in st: st["slots"] = [{"trade": st.pop("trade", None), "pending": st.pop("pending", None)}]
    while len(st["slots"]) < MAXSLOTS: st["slots"].append({"trade": None, "pending": None})
    used = set()
    for slot in st["slots"]:
        for x in (slot.get("trade"), slot.get("pending")):
            if x: used.add(round(x["lvl"], 2))
    for slot in st["slots"]:
        for x in (slot.get("trade"), slot.get("pending")):
            if x: used.discard(round(x["lvl"], 2))
        slot_step(st, slot, ex, px, now, new, longs, shorts, bull, cs, used)
    st["last_bar"] = str(rx.index[-1])
    live_ids = {v for sl in st["slots"] for x in (sl.get("trade"), sl.get("pending")) if x for v in x.values() if isinstance(v, str)}
    st["orders"] = {k: v for k, v in st["orders"].items() if k in live_ids}
    json.dump(st, open(f, "w"), indent=1, default=str)
    c = pd.DataFrame(st["closed"]); log("slots: " + "; ".join(f"{'TRADE' if sl['trade'] else 'bids' if sl['pending'] else '-'} {round((sl['trade'] or sl['pending'] or {}).get('lvl', 0)):,}" for sl in st["slots"]))
    log(f"book ${st['eq_usd']:.2f} (£{st['eq_usd'] / USD_PER_GBP:.2f}); trades {len(c)}" + (f", won {(c.pnl_usd > 0).sum()}, total ${c.pnl_usd.sum():+.2f}" if len(c) else ""))

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "dry")
