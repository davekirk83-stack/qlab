"""
THE REGIME GATE, ON ELEVEN YEARS INSTEAD OF THIRTEEN MONTHS.

The portfolio simulation settled what is wrong. The book earns +0.949% a trade
at t=7.49 and delivers 5.7% a year with a 34% drawdown, because a 0.5 ATR
target against a 3 ATR stop means one loss erases six wins, and in crypto the
losses arrive together. Year by year: 2021 +210%, 2024 -58%, 2025 +1729%,
2026 -54%. The mechanism is sound and it trades in every regime, two of which
destroy the account.

So the gate is not an enhancement, it is the missing component. It failed in
finding 93 for one reason only: that sample held a single regime change and a
gate cannot be learned from one transition. This sample holds six or seven.

GATES TESTED, all causal, all computed from trailing daily data and lagged one
bar before use:
  mkt_200     equal-weight index above its own 200-day mean
  breadth     share of products above their own 100-day mean
  mkt_dd      drawdown of the equal-weight index from its running high
  mkt_vol     60-day realised vol of the index, in expanding percentile
  mkt_eff     Kaufman efficiency of the index - high means it is going
              somewhere, which is when a reversion book should stand aside
  btc_200     BTC itself above its 200-day mean (the crude version everyone
              uses, included so the sophisticated ones have to beat it)

Each is judged on the thing that actually matters: does gating OFF in the bad
state remove the losing years without removing the winning ones? Per-trade
statistics are reported but the decision is made on the EQUITY CURVE, because
that is what the previous step proved can disagree with them.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import system_on_history as SYS
import portfolio as PF

START = 2000.0


def market_series(data):
    C = pd.DataFrame({s: d.close for s, d in data.items()}).sort_index()
    C = C[C.notna().sum(axis=1) >= 8]
    rel = C / C.ffill().bfill().iloc[0]
    idx = rel.mean(axis=1)
    out = pd.DataFrame(index=C.index)
    out["mkt_200"] = (idx > idx.rolling(200).mean()).astype(float)
    out["breadth"] = (C > C.rolling(100).mean()).sum(axis=1) / C.notna().sum(axis=1)
    out["mkt_dd"] = idx / idx.cummax() - 1
    r = idx.pct_change()
    out["mkt_vol"] = r.rolling(60).std()
    net = idx.diff(100).abs(); gross = idx.diff().abs().rolling(100).sum()
    out["mkt_eff"] = net / gross.replace(0, np.nan)
    if "BTCUSD" in C.columns:
        b = C["BTCUSD"]
        out["btc_200"] = (b > b.rolling(200).mean()).astype(float)
    return out.shift(1)


def run_gated(S, M, col, keep, maxpos=20, lev=1):
    """keep(value) -> True means the book is allowed to open."""
    g = M[col].reindex(pd.DatetimeIndex(S.entry.unique())).to_dict()
    mask = S.entry.map(lambda d: keep(g.get(d, np.nan)))
    kept = S[mask.fillna(False)]
    if len(kept) < 100: return None
    r = PF.simulate(kept.reset_index(drop=True), maxpos, lev)
    if r: r["n_sig"] = len(kept); r["pct_kept"] = len(kept)/len(S)
    return r


if __name__ == "__main__":
    data = SYS.load()
    S = PF.signals(data)
    M = market_series(data)
    print(f"{len(S):,} signals; market series {M.index[0].date()} -> {M.index[-1].date()}\n")

    base = PF.simulate(S, 20, 1)
    print("=" * 108)
    print(f"{'gate':<34}{'kept':>7}{'final $':>11}{'CAGR':>8}{'maxDD':>9}"
          f"{'Sharpe':>8}{'trades/mo':>11}{'worst yr':>10}")

    def line(tag, r):
        if r is None: print(f"  {tag:<32}  too few signals"); return None
        E = r["curve"]
        wy = min((g.iloc[-1]/g.iloc[0]-1) for _, g in E.groupby(E.index.year)
                 if len(g) > 30)
        print(f"  {tag:<32}{r.get('pct_kept',1)*100:>6.0f}%{r['final']:>11,.0f}"
              f"{r['cagr']*100:>7.1f}%{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}"
              f"{r['per_month']:>11.1f}{wy*100:>9.1f}%")
        return wy

    line("UNGATED (baseline)", base)
    print()
    tests = [
        ("index above its 200d mean", "mkt_200", lambda v: v == 1),
        ("index BELOW its 200d mean", "mkt_200", lambda v: v == 0),
        ("BTC above its 200d mean", "btc_200", lambda v: v == 1),
        ("BTC below its 200d mean", "btc_200", lambda v: v == 0),
        ("breadth > 0.5", "breadth", lambda v: v > 0.5),
        ("breadth < 0.5", "breadth", lambda v: v < 0.5),
        ("breadth < 0.3 (washed out)", "breadth", lambda v: v < 0.3),
        ("index drawdown shallower than -30%", "mkt_dd", lambda v: v > -0.30),
        ("index drawdown deeper than -30%", "mkt_dd", lambda v: v < -0.30),
        ("index drawdown deeper than -60%", "mkt_dd", lambda v: v < -0.60),
        ("efficiency < 0.30 (market churning)", "mkt_eff", lambda v: v < 0.30),
        ("efficiency > 0.30 (market trending)", "mkt_eff", lambda v: v > 0.30),
    ]
    res = {}
    for tag, col, fn in tests:
        if col not in M.columns: continue
        r = run_gated(S, M, col, fn)
        res[tag] = (r, line(tag, r))

    print("\n" + "=" * 108)
    print("THE TEST THAT DECIDES IT: does any gate remove 2024 and 2026 while")
    print("keeping 2021 and 2025? Year-by-year equity for the best candidates.\n")
    cands = sorted([(t, v[0]) for t, v in res.items() if v[0]],
                   key=lambda z: -z[1]["sharpe"])[:4]
    for tag, r in cands:
        E = r["curve"]
        yrs = {y: (g.iloc[-1]/g.iloc[0]-1) for y, g in E.groupby(E.index.year)
               if len(g) > 30}
        s = "  ".join(f"{y}:{v*100:+.0f}%" for y, v in sorted(yrs.items()))
        neg = sum(1 for v in yrs.values() if v < 0)
        print(f"  {tag}")
        print(f"    Sharpe {r['sharpe']:.2f}  maxDD {r['dd']*100:.1f}%  "
              f"CAGR {r['cagr']*100:.1f}%  losing years {neg}/{len(yrs)}")
        print(f"    {s}\n")
