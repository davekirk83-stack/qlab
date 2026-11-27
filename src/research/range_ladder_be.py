"""DK 27 Nov (winners that turned into losers): on the demo range ladder 6 of 11 losers had been up at least as much as they finally lost.
Tests profit protection on the IG range ladder (resting orders priced from the previous closed bar, as src/ig_range_engine.py trades it;
src/revx_honest_test.honest2 logic, both sides via the price mirror), 15-min bars, IG-like costs:
  be=b    once the best price since the first fill is >= avg + b ATR, the stop moves to the average cost (exit there if touched);
  half=x  take half the position at avg + x ATR, rest to the mid EMA as now."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import paperbook6 as P, revx_honest_test as H
P.MK, P.TAKER, P.SLIP = 0.0, 0.0, 0.0001
STOP = H.STOP

def to15(d): return d.resample("15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
def load(f):
    d = pd.read_csv(f); d.index = pd.to_datetime(d.iloc[:, 0], utc=True, format="ISO8601"); d.columns = [c.lower() for c in d.columns]
    return to15(d[["open", "high", "low", "close"]].astype(float))

def ladder(d, sym, start, be=None, half=None):
    ema, lo_b, hi_b, a, allow = P.indicators(d, sym); O, Hh, L, C = d.open.values, d.high.values, d.low.values, d.close.values; idx = d.index
    out = []; p = None; cool = None; s0 = max(251, idx.searchsorted(start))
    for i in range(s0, len(C)):
        j = i - 1
        if not (np.isfinite(a[j]) and a[j] > 0): continue
        if p and p["u"] > 0:
            avg = p["spent"] / p["u"]
            # protection exits (checked before the mid target: conservative)
            if p.get("armed") and L[i] <= avg:
                p["cash"] += p["u"] * min(avg, O[i]) * (1 - P.SLIP); p["u"] = 0.0
                out.append((idx[p["i0"]], p["cash"], "be")); p = None; cool = idx[i]; continue
            if half and not p.get("halved") and Hh[i] >= avg + half * p["a0"]:
                q = p["u"] / 2; p["cash"] += q * max(avg + half * p["a0"], O[i]); p["u"] -= q; p["halved"] = True
            if ema[j] < Hh[i]:
                p["cash"] += p["u"] * max(ema[j], O[i]); p["u"] = 0.0
                out.append((idx[p["i0"]], p["cash"], "mid")); p = None; cool = idx[i]; continue
            p["best"] = max(p.get("best", 0), Hh[i])
            if be and p["best"] >= avg + be * p["a0"]: p["armed"] = True
        if allow[j] and (cool is None or idx[i] >= cool + pd.Timedelta(hours=P.COOLDOWN_H)):
            for k, (frac, off) in enumerate(P.BID):
                if p and k in p["tried"]: continue
                price = lo_b[j] + off * a[j]
                if price > 0 and L[i] < price:
                    fill = min(price, O[i])
                    if p is None: p = {"u": 0.0, "cash": 0.0, "tried": [], "i0": i, "spent": 0.0, "a0": a[j]}
                    p["tried"].append(k); p["u"] += frac / fill; p["cash"] -= frac; p["spent"] += frac
        if p and p["u"] > 0:
            avg = p["spent"] / p["u"]
            why = ("stop" if L[i] <= avg * (1 - STOP) else "break" if (C[i] < lo_b[i] - 1.5 * a[i] or C[i] > hi_b[i] + 1.5 * a[i])
                   else "cap" if i - p["i0"] >= P.CAP_BARS else "regime" if not allow[i] else None)
            if why:
                px = (min(avg * (1 - STOP), O[i]) if why == "stop" else C[i]) * (1 - P.SLIP - P.TAKER)
                p["cash"] += p["u"] * px
                out.append((idx[p["i0"]], p["cash"], why)); p = None; cool = idx[i]
    return out

F = {"NQ": "data_nq_cache/nq_5m.csv", "US500": "data_ig_cache/USA500IDXUSD_5m.csv", "FTSE": "data_ig_cache/GBRIDXGBP_5m.csv",
     "WALLST": "data_ig_cache/USA30IDXUSD_5m.csv", "DAX": "data_ig_cache/DEUIDXEUR_5m.csv"}
if __name__ == "__main__":
    D = {}
    for k, f in F.items():
        if not os.path.exists(f): continue
        d = load(f); ema, lo, hi, a, _ = P.indicators(d); cont = pd.Series(((d.close.values <= hi) & (d.close.values >= lo)).astype(float)).rolling(50).mean()
        P._MED[k] = {"median": float(cont.median())}; K = 2 * d.high.max()
        D[k] = (d, pd.DataFrame({"open": K - d.open, "high": K - d.low, "low": K - d.high, "close": K - d.close}, index=d.index))
    rows = []
    for name, kw in (("live rule", {}), ("BE at +0.5 ATR", {"be": 0.5}), ("BE at +1 ATR", {"be": 1.0}), ("BE at +1.5 ATR", {"be": 1.5}),
                     ("half at +1 ATR", {"half": 1.0}), ("half at +0.5 ATR", {"half": 0.5}), ("BE 1 + half 1", {"be": 1.0, "half": 1.0})):
        E = []
        for k, (d, m) in D.items():
            st = d.index[300]; E += ladder(d, k, st, **kw) + ladder(m, k, st, **kw)
        t = pd.DataFrame(E, columns=["t", "r", "why"]).sort_values("t"); h = len(t) // 2; mo = t.groupby(t.t.dt.to_period("M")).r.sum()
        rows.append(dict(variant=name, n=len(t), win=(t.r > 0).mean(), mean_pct=100 * t.r.mean(), h1=100 * t.r[:h].mean(), h2=100 * t.r[h:].mean(),
                         months_pos=f"{(mo>0).sum()}/{len(mo)}", worst_month_pct=100 * mo.min(), total_pct=100 * t.r.sum()))
        print(rows[-1], flush=True)
    r = pd.DataFrame(rows); r.to_csv("runs/research/range_ladder_be.csv", index=False); pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
