"""DK 22 Nov 10:32: "find a workaround for the other point ... Divergence". Our delta is tick-rule (Dukascopy quote upticks - downticks),
not his true bid/ask volume, so delta divergence lost (doc 256). Workaround from his own words (memory: his /CL algo - "new high on weaker
momentum -> short and scale in", scaling in at -12 and -17 before a -26 hard stop, one +32 target for all lots):
MOMENTUM divergence (RSI 14 lower high at a new 20-bar high, and the reverse) + his SCALE-IN exits, scaled to NQ by ATR
(adds at 0.46 and 0.65 of the stop distance, hard stop, one target at 1.23 x stop: his 12/17/26/32 ratios).
Gated like his: regime not against the trade (none or same side), Tue/Wed off, US lunch off. US Tech 100 5-min, costs = spread +1 pt outside cash."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); os.environ.setdefault("QLAB_ROOT", os.getcwd())
src = open("src/ad_stack_gate.py").read(); exec(src[:src.index("R = []")])
F = P7.features(d); a = F.atr.values; C_, O_, H_, L_ = F.close.values, F.open.values, F.high.values, F.low.values; cost = F.cost.values
delta = F.delta.diff() if False else None
rs = pd.Series(C_).diff(); up = rs.clip(lower=0).ewm(alpha=1/14).mean(); dn = (-rs.clip(upper=0)).ewm(alpha=1/14).mean(); rsi = (100 - 100/(1 + up/dn)).values
N = len(F); dow = lt.dayofweek.values
hh = pd.Series(H_).rolling(20).max().shift(1).values; ll = pd.Series(L_).rolling(20).min().shift(1).values
rsi_hh = pd.Series(rsi).rolling(20).max().shift(1).values; rsi_ll = pd.Series(rsi).rolling(20).min().shift(1).values
def signals(rsi_gap=3, regime="not_against"):
    s = np.where((H_ > hh) & (rsi < rsi_hh - rsi_gap) & (C_ < H_ - 0.5*(H_-L_)), -1, np.where((L_ < ll) & (rsi > rsi_ll + rsi_gap) & (C_ > L_ + 0.5*(H_-L_)), 1, 0))
    if regime == "not_against": s = np.where((REG == 0) | (REG == s), s, 0)
    elif regime == "none_only": s = np.where(REG == 0, s, 0)
    ok = (s != 0) & np.isfinite(a) & EL & ~np.isin(dow, (1, 2)); return s, ok
def sim(s, ok, stop_atr=2.0, scale=True, hold=36):
    res = []; nxt = 0
    for i in np.where(ok)[0]:
        if i < nxt or i + hold + 2 >= N: continue
        sd = s[i]; D = max(stop_atr * a[i], 20); e = O_[i+1] + sd*cost[i+1]
        rungs = [(e, 1.0)] + ([(e - sd*0.46*D, 1.0), (e - sd*0.65*D, 1.0)] if scale else [])
        stop = e - sd*D; filled = []; out = None
        for j in range(i+1, i+1+hold):
            for k, (px, w) in enumerate(rungs):
                if k not in [f[0] for f in filled] and (k == 0 or (sd == 1 and L_[j] <= px) or (sd == -1 and H_[j] >= px)): filled.append((k, px, w))
            qty = sum(w for _, _, w in filled); avg = sum(px*w for _, px, w in filled)/qty; tgt = avg + sd*1.23*D*(0.6 if scale else 1)
            if (sd == 1 and L_[j] <= stop) or (sd == -1 and H_[j] >= stop): out = (stop - avg)*sd*qty - cost[j]*qty; break
            if (sd == 1 and H_[j] >= tgt) or (sd == -1 and L_[j] <= tgt): out = (tgt - avg)*sd*qty - cost[j]*qty; break
        if out is None: out = (C_[i+hold] - avg)*sd*qty - cost[i+hold]*qty
        res.append((F.index[i], out / (3 if scale else 1))); nxt = j + 3   # pts per unit of full position (3 lots), so comparable
    return pd.Series([r for _, r in res], index=[t for t, _ in res])
cut = F.index[int(len(F) * 0.6)]; days = (F.index[-1] - F.index[0]).days / 365.25; out = []
for gap in (3, 6):
    for reg in ("not_against", "none_only"):
        for scale in (True, False):
            for sa in (1.5, 2.5):
                s, ok = signals(gap, reg); R = sim(s, ok, sa, scale)
                if not len(R): continue
                mo = R.groupby(R.index.to_period("M")).sum()
                out.append(f"rsi gap {gap} regime {reg:11} {'scale-in' if scale else 'single  '} stop {sa} ATR | n {len(R):4} ({len(R)/days/252:.1f}/day) pts {R.mean():+.2f} win {(R>0).mean():.0%} | dev {R[R.index<cut].mean():+.2f} hold {R[R.index>=cut].mean():+.2f} | months+ {(mo>0).sum()}/{len(mo)}")
                print(out[-1], flush=True)
open("runs/research/ad_divergence_momentum.txt", "w").write("\n".join(out))
