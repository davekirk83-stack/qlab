"""Doc 194 check: the Range v3 long book with orders priced from the PREVIOUS closed bar (how resting orders really work) versus the
paperbook6 engine, which prices bar i's rungs and mid from bar i's own close (look-ahead). Coinbase 15-min cache, last N days, Revolut X costs."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.environ.get("QLAB_ROOT", "/home/claude/qlab"); import paperbook6 as P, paperbook14 as B
P.MK, P.TAKER, P.SLIP = 0.0, 0.0009, 0.0010
STOP = P.MARGIN_STOP / P.LEV

def honest(d, sym, start, touch="strict"):
    ema, lo_b, hi_b, a, allow = P.indicators(d, sym); O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; idx = d.index
    out = []; p = None; cool = None; s0 = max(251, idx.searchsorted(start))
    hit = (lambda x, y: x < y) if touch == "strict" else (lambda x, y: x <= y)
    for i in range(s0, len(C)):
        j = i - 1
        if not (np.isfinite(a[j]) and a[j] > 0): continue
        # fills during bar i of the orders priced at bar j
        if p and p["qty"] > 0 and hit(-H[i], -ema[j]):         # sell at the mid
            p["pnl"] += p["qty"] * (ema[j] / (p["cost"] / p["qty"]) - 1) * 1.0; p["qty"] = 0.0
            out.append((sym, p["o"], idx[i], p["pnl"] / p["budget"], "mid")); p = None; cool = idx[i]
        ok_cool = cool is None or idx[i] >= cool + pd.Timedelta(hours=P.COOLDOWN_H)
        if allow[j] and ok_cool:
            for k, (frac, off) in enumerate(P.BID):
                if p and k in p["tried"]: continue
                price = lo_b[j] + off * a[j]
                fill = min(price, O[i]) if O[i] < price else price      # gapped through: filled at the open (better)
                if hit(L[i], price):
                    if p is None: p = {"o": idx[i], "qty": 0.0, "cost": 0.0, "tried": [], "pnl": 0.0, "budget": 1.0, "i0": i}
                    p["tried"].append(k); p["qty"] += frac / fill * fill; p["cost"] += frac      # qty in budget units at cost
                    p.setdefault("units", 0.0); p["units"] = p.get("units", 0.0) + frac / fill
        if p and p.get("units", 0) > 0:
            # recompute in coin units
            pass
        # exits at bar i close
        if p and p.get("units", 0) > 0:
            avg = p["cost"] / p["units"]
            why = ("stop" if L[i] <= avg * (1 - STOP) else "break" if (C[i] < lo_b[i] - 1.5 * a[i] or C[i] > hi_b[i] + 1.5 * a[i])
                   else "cap" if i - p["i0"] >= P.CAP_BARS else "regime" if not allow[i] else None)
            if why:
                px = (avg * (1 - STOP) if why == "stop" else C[i]) * (1 - P.SLIP - P.TAKER)
                pnl = p["units"] * px - p["cost"]
                out.append((sym, p["o"], idx[i], pnl, why)); p = None; cool = idx[i]
    return out

def honest2(d, sym, start, touch="strict", reprice=False):
    """clean version: track coin units and cash per episode (budget 1.0)"""
    ema, lo_b, hi_b, a, allow = P.indicators(d, sym); O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; idx = d.index
    out = []; p = None; cool = None; s0 = max(251, idx.searchsorted(start))
    lt = (lambda x, y: x < y) if touch == "strict" else (lambda x, y: x <= y)
    for i in range(s0, len(C)):
        j = i - 1
        if not (np.isfinite(a[j]) and a[j] > 0): continue
        if p and p["u"] > 0 and lt(ema[j], H[i]):
            p["cash"] += p["u"] * max(ema[j], O[i]); p["u"] = 0.0
            out.append((sym, p["o"], idx[i], p["cash"], "mid")); p = None; cool = idx[i]; continue
        if allow[j] and (cool is None or idx[i] >= cool + pd.Timedelta(hours=P.COOLDOWN_H)):
            for k, (frac, off) in enumerate(P.BID):
                if p and k in p["tried"]: continue
                price = (ema[j] - (2 - off) * a[j] / (1 - 2 / 21)) if reprice else (lo_b[j] + off * a[j])
                if price > 0 and lt(L[i], price):
                    fill = min(price, O[i])
                    if p is None: p = {"o": idx[i], "u": 0.0, "cash": 0.0, "tried": [], "i0": i, "spent": 0.0}
                    p["tried"].append(k); p["u"] += frac / fill; p["cash"] -= frac; p["spent"] += frac
        if p and p["u"] > 0:
            avg = p["spent"] / p["u"]
            why = ("stop" if L[i] <= avg * (1 - STOP) else "break" if (C[i] < lo_b[i] - 1.5 * a[i] or C[i] > hi_b[i] + 1.5 * a[i])
                   else "cap" if i - p["i0"] >= P.CAP_BARS else "regime" if not allow[i] else None)
            if why:
                px = (min(avg * (1 - STOP), O[i]) if why == "stop" else C[i]) * (1 - P.SLIP - P.TAKER)
                p["cash"] += p["u"] * px
                out.append((sym, p["o"], idx[i], p["cash"], why)); p = None; cool = idx[i]
    return out

if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 365
    src = sys.argv[2] if len(sys.argv) > 2 else "cb"
    U = [s for s in json.load(open(f"{ROOT}/runs/range_universe.json"))["registered_universe"] if s != "ZECUSD"]
    R = {"engine": [], "honest_strict": [], "honest_reprice": []}
    for s in U:
        if src == "cb":
            f = os.environ.get("D15", f"{ROOT}/data_15m_cache") + f"/{s}.csv.gz"; f = f if os.path.exists(f) else f[:-3]
            if not os.path.exists(f): continue
            d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d = d[["open", "high", "low", "close"]].astype(float)
        else:
            d = pd.read_csv(f"{ROOT}/data_rx_cache/{s}.csv.gz", index_col=0, parse_dates=True); d.index = pd.to_datetime(d.index, utc=True); d = d[["open","high","low","close"]].astype(float)
        start = d.index.max() - pd.Timedelta(days=days) if src == "cb" else pd.Timestamp("2026-11-01", tz="UTC")
        d = d[d.index >= start - pd.Timedelta(days=20)]
        B.START = start
        R["engine"] += [(x[0], x[1], x[2], x[3], x[4]) for x in B.episodes(d, s)]
        for nm, rp in (("honest_strict", False), ("honest_reprice", True)):
            R[nm] += [(x[0], x[1], x[2], x[3], x[4]) for x in honest2(d, s, start, "strict", rp)]
    for k, E in R.items():
        eq, mdd, rows = B.pool(E); rets = np.array([e[3] for e in E])
        print(f"{k:14s} £500 -> £{eq:,.0f}  episodes {len(E)} mean {100*rets.mean():+.3f}% win {100*(rets>0).mean():.0f}%  maxDD {100*mdd:.1f}%", flush=True)
