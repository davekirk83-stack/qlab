"""
THE ALLOCATOR — one shared risk pool drawn by whichever books are active (DK, 19 Oct: "allocate
capital according to what is active at any moment… maximum punch from our limited capital…
if multiple are active they then share it accordingly"), against the alternatives.

Books over the common 12-month window (15 Oct 2025 – 16 Oct 2026), each expressed as the DAILY
RETURN of its own $2,000 paper book at its registered sizing (so "1 unit" of a book = the paper
book as it runs):
  RANGE v3     registered bids, one mid-EMA target, 27 coins, 15m, 20 slots at 3x (doc 91)
  IGNITION     NQ 5-min, 1 MNQ at $2/pt (doc 92)
  DEATH-CROSS  4h anticipated 20/50 short, 3-ATR trail, 25 alts, 20 slots at 3x (doc 82)
  GOLDEN-CROSS 4h confirmed 20/50 long with BTC>EMA200 gate, hold 18, 27 coins, 20 slots at 3x (doc 83)
Episode returns are booked on the exit day at 1/20 of capital x 3x (the slot model, no slot cap).

SCHEMES (portfolio return = sum_i m_i * r_i, with m_i the multiplier on book i's unit):
  ALONE          each book by itself (m = 1)
  RESERVED       fixed equal split, m_i = 1/N always
  POOLED-ACTIVE  each day the pool splits equally among books ACTIVE that day (an open position),
                 m_i = min(CEIL, 1/n_active); inactive books get nothing; idle budget stays idle
  POOLED-RISK    as above but shares are inverse to each book's trailing 30-day daily volatility
  + GOVERNORS    on POOLED-RISK: book budget halved while >15% off its own high; portfolio day
                 stopped at -4% (the rest of that day's returns removed)
Reported: CAGR, max drawdown, Sharpe (daily), worst day, months positive, and the diversification
test: share of days when two or more books each lose more than half their daily budget.
"""
import warnings; warnings.filterwarnings("ignore")
import os, json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import clean_portfolio as CP, regime_detect as RD
from range_scalein import load_all, run as run_range

T0, T1 = pd.Timestamp("2025-10-15", tz="UTC"), pd.Timestamp("2026-10-16", tz="UTC")
SLOT = 3.0/20          # 3x over 20 slots
CEIL = 0.5


def daily_from_eps(R, label, slots=20, lev=3):
    """Daily return of the book run through the registered simulator ($2,000, 20 slots, 3x) — slot-capped."""
    R = R[(R.entry >= T0) & (R.exit <= T1)].copy()
    S = R[["sym","entry","exit","ret"]].sort_values("entry").reset_index(drop=True)
    eq = CP.START; openp = []; curve = {}; ei = 0
    for t in sorted(set(S.entry) | set(S.exit)):
        still = []
        for p in openp:
            if p["exit"] <= t: eq += p["margin"]*p["ret"]*lev
            else: still.append(p)
        openp = still
        while ei < len(S) and S.entry.iloc[ei] <= t:
            r = S.iloc[ei]; ei += 1
            if len(openp) < slots and eq > 0:
                m = eq/slots; openp.append({"exit": r.exit, "ret": r.ret, "margin": m})
        curve[t] = eq
    E = pd.Series(curve); E = E[~E.index.duplicated(keep="last")].sort_index()
    pnl = E.resample("1D").last().ffill().pct_change().fillna(0.0)
    pnl.index = pnl.index.tz_convert("UTC") if pnl.index.tz is not None else pnl.index.tz_localize("UTC")
    # active days: any day between entry and exit
    act = pd.Series(0, index=pd.date_range(T0.floor("D"), T1.floor("D"), freq="D", tz="UTC"))
    for e, x in zip(R.entry.dt.floor("D"), R.exit.dt.floor("D")):
        act.loc[e:x] = 1
    r = pnl.reindex(act.index).fillna(0.0)
    print(f"  {label:<14} eps {len(R):>6}  per ep {R.ret.mean()*100:+.3f}%  active days {int(act.sum())}/{len(act)}  final ${E.iloc[-1]:,.0f}", flush=True)
    return r, act


def range_book():
    B = load_all(); R = run_range(B, RD.BID, [(1.0, "mid")]); return daily_from_eps(R, "RANGE v3")


def crossover_books(B):
    import paperbook4 as P4, paperbook5 as P5
    rows4, rows5 = [], []
    btc = B["BTCUSD"][0]; b4 = P4.bars4h(btc[["open","high","low","close","volume"]].astype(float)); C_, H_, L_, a_, s_, e200 = P5.indicators(b4)
    btc_bull = pd.Series(C_ > e200, index=b4.index)
    for sym, (d, *_rest) in B.items():
        d4 = P4.bars4h(d[["open","high","low","close","volume"]].astype(float)); idx = d4.index
        if sym not in P4.EXCLUDE:
            C, H, L, a, ant = P4.indicators(d4)
            for i in np.where(ant)[0]:
                if i + 1 >= len(C): continue
                pos = {"entry": C[i]*(1-P4.COST), "best": L[i], "atr": a[i], "bars": 0, "sym": sym, "opened": str(idx[i]), "shadow": 0}
                for j in range(i+1, len(C)):
                    r = P4.manage(pos, H, L, C, j, idx)
                    if r: rows4.append((sym, idx[i], idx[j], r[3])); break
        C, H, L, a, sig, _ = P5.indicators(d4)
        for i in np.where(sig)[0]:
            if i + 1 >= len(C) or not btc_bull.reindex([idx[i]], method="ffill").iloc[0]: continue
            pos = {"entry": C[i]*(1+P5.COST), "atr": a[i], "bars": 0, "sym": sym, "opened": str(idx[i]), "shadow": 0}
            for j in range(i+1, len(C)):
                r = P5.manage(pos, H, L, C, j, idx)
                if r: rows5.append((sym, idx[i], idx[j], r[3])); break
    R4 = pd.DataFrame(rows4, columns=["sym","entry","exit","ret"]); R5 = pd.DataFrame(rows5, columns=["sym","entry","exit","ret"])
    return daily_from_eps(R4, "DEATH-CROSS"), daily_from_eps(R5, "GOLDEN-CROSS")


def ignition_book():
    import paperbook7 as P7
    bars = pd.read_csv(P7.BARS, index_col=0); bars.index = pd.to_datetime(bars.index, utc=True); d = P7.features(bars)
    tr, sh, op = P7.replay(d, "2025-10-15", 0); T = pd.DataFrame(tr); T["entry"] = pd.to_datetime(T.opened); T["exit"] = pd.to_datetime(T.closed)
    T["ret"] = T.pts*2.0/2000.0; T["sym"] = "NQ"
    return daily_from_eps(T[["sym","entry","exit","ret"]], "IGNITION", slots=1, lev=1)


def stats(lbl, r):
    r = r.fillna(0.0); eq = (1 + r).cumprod(); yrs = len(r)/365.25
    cagr = eq.iloc[-1]**(1/yrs) - 1; dd = (eq/eq.cummax() - 1).min(); sh = r.mean()/r.std()*np.sqrt(365) if r.std() > 0 else 0
    m = r.resample("ME").apply(lambda x: (1+x).prod()-1)
    print(f"  {lbl:<34}{cagr*100:>+8.1f}%{dd*100:>+8.1f}%{sh:>7.2f}{r.min()*100:>+8.2f}%{(m>0).mean()*100:>7.0f}%{eq.iloc[-1]*2000:>10,.0f}", flush=True)


if __name__ == "__main__":
    B = load_all()
    books = {}
    books["RANGE v3"] = daily_from_eps(run_range(B, RD.BID, [(1.0, "mid")]), "RANGE v3")
    (books["DEATH-CROSS"], books["GOLDEN-CROSS"]) = crossover_books(B)
    books["IGNITION"] = ignition_book()
    names = list(books); R = pd.DataFrame({k: v[0] for k, v in books.items()}).fillna(0.0); A = pd.DataFrame({k: v[1] for k, v in books.items()}).fillna(0).astype(int)
    R.to_csv("/home/claude/qlab/runs/allocator_daily.csv"); A.to_csv("/home/claude/qlab/runs/allocator_active.csv")
    # NORMALISE: every book scaled to the same 1%/day volatility so only the allocation logic is compared
    R = R/R.std()*0.01
    print("\n  All books scaled to 1%/day volatility (so CAGR is comparable across schemes, not a forecast):")
    N = len(names)
    print(f"\n  {'scheme':<34}{'CAGR':>9}{'maxDD':>9}{'Sharpe':>7}{'worst d':>9}{'mo>0':>7}{'$2k ->':>10}")
    for k in names: stats(f"ALONE {k}", R[k])
    stats("RESERVED equal split (1/N always)", (R/N).sum(axis=1))
    # pooled-active: equal shares among active books, ceiling
    nact = A.sum(axis=1).replace(0, np.nan); w_act = A.div(nact, axis=0).clip(upper=CEIL).fillna(0.0)
    stats("POOLED-ACTIVE equal shares, ceil 50%", (R*w_act).sum(axis=1))
    stats("POOLED-ACTIVE no ceiling", (R*A.div(nact, axis=0).fillna(0.0)).sum(axis=1))
    # pooled-risk: inverse trailing vol among active
    vol = R.rolling(30, min_periods=10).std().shift(1).replace(0, np.nan)
    inv = (1/vol).where(A == 1, 0.0).fillna(0.0); w_risk = inv.div(inv.sum(axis=1).replace(0, np.nan), axis=0).clip(upper=CEIL).fillna(0.0)
    stats("POOLED-RISK inverse-vol shares, ceil 50%", (R*w_risk).sum(axis=1))
    # governors: drawdown halving per book, portfolio daily cap -4%
    eqb = (1 + R).cumprod(); ddb = eqb/eqb.cummax() - 1; gov = (ddb.shift(1) > -0.15).astype(float).replace(0.0, 0.5)
    pr = (R*w_risk*gov).sum(axis=1); pr = pr.clip(lower=-0.04)
    stats("POOLED-RISK + governors (DD halve, -4% day cap)", pr)
    # diversification test: days when 2+ books each lose more than half a daily budget (budget = 1% of book)
    bad = (R < -0.005).sum(axis=1); print(f"\n  days with 2+ books losing >0.5% of their own unit: {(bad>=2).mean()*100:.1f}% of days ({int((bad>=2).sum())}); 3+: {(bad>=3).sum()}")
    print("  pairwise daily-return correlations:\n" + R.corr().round(2).to_string())
    print("  share of days each book is active:", {k: f"{A[k].mean()*100:.0f}%" for k in names}, "| days with no book active:", f"{(A.sum(axis=1)==0).mean()*100:.0f}%")
