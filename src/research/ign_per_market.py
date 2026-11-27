"""Queued since 22 Nov (doc 255 correction): Ignition on other markets needs stops scaled to each market (its 45-pt floor and +15 breakeven
are NQ points). IG caches for US500 / Wall St / DAX / FTSE / gold have no order-flow delta, so this is the PRICE-ONLY Ignition
(ignition bar >= 1.25x avg range, in the HTF EMA20/50 direction, bar closes with it) — run on NQ too so the two can be compared.
Point parameters (stop floor 45, breakeven 15, costs from the data's spread) scaled by each market's median price vs NQ's."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import paperbook7 as P7
F = {"NQ": "data_nq_cache/nq_5m.csv", "US500": "data_ig_cache/USA500IDXUSD_5m.csv", "WALLST": "data_ig_cache/USA30IDXUSD_5m.csv",
     "DAX": "data_ig_cache/DEUIDXEUR_5m.csv", "FTSE": "data_ig_cache/GBRIDXGBP_5m.csv", "GOLD": "data_ig_cache/XAUUSD_5m.csv"}
base = dict(STOP=P7.STOP, BE=P7.BE)
nq_px = None; rows = []
for m, f in F.items():
    b = pd.read_csv(f, index_col=0); b.index = pd.to_datetime(b.index, utc=True)
    if "spread" not in b: b["spread"] = 0.0
    px = b.close.median(); nq_px = nq_px or px; k = px / nq_px
    for flow in (("price-only",) if m != "NQ" else ("order-flow", "price-only")):
        bb = b.copy()
        if flow == "price-only" or "delta" not in bb: bb["delta"] = np.sign(bb.close - bb.open) * bb.vol.clip(lower=1)
        d = P7.features(bb)
        P7.STOP, P7.BE = base["STOP"] * k, base["BE"] * k
        for lab, kw in (("US hours v1.1", dict(us_hours=True, v11=True)), ("all hours", dict())):
            t, _, _ = P7.replay(d, str(d.index[300].date()), 0, **kw); t = pd.DataFrame(t)
            if t.empty: continue
            h = len(t) // 2; atr = float(d.atr.median())
            rows.append(dict(m=m, flow=flow, hours=lab, n=len(t), win=(t.pts > 0).mean(), pts=t.pts.mean(), per_atr=t.pts.mean() / atr,
                             h1=t.pts[:h].mean() / atr, h2=t.pts[h:].mean() / atr, since=str(d.index[0].date())))
            print(rows[-1], flush=True)
P7.STOP, P7.BE = base["STOP"], base["BE"]
r = pd.DataFrame(rows); r.to_csv("runs/research/ign_per_market.csv", index=False); pd.set_option("display.width", 250); print(r.round(3).to_string(index=False))
