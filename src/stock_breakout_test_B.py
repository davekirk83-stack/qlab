"""Doc 148 part B (POST-HOC, declared after part A failed; stricter bar: must pass the holdout and the timing control):
 ENTRY at the pivot intraday, as Minervini/Qullamaggie actually buy: buy stop at the prior 20-day high on a template day with a tight base;
 fill at max(open, pivot) + cost. Volume confirmation dropped (it is only known at the close). Stop = that day's low; same exits.
 Controls enter at the OPEN of random days with the same stop and exit.
Part A docstring follows.

Doc 148: Minervini trend template + tight-base volume breakout + Qullamaggie-style management, S&P 500 stocks (DK 28 Oct: 'Yes please').
Pre-registered 28 Oct 2026, before any result:
 TEMPLATE (known at the prior close): close > SMA150 and SMA200; SMA150 > SMA200; SMA200 above its value 21 days ago; SMA50 > SMA150;
   close > SMA50; close >= 1.30 x 52-week low; close >= 0.75 x 52-week high; 12-month return in the top 30% of the universe that day.
 ENTRY: tight base (prior 20-day range <= 15% of its high), today's CLOSE above the prior 20-day high, volume >= 1.5 x its 50-day average.
   Buy at the close (no intraday look-ahead on volume).
 STOP: the breakout day's low (Qullamaggie's low-of-day stop), from the next day; fill at min(stop, open).
 EXIT: close below the 20-day SMA (primary) / 10-day SMA (variant).
 COSTS: 0.10% per side (IG share spread bet) + 6.5%/yr overnight financing.
 Dev 2005-2018, holdout 2019 on. Universe: today's S&P 500 (survivorship bias: flatters every arm alike; the controls share it).
 CONTROLS (100 draws): (a) TIMING - random days that pass the template, same stop rule (that day's low) and exit; (b) FILTER - random days
   with no template, same stop and exit. Arms: TT+breakout/20MA, TT+breakout/10MA, breakout without template/20MA. Trials 3."""
import json, glob, os, numpy as np, pandas as pd
COST, FIN = 0.001, 0.065; HOLD = pd.Timestamp("2019-01-01")
fs = sorted(glob.glob("data_stk/*.csv")); fs = [f for f in fs if os.path.basename(f)[:-4] not in ("SPY", "QQQ")]
D = {}
for f in fs:
    d = pd.read_csv(f, parse_dates=["t"]).set_index("t"); d = d[~d.index.duplicated()]
    if len(d) > 400: D[os.path.basename(f)[:-4]] = d
ret12 = pd.DataFrame({s: d.close / d.close.shift(252) - 1 for s, d in D.items()})
rs = ret12.rank(axis=1, pct=True)
S = {}
for s, d in D.items():
    c, h, l, v = d.close, d.high, d.low, d.volume
    m50, m150, m200 = c.rolling(50).mean(), c.rolling(150).mean(), c.rolling(200).mean()
    tt = (c > m150) & (c > m200) & (m150 > m200) & (m200 > m200.shift(21)) & (m50 > m150) & (c > m50) & \
         (c >= 1.3 * l.rolling(252).min()) & (c >= 0.75 * h.rolling(252).max()) & (rs[s].reindex(d.index) >= 0.70)
    h20, l20 = h.rolling(20).max().shift(1), l.rolling(20).min().shift(1)
    bo = ((h20 - l20) / h20 <= 0.15) & (h > h20)
    S[s] = dict(idx=d.index, O=d.open.values, P=h20.values, H=h.values, L=l.values, C=c.values,
                m10=c.rolling(10).mean().values, m20=c.rolling(20).mean().values,
                tt=tt.shift(1).fillna(False).values.astype(bool), bo=bo.fillna(False).values.astype(bool))
def trade(x, i, ma, rnd=False):
    C, L, O, M = x["C"], x["L"], x["O"], x[ma]; n = len(C)
    e0 = O[i] if rnd else max(O[i], x["P"][i]); e = e0 * (1 + COST); stop = L[i]
    for j in range(i + 1, n):
        if L[j] <= stop: px = min(stop, O[j]); break
        if C[j] < M[j]: px = C[j]; break
    else: j = n - 1; px = C[j]
    days = (x["idx"][j] - x["idx"][i]).days
    r = px * (1 - COST) / e - 1 - FIN * days / 365; risk = max((e0 - stop) / e0, 0.002)
    return r, r / risk, days
def stats(rows):
    if not rows: return "n0"
    r = np.array([a for a, b, c in rows]); R = np.array([b for a, b, c in rows]); dd = np.array([c for a, b, c in rows])
    pf = r[r > 0].sum() / -r[r < 0].sum()
    return f"n{len(r):5} win {100*(r>0).mean():3.0f}% PF {pf:.2f} mean {100*r.mean():+.2f}% ({R.mean():+.2f}R) median hold {np.median(dd):.0f}d"
def tot(rows): return np.mean([a for a, b, c in rows]) * 100 if rows else np.nan
out = []
arms = (("B: TT + pivot buy-stop, 20MA exit", True, "m20"), ("B: TT + pivot buy-stop, 10MA exit", True, "m10"))
for name, use_tt, ma in arms:
    lines = [name]
    for seg, hold in (("DEV ", False), ("HOLD", True)):
        real = []; cnt = {}
        for s, x in S.items():
            sel = x["bo"] & (x["tt"] if use_tt else True) & ((x["idx"] >= HOLD) == hold); ii = np.flatnonzero(sel[:-1])
            cnt[s] = len(ii); real += [trade(x, i, ma) for i in ii]
        mt, mf = [], []
        for k in range(100):
            rng = np.random.default_rng(k); pt, pf_ = [], []
            for s, x in S.items():
                m = cnt[s]
                if not m: continue
                inseg = (x["idx"] >= HOLD) == hold; inseg[:252] = False; inseg[-1] = False
                ct = np.flatnonzero(x["tt"] & inseg); cf = np.flatnonzero(inseg)
                if len(ct): pt += [trade(x, i, ma, True) for i in rng.choice(ct, min(m, len(ct)), replace=False)]
                pf_ += [trade(x, i, ma, True) for i in rng.choice(cf, min(m, len(cf)), replace=False)]
            mt.append(tot(pt)); mf.append(tot(pf_))
        mt, mf = np.array(mt), np.array(mf); rv = tot(real)
        lines.append(f"  {seg} {stats(real)} | random template days {np.median(mt):+.2f}%/trade (beats {100*(mt<rv).mean():.0f}%) | random any day {np.median(mf):+.2f}%/trade (beats {100*(mf<rv).mean():.0f}%)")
    out.append("\n".join(lines)); print(out[-1], flush=True)
open("runs/stock_breakout_test_B.txt", "w").write(f"{len(S)} stocks\n" + "\n".join(out) + "\n")
