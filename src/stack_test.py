"""Doc 197 — AuclairsDad's stack on US Tech 100 (DK 9 Nov: "We know how he does it"). (1) Ignition sets the day's direction;
(3) the noise-band breakout (range-break) trades only in that direction, only after Ignition has fired that day. Through THE GATE."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, paperbook7 as P7
from market_search_2 import nb_prep, nb_signals, nb_manage
from gate_books import ign_eligible, sigframe
d = nb_prep("data_nq_cache/nq_5m.csv", 1.0)
b = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); b.index = pd.to_datetime(b.index, utc=True); f = P7.features(b)
d["isig"] = f.sig.reindex(d.index).fillna(0).values * ign_eligible(f.reindex(d.index).ffill()).astype(int)
def daydir(x):
    s = pd.Series(np.where(x.isig.values != 0, x.isig.values, np.nan), index=x.index)
    return s.groupby(x.session.values).ffill().fillna(0).values          # direction of the latest Ignition bar so far today (closed bars only)
def stack_signals(x):
    nb = nb_signals(x); dd = pd.Series(daydir(x), index=x.index).reindex(nb.index).values
    return nb[(dd != 0) & (np.sign(dd) == nb.side.values)]
def stack_first_signals(x):   # first Ignition of the day's direction only (not the latest)
    s = pd.Series(np.where(x.isig.values != 0, x.isig.values, np.nan), index=x.index)
    first = s.groupby(x.session.values).transform(lambda v: v.dropna().iloc[0] if v.notna().any() else np.nan)
    seen = s.notna().groupby(x.session.values).cummax()
    nb = nb_signals(x); fd = (first.where(seen)).reindex(nb.index).values
    return nb[np.isfinite(fd) & (np.sign(fd) == nb.side.values)]
for name, fn in (("STACK NQ ignition-latest + noiseband", stack_signals), ("STACK NQ ignition-first + noiseband", stack_first_signals)):
    r = G.judge(name, d, fn, manage=nb_manage, flat_at_session_end=True, max_bars_for_random=24); print(G.line(r), flush=True)
    t = pd.read_csv(f"{G.OUT}/{name.replace(' ', '_')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    for lab, g in (("dev", t[t.t < cut]), ("hold", t[t.t >= cut])):
        h = len(g) // 2
        if len(g): print(f"   {lab:4s} n{len(g):3d} pts/trade {g.pts.mean():+7.2f} total {g.pts.sum():+7.0f} halves {g.pts.iloc[:h].mean():+.2f}/{g.pts.iloc[h:].mean():+.2f} t {g.pts.mean()/g.pts.std()*np.sqrt(len(g)):+.2f}", flush=True)
