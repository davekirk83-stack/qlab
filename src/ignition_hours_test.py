"""Ignition on IG beyond US cash hours (avenue 1, 26 Oct 2026). One year of NQ 5-min bars (data_nq_cache), v1.1 stop rule, costs at IG
spread-bet spreads: US Tech 100 1 pt in US cash hours (13:30-20:00 UTC), out-of-hours modelled at 2 pts and at 4 pts (conservative).
Reported by entry-hour block, both halves, vs the registered US-hours slice."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src"); import paperbook7 as P
bars = pd.read_csv("/home/claude/qlab/data_nq_cache/nq_5m.csv", index_col=0); bars.index = pd.to_datetime(bars.index, utc=True)
d0 = P.features(bars)
def run(d, ooh_spread, keep):
    m = d.index.hour*60 + d.index.minute; us = (m >= P.US_OPEN) & (m < P.US_CLOSE)
    d = d.copy(); d["cost"] = np.where(us, 0.5, ooh_spread/2)
    O, H, L, C, cost, atr, sig = d.open.values, d.high.values, d.low.values, d.close.values, d.cost.values, d.atr.values, d.sig.values
    idx = d.index; day = d.day.values; out = []; last = -10**9; cur = None; ntr = 0; dpl = 0.0
    for i in range(300, len(C)-1):
        if day[i] != cur: cur = day[i]; ntr = 0; dpl = 0.0
        s = int(sig[i])
        if s == 0 or np.isnan(atr[i]) or i < last + P.COOL or ntr >= P.MAXT or dpl <= -P.LOSSCAP: continue
        if not keep(idx[i]): continue
        r = P.manage(O, H, L, C, cost, atr, i, s, len(C), max(P.STOP, P.V11_STOP_ATR*atr[i]))
        if r is None: break
        out.append((idx[i], r[0])); last = i + r[1]; ntr += 1; dpl += r[0]
    return pd.DataFrame(out, columns=["t", "pts"])
blocks = {"Asia 00-07": (0, 7), "London 07-13:30": (7, 13.5), "US 13:30-16": (13.5, 16), "US lunch 16-19": (16, 19), "US late 19-20": (19, 20), "evening 20-24": (20, 24)}
def hr(t): return t.hour + t.minute/60
for ooh in (2.0, 4.0):
    print(f"\n== out-of-hours spread {ooh} pts (US cash hours 1 pt)")
    for nm, (a, b) in blocks.items():
        r = run(d0, ooh, lambda t, a=a, b=b: a <= hr(t) < b); x = r.pts.values; h = len(x)//2
        if len(x) < 5: print(f"  {nm:16s} n {len(x)}"); continue
        print(f"  {nm:16s} n {len(x):3d}  {x.mean():+6.1f} pts/trade  t {x.mean()/x.std()*np.sqrt(len(x)):+.1f}  win {100*(x>0).mean():.0f}%  H1 {x[:h].mean():+.1f} H2 {x[h:].mean():+.1f}  total {x.sum():+.0f}")
    for nm, keep in (("registered v1.1 (US hrs, no lunch)", lambda t: 13.5 <= hr(t) < 20 and t.hour not in (16, 17, 18)),
                     ("v1.1 + Asia + London", lambda t: hr(t) < 13.5 or (13.5 <= hr(t) < 20 and t.hour not in (16, 17, 18))),
                     ("all hours except lunch", lambda t: t.hour not in (16, 17, 18))):
        r = run(d0, ooh, keep); x = r.pts.values; h = len(x)//2
        print(f"  {nm:36s} n {len(x):3d}  {x.mean():+6.1f}/trade  t {x.mean()/x.std()*np.sqrt(len(x)):+.1f}  H1 {x[:h].mean():+.1f} H2 {x[h:].mean():+.1f}  total {x.sum():+.0f} pts  (= £{x.sum():,.0f} at £1/pt)")
