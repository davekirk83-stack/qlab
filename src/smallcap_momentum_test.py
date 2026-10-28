"""Doc 149: the 'legends' setups on the stocks they are built for (DK 28 Oct: "Test those theories on stocks of the kind they are meant to target").
Pre-registered 28 Oct 2026 before any result. Universe: all ~5,000 currently listed US common stocks (Nasdaq trader directories, Yahoo daily,
2005-2026). Survivorship bias (delisted names missing) flatters real AND random entries alike; the controls share it.
ELIGIBLE (known at the prior close): price >= $5, 20-day median dollar volume >= $5m, average daily range (20d) >= 4% (high-ADR names).
SETUPS (all: buy at the CLOSE of the signal day, stop = that day's low from the next day, exit on a close below the 10- or 20-day SMA,
one open trade per stock; costs 0.20% per side + 6.5%/yr financing):
 S1 MINERVINI: trend template (as doc 148) + tight 20-day base (range <= 15%) + close above the base high on volume >= 1.5x the 50-day average.
 S2 QULLAMAGGIE BREAKOUT: up >= 30% from its lowest close 21-63 days ago, then a tight 10-day flag (range <= 2.5 x ADR), price above SMA10 > SMA20,
    close above the flag high on volume >= 1.5x.
 S3 EPISODIC PIVOT (Bonde / Qullamaggie): opens >= 10% above the prior close, volume >= 3x the 50-day average, closes above its open,
    and was NOT already extended (prior 60-day return <= +20%).
CONTROLS (50 draws): random ELIGIBLE days on the same stocks, same count per stock, same stop (that day's low) and exit.
Dev 2005-2018, holdout 2019 on. Trials: 3 setups x 2 exits = 6 (cumulative with doc 148: 11)."""
import glob, os, numpy as np, pandas as pd
COST, FIN = 0.002, 0.065; HOLD = pd.Timestamp("2019-01-01")
D = {}
for f in glob.glob("data_stk2/*.csv"):
    d = pd.read_csv(f, parse_dates=["t"]).set_index("t"); d = d[~d.index.duplicated()].dropna()
    d = d[(d.close > 0) & (d.low > 0)]
    if len(d) > 300: D[os.path.basename(f)[:-4]] = d
print(len(D), "stocks", flush=True)
rs = pd.DataFrame({s: d.close / d.close.shift(252) - 1 for s, d in D.items()}).rank(axis=1, pct=True)
S = {}
for s, d in D.items():
    o, c, h, l, v = d.open, d.close, d.high, d.low, d.volume
    m10, m20, m50, m150, m200 = (c.rolling(n).mean() for n in (10, 20, 50, 150, 200))
    adr = (h / l - 1).rolling(20).mean()
    elig = ((c >= 5) & ((c * v).rolling(20).median() >= 5e6) & (adr >= 0.04)).shift(1).fillna(False)
    v50 = v.rolling(50).mean().shift(1)
    tt = ((c > m150) & (c > m200) & (m150 > m200) & (m200 > m200.shift(21)) & (m50 > m150) & (c > m50) &
          (c >= 1.3 * l.rolling(252).min()) & (c >= 0.75 * h.rolling(252).max()) & (rs[s].reindex(d.index) >= 0.70)).shift(1).fillna(False)
    h20, l20 = h.rolling(20).max().shift(1), l.rolling(20).min().shift(1)
    s1 = tt & ((h20 - l20) / h20 <= 0.15) & (c > h20) & (v >= 1.5 * v50)
    h10, l10 = h.rolling(10).max().shift(1), l.rolling(10).min().shift(1)
    lowc = c.shift(21).rolling(43).min()
    s2 = (c.shift(1) / lowc >= 1.3) & ((h10 - l10) / h10 <= 2.5 * adr.shift(1)) & (c > m10) & (m10 > m20) & (c > h10) & (v >= 1.5 * v50)
    s3 = (o >= 1.10 * c.shift(1)) & (v >= 3 * v50) & (c > o) & (c.shift(1) / c.shift(61) - 1 <= 0.20)
    S[s] = dict(idx=d.index, L=l.values, O=o.values, C=c.values, m10=m10.values, m20=m20.values,
                elig=elig.values.astype(bool), S1=(s1 & elig).fillna(False).values, S2=(s2 & elig).fillna(False).values, S3=(s3 & elig).fillna(False).values)
del rs
def trade(x, i, ma):
    C, L, O, M = x["C"], x["L"], x["O"], x[ma]; e = C[i] * (1 + COST); stop = L[i]; n = len(C)
    for j in range(i + 1, n):
        if L[j] <= stop: px = min(stop, O[j]); break
        if C[j] < M[j]: px = C[j]; break
    else: j = n - 1; px = C[j]
    days = (x["idx"][j] - x["idx"][i]).days
    return px * (1 - COST) / e - 1 - FIN * days / 365, days, j
def summ(r):
    r = np.asarray(r)
    if len(r) == 0: return "n0", np.nan
    pf = r[r > 0].sum() / -r[r < 0].sum(); top = np.sort(r)[::-1]; t5 = top[:max(1, len(r)//20)].sum() / r.sum() if r.sum() > 0 else np.nan
    return f"n{len(r):5} win {100*(r>0).mean():3.0f}% PF {pf:.2f} mean {100*r.mean():+.2f}% median {100*np.median(r):+.2f}%", r.mean()
out = []
for setup in ("S1", "S2", "S3"):
    for ma in ("m20", "m10"):
        lines = [f"{setup} exit {ma}"]
        for seg, hold in (("DEV ", False), ("HOLD", True)):
            real = []; cnt = {}
            for s, x in S.items():
                sig = np.flatnonzero(x[setup][:-1] & ((x["idx"][:-1] >= HOLD) == hold)); busy = -1; k = 0
                for i in sig:
                    if i <= busy: continue
                    r, dd, j = trade(x, i, ma); real.append(r); busy = j; k += 1
                cnt[s] = k
            txt, rv = summ(real); means = []
            for k in range(50):
                rng = np.random.default_rng(k); pool = []
                for s, m in cnt.items():
                    if not m: continue
                    x = S[s]; cand = np.flatnonzero(x["elig"][:-1] & ((x["idx"][:-1] >= HOLD) == hold))
                    if len(cand): pool += [trade(x, i, ma)[0] for i in rng.choice(cand, min(m, len(cand)), replace=False)]
                means.append(np.mean(pool))
            means = np.array(means)
            lines.append(f"  {seg} {txt} | random eligible days {100*np.median(means):+.2f}%/trade, setup beats {100*(means < rv).mean():.0f}%")
        out.append("\n".join(lines)); print(out[-1], flush=True)
open("runs/smallcap_momentum_test.txt", "w").write(f"{len(S)} stocks\n" + "\n".join(out) + "\n")
