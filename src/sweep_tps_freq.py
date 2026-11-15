"""15 Nov: TPS ladder swept looser (RSI(2) threshold, 1 or 2 closes, trend filter). Same mechanics as review2_fixes.tps_o.
£ at live stakes: whole ladder loses 2% of £500 (£10) at the 15% kill -> full ladder notional £66.7, £ = pnl fraction x £66.7."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, itertools, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F
def tps(d, cost, th=25, consec=2, filt="200d", maxd=30, kill=0.15, ladder=(0.1, 0.2, 0.3, 0.4), fund=0.06):
    O, C = d.open.values, d.close.values; r = F.rsi(d.close, 2).values
    ma = d.close.rolling(200).mean().values if filt == "200d" else np.full(len(C), -np.inf); out = []; i = 201; n = len(C)
    while i < n - 2:
        ok = C[i] > ma[i] and r[i] < th and (consec == 1 or r[i - 1] < th)
        if not ok: i += 1; continue
        qty = spent = 0.0; lastfill = None; k = 0; j0 = i; buy_next = True; j = i
        while j < n - 1:
            if buy_next and k < len(ladder):
                px = O[j + 1]; w = ladder[k]; qty += w / (px * (1 + cost)); spent += w; lastfill = px; k += 1
            buy_next = False; jj = j + 1
            if jj >= n: break
            avg = spent / qty
            if r[jj] > 70 or (jj - j0) >= maxd or C[jj] <= avg * (1 - kill):
                if jj + 1 >= n: break
                val = qty * O[jj + 1] * (1 - cost) - spent * fund / 365 * 1.4 * (jj + 1 - j0) * 0.5
                out.append((d.index[j0], val - spent)); break
            if k < len(ladder) and C[jj] < lastfill: buy_next = True
            j = jj
        i = j + 2
    return out
if __name__ == "__main__":
    rows = []
    for th, consec, filt in itertools.product((25, 30, 35), (2, 1), ("200d", "none")):
        t = pd.DataFrame([(a, b, k) for k in F.IXG for a, b in tps(F.D[k], F.COST[k], th, consec, filt)], columns=["t", "P", "m"])
        t = t[t.t >= "2000-01-01"]; yrs = (t.t.max() - pd.Timestamp("2000-01-01")).days / 365.25; g = t.groupby(t.t.dt.year).P.sum()
        l5 = t[t.t >= t.t.max() - pd.Timedelta(days=1826)]; l1 = t[t.t >= t.t.max() - pd.Timedelta(days=365)]
        rows.append(dict(rsi2_lt=th, closes=consec, filt=filt, n_yr=len(t) / yrs, win=(t.P > 0).mean(), gbp_yr=t.P.sum() * 66.7 / yrs,
                         yrs_pos=f"{(g > 0).sum()}/{len(g)}", gbp5=l5.P.sum() * 66.7 / 5, gbp1=l1.P.sum() * 66.7, worst=t.P.min() * 66.7))
    r = pd.DataFrame(rows); r.to_csv("runs/sweep/tps_sweep.csv", index=False); print(r.round(2).sort_values("gbp_yr", ascending=False).to_string(index=False))
