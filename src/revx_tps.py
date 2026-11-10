"""
REVOLUT X — TPS coin ladder (doc 215; DK 10 Nov 09:51 "Yes": build it as a dry run, ready for live on Revolut X).
Rules = doc 200 backtest (src/ladder_daily_tps.py), daily UTC candles, decided on the candle that has just CLOSED:
  start : close above its 200-day average and RSI(2) < 25 on two closes running -> buy 10% of the episode budget
  add   : each later close BELOW the last buy adds 20%, then 30%, then 40% of the budget (4 rungs max)
  exit  : sell everything when RSI(2) > 70, or after 30 days, or when the close is 15% under the average cost
Episode budget = 10% of book equity at the start (CAP-021 5 Nov: 10% of the book per episode, at most 10 open); spot, long only, no leverage.
Book down 15% from its start -> no new episodes (back to paper, DK decides).
Orders: market through the price (IOC limit 1% beyond, Revolut X taker 0.09%) a few minutes after the 00:00 UTC close.
Modes: dry  = no orders, fills at the live price, state in runs/revx_tps_dry/
       live = DK's Revolut X account; only via .github/workflows/revx-tps.yml when DK sets REVX_TPS_LIVE_ENABLED=true; runs/revx_tps_live/
`replay(days)` runs the same step() over Revolut X's daily history (backtest)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, math, time, datetime as dt
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("QLAB_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); os.environ.setdefault("QLAB_ROOT", ROOT)

COINS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "AVAX", "LINK", "ADA", "LTC", "DOT"]
LADDER, RSI_IN, RSI_OUT, MAXD, KILL = (0.1, 0.2, 0.3, 0.4), 25, 70, 30, 0.15
FRAC, MAXOPEN, BOOK_STOP, START_GBP, USD_PER_GBP = 0.10, 10, 0.15, 500.0, 1.27
TK, SLIP = 0.0009, 0.0010

def log(*a): print(dt.datetime.utcnow().strftime("%H:%M:%S"), *a, flush=True)
def rsi2(c):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def daily(coin):
    """Completed daily UTC candles from Revolut X (public endpoint, ~1,000 days)."""
    import paperbook14 as B
    d = B.rx_get(f"1.0/public/candles/{coin}-USD?interval=1440")["data"]
    x = pd.DataFrame(d); x.index = pd.to_datetime(x.start, unit="ms", utc=True); x = x[["open", "high", "low", "close"]].astype(float).sort_index()
    return x[x.index < pd.Timestamp.utcnow().floor("1D")]          # today's candle is still forming

def step(st, coin, d, ex):
    """One decision for one coin on its last CLOSED daily candle d.iloc[-1]. ex: executor with buy/sell(coin, usd_or_qty, ref)."""
    if len(d) < 202: return
    c = d.close; r = rsi2(c); ma = c.rolling(200).mean(); C, R1, R0, M = c.iloc[-1], r.iloc[-1], r.iloc[-2], ma.iloc[-1]; day = str(d.index[-1].date())
    e = st["eps"].get(coin)
    if e is not None:
        if e["k"] < len(LADDER) and C < e["last"]:
            q, px = ex.buy(coin, LADDER[e["k"]] * e["budget"], C)
            if q > 0: e["qty"] += q; e["spent"] += q * px * (1 + TK); e["last"] = C; e["k"] += 1; log(f"{coin}: rung {e['k']} bought {q:.6g} at {px:.6g}")
        e["days"] = e.get("days", 0) + 1; avg = e["spent"] / e["qty"] if e["qty"] else C
        why = "RSI(2) > 70" if R1 > RSI_OUT else f"{MAXD} days" if e["days"] >= MAXD else "15% under average cost" if C <= avg * (1 - KILL) else None
        if why:
            q, px = ex.sell(coin, e["qty"], C); pnl = q * px * (1 - TK) - e["spent"]
            st["closed"].append({"coin": coin, "start": e["start"], "end": day, "rungs": e["k"], "spent": round(e["spent"], 2), "pnl_usd": round(pnl, 2), "why": why})
            log(f"{coin}: EXIT ({why}) {q:.6g} at {px:.6g} -> ${pnl:+.2f}"); st["eps"].pop(coin)
        return
    if C > M and R1 < RSI_IN and R0 < RSI_IN:
        if st.get("halt"): log(f"{coin}: signal, but the book is halted ({st['halt']})"); return
        if len(st["eps"]) >= MAXOPEN: log(f"{coin}: signal, but {MAXOPEN} episodes already open"); return
        budget = FRAC * st["eq"]; q, px = ex.buy(coin, LADDER[0] * budget, C)
        if q > 0:
            st["eps"][coin] = {"start": day, "budget": budget, "qty": q, "spent": q * px * (1 + TK), "last": C, "k": 1, "days": 0}
            log(f"{coin}: START episode, budget ${budget:.2f}; rung 1 bought {q:.6g} at {px:.6g} (RSI2 {R0:.0f}/{R1:.0f}, close > 200d)")

class DryEx:
    def __init__(self, st): self.st = st
    def buy(self, coin, usd, ref):
        px = ref * (1 + SLIP); usd = min(usd, self.st["cash"])
        if usd < 1: return 0.0, 0.0
        q = usd / (px * (1 + TK)); self.st["cash"] -= usd; return q, px
    def sell(self, coin, q, ref):
        px = ref * (1 - SLIP); self.st["cash"] += q * px * (1 - TK); return q, px

class LiveEx(DryEx):
    """Revolut X: IOC limit 1% through the reference price (keys: DK's GitHub secrets only, via src/revx_client.py)."""
    def __init__(self, st):
        super().__init__(st); from revx_client import RevX; self.rx = RevX()
        f = f"{ROOT}/runs/revx_live/pairs.json"; self.cfg = json.load(open(f)) if os.path.exists(f) else self.rx.pairs()
    def _q(self, coin, q):
        step = float(self.cfg.get(f"{coin}/USD", {}).get("base_step", "0.000001")); dp = max(0, -int(math.floor(math.log10(step))))
        v = math.floor(q / step + 1e-9) * step; return f"{v:.{dp}f}", v
    def _px(self, p): dp = min(8, max(2, 5 - int(math.floor(math.log10(p))))); return f"{p:.{dp}f}"
    def _fill(self, oid):
        for _ in range(6):
            time.sleep(1.5); o = self.rx.order(oid); o = o.get("data", o)
            if o.get("status") in ("filled", "cancelled", "rejected", "partially_filled"): break
        return float(o.get("filled_quantity") or 0), float(o.get("average_fill_price") or 0)
    def _go(self, coin, side, q, ref):
        qs, qv = self._q(coin, q)
        if qv * ref < 1: return 0.0, 0.0
        try: r = self.rx.place(f"{coin}-USD", side, base_size=qs, price=self._px(ref * (1.01 if side == "buy" else 0.99)), tif="ioc")
        except Exception as e: log(f"{coin} {side} refused: {str(e)[:160]}"); return 0.0, 0.0
        d = r.get("data", r); return self._fill(d.get("venue_order_id") or d.get("id"))
    def buy(self, coin, usd, ref):
        usd = min(usd, self.st["cash"]); q, px = self._go(coin, "buy", usd / (ref * 1.01 * (1 + TK)), ref)
        self.st["cash"] -= q * px * (1 + TK); return q, px
    def sell(self, coin, q, ref):
        q, px = self._go(coin, "sell", q, ref); self.st["cash"] += q * px * (1 - TK); return q, px

def equity(st, last):
    return st["cash"] + sum(e["qty"] * last.get(c, e["last"]) for c, e in st["eps"].items())

def run(mode):
    out = f"{ROOT}/runs/revx_tps_{mode}"; os.makedirs(out, exist_ok=True); f = f"{out}/state.json"
    st = json.load(open(f)) if os.path.exists(f) else {"start": str(dt.date.today()), "cash": START_GBP * USD_PER_GBP, "eps": {}, "closed": [], "done": []}
    today = str(pd.Timestamp.utcnow().date())
    if today in st["done"]: log("already ran today — exit"); return
    ex = LiveEx(st) if mode == "live" else DryEx(st)
    D = {}
    for c in COINS:
        try: D[c] = daily(c); time.sleep(0.5)
        except Exception as e: log(f"{c}: candles failed ({e}) — skipped today")
    last = {c: d.close.iloc[-1] for c, d in D.items()}
    st["eq"] = equity(st, last); st.setdefault("eq0", st["eq"])
    if st["eq"] < st["eq0"] * (1 - BOOK_STOP) and not st.get("halt"): st["halt"] = f"book down 15% on {today}"; log("HALT:", st["halt"])
    for c, d in D.items(): step(st, c, d, ex)
    st["eq"] = equity(st, last); st["done"] = (st["done"] + [today])[-60:]
    json.dump(st, open(f, "w"), indent=1, default=str)
    log(f"book ${st['eq']:.2f} (£{st['eq'] / USD_PER_GBP:.2f}), open {list(st['eps'])}, closed episodes {len(st['closed'])}")

def replay(days=800):
    """Backtest: the same step() day by day over Revolut X daily history."""
    import contextlib, io
    D = {c: daily(c) for c in COINS}; idx = sorted(set().union(*[d.index for d in D.values()]))[-days:]
    st = {"cash": START_GBP * USD_PER_GBP, "eps": {}, "closed": []}; ex = DryEx(st); curve = []
    for t in idx:
        last = {c: d.close[d.index <= t].iloc[-1] for c, d in D.items() if (d.index <= t).any()}
        st["eq"] = equity(st, last); st.setdefault("eq0", st["eq"])
        with contextlib.redirect_stdout(io.StringIO()):
            for c, d in D.items(): step(st, c, d[d.index <= t], ex)
        curve.append((t, equity(st, last)))
    return st, pd.Series(dict(curve))

if __name__ == "__main__":
    if sys.argv[1:2] == ["replay"]:
        st, eq = replay(int(sys.argv[2]) if len(sys.argv) > 2 else 800); cl = pd.DataFrame(st["closed"]); g = eq / USD_PER_GBP
        print(f"replay {eq.index[0].date()} -> {eq.index[-1].date()}: £{g.iloc[0]:.0f} -> £{g.iloc[-1]:.0f}; episodes {len(cl)}, win {100 * (cl.pnl_usd > 0).mean():.0f}%, "
              f"worst ${cl.pnl_usd.min():.2f}; max drawdown {100 * (1 - g / g.cummax()).max():.1f}%; lowest £{g.min():.0f}")
        print("by year £:", " ".join(f"{y}:{v / USD_PER_GBP:+.0f}" for y, v in cl.groupby(pd.to_datetime(cl.end).dt.year).pnl_usd.sum().items()))
        print("by coin £:", " ".join(f"{k}:{v / USD_PER_GBP:+.0f}" for k, v in cl.groupby("coin").pnl_usd.sum().items()))
        m = g.resample("ME").last().diff().dropna(); print(f"months positive {(m > 0).sum()}/{len(m)}, worst month £{m.min():+.0f}")
    else:
        run(sys.argv[1] if len(sys.argv) > 1 else "dry")
