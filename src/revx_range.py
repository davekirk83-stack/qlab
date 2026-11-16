"""
REVOLUT X RANGE-LONG BOOK — live-capable version of paper book 14 (doc 238; DK 16 Nov "We have to make them work").
Paper book 14 (Range v3 long side, Revolut X 15-min candles, 26 coins) is our most consistent book: £500 -> £523 in two weeks through
the worst crypto fortnight in years. This engine trades the same rules on the Revolut X £500 book with RESTING LIMIT ORDERS, because
the paper edge comes from limit fills (a first version that copied the paper position at each bar close with taker orders turned
+$3.46 of paper profit into -$0.85 on the same coins and days — so it was rebuilt this way before anything went live).

Every 15 minutes, just after the bar closes, for each coin:
  1. replay the registered engine (paperbook6.step, longs only) on Revolut X candles from the book start -> is a long episode open,
     which ladder rungs has it already tried, and did the last one close?
  2. resting orders for the next 15 minutes (all cancelled and re-placed each run, because the band moves):
       BUY limits at each untried rung  = band low + offset x ATR + 0.05 ATR (the paper's fill price), size = rung share of the budget
       (when no episode is open and the coin's range filter allows, the four entry rungs are placed the same way)
       SELL limit for everything held   = the mid EMA (the paper's single target)
  3. forced exits at market (IOC 0.5% through): the engine stopped out, broke the band, hit the 12-hour cap or the regime turned,
     or the episode ended while we still hold coins.
Book limits (CAP-021, shared Revolut X £500 book): 10% of book equity per episode, at most 10 episodes open across the Revolut X
books (counts the LIQ and TPS books), spot long only, no leverage; book equity -15% from start -> no new episodes.
Holdings are this book's own (state file), never read from the account balance, which the other books share.
Modes: dry (default; a resting order fills if the next bars trade through it, at its limit; taker exits pay 0.09% + 0.10%)
       live (needs DK's REVX_RANGE_LIVE_ENABLED; Claude never sets it).
State runs/revx_range_<mode>/state.json; trades runs/revx_range_<mode>/trades.csv.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, math, time, csv, datetime as dt, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("QLAB_ROOT", os.getcwd()); os.environ["QLAB_ROOT"] = ROOT
import paperbook6 as P
P.MK, P.TAKER, P.SLIP = 0.0, 0.0009, 0.0010
try: P._MED.clear(); P._MED.update(json.load(open(f"{ROOT}/runs/contain_median.json")))   # the registered medians, wherever the repo sits
except Exception as e: raise SystemExit(f"registered contain_median.json missing: {e}")
START = os.environ.get("REVX_RANGE_START", "2026-11-16")
GBP_USD = 1.27; BOOK_USD = 500.0 * GBP_USD; FRAC, MAXOPEN, BOOK_STOP, MIN_USD, TK, SL = 0.10, 10, 0.15, 2.0, 0.0009, 0.0010

def log(*a): print(dt.datetime.utcnow().strftime("%H:%M:%S"), "[revx-range]", *a, flush=True)

def plan(sym, d, start):
    """Engine view at the last completed bar: (episode_open, tried_rungs, closed_how, buys[(k, price, frac)], sell_px, allow)."""
    ema, lo_b, hi_b, a, allow = P.indicators(d, sym)
    w = str(d.index[max(250, d.index.searchsorted(pd.Timestamp(start, tz="UTC")) - 1)])
    pos = {}; closed, _ = P.step(sym, d, pos, w, [40]); p = pos.get("L")
    i = len(d) - 1; A = a[i]; ok = bool(allow[i]) if np.isfinite(allow[i]) else False
    last = [c for c in closed if c[1] == "L"]; how = last[-1][5] if last and last[-1][3] == str(d.index[-1]) else None
    if not np.isfinite(A) or A <= 0: return (p["open"] if p else None), [], how, [], None, False
    cool = pos.get("cool", {}).get("L"); cooling = bool(cool and d.index[-1] + pd.Timedelta(minutes=15) < pd.Timestamp(cool) + pd.Timedelta(hours=P.COOLDOWN_H))
    tried = list(p["tried"]) if p else []
    buys = [] if (not ok or (p is None and cooling)) else \
        [(k, float(lo_b[i] + off * A + P.CHASE_PREM * A), f) for k, (f, off) in enumerate(P.BID) if k not in tried]
    return (p["open"] if p else None), tried, how, buys, float(ema[i]), ok

class Dry:
    """Resting orders are checked against the bars that printed after they were placed."""
    def __init__(self, bars): self.bars = bars
    def fills(self, sym, orders, since):
        b = self.bars[sym]; b = b[b.index >= pd.Timestamp(since)]; out = []
        for o in orders:
            if not len(b): continue
            hit = (b.low.min() <= o["px"]) if o["side"] == "buy" else (b.high.max() >= o["px"])
            if hit: out.append((o, o["qty"], o["px"]))
        return out
    def cancel_all(self, sym, orders): pass
    def place(self, sym, side, qty, px): return {"id": None}
    def market(self, sym, side, qty, px): return qty, px * ((1 + SL) if side == "buy" else (1 - SL))

class Live:
    def __init__(self):
        from revx_client import RevX; self.rx = RevX(); c = self.rx.pairs(); self.cfg = c.get("data", c)
    def _fmt(self, sym, qty, px):
        c = self.cfg.get(f"{sym[:-3]}/USD", {}) if isinstance(self.cfg, dict) else {}
        step = float(c.get("base_step", "0.00000001")); dp = max(0, -int(math.floor(math.log10(step))))
        qstep = float(c.get("quote_step", "0")) or 10 ** (math.floor(math.log10(max(px, 1e-9))) - 4)
        pd_ = max(0, -int(math.floor(math.log10(qstep))))
        q = math.floor(qty / step + 1e-9) * step; p = round(math.floor(px / qstep + 1e-9) * qstep, pd_)
        return f"{q:.{dp}f}", f"{p:.{pd_}f}", q
    def fills(self, sym, orders, since):
        out = []
        for o in orders:
            if not o.get("id"): continue
            r = self.rx.order(o["id"]); r = r.get("data", r); q = float(r.get("filled_quantity") or 0)
            if q > 0: out.append((o, q, float(r.get("average_fill_price") or o["px"])))
        return out
    def cancel_all(self, sym, orders):
        for o in orders:
            if o.get("id"):
                try: self.rx.cancel(o["id"])
                except Exception as e: log(sym, "cancel failed", e)
    def place(self, sym, side, qty, px):
        qs, ps, q = self._fmt(sym, qty, px)
        if q <= 0: return {"id": None}
        r = self.rx.place(f"{sym[:-3]}-USD", side, base_size=qs, price=ps, tif="gtc"); r = r.get("data", r)
        return {"id": r.get("venue_order_id") or r.get("id")}
    def market(self, sym, side, qty, px):
        qs, ps, q = self._fmt(sym, qty, px * (1.005 if side == "buy" else 0.995))
        if q <= 0: return 0.0, 0.0
        r = self.rx.place(f"{sym[:-3]}-USD", side, base_size=qs, price=ps, tif="ioc"); r = r.get("data", r)
        k = r.get("venue_order_id") or r.get("id"); o = {}
        for _ in range(6):
            time.sleep(1.5); o = self.rx.order(k); o = o.get("data", o)
            if o.get("status") in ("filled", "cancelled", "rejected", "partially_filled"): break
        return float(o.get("filled_quantity") or 0), float(o.get("average_fill_price") or 0)

def others_open(mode):
    """Episodes the other Revolut X books hold open (shared 10-open limit): LIQ slots with a trade or a resting bid, TPS episodes."""
    n = 0
    try: n += sum(1 for x in json.load(open(f"{ROOT}/runs/revx_liq_{mode}/state.json")).get("slots", []) if x.get("trade") or x.get("pending"))
    except Exception: pass
    try: n += len(json.load(open(f"{ROOT}/runs/revx_tps_{mode}/state.json")).get("eps", {}))
    except Exception: pass
    return n

def book(st, sym, d, ex, now, eq, can_open, rows):
    """One coin, one run: settle fills of the resting orders, then act on the engine's view."""
    h = st["hold"].setdefault(sym, {"qty": 0.0, "cost": 0.0, "ep": None, "budget": 0.0, "orders": [], "since": None})
    px = float(d.close.iloc[-1])
    for o, q, fp in ex.fills(sym, h["orders"], h["since"] or now):           # 1. fills since the last run (maker: no fee)
        if o["side"] == "buy":
            q = min(q, st["cash"] / fp)
            st["cash"] -= q * fp; h["cost"] += q * fp; h["qty"] += q; rows.append([now, sym, "buy", q, fp, "", h["ep"], f"rung {o['k']}"])
        else:
            q = min(q, h["qty"]); share = q / max(h["qty"], 1e-12); pnl = q * fp - h["cost"] * share
            st["cash"] += q * fp; h["cost"] -= h["cost"] * share; h["qty"] -= q; rows.append([now, sym, "sell", q, fp, round(pnl, 4), h["ep"], "mid"])
    ex.cancel_all(sym, h["orders"]); h["orders"] = []
    if h["qty"] * px < 0.5: h["qty"], h["cost"] = 0.0, 0.0
    ep, tried, how, buys, mid, ok = plan(sym, d, st["start_day"])
    if h["ep"] == "pending" and ep is not None: h["ep"] = ep                  # our entry bids belonged to the episode the engine opened
    if h["qty"] > 0 and (ep is None or ep != h["ep"]):                       # 2. the engine's episode ended: leave at market
        q, fp = ex.market(sym, "sell", h["qty"], px)
        if q > 0:
            q = min(q, h["qty"]); share = q / h["qty"]; fee = q * fp * TK; pnl = q * fp - fee - h["cost"] * share
            st["cash"] += q * fp - fee; h["cost"] -= h["cost"] * share; h["qty"] -= q
            rows.append([now, sym, "sell", q, fp, round(pnl, 4), h["ep"], how or "episode ended"])
        if h["qty"] * px < 0.5: h["qty"], h["cost"] = 0.0, 0.0
    if h["qty"] <= 0 and ep != h["ep"]: h["ep"], h["budget"] = None, 0.0
    if ep is not None and h["ep"] is None and h["qty"] <= 0 and tried:        # engine opened an episode our orders missed: skip it
        buys = []
    if ep is None and buys:                                                   # 3. entry rungs for a possible new episode
        if not can_open(): buys = []
        else: h["budget"] = FRAC * eq; h["ep"] = "pending"
    elif ep is not None and h["ep"] in (None, "pending") and h["qty"] > 0: h["ep"] = ep
    if h["ep"] == "pending" and ep is not None: h["ep"] = ep
    if h["ep"] is not None and h["ep"] != "pending" and ep is None and h["qty"] <= 0: h["ep"], h["budget"] = None, 0.0
    for k, bp, f in buys:
        qty = h["budget"] * f / bp
        if qty * bp < MIN_USD or bp >= px * 1.002: continue                   # never a resting buy above the market
        r = ex.place(sym, "buy", qty, bp); h["orders"].append({"side": "buy", "k": k, "px": bp, "qty": qty, "id": r.get("id")})
    if h["qty"] > 0 and mid and ok:
        r = ex.place(sym, "sell", h["qty"], max(mid, px * 1.0005)); h["orders"].append({"side": "sell", "k": "mid", "px": max(mid, px * 1.0005), "qty": h["qty"], "id": r.get("id")})
    if not h["orders"] and h["qty"] <= 0 and h["ep"] == "pending": h["ep"], h["budget"] = None, 0.0
    h["since"] = now; h["px"] = px

def run(mode, bars=None, now=None, st=None, save=True):
    out = f"{ROOT}/runs/revx_range_{mode}"; os.makedirs(out, exist_ok=True); sf = f"{out}/state.json"
    if st is None:
        st = json.load(open(sf)) if os.path.exists(sf) else {"start_day": START, "cash": BOOK_USD, "eq0": BOOK_USD, "hold": {}}
    if bars is None:
        import paperbook14 as B
        U = [s for s in json.load(open(f"{ROOT}/runs/range_universe.json"))["registered_universe"] if s != "ZECUSD"]; bars = {}
        for s in U:
            b = B.refresh(s); time.sleep(1.0)
            if len(b) and b.index.max() >= pd.Timestamp.utcnow() - pd.Timedelta(hours=2): bars[s] = b[["open", "high", "low", "close"]].astype(float)
            else: log(s, "stale Revolut X data — skipped")
    now = now or str(pd.Timestamp.utcnow().floor("15min"))
    ex = Dry(bars) if mode != "live" else Live()
    eq = st["cash"] + sum(h["qty"] * float(bars[s].close.iloc[-1]) for s, h in st["hold"].items() if s in bars)
    halted = eq < st["eq0"] * (1 - BOOK_STOP); oth = others_open(mode) if mode in ("live", "dry") else 0
    def can_open():
        n = sum(1 for h in st["hold"].values() if h["qty"] > 0 or h.get("ep") == "pending") + oth
        return not halted and n < MAXOPEN
    rows = []
    for s, d in bars.items():
        if len(d) < 300: continue
        try: book(st, s, d, ex, now, eq, can_open, rows)
        except Exception as e: log(s, "error", repr(e))
    eq = st["cash"] + sum(h["qty"] * h.get("px", 0) for h in st["hold"].values())
    st.update(eq=eq, asof=now, halted=bool(halted))
    if save:
        json.dump(st, open(sf, "w"), indent=1, default=str)
        if rows:
            new = not os.path.exists(f"{out}/trades.csv")
            with open(f"{out}/trades.csv", "a", newline="") as f:
                w = csv.writer(f)
                if new: w.writerow(["t", "sym", "side", "qty", "px", "pnl_usd", "episode", "why"])
                w.writerows(rows)
        nb = sum(1 for h in st["hold"].values() for o in h["orders"] if o["side"] == "buy")
        log(f"{mode}: equity ${eq:,.2f} (start ${st['eq0']:,.2f}), holding {sum(1 for h in st['hold'].values() if h['qty'] > 0)} coins, "
            f"{nb} resting bids, {len(rows)} fills this run{' — BOOK STOP: no new episodes' if halted else ''}")
    return st, rows

if __name__ == "__main__":
    mode = (sys.argv[1:] or ["dry"])[0]
    if mode == "live" and os.environ.get("REVX_RANGE_LIVE_ENABLED") != "true": raise SystemExit("live needs DK's REVX_RANGE_LIVE_ENABLED")
    run(mode)
