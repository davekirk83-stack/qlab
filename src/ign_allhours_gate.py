"""Doc 197 — Ignition v1.1 rules at all hours (AuclairsDad runs all sessions, 3.5-5 trades/day). Through THE GATE, with the data's own spread,
and again with +1 pt extra cost outside US cash hours (IG's out-of-hours spread on US Tech 100 is wider)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, paperbook7 as P7
from gate_books import ign_prep, ign_signals, ign_manage, NY, sigframe
d = ign_prep(); lt = d.index.tz_convert(NY)
for label, extra, hours in (("IGNITION all hours ex-lunch, data spread", 0.0, "all"), ("IGNITION all hours ex-lunch, +1pt out of hours", 1.0, "all"),
                            ("IGNITION outside US cash hours only, +1pt", 1.0, "out")):
    x = d.copy(); m = lt.hour * 60 + lt.minute; cash = (m >= P7.US_OPEN) & (m < P7.US_CLOSE)
    x.loc[~cash, "cost"] = x.loc[~cash, "cost"] + extra
    el = ~np.isin(lt.hour, P7.V11_SKIP_HOURS) if hours == "all" else ~cash
    x["eligible"] = el
    def sigs(df, el=el):
        df2 = P7.features(df) if "sig" not in df else df
        s = df2.sig.values; a = df2.atr.values; e2 = pd.Series(el, index=d.index).reindex(df2.index).fillna(False).values
        ix = np.where(e2 & (s != 0) & np.isfinite(a))[0]
        return sigframe(df2.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)
    r = G.judge(label, x, sigs, manage=ign_manage); print(G.line(r), flush=True)
    t = pd.read_csv(f"{G.OUT}/{label.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    for lab, g in (("dev", t[t.t < cut]), ("hold", t[t.t >= cut])):
        h = len(g) // 2
        print(f"   {lab:4s} n{len(g):4d} pts/trade {g.pts.mean():+6.2f} total {g.pts.sum():+7.0f} halves {g.pts.iloc[:h].mean():+.2f}/{g.pts.iloc[h:].mean():+.2f} t {g.pts.mean()/g.pts.std()*np.sqrt(len(g)):+.2f}", flush=True)
