"""Weekly review 28 Nov 2026. WVB NQ entries at the New York open this week were stopped inside 10 minutes and then ran our way:
live NQ short 24 Nov 14:35 UTC -206.6 pts, +265 pts in the 2h after the stop; demo NQ long 25 Nov 14:55 -103.4 pts, +138 after.
Hypothesis (from 2 trades, so it must hold on full history, both halves): the stop at the other side of the bracket is too tight
in the opening minutes. Variants, judged in R of the INITIAL risk actually taken (a wider stop = a bigger R, so smaller stake):
  mult m      stop = m x bracket width from entry (live m = 1)
  grace g/w   for the first g minutes after entry the stop sits at w x bracket width, then tightens to 1 x
  each with and without the 2R target now on demo (IG_WVB_TGT_R=2).
Same engine, data and costs as wvb_exit_fixes.py; calibration: 'm1.0' and 'm1.0 tgt2' must reproduce its 'live rule' / 'target 2R' rows."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import champions_intraday as C
KM = {"NQ": 0.4, "US500": 0.5, "USDJPY": 0.5, "GOLD": 0.3}

def trade(O, H, L, Cl, MM, up, dn, mult, tgt, grace, gw):
    for k in range(len(O)):
        bu, bd = H[k] >= up, L[k] <= dn
        if not (bu or bd): continue
        s = 1 if bu else -1
        e = max(up, O[k]) if s == 1 else min(dn, O[k])
        width = up - dn; m0 = gw if grace else mult; R = m0 * width; st = e - s * m0 * width
        if (s == 1 and L[k] <= st) or (s == -1 and H[k] >= st) or (bu and bd): return s, e, st, R
        for q in range(k + 1, len(O)):
            if grace and (MM[q] - MM[k]) >= grace: st = e - s * mult * width if s * ((e - s * mult * width) - st) > 0 else st
            if (s == 1 and L[q] <= st) or (s == -1 and H[q] >= st):
                x = min(st, O[q]) if s == 1 else max(st, O[q]); return s, e, x, R
            if tgt:
                tp = e + s * tgt * width * mult      # target in units of the normal (m=1 x mult) risk, as the live 2R target
                if (s == 1 and H[q] >= tp) or (s == -1 and L[q] <= tp): return s, e, (max(tp, O[q]) if s == 1 else min(tp, O[q])), R
        return s, e, Cl[-1], R
    return None

def run(m, d, S, mult=1.0, tgt=0, grace=0, gw=1.0):
    k = KM[m]; g = dict(tuple(d.groupby("day"))); out = []
    for day, r in S.iterrows():
        if not np.isfinite(r.prng) or not np.isfinite(r.avg10) or day not in g: continue
        b = g[day]; a = k * r.prng
        res = trade(b.open.values, b.high.values, b.low.values, b.close.values, b.mm.values, r.o + a, r.o - a, mult, tgt, grace, gw)
        if res:
            s, e, x, R = res; out.append((pd.Timestamp(day), (s * (x - e) - r.cost) / R))
    return pd.DataFrame(out, columns=["t", "R"])

V = [("m1.0", {}), ("m1.25", {"mult": 1.25}), ("m1.5", {"mult": 1.5}), ("m2.0", {"mult": 2.0}),
     ("grace 15m at 2x", {"grace": 15, "gw": 2.0}), ("grace 30m at 2x", {"grace": 30, "gw": 2.0}), ("grace 30m at 1.5x", {"grace": 30, "gw": 1.5})]
if __name__ == "__main__":
    rows = []
    for m in ["NQ", "US500", "USDJPY"]:
        d, S = C.sessions(m)
        for tg in (0, 2.0):
            for name, kw in V:
                t = run(m, d, S, tgt=tg, **kw)
                if len(t) < 30: continue
                h = len(t) // 2; mo = t.groupby(t.t.dt.to_period("M")).R.sum()
                rows.append(dict(m=m, variant=name + (" tgt2" if tg else ""), n=len(t), win=(t.R > 0).mean(), meanR=t.R.mean(), medR=t.R.median(),
                                 h1=t.R[:h].mean(), h2=t.R[h:].mean(), worst_month=mo.min(), months_pos=f"{(mo>0).sum()}/{len(mo)}",
                                 worst_dd=(t.R.cumsum() - t.R.cumsum().cummax()).min(), since=str(t.t.iloc[0].date())))
    r = pd.DataFrame(rows); r.to_csv("runs/research/wvb_stop_fix.csv", index=False)
    pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
