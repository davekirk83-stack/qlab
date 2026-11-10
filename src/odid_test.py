"""Doc 226 — Linda Raschke's OD/ID breakout (DK 18:41: her "all time favorite breakout formation… still pays better than any other").
Pattern: an OUTSIDE day (high above and low below the previous day's) followed by an INSIDE day (high and low inside the outside day's).
Entry: a STOP order through the inside day's high (buy) or low (sell), live for the next 3 days; a gap through the level fills at the open
(FTSE: Yahoo opens are faulty, fill at the level). Same-day both sides -> counted as a loss (in at one side, stopped at the other).
Stop: the other side of the inside day. Exit: after H days, decided at the close, out at the next open. IG real costs (one full spread per
side), long funding 6% x1.4. R in ATR(14) at the signal. Variants fixed in advance: both sides H=5; long only H=5; both sides H=10."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, std_books as SB, standard_test as ST
MK = ["SPX", "NDX", "DJI", "DAX", "FTSE", "GOLD", "TNOTE", "EURUSD", "GBPUSD", "USDJPY", "OIL"]
def sig(d):
    od = (d.high > d.high.shift(1)) & (d.low < d.low.shift(1))
    return od.shift(1).fillna(False) & (d.high < d.high.shift(1)) & (d.low > d.low.shift(1))
def run(k, E, hold, sides, win=3):
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values
    E = E.reindex(d.index).fillna(False).values.astype(bool); cost = F.COST.get(k, .0005); fy = 0.06 / 365 * 1.4; out = []; n = len(C); i = 0
    while i < n - 2:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        up, dn = H[i], L[i]; j0 = None
        for j in range(i + 1, min(n, i + 1 + win)):
            bu, bd = H[j] >= up, L[j] <= dn
            if bu and bd:                                              # both triggered the same day: assume the worse order
                s = 1 if 1 in sides else -1; e = up if s == 1 else dn; x = dn if s == 1 else up
                out.append((d.index[i], (s * (x - e) - cost * (e + x)) / A[i])); j0 = -1; break
            if (bu and 1 in sides) or (bd and -1 in sides):
                s = 1 if bu else -1; lvl = up if s == 1 else dn
                e = lvl if k == "FTSE" else (max(O[j], lvl) if s == 1 else min(O[j], lvl)); st = dn if s == 1 else up; j0 = j; break
            if bu or bd: j0 = -1; break                                # wrong-side break for a one-sided variant: setup over
        if j0 is None or j0 == -1: i += 1; continue
        px = None; j = j0
        while j < n:
            if j > j0 and ((s == 1 and L[j] <= st) or (s == -1 and H[j] >= st)): px = (min(st, O[j]) if s == 1 else max(st, O[j])) if k != "FTSE" else st; break
            if j == j0 and ((s == 1 and L[j] <= st and C[j] < e) or (s == -1 and H[j] >= st and C[j] > e)): px = st; break    # reversal on the entry day
            if (j - j0 + 1) >= hold and j + 1 < n: px = O[j + 1] if k != "FTSE" else C[j]; j += 1; break
            j += 1
        if px is None: break
        out.append((d.index[i], (s * (px - e) - cost * (e + px) - (fy * e * (j - j0) if s == 1 else 0)) / A[i])); i = j
    return out
def build(hold, sides):
    def b(cm=1.0, rnd=None):
        with SB.cost(cm): return SB.mk([(t, R, k) for k in MK for t, R in run(k, (rnd or (lambda k, e: e))(k, sig(F.D[k])), hold, sides)])
    return b
if __name__ == "__main__":
    core = SB.core()
    for nm, h, sd in (("OD/ID both sides, 5 days", 5, (1, -1)), ("OD/ID long only, 5 days", 5, (1,)), ("OD/ID both sides, 10 days", 10, (1, -1))):
        out, t = ST.judge(nm, "breakout (Raschke OD/ID)", MK, build(h, sd), core=core, random_runs=60)
        by = t.groupby("m").R.agg(["count", "mean"]); print("      by market:", "  ".join(f"{k} n{int(r['count'])} {r['mean']:+.2f}" for k, r in by.iterrows()))
        d = t[t.t.dt.year >= 2016]; print(f"      since 2016: n {len(d)} mean {d.R.mean():+.3f}; win {100 * (t.R > 0).mean():.0f}%; per year {len(t) / t.t.dt.year.nunique():.0f}\n")
