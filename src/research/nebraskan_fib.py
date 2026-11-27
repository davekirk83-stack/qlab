"""Nebraskangooner's Fib rule (Grok summary DK sent 22 Nov; doc 260), tested without his paid indicator:
after an up-swing (zigzag low -> high), a pullback to the 0.786 retracement is a buy; target the 0.236 retracement (back near the high);
losing the 0.786 'opens the 1.337 extension' -> stop variants: a close below 1.0 (the swing low) or a close below 0.886.
Mirror for shorts after a down-swing. Daily bars: BTC 2015-26, US 500 / US Tech 100 / Wall St / DAX 2000-26. Swings from a zigzag
(confirmed only once price has reversed by the threshold, so no look-ahead). Costs 0.1% BTC, 0.03% indices. Results in R (risk to the stop)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import market_search_2 as M2

def zig_swings(H, L, th):
    """yield (i_confirm, kind, start_px, end_px): an up-swing low->high is confirmed when price falls th from the high (and vice versa)."""
    out = []; mode = 0; hi = H[0]; lo = L[0]; ihi = ilo = 0; last_low = L[0]; last_high = H[0]
    for i in range(1, len(H)):
        if mode >= 0:
            if H[i] > hi: hi, ihi = H[i], i
            if L[i] <= hi * (1 - th) and mode == 1: out.append((i, "up", last_low, hi)); last_high = hi; mode = -1; lo, ilo = L[i], i; continue
            if mode == 0 and L[i] <= hi * (1 - th): mode = -1; lo, ilo = L[i], i; last_high = hi; continue
        if mode <= 0:
            if L[i] < lo: lo, ilo = L[i], i
            if H[i] >= lo * (1 + th) and mode == -1: out.append((i, "down", last_high, lo)); last_low = lo; mode = 1; hi, ihi = H[i], i; continue
            if mode == 0 and H[i] >= lo * (1 + th): mode = 1; hi, ihi = H[i], i; last_low = lo
    return out

def run(d, th, cost, stop_lvl=1.0, tgt_lvl=0.236, wait=40):
    H, L, C, O = d.high.values, d.low.values, d.close.values, d.open.values; res = []
    for (i0, kind, a, b) in zig_swings(H, L, th):
        if kind == "up":
            lo, hi = a, b; rng = hi - lo; e_lvl = hi - 0.786 * rng; tgt = hi - tgt_lvl * rng; stp = hi - stop_lvl * rng; s = 1
        else:
            hi, lo = a, b; rng = hi - lo; e_lvl = lo + 0.786 * rng; tgt = lo + tgt_lvl * rng; stp = lo + stop_lvl * rng; s = -1
        if rng <= 0: continue
        for j in range(i0 + 1, min(len(C), i0 + wait)):
            # invalidated before entry: price ran back past the target zone (new swing) -> skip
            if (s == 1 and H[j] >= tgt) or (s == -1 and L[j] <= tgt): break
            if (s == 1 and L[j] <= e_lvl) or (s == -1 and H[j] >= e_lvl):
                e = min(e_lvl, O[j]) if s == 1 else max(e_lvl, O[j]); risk = abs(e - stp)
                if risk <= 0: break
                x = None
                for q in range(j + 1, min(len(C), j + 120)):
                    if (s == 1 and C[q] <= stp) or (s == -1 and C[q] >= stp): x = C[q]; break     # stop on a CLOSE beyond (his 'losing' the level)
                    if (s == 1 and H[q] >= tgt) or (s == -1 and L[q] <= tgt): x = tgt; break
                if x is None: x = C[min(len(C) - 1, j + 119)]
                res.append((d.index[j], (s * (x - e) - cost * e) / risk)); break
    return res

if __name__ == "__main__":
    rows = []
    sets = {"BTC": (["BTC"], (0.15, 0.25), 0.001), "Indices": (["SPX", "NDX", "DJI", "DAX"], (0.05, 0.08), 0.0003)}
    for grp, (mk, ths, cost) in sets.items():
        D = {k: M2.daily(k, cost, 0) for k in mk}
        for th in ths:
            for stop in (1.0, 0.886):
                for tgt in (0.236, 0.5):
                    E = []; [E.extend(run(D[k], th, cost, stop, tgt)) for k in mk]
                    t = pd.DataFrame(E, columns=["t", "R"]).sort_values("t")
                    if len(t) < 10: continue
                    h = len(t) // 2
                    rows.append(dict(grp=grp, swing=th, stop=stop, tgt=tgt, n=len(t), win=(t.R > 0).mean(), meanR=t.R.mean(), h1=t.R[:h].mean(), h2=t.R[h:].mean(),
                                     last5=t[t.t.dt.year >= 2022].R.mean()))
                    print(rows[-1], flush=True)
    r = pd.DataFrame(rows); r.to_csv("runs/research/nebraskan_fib.csv", index=False); pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
