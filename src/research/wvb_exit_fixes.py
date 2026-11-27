"""
DK 27 Nov: fix the mistakes — winning trades that ended as losses, timing, profit taking, loss avoidance.
Live WVB (Williams breakout) record 17-26 Nov: winners kept only ~35% of their best open profit (no target, held to the cash close);
every US-index entry in the first 30 minutes of the New York open lost (-£36 of the -£47 WVB live loss).
Tests on the full 5-min history (champions_intraday data, IG costs), live k per market:
  delay  = orders only live from N minutes after the session open (DK's own rule: nothing before 15:15 London);
  be     = stop to entry once the trade is up b x the initial risk;
  tgt    = take profit at T x initial risk (instead of holding to the close);
  trail  = after +1R, trail the stop 1R behind the best price.
Conservative fills: stop before target when both are touched in one bar; target only from the bar after entry.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import champions_intraday as C

KM = {"NQ": 0.4, "US500": 0.5, "USDJPY": 0.5, "GOLD": 0.3}

def trade(O, H, L, Cl, MM, up, dn, delay, be, tgt, trail):
    for k in range(len(O)):
        if MM[k] < delay: continue
        bu, bd = H[k] >= up, L[k] <= dn
        if not (bu or bd): continue
        if bu and bd: s = 1
        else: s = 1 if bu else -1
        e = max(up, O[k]) if s == 1 else min(dn, O[k])
        # if the session opened beyond the trigger after the delay, entry is at the bar open (gap through)
        risk = up - dn; st = e - s * risk                                 # stop = the other side of the bracket (2a)
        if (s == 1 and L[k] <= st) or (s == -1 and H[k] >= st) or (bu and bd): return s, e, st, risk
        best = e
        for q in range(k + 1, len(O)):
            # stop first
            if (s == 1 and L[q] <= st) or (s == -1 and H[q] >= st):
                x = min(st, O[q]) if s == 1 else max(st, O[q]); return s, e, x, risk
            if tgt:
                tp = e + s * tgt * risk
                if (s == 1 and H[q] >= tp) or (s == -1 and L[q] <= tp): return s, e, (max(tp, O[q]) if s == 1 else min(tp, O[q])), risk
            best = max(best, H[q]) if s == 1 else min(best, L[q])
            fav = (best - e) * s
            if be and fav >= be * risk: st = max(st, e) if s == 1 else min(st, e)
            if trail and fav >= risk: st = max(st, best - risk) if s == 1 else min(st, best + risk)
        return s, e, Cl[-1], risk
    return None

def run(m, d, S, delay=0, be=0, tgt=0, trail=False):
    k = KM[m]; g = dict(tuple(d.groupby("day"))); out = []
    for day, r in S.iterrows():
        if not np.isfinite(r.prng) or not np.isfinite(r.avg10) or day not in g: continue
        b = g[day]; a = k * r.prng
        res = trade(b.open.values, b.high.values, b.low.values, b.close.values, b.mm.values, r.o + a, r.o - a, delay, be, tgt, trail)
        if res:
            s, e, x, risk = res; pts = s * (x - e) - r.cost
            out.append((pd.Timestamp(day), pts / risk))            # in R (initial risk) -> £ = R x £ risked
    return pd.DataFrame(out, columns=["t", "R"])

VARIANTS = [("live rule", {}),
            ("delay 30m", {"delay": 30}), ("delay 45m", {"delay": 45}), ("delay 60m", {"delay": 60}),
            ("BE at 0.5R", {"be": 0.5}), ("BE at 1R", {"be": 1.0}),
            ("target 1R", {"tgt": 1.0}), ("target 1.5R", {"tgt": 1.5}), ("target 2R", {"tgt": 2.0}),
            ("trail 1R", {"trail": True}),
            ("delay 30 + BE 1R", {"delay": 30, "be": 1.0}), ("delay 30 + trail", {"delay": 30, "trail": True}),
            ("delay 45 + trail", {"delay": 45, "trail": True}), ("delay 30 + tgt 1.5R", {"delay": 30, "tgt": 1.5})]

if __name__ == "__main__":
    rows = []
    for m in ["NQ", "US500", "GOLD", "USDJPY"]:
        d, S = C.sessions(m)
        for name, kw in VARIANTS:
            t = run(m, d, S, **kw)
            if len(t) < 30: continue
            h = len(t) // 2; yrs = (t.t.iloc[-1] - t.t.iloc[0]).days / 365.25
            rows.append(dict(m=m, variant=name, n=len(t), win=(t.R > 0).mean(), meanR=t.R.mean(), h1=t.R[:h].mean(), h2=t.R[h:].mean(),
                             last12m=t[t.t >= t.t.iloc[-1] - pd.Timedelta("365D")].R.mean(), worst_dd=(t.R.cumsum() - t.R.cumsum().cummax()).min(),
                             since=str(t.t.iloc[0].date())))
    r = pd.DataFrame(rows); os.makedirs("runs/research", exist_ok=True); r.to_csv("runs/research/wvb_exit_fixes.csv", index=False)
    pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
