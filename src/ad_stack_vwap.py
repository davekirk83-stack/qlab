"""Doc 227 addendum — DK 11 Nov 09:07, AuclairsDad's post: his algo "made 700 ticks just going long over and over" overnight in a slow trend with
strong internals; his panel shows Regime Score, Trigger Score, VWAP and an HTF Fast EMA. Add his two visible filters to our stack:
  VWAP  : longs only above the session VWAP (CME session from 18:00 New York), shorts only below (tick volume);
  HTF   : longs only when the 1-hour fast EMA(9) is rising (and price above it), shorts the mirror.
Base = the doc-227 winner: full stack (regime + coil + Ignition), all hours, Tue/Wed off."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ad_stack_refine.py")).read(); exec(src[:src.index("ALL = np.ones")])
raw = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); raw.index = pd.to_datetime(raw.index, utc=True); raw = raw.reindex(d.index)
sess = (d.index.tz_convert("America/New_York") - pd.Timedelta(hours=18)).date
tp = (d.high + d.low + d.close) / 3; v = raw.vol.fillna(0).clip(lower=1)
VW = ((tp * v).groupby(sess).cumsum() / v.groupby(sess).cumsum()).shift(1).values
h1 = d.close.resample("1h").last().dropna(); e9 = h1.ewm(span=9, adjust=False).mean()
slope = np.sign(e9.diff()).shift(1).reindex(d.index, method="ffill").values; e9f = e9.shift(1).reindex(d.index, method="ffill").values
CL = d.close.shift(1).values
def var2(vw, htf):
    base = variant(np.ones(len(d), bool), (1, 2))
    def fn(x):
        f = base(x)
        if not len(f): return f
        ii = pd.Series(np.arange(len(d)), index=d.index).reindex(f.index).values.astype(int); s = f.side.values if "side" in f else f.s.values
        ok = np.ones(len(f), bool)
        if vw: ok &= np.sign(CL[ii] - VW[ii]) == s
        if htf: ok &= (slope[ii] == s) & (np.sign(CL[ii] - e9f[ii]) == s)
        return f[ok]
    return fn
for name, fn in (("Stack all hours TueWed off (base)", var2(False, False)), ("+ VWAP side", var2(True, False)), ("+ 1h fast EMA", var2(False, True)), ("+ VWAP + 1h fast EMA", var2(True, True))):
    r = G.judge(name, d, fn, manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/{name.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    m_ = t.groupby(t.t.dt.to_period("M")).pts.sum()
    print(f"{name:36s} n {len(t)} pts/trade {t.pts.mean():+.2f} total {t.pts.sum():+.0f} win {100 * (t.pts > 0).mean():.0f}% | dev {t[t.t < cut].pts.mean():+.2f} hold-out {t[t.t >= cut].pts.mean():+.2f} | months + {(m_ > 0).sum()}/{len(m_)} worst {m_.min():+.0f}", flush=True)
