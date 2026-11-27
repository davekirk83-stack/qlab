"""Doc 244 found (18 Nov) that fading NQ's first move (09:35 open -> 10:00 bar close) from the 10:05 open to 12:00 ET made +18.4 pts/trade
(n211, both halves +) — but it was never built. Before it can trade it needs a stop. Tests protective stops on the same data:
none (as doc 244), stop at the first move's extreme (+buffer), stop = k x the first move's size beyond entry, and a breakeven after +x pts.
NQ 5m, cost 2 pts round trip."""
import pandas as pd, numpy as np
d = pd.read_csv("data_nq_cache/nq_5m.csv", parse_dates=["ts"]).set_index("ts").tz_convert("America/New_York"); d = d[d.index.dayofweek < 5]; COST = 2.0
def run(stop_mode=None, k=1.0, be=None):
    out = []
    for day, g in d.groupby(d.index.date):
        g = g.between_time("09:30", "12:00")
        if len(g) < 30: continue
        try:
            m0 = float(g.between_time("09:35", "09:35").open.iloc[0]); m1 = float(g.between_time("10:00", "10:00").close.iloc[0])
            e = float(g.between_time("10:05", "10:05").open.iloc[0])
        except IndexError: continue
        mv = m1 - m0; s = -np.sign(mv)
        if s == 0: continue
        fm = g.between_time("09:35", "10:00"); ext = fm.high.max() if s == -1 else fm.low.min()   # the first move's extreme (we fade it)
        st = None
        if stop_mode == "extreme": st = ext - s * 5
        if stop_mode == "k": st = e - s * k * max(abs(mv), 20)
        w = g.between_time("10:05", "11:55"); x = None; best = 0.0
        for _, b in w.iterrows():
            if st is not None and ((s == 1 and b.low <= st) or (s == -1 and b.high >= st)): x = st; break
            best = max(best, s * ((b.high if s == 1 else b.low) - e))
            if be and best >= be: st = e if st is None else (max(st, e) if s == 1 else min(st, e))
        if x is None:
            try: x = float(g.between_time("12:00", "12:00").open.iloc[0])
            except IndexError: x = float(w.close.iloc[-1])
        out.append((pd.Timestamp(day), s * (x - e) - COST))
    t = pd.DataFrame(out, columns=["t", "pts"]); h = len(t) // 2; mo = t.groupby(t.t.dt.to_period("M")).pts.sum()
    return dict(n=len(t), win=round((t.pts > 0).mean(), 3), mean=round(t.pts.mean(), 1), h1=round(t.pts[:h].mean(), 1), h2=round(t.pts[h:].mean(), 1),
                worst=round(t.pts.min()), months_pos=f"{(mo>0).sum()}/{len(mo)}", worst_month=round(mo.min()))
if __name__ == "__main__":
    rows = []
    for lab, kw in (("no stop (doc 244)", {}), ("stop at first-move extreme +5", {"stop_mode": "extreme"}), ("stop 1x first move", {"stop_mode": "k", "k": 1.0}),
                    ("stop 1.5x first move", {"stop_mode": "k", "k": 1.5}), ("stop 2x first move", {"stop_mode": "k", "k": 2.0}),
                    ("stop 1.5x + BE at +40", {"stop_mode": "k", "k": 1.5, "be": 40}), ("extreme + BE at +40", {"stop_mode": "extreme", "be": 40})):
        r = run(**kw); r["variant"] = lab; rows.append(r); print(r, flush=True)
    pd.DataFrame(rows).to_csv("runs/research/froth_fade_stops.csv", index=False)
