"""NEW YORK OPEN STUDY (DK, 20 Oct 2026: "It's useful to study these NYO patterns and I think eventually we may be able to develop a book for it").
BTC 15-min, weekdays since Oct 2021. Sessions UTC: Asia 00-07, London 07-13, New York 13-20.
Conditions: London range in the bottom 35% of all days ("tight"); London close in the lower/upper half of the Asia range; London drift sign.
Outputs: first-hour direction, NY session direction, which Asia level is taken first, NY range vs London range, first-hour-predicts-session.
"""
import pandas as pd, numpy as np, sys
sym = sys.argv[1] if len(sys.argv) > 1 else "BTCUSD"
d = pd.read_csv(f"/home/claude/qlab/data_15m/{sym}.csv"); d.index = pd.to_datetime(d[d.columns[0]], utc=True); d = d[["open","high","low","close"]].astype(float); d = d[d.index >= "2021-10-01"]
rows = []
for day, g in d.groupby(d.index.date):
    if g.index[0].weekday() >= 5: continue
    asia = g.between_time("00:00","06:59"); lon = g.between_time("07:00","12:59"); ny = g.between_time("13:00","19:59")
    if len(asia) < 20 or len(lon) < 20 or len(ny) < 24: continue
    ah, al = asia.high.max(), asia.low.min(); lh, ll = lon.high.max(), lon.low.min(); lc = lon.close.iloc[-1]
    pos = (lc - al)/(ah - al) if ah > al else np.nan
    first_move = ny.iloc[:4].close.iloc[-1] - ny.open.iloc[0]; nyc = ny.close.iloc[-1] - ny.open.iloc[0]
    hit_lo = (ny.low <= al).values; hit_hi = (ny.high >= ah).values
    ilo = np.argmax(hit_lo) if hit_lo.any() else 999; ihi = np.argmax(hit_hi) if hit_hi.any() else 999
    first = "low" if ilo < ihi else ("high" if ihi < ilo else "neither")
    rows.append(dict(day=day, lon_rng=(lh-ll)/lc, pos=pos, lon_drift=(lc-lon.open.iloc[0])/lc, first60=first_move/lc, ny=nyc/lc, first=first, ny_rng=(ny.high.max()-ny.low.min())/lc))
R = pd.DataFrame(rows); print(sym, len(R), "weekdays since Oct 2021")
tight = R.lon_rng <= R.lon_rng.quantile(0.35); low = R.pos < 0.5; down = R.lon_drift < 0
def rep(lbl, X):
    print(f"{lbl:<52} n {len(X):>4} | first-hour up {(X.first60>0).mean()*100:.0f}% | NY session up {(X.ny>0).mean()*100:.0f}% | Asia low first {(X['first']=='low').mean()*100:.0f}%, high first {(X['first']=='high').mean()*100:.0f}% | NY range med {X.ny_rng.median()*100:.2f}% vs London {X.lon_rng.median()*100:.2f}% | first hour predicts session {((np.sign(X.first60)==np.sign(X.ny))).mean()*100:.0f}%")
rep("ALL weekdays", R); rep("tight London (bottom 35%)", R[tight]); rep("tight + lower half of Asia range", R[tight & low])
rep("tight + lower half + London drifted DOWN", R[tight & low & down]); rep("mirror: tight + upper half + drifted UP", R[tight & ~low & (R.lon_drift>0)])
R.to_csv(f"/home/claude/qlab/runs/nyo_{sym}.csv", index=False)
