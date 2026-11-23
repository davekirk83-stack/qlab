"""doc 256: AuclairsDad's entry paths on TRUE NQ order flow (Databento CME trades, aggressor side, Apr-Nov 2026, ~$85.51 of DK's free
credit) against our tick-rule stand-in, same window, same prices (IG/Dukascopy CFD bars), same gates and exits as ad_full_stack.py.
Only the order-flow columns (vol, delta) change. The window is shorter (7.7 months), so the split is earlier/later halves of it."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); os.environ.setdefault("QLAB_ROOT", os.getcwd())
src = open("src/ad_stack_gate.py").read(); exec(src[:src.index("R = []")])
t = pd.read_csv("data_nq_cache/nq_true_delta_5m.csv.gz", index_col=0, parse_dates=True)
t["delta"] = t.buy.astype("int64") - t.sell.astype("int64")
lo, hi = t.index[0], t.index[-1]; inwin = (d.index >= lo) & (d.index <= hi)
cov = d.index[inwin].isin(t.index).mean(); print(f"true-delta coverage of our bars in window: {cov:.0%}")
def run(dd, label):
    F = P7.features(dd); a = F.atr.values; ds = F.dshare.values; htf = F.htf.values; C_, O_, H_, L_ = F.close.values, F.open.values, F.high.values, F.low.values
    rng = H_ - L_; loc = np.where(rng > 0, (C_ - L_) / np.where(rng > 0, rng, 1), 0.5); dow = lt.dayofweek.values; N = len(F)
    nd6 = pd.Series(F.delta.values).rolling(6).sum().values; thr = np.nanpercentile(np.abs(nd6[inwin]), 90)
    hh = pd.Series(H_).rolling(20).max().shift(1).values; ll = pd.Series(L_).rolling(20).min().shift(1).values
    ih = pd.Series(H_).rolling(20).apply(np.argmax, raw=True).shift(1).values; il = pd.Series(L_).rolling(20).apply(np.argmin, raw=True).shift(1).values
    idx = np.arange(N); ph = np.full(N, np.nan); pl = np.full(N, np.nan)
    ok = np.isfinite(ih); j = (idx - 20 + np.nan_to_num(ih)).astype(int); ph[ok] = nd6[np.clip(j, 0, N-1)][ok]
    ok = np.isfinite(il); j = (idx - 20 + np.nan_to_num(il)).astype(int); pl[ok] = nd6[np.clip(j, 0, N-1)][ok]
    div = np.where((H_ > hh) & (nd6 < ph) & (np.abs(ph) >= thr) & (C_ < O_), -1, np.where((L_ < ll) & (nd6 > pl) & (np.abs(pl) >= thr) & (C_ > O_), 1, 0))
    brk = F.sig.values * (RNG20 <= 4.0 * a)
    conv = np.where((ds >= 0.087) & (loc >= 0.7) & (htf == 1), 1, np.where((ds <= -0.087) & (loc <= 0.3) & (htf == -1), -1, 0))
    out = []
    for name, paths in (("breakout", ["brk"]), ("breakout + conviction", ["brk", "conv"]), ("divergence alone", ["div"]), ("conviction alone", ["conv"]), ("all three", ["brk", "conv", "div"])):
        s = np.zeros(N, int)
        for p in paths:
            v = {"brk": brk, "conv": conv, "div": div}[p]
            v = np.where((REG == 0) | (REG == v), v, 0) if p == "div" else np.where(REG == v, v, 0)
            s = np.where(s == 0, v, s)
        okk = (s != 0) & np.isfinite(a) & EL & ~np.isin(dow, (1, 2)) & inwin; ix = np.where(okk)[0]
        if not len(ix): out.append(f"{label:10} {name:24} n0"); continue
        sf = lambda x, ix=ix, s=s, a=a: sigframe(F.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)
        key = f"ADTRUE {label} {name}"; G.judge(key, dd, sf, manage=ign_manage)
        tr = pd.read_csv(f"{G.OUT}/{key.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"])
        tr = tr[(tr.t >= lo) & (tr.t <= hi)]; mid = lo + (hi - lo) / 2; mo = tr.groupby(tr.t.dt.to_period("M")).pts.sum()
        out.append(f"{label:10} {name:24} n {len(tr):4} pts/trade {tr.pts.mean():+.2f} win {100*(tr.pts>0).mean():.0f}% total {tr.pts.sum():+.0f} | early {tr[tr.t<mid].pts.mean():+.2f} / late {tr[tr.t>=mid].pts.mean():+.2f} | months+ {(mo>0).sum()}/{len(mo)}")
        print(out[-1], flush=True)
    return out
res = run(d.copy(), "tick-rule")
dt_ = d.copy(); m = dt_.index.isin(t.index) & inwin
dt_.loc[m, "delta"] = t.delta.reindex(dt_.index[m]).values; dt_.loc[m, "vol"] = t.vol.reindex(dt_.index[m]).values
res += run(dt_, "TRUE")
open("runs/research/ad_true_delta.txt", "w").write(f"window {lo} -> {hi}, coverage {cov:.0%}\n" + "\n".join(res))
