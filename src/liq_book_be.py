"""Doc 225 addendum — DK 16:36: "I should have taken profit on the bounce… instead out at B/E".
LIQ book (target 3%, stop 4%, 3 days, 200-day + CPI + toxicity skips) with trade management variants:
  A: as doc 225;  B: stop to breakeven once +0.75% above the cluster;  C: B + half off at +1% (limit, maker);  D: half off at +1% only;
  E: B with +0.5% trigger;  F: C with half off at +0.8%.  Same-bar conflicts resolved against us (stop first)."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import liq_book as LB
H, L, C, N, IX = LB.H, LB.L, LB.C, LB.N, LB.IX
def trade(j, lvl, cm=1.0, be=None, part=None, tgt_f=0.03, stop_f=0.04, hold=288):
    tgt, stop, r2 = lvl * (1 + tgt_f), lvl * (1 - stop_f), lvl * (1 - LB.RUNG2); e = min(N - 1, j + hold)
    nx = np.searchsorted(LB.CPI_J, j + 1); nx = LB.CPI_J[nx] if nx < len(LB.CPI_J) else 10 ** 9
    if nx - 1 <= e: e = max(j, nx - 2)
    got2 = False; pnl = 0.0; open_sz = None; cur_stop = stop; armed = False; parted = False
    for k in range(j, e + 1):
        if not got2 and L[k] <= r2: got2 = True
        size = 1.0 if got2 else 0.5; avg = (lvl + r2) / 2 if got2 else lvl
        rem = size * (0.5 if parted else 1.0)
        if L[k] <= cur_stop:                                                   # stop (taker) — checked first
            px = cur_stop * (1 - LB.SLIP); return pnl + rem * (px * (1 - cm * LB.TAKER) / avg - 1) * 100
        if k == j: continue
        if part and not parted and H[k] >= lvl * (1 + part):
            parted = True; pnl += size * 0.5 * (lvl * (1 + part) / avg - 1) * 100; rem = size * 0.5
        if H[k] >= tgt: return pnl + rem * (tgt / avg - 1) * 100
        if be and not armed and H[k] >= lvl * (1 + be): armed = True; cur_stop = max(cur_stop, avg * (1 + cm * LB.TAKER + LB.SLIP))   # true breakeven incl. exit fee
    size = 1.0 if got2 else 0.5; avg = (lvl + r2) / 2 if got2 else lvl; rem = size * (0.5 if parted else 1.0)
    return pnl + rem * (C[e] * (1 - LB.SLIP) * (1 - cm * LB.TAKER) / avg - 1) * 100
EV = LB.events(cpi=True, regime=True)
def build(cm=1.0, rnd=None, **kw):
    if rnd is not None:
        g = np.random.default_rng(); js = g.integers(2000, N - 300, len(EV)); return pd.DataFrame({"t": IX[js], "R": [trade(j, LB.O[j], cm, **kw) for j in js], "m": "BTC"})
    return pd.DataFrame({"t": IX[EV.j.values.astype(int)], "R": [trade(int(j), l, cm, **kw) for j, l in EV[["j", "lvl"]].values], "m": "BTC"})
if __name__ == "__main__":
    import standard_test as ST
    for nm, kw in (("A as doc 225", {}), ("B breakeven at +0.75%", {"be": 0.0075}), ("C breakeven +0.75% & half off +1%", {"be": 0.0075, "part": 0.01}),
                   ("D half off at +1% only", {"part": 0.01}), ("E breakeven at +0.5%", {"be": 0.005}), ("F breakeven +0.75% & half off +0.8%", {"be": 0.0075, "part": 0.008})):
        out, t = ST.judge(f"LIQ mgmt {nm}", "liquidation clusters (crypto, Revolut X costs)", ["BTC"], lambda cm=1.0, rnd=None, kw=kw: build(cm, rnd, **kw), random_runs=30)
        y = t.groupby(t.t.dt.year).R.mean(); print("      by year:", "  ".join(f"{i}: {v:+.2f}%" for i, v in y.items()), f"| win {100 * (t.R > 0).mean():.0f}%, worst {t.R.min():+.2f}%\n")
