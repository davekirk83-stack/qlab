"""
TIGHTENING THE GOLDEN CROSS — DK, 19 Oct: "Consider ways to tighten and improve
the golden cross strategy."

Doc 82: the 4h golden-cross entry beats random but not zero (best +0.02%/ep).
Here every tightening with a precedent in this project is tried as a GATE on
the cross-20/50 long, on 4-hour and on daily bars, with the two exits that did
best yesterday (scaled; hold 12 bars). Random control with the same exit.

GATES
  none            the doc-82 baseline
  btc bull        BTC close above its own EMA200 on the same bars (regime: longs
                  in a bull backdrop - doc 27 found shorts/longs regime-bound)
  slope           EMA50 rising over the last 10 bars (the slow line agrees)
  confirmed       close > EMA20 > EMA50 and the gap > 0.5 ATR (not a graze)
  pullback        after the cross, buy the FIRST bar within 30 that touches
                  EMA20 (low <= EMA20) and closes above it - the pullback-in-
                  uptrend entry had the best exit-free edge in doc 29
  bull+pullback   both
  alts only / majors only   BTC+ETH vs the other 25
  week4           entry in days 22-28 of the month (doc 22, the one calendar
                  effect that replicated)
  not US session  entry bar not in 13-21 UTC (doc 22: the US session loses)
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import crossover as X
import golden_scaled as G
X.CAP = 180; X.X_MIN_GAP = 2
RNG = np.random.default_rng(11)
MAJ = {"BTCUSD", "ETHUSD"}


def build(data, rule):
    P = {}
    for s, d in data.items():
        dd = d.resample(rule).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
        C, H, L, a = X.prep(dd)
        up, dn, au, ad = X.signals(C, a, 20, 50)
        ef = pd.Series(C).ewm(span=20, adjust=False).mean().values
        es = pd.Series(C).ewm(span=50, adjust=False).mean().values
        e200 = pd.Series(C).ewm(span=200, adjust=False).mean().values
        P[s] = dict(C=C, H=H, L=L, a=a, up=up, ef=ef, es=es, e200=e200, idx=dd.index)
    return P


def entries(P, s, gate):
    p = P[s]; C, L, ef, es, a, up = p["C"], p["L"], p["ef"], p["es"], p["a"], p["up"]
    idx = np.where(up)[0]; idx = idx[(idx > 250) & (idx < len(C)-2)]
    btc = P.get("BTCUSD")
    out = []
    for i in idx:
        j = i
        if "pullback" in gate:
            j = None
            for k in range(i+1, min(i+31, len(C)-2)):
                if ef[k] < es[k]: break                       # cross undone
                if L[k] <= ef[k] and C[k] > ef[k]: j = k; break
            if j is None: continue
        if "bull" in gate and btc is not None:
            t = p["idx"][j]; kb = int(np.searchsorted(btc["idx"], t, side="right")) - 1
            if kb < 0 or btc["C"][kb] <= btc["e200"][kb]: continue
        if gate == "slope" and not (es[j] > es[j-10]): continue
        if gate == "confirmed" and not (C[j] > ef[j] > es[j] and (ef[j]-es[j]) > 0.5*a[j]): continue
        if gate == "alts only" and s in MAJ: continue
        if gate == "majors only" and s not in MAJ: continue
        if gate == "week4" and not (22 <= p["idx"][j].day <= 28): continue
        if gate == "not US" and 13 <= p["idx"][j].hour < 21: continue
        out.append(j)
    return out


def run(P, gate, exit_fn):
    rows, ctrl = [], []
    for s in P:
        p = P[s]; C, H, L, a = p["C"], p["H"], p["L"], p["a"]
        last = -10**9
        for i in entries(P, s, gate):
            if i - last < X.X_MIN_GAP: continue
            last = i
            r, b, _ = exit_fn(C, H, L, a, i, 1); rows.append((s, p["idx"][i].year, r))
            j = int(RNG.integers(250, len(C)-2)); r2, _, _ = exit_fn(C, H, L, a, j, 1); ctrl.append((s, p["idx"][j].year, r2))
    return pd.DataFrame(rows, columns=["sym","y","ret"]), pd.DataFrame(ctrl, columns=["sym","y","ret"])


if __name__ == "__main__":
    data = X.load()
    GATES = ["none", "btc bull", "slope", "confirmed", "pullback", "bull+pullback", "alts only", "majors only", "week4", "not US"]
    for rule, label, exits in (("4h", "4-HOUR", [("scaled", G.scaled), ("hold 12", lambda *q: G.hold(*q, 12))]),
                               ("1D", "DAILY", [("scaled", G.scaled), ("hold 10", lambda *q: G.hold(*q, 10))])):
        P = build(data, rule)
        print(f"\n{label} bars, cross 20/50 LONG, {len(P)} coins. edge = real minus random (same exit); yrs+ = years real beats random")
        print(f"  {'gate':<15}{'exit':<9}{'n':>7}{'per ep':>9}{'t':>7}{'win':>6}{'ctrl':>8}{'edge':>8}{'coins>ctrl':>11}{'yrs+':>6}")
        for gate in GATES:
            if gate == "not US" and rule == "1D": continue
            for ename, efn in exits:
                R, Cc = run(P, gate, efn)
                if len(R) < 60: print(f"  {gate:<15}{ename:<9}{len(R):>7} too few"); continue
                t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
                by = (R.groupby("sym").ret.mean() - Cc.groupby("sym").ret.mean()); byy = (R.groupby("y").ret.mean() - Cc.groupby("y").ret.mean())
                print(f"  {gate:<15}{ename:<9}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+7.1f}{(R.ret>0).mean()*100:>5.0f}%"
                      f"{Cc.ret.mean()*100:>+7.3f}%{(R.ret.mean()-Cc.ret.mean())*100:>+7.3f}{(by>0).mean()*100:>10.0f}%"
                      f"{(byy>0).sum():>4}/{len(byy)}", flush=True)
