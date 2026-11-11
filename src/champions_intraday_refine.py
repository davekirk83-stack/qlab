"""Doc 228 part 3 — refine the intraday winners (Williams volatility breakout) and fix the stops that broke the others
(Crabel stretch stopped at the open = 17% win; widen to the other side of the bracket)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import champions_intraday as CI
def wvb(m, S, d, k, stop_mult, sides=(1, -1), cm=1.0, filt=None):
    out = []; g = dict(tuple(d.groupby("day")))
    for day, r in S.iterrows():
        if not np.isfinite(r.avg10) or day not in g or not np.isfinite(r.prng) or (filt is not None and not filt(r)): continue
        b = g[day]; bars = (b.open.values, b.high.values, b.low.values, b.close.values); a = k * r.prng; sd = stop_mult * a
        res = CI.bracket(bars, r.o + a, r.o - a, r.o + a - sd, r.o - a + sd, sides)
        if res: s, e, x = res; pts = s * (x - e) - cm * r.cost; out.append((pd.Timestamp(day), s, pts, pts / r.avg10))
    return pd.DataFrame(out, columns=["t", "side", "pts", "R"])
def stretch(m, S, d, mult, cm=1.0):
    out = []; g = dict(tuple(d.groupby("day")))
    for day, r in S.iterrows():
        if not np.isfinite(r.avg10) or day not in g: continue
        b = g[day]; bars = (b.open.values, b.high.values, b.low.values, b.close.values); st = r.stretch
        res = CI.bracket(bars, r.o + st, r.o - st, r.o + st - mult * st, r.o - st + mult * st, (1, -1))
        if res: s, e, x = res; pts = s * (x - e) - cm * r.cost; out.append((pd.Timestamp(day), s, pts, pts / r.avg10))
    return pd.DataFrame(out, columns=["t", "side", "pts", "R"])
def show(lab, t, t15):
    sm = CI.summary(t)
    if sm: print(f"  {lab:44s} n {sm['n']:4d} | {sm['pts']:+8.2f} pts {sm['R']:+.3f} R (t {sm['t']:+.2f}) win {100 * sm['win']:.0f}% | first 60% {sm['dev']:+.3f} last 40% {sm['hold']:+.3f} | months + {sm['mpos']} | x1.5 {t15.R.mean():+.3f}", flush=True)
for m in sys.argv[1:] or ["NQ"]:
    d, S = CI.sessions(m); print(f"== {m}", flush=True)
    for k in (0.3, 0.4, 0.5, 0.6, 0.7):
        for sm_ in (1.0, 2.0):
            show(f"Williams VB k={k} stop {sm_:.0f}x (opposite side = 2x)", wvb(m, S, d, k, sm_), wvb(m, S, d, k, sm_, cm=1.5))
    for mult in (2, 3, 4): show(f"Crabel stretch, stop {mult}x stretch", stretch(m, S, d, mult), stretch(m, S, d, mult, cm=1.5))
