"""Doc 222 — the assessment back to 1900 (DK 11:22–11:23: "since 2001 has been a perversion of the stock markets ... modern monetary policy").
Daily: S&P 500 1928–2026 (Yahoo ^GSPC; close-only before 1962). Monthly: Shiller S&P composite 1871–2026 (+ long rate GS10).
Same rules as the live/demo books; to treat every era alike: ATR = 20-day mean of |close-to-close change| (works without highs/lows),
decisions at a close, execution at the NEXT close (in and out), stops checked on closes. Costs: IG US 500 spread (0.0075% per side) +
funding from that era's rate (Shiller GS10 as the benchmark): longs pay rate + 2.5%, shorts earn rate − 2.5%.
Eras: 1928–45 (crash, depression, war) · 1946–81 (high rates, 1970s stagflation bears) · 1982–2000 (disinflation bull) · 2001–26 (QE era)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = pd.read_csv(f"{ROOT}/data_hist/SPX_yahoo.csv", index_col=0, parse_dates=True)[["Close"]].rename(columns={"Close": "close"}).dropna()
d = d[d.close > 0]; d["atr"] = d.close.diff().abs().rolling(20).mean()
sh = pd.read_csv(f"{ROOT}/data_hist/shiller_monthly.csv"); sh = sh[pd.to_numeric(sh.Date, errors="coerce").notna()].copy()
sh["Date"] = sh.Date.astype(float); sh["P"] = pd.to_numeric(sh.P, errors="coerce"); sh["D"] = pd.to_numeric(sh.D, errors="coerce"); sh["GS10"] = pd.to_numeric(sh["Rate GS10"], errors="coerce")
sh.index = pd.to_datetime([f"{int(x)}-{int(round((x - int(x)) * 100)):02d}-01" for x in sh.Date]); sh = sh[["P", "D", "GS10"]].dropna(subset=["P"])
RATE = (sh.GS10 / 100).ffill()
def rate_at(ts): return float(RATE.asof(ts)) if ts >= RATE.index[0] else float(RATE.iloc[0])
COST = 0.000075
def rsi(c, n):
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
C = d.close.values; A = d.atr.values; IX = d.index; N = len(C)
ma200 = d.close.rolling(200).mean(); ma50 = d.close.rolling(50).mean(); r4 = rsi(d.close, 4); r2 = rsi(d.close, 2)
def run(entry, exit_=None, maxd=10, stop=3.0, side=1):
    E = entry.fillna(False).values; X = exit_.fillna(False).values if exit_ is not None else np.zeros(N, bool); out = []; i = 0
    while i < N - 2:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        j0 = i + 1; e = C[j0]; st = e - side * stop * A[i]; j = j0 + 1; px = None
        while j < N:
            if side * (C[j] - st) <= 0: px = C[j]; break
            if (X[j] or (j - j0) >= maxd) and j + 1 < N: j += 1; px = C[j]; break
            j += 1
        if px is None: break
        days = (IX[j] - IX[j0]).days; r = rate_at(IX[j0]); fund = ((r + 0.025) if side == 1 else (0.025 - r)) / 365 * days * e
        out.append((IX[i], (side * (px - e) - COST * e * 2 - fund) / A[i])); i = j
    return pd.DataFrame(out, columns=["t", "R"])
def tps(side=1, maxd=30, kill=0.15, lad=(0.1, 0.2, 0.3, 0.4)):
    R = r2.values; M = ma200.values; out = []; i = 201
    while i < N - 2:
        cond = (C[i] > M[i] and R[i] < 25 and R[i - 1] < 25) if side == 1 else (C[i] < M[i] and R[i] > 75 and R[i - 1] > 75)
        if not cond: i += 1; continue
        q = sp = 0.0; last = None; k = 0; j0 = i; buy = True; j = i
        while j < N - 1:
            if buy and k < len(lad): px = C[j + 1]; q += lad[k] / px; sp += lad[k]; last = px; k += 1
            buy = False; jj = j + 1; avg = sp / q
            ex = (R[jj] > 70 if side == 1 else R[jj] < 30) or (jj - j0) >= maxd or (C[jj] <= avg * (1 - kill) if side == 1 else C[jj] >= avg * (1 + kill))
            if ex and jj + 1 < N:
                xp = C[jj + 1]; days = (IX[jj + 1] - IX[j0]).days; r = rate_at(IX[j0])
                pnl = side * (q * xp - sp) - (sp + q * xp) * COST - sp * ((r + 0.025) if side == 1 else (0.025 - r)) / 365 * days * 0.5
                out.append((IX[j0], 100 * pnl)); break
            if ex: break
            if k < len(lad) and (C[jj] < last if side == 1 else C[jj] > last): buy = True
            j = jj
        i = j + 2
    return pd.DataFrame(out, columns=["t", "R"])
up, dn = d.close > ma200, d.close < ma200
bme = pd.Series(IX == (IX + pd.offsets.BMonthEnd(0)), index=IX)
s_ = pd.Series((IX.month == 12) & (IX.day >= 22) & (IX.day <= 24) & (IX.dayofweek < 5), index=IX); santa = s_ & ~s_.shift(1, fill_value=False)
BOOKS = {
    "LONG  RSI(4) dip (above 200d)": run(up & (r4 < 25), r4 > 55, 10, 3.0),
    "LONG  TPS ladder (above 200d, % of budget)": tps(1),
    "LONG  turn of the month": run(bme, None, 3, 5.0),
    "LONG  Santa rally": run(santa, None, 7, 5.0),
    "SHORT bear-rally fade (below 200d, RSI(4) > 75)": run(dn & (r4 > 75), r4 < 45, 10, 3.0, -1),
    "SHORT TPS short ladder (below 200d, % of budget)": tps(-1),
    "SHORT trend: 50d crosses below 200d, exit > 50d": run((ma50 < ma200) & ~(ma50 < ma200).shift(1, fill_value=True) & dn, d.close > ma50, 250, 3.0, -1),
    "SHORT breakdown: below 200d, 20-day low, exit 10-day high": run(dn & (d.close < d.close.rolling(20).min().shift(1)), d.close > d.close.rolling(10).max().shift(1), 60, 2.0, -1),
}
ERAS = [(1928, 1945), (1946, 1981), (1982, 2000), (2001, 2026)]
def era_line(t):
    cells = []
    for a, b in ERAS:
        g = t[(t.t.dt.year >= a) & (t.t.dt.year <= b)]
        if len(g) < 5: cells.append(f"{a}-{b}: -"); continue
        y = g.groupby(g.t.dt.year).R.sum(); tt = g.R.mean() / g.R.std() * np.sqrt(len(g))
        cells.append(f"{a}-{str(b)[2:]}: n{len(g):4d} {g.R.mean():+.3f} t{tt:+.1f} yrs+ {100 * (y > 0).mean():.0f}%")
    return " | ".join(cells)
if __name__ == "__main__" and "longbear" not in sys.argv:
    print(f"S&P 500 daily {IX[0].date()} -> {IX[-1].date()}  (next-close execution, IG spread, era funding)")
    for nm, t in BOOKS.items():
        tt = t.R.mean() / t.R.std() * np.sqrt(len(t)); print(f"\n{nm}: ALL n{len(t)} {t.R.mean():+.3f} t{tt:+.2f}\n   {era_line(t)}")
    # regime rule (doc 220) on the long dips, by era: what the dip books earned while the US 500 was BELOW its 200-day
    t = run(r4 < 25, r4 > 55, 10, 3.0); t["bear"] = dn.reindex(t.t).values
    print("\nRSI(4) dips taken BELOW the 200-day (what the regime rule skips):\n   " + era_line(t[t.bear]) + "\n   above:\n   " + era_line(t[~t.bear]))
    # monthly 1871-: bear markets and 10-month trend timing (Faber 2007) by era
    m = sh.copy(); m["tr"] = (m.P + m.D / 12) / m.P.shift(1) - 1; m["rate"] = m.GS10 / 100; ma10 = m.P.rolling(10).mean(); sig = (m.P > ma10).shift(1)
    m["bh"] = m.tr; m["lf"] = np.where(sig, m.tr, m.rate / 12); m["ls"] = np.where(sig, m.tr, -m.tr + (m.rate - 0.025) / 12)
    print("\nMonthly 1871- (Shiller S&P composite, total return): buy & hold vs 10-month-average timing (long / flat at the bond rate / long-short)")
    for a, b in [(1871, 1899), (1900, 1929), (1930, 1945), (1946, 1981), (1982, 2000), (2001, 2026)]:
        g = m[(m.index.year >= a) & (m.index.year <= b)].dropna(subset=["tr"])
        cg = lambda x: (np.prod(1 + x) ** (12 / len(x)) - 1) * 100; dd = lambda x: (1 - (np.cumprod(1 + x) / np.maximum.accumulate(np.cumprod(1 + x)))).max() * 100
        print(f"   {a}-{b}: buy&hold {cg(g.bh):+5.1f}%/yr (max fall {dd(g.bh):.0f}%) | 10m timing long/flat {cg(g.lf):+5.1f}% ({dd(g.lf):.0f}%) | long/short {cg(g.ls):+5.1f}% ({dd(g.ls):.0f}%)")
    print("\nBear markets (monthly, >= 20% fall from a high) since 1900:")
    p = m.P[m.index.year >= 1900]; pk = p.cummax(); i = 0; v = p.values; P = pk.values
    while i < len(p):
        if v[i] / P[i] - 1 <= -0.20:
            s = i
            while s > 0 and P[s - 1] == P[i]: s -= 1
            j = i
            while j < len(p) and v[j] < P[i]: j += 1
            seg = p.iloc[s:j]; t_ = int(np.argmin(seg.values))
            print(f"   {p.index[s]:%Y-%m} -> {seg.index[t_]:%Y-%m}  {100 * (seg.values[t_] / P[i] - 1):5.1f}%  {t_:3d} months down, {('recovered after ' + str(j - s - t_) + ' months') if j < len(p) else 'not recovered'}")
            i = j
        else: i += 1

# ---- doc 222 addendum (DK 11:30 "worth looking back to previous long-term bear markets"): a DORMANT long-bear short that switches on only once a
# long bear is established — fixed in advance: the 200-day average itself has fallen for 60 trading days AND the index is >= 15% below its 1-year high.
if __name__ == "__main__" and "longbear" in sys.argv:
    est = (ma200 < ma200.shift(60)) & (d.close <= 0.85 * d.close.rolling(252).max())
    print(f"days classed as an established long bear: {100 * est.mean():.1f}% of all days; by decade: " + " ".join(f"{y}s:{100 * est[(IX.year >= y) & (IX.year < y + 10)].mean():.0f}%" for y in range(1930, 2030, 10)))
    for nm, t in {"SHORT breakdown, only in an established long bear": run(est & dn & (d.close < d.close.rolling(20).min().shift(1)), d.close > d.close.rolling(10).max().shift(1), 60, 2.0, -1),
                  "SHORT bear-rally fade, only in an established long bear": run(est & dn & (r4 > 75), r4 < 45, 10, 3.0, -1),
                  "LONG RSI(4) dips in an established long bear (what to avoid?)": run(est & (r4 < 25), r4 > 55, 10, 3.0)}.items():
        tt = t.R.mean() / t.R.std() * np.sqrt(len(t)) if len(t) > 2 else float("nan")
        print(f"\n{nm}: ALL n{len(t)} {t.R.mean():+.3f} t{tt:+.2f}\n   {era_line(t)}\n   by bear: " + " ".join(f"{y}:{v:+.1f}" for y, v in t.groupby(t.t.dt.year).R.sum().items()))
