"""Doc 221 — corrections, crashes and bear markets; improving the short side (DK 11:17).
A. Catalogue: every drawdown >= 10% from a running closing high since 2000 on the traded indices (US 500, US Tech 100, Wall St, DAX, FTSE).
B. Short books, rules fixed in advance, next-open in AND out, stops on every bar, IG index spreads (one full spread per side), and REAL short
   funding: an IG short is credited the benchmark minus the 2.5% admin fee each night (benchmark = US fed funds, data_daily/FEDFUNDS.csv),
   i.e. it PAYS when rates are under 2.5% and EARNS when above.
   B1 bear-rally fade (Connors-style short): below 200-day, RSI(4) > 75 -> short; exit RSI(4) < 45 or 10 days; stop 3 ATR
   B2 trend short: first close with 50-day < 200-day and close < 200-day -> short; exit close > 50-day; stop 3 ATR; max 250 days
   B3 breakdown short: below 200-day and close < 20-day low -> short; exit close > 10-day high; stop 2 ATR; max 60
   B4 crash continuation: 5-day fall >= 6% and VIX > 25 -> short 3 days; stop 2 ATR
   B5 failed rally: below 200-day, 3 higher closes in a row that end above the 20-day average -> short 5 days; stop 2 ATR
   B6 TPS short ladder (mirror of the long TPS) only below the 200-day: RSI(2) > 75 twice -> short 10/20/30/40% on higher closes; exit RSI(2) < 30,
      30 days, or 15% above average cost
C. Each through the standard test (doc 217) incl. the portfolio test against the long core (RSI4 + TOM), plus results by regime (doc 220)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, std_books as B, standard_test as S, regime_layer as RL
MK = ["SPX", "NDX", "DJI", "DAX", "FTSE", "RUT", "N225"]
FF = pd.read_csv("data_daily/FEDFUNDS.csv", comment="#"); FF.index = pd.PeriodIndex(FF.month, freq="M"); RATE = FF.rate / 100
def rate_at(ts): return float(RATE.get(pd.Period(ts, "M"), RATE.iloc[-1]))
up = lambda d: d.close > d.close.rolling(200).mean(); dn = lambda d: d.close < d.close.rolling(200).mean(); r4 = lambda d: F.rsi(d.close, 4)
def run_short(k, entry, exit_=None, maxd=10, stop=3.0):
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values; ix = d.index
    E = entry.reindex(ix).fillna(False).values; X = exit_.reindex(ix).fillna(False).values if exit_ is not None else np.zeros(len(d), bool)
    cost = F.COST[k]; out = []; i = 0; n = len(C)
    while i < n - 2:
        if not E[i] or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        j0 = i + 1; e = O[j0]; st = e + stop * A[i]; j = j0; px = None
        while j < n:
            if H[j] >= st: px = max(st, O[j]) if j > j0 else (O[j] if O[j] > st else st); break
            if (X[j] or (j - j0 + 1) >= maxd) and j + 1 < n: px = O[j + 1]; j += 1; break
            j += 1
        if px is None: break
        nights = (ix[min(j, n - 1)] - ix[j0]).days; fund = (0.025 - rate_at(ix[j0])) / 365 * nights * e   # + = short pays
        out.append((ix[i], ((e - px) - cost * e * 2 - fund) / A[i], k)); i = j
    return out
def tps_short(d, k, cost, kill=0.15, maxd=30, ladder=(0.1, 0.2, 0.3, 0.4)):
    O, C = d.open.values, d.close.values; r = F.rsi(d.close, 2).values; ma = d.close.rolling(200).mean().values; ix = d.index; out = []; i = 201; n = len(C)
    while i < n - 2:
        if not (C[i] < ma[i] and r[i] > 75 and r[i - 1] > 75): i += 1; continue
        qty = spent = 0.0; last = None; kk = 0; j0 = i; buy = True; j = i
        while j < n - 1:
            if buy and kk < len(ladder): px = O[j + 1]; w = ladder[kk]; qty += w / px; spent += w; last = px; kk += 1
            buy = False; jj = j + 1
            if jj >= n: break
            avg = spent / qty
            if r[jj] < 30 or (jj - j0) >= maxd or C[jj] >= avg * (1 + kill):
                if jj + 1 >= n: break
                xp = O[jj + 1]; nights = (ix[jj + 1] - ix[j0]).days
                pnl = spent - qty * xp - (spent + qty * xp) * cost - spent * (0.025 - rate_at(ix[j0])) / 365 * nights * 0.5
                out.append((ix[j0], 100 * pnl, k)); break
            if kk < len(ladder) and C[jj] > last: buy = True
            j = jj
        i = j + 2
    return out
def book(sig, exit_=None, maxd=10, stop=3.0):
    def b(cm=1.0, rnd=None):
        with B.cost(cm): return B.mk([r for k in MK for r in run_short(k, (rnd or (lambda k, e: e))(k, sig(F.D[k]).fillna(False)), exit_(F.D[k]) if exit_ else None, maxd, stop)])
    return b
vix = F.D["VIX"].close
BOOKS = {
    "B1 bear-rally fade: below 200d, RSI(4) > 75 -> short, exit RSI(4) < 45 / 10d": book(lambda d: dn(d) & (r4(d) > 75), lambda d: r4(d) < 45, 10, 3.0),
    "B2 trend short: 50d crosses below 200d (close < 200d), exit close > 50d": book(lambda d: (d.close.rolling(50).mean() < d.close.rolling(200).mean()) & ~(d.close.rolling(50).mean() < d.close.rolling(200).mean()).shift(1, fill_value=True) & dn(d), lambda d: d.close > d.close.rolling(50).mean(), 250, 3.0),
    "B3 breakdown short: below 200d, close < 20-day low, exit > 10-day high": book(lambda d: dn(d) & (d.close < d.low.rolling(20).min().shift(1)), lambda d: d.close > d.high.rolling(10).max().shift(1), 60, 2.0),
    "B4 crash continuation: 5-day fall >= 6% and VIX > 25 -> short 3 days": book(lambda d: (d.close / d.close.shift(5) - 1 <= -0.06) & (vix.reindex(d.index).ffill() > 25), None, 3, 2.0),
    "B5 failed rally: below 200d, 3 higher closes ending above 20d avg -> short 5 days": book(lambda d: dn(d) & (d.close > d.close.shift(1)) & (d.close.shift(1) > d.close.shift(2)) & (d.close.shift(2) > d.close.shift(3)) & (d.close > d.close.rolling(20).mean()), None, 5, 2.0),
}
def b6(cm=1.0, rnd=None):
    with B.cost(cm): return B.mk([r for k in MK for r in tps_short(F.D[k], k, F.COST[k])])
def catalogue():
    print("== A. Drawdowns >= 10% from a closing high, 2000-2026 (depth / trading days peak->trough / days trough->recovery / biggest rally inside)")
    for k, nm in [("SPX", "US 500"), ("NDX", "US Tech 100"), ("DJI", "Wall St"), ("DAX", "DAX"), ("FTSE", "FTSE")]:
        c = F.D[k].close[F.D[k].index >= "2000-01-01"]; peak = c.cummax(); dd = c / peak - 1; ev = []; i = 0; v = c.values; P = peak.values; D = dd.values; ix = c.index
        while i < len(c):
            if D[i] <= -0.10:
                s = i
                while s > 0 and P[s - 1] == P[i]: s -= 1
                j = i
                while j < len(c) and v[j] < P[i]: j += 1
                seg = c.iloc[s:j]; t = int(np.argmin(seg.values)); tro = seg.index[t]; depth = seg.values[t] / P[i] - 1
                low = seg.iloc[:t + 1].cummin(); rally = ((seg.iloc[:t + 1] / low) - 1).max()
                ev.append((ix[s].date(), tro.date(), depth, t, (j - s - t) if j < len(c) else None, rally)); i = j
            else: i += 1
        print(f"  {nm}: {len(ev)} episodes")
        for a, b_, depth, td, rec, ral in ev:
            kind = "CRASH" if depth <= -0.20 and td <= 40 else ("BEAR" if depth <= -0.20 else "correction")
            print(f"     {a} -> {b_}  {100 * depth:5.1f}%  {kind:10s} fall {td:4d} days, recovery {rec if rec is not None else 'not yet':>8} days, biggest rally inside the fall {100 * ral:4.1f}%")
if __name__ == "__main__" and "gated" not in sys.argv:
    catalogue()
    print("\n== B/C. Short books through the standard test (IG spreads, real short funding)")
    C = B.core()
    for nm, b in list(BOOKS.items()) + [("B6 TPS short ladder below 200d (% of budget)", b6)]:
        o, t = S.judge(nm, "short", MK, b, core=C, random_runs=40)
        t["g"] = RL.regime(t.t); print("      by regime: " + " | ".join(f"{g} n{len(x)} {x.R.mean():+.3f}" for g, x in t.groupby("g")), flush=True)

# ---- D. the same shorts, GATED to the US 500 being below its 200-day at the signal (mirror of the long-side rule, doc 220)
SPXDN = (F.D["SPX"].close < F.D["SPX"].close.rolling(200).mean())
def gate(sig): return lambda d: sig(d) & SPXDN.reindex(d.index).ffill().fillna(False)
GATED = {
    "G1 bear-rally fade, only while US 500 < 200d": book(gate(lambda d: dn(d) & (r4(d) > 75)), lambda d: r4(d) < 45, 10, 3.0),
    "G3 breakdown short, only while US 500 < 200d": book(gate(lambda d: dn(d) & (d.close < d.low.rolling(20).min().shift(1))), lambda d: d.close > d.high.rolling(10).max().shift(1), 60, 2.0),
}
def g6(cm=1.0, rnd=None):
    t = b6(cm, rnd); ok = SPXDN.reindex(pd.to_datetime(t.t).dt.normalize()).ffill().fillna(False).values; return t[ok]
if __name__ == "__main__" and "gated" in sys.argv:
    C = B.core(); print("== D. shorts only while the US 500 is below its 200-day")
    for nm, b in list(GATED.items()) + [("G6 TPS short ladder, only while US 500 < 200d (% of budget)", g6)]:
        o, t = S.judge(nm, "short-gated", MK, b, core=C, random_runs=40)
        print("      by year: " + " ".join(f"{y}:{v:+.0f}" for y, v in t.groupby(t.t.dt.year).R.sum().items()), flush=True)
