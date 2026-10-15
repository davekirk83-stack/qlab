"""
SHORT-TERM REVERSAL IN LARGE CAPS — de Groot, Huij & Zhou (Quantpedia #0013).

WHY THIS ONE
Our cross-sectional factor book died twice: once on survivorship (98% of the
2024 shorts were coins being delisted) and once as a plain null on live panels.
The diagnosis was breadth — 33 perps and 129 equities seemed too narrow.

This paper says the opposite, and it is the most interesting robustness table
in the whole Quantpedia sweep:

    universe size     net return per week
    1,500 stocks          -31.4 bp
      500 stocks          +10.6 bp
      100 stocks          +29.0 bp

The effect does not merely survive in large caps, it EXISTS ONLY THERE. A broad
universe destroys it, because the small names that generate the biggest raw
reversal are the ones whose spreads eat it. Our 129 liquid US names are the
right universe for this, not the wrong one — the earlier failure was the
construction, not the panel.

Paper: 16.25% p.a. NET of costs, vol 14.94%, Sharpe 1.09, 1990-2009, weekly.
Costs INCLUDED, which is rare and is why this entry is worth more than the
higher-Sharpe ones around it.

THE RULE
  universe   the 100 largest by market cap. We proxy size by median dollar
             volume, since we have no market-cap series — a reasonable stand-in
             for the liquidity the paper is really selecting on.
  long       the 10 worst performers of the PRIOR WEEK
  short      the 10 best performers of the PRIOR MONTH
             (note the asymmetry: it is in the paper and it matters)
  rebalance  weekly, equal weight

HONESTY
  - costs charged on turnover both legs, swept across a plausible range
  - the two legs reported separately, because a book carried entirely by one
    leg is a different and more fragile animal
  - by year, and both halves
  - the paper's own universe-size claim re-tested by running 40 / 80 / 129
  - a long/short pair is market-neutral by construction, so drift cannot
    masquerade as edge the way it did in the Keltner work
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DIR = "/home/claude/qlab/data_wide"


def load():
    px, dv = {}, {}
    for p in sorted(glob.glob(f"{DIR}/*.csv")):
        s = os.path.basename(p)[:-4]
        d = pd.read_csv(p)
        if "date" not in d.columns:
            continue
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"]).set_index("date").sort_index()
        d = d[~d.index.duplicated()]
        if len(d) < 600 or d.close.le(0).any():
            continue
        px[s] = d.close
        dv[s] = (d.close * d.volume) if "volume" in d.columns else d.close * 0
    return pd.DataFrame(px).sort_index(), pd.DataFrame(dv).sort_index()


def run(P, DV, n_universe=100, n_leg=10, cost_bp=10.0):
    R = P.pct_change()
    wk = P.resample("W-FRI").last()
    rows, prev = [], pd.Series(dtype=float)
    for i in range(6, len(wk) - 1):
        t = wk.index[i]
        pos = P.index.searchsorted(t)
        if pos < 30 or pos >= len(P.index) - 6:
            continue
        # universe: largest by trailing median dollar volume (size proxy)
        liq = DV.iloc[max(0, pos - 60):pos].median().dropna()
        uni = liq.nlargest(min(n_universe, len(liq))).index
        hist = P.iloc[:pos + 1][uni]
        if len(hist) < 30:
            continue
        r_week = hist.iloc[-1] / hist.iloc[-6] - 1          # prior week
        r_month = hist.iloc[-1] / hist.iloc[-22] - 1        # prior month
        r_week, r_month = r_week.dropna(), r_month.dropna()
        if len(r_week) < 2 * n_leg or len(r_month) < 2 * n_leg:
            continue
        longs = r_week.nsmallest(n_leg).index               # worst last WEEK
        shorts = r_month.nlargest(n_leg).index              # best last MONTH
        w = pd.Series(0.0, index=uni)
        w[longs] += 0.5 / n_leg
        w[shorts] -= 0.5 / n_leg
        nxt = P.index.searchsorted(wk.index[i + 1])
        seg = R.iloc[pos + 1:nxt + 1][uni].fillna(0)
        if not len(seg):
            continue
        turn = float((w - prev.reindex(w.index).fillna(0)).abs().sum())
        gross = float((seg.add(1).prod() - 1).mul(w).sum())
        lr = float((seg[longs].add(1).prod() - 1).mean())
        sr = float(-(seg[shorts].add(1).prod() - 1).mean())
        rows.append(dict(date=t, gross=gross, net=gross - turn * cost_bp / 10000,
                         long=lr, short=sr, turn=turn))
        prev = w
    return pd.DataFrame(rows)


def stat(v):
    v = np.asarray(v, float)
    se = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan
    ann = v.mean() * 52
    vol = v.std() * np.sqrt(52)
    return ann, vol, (ann / vol if vol > 0 else np.nan), v.mean() / se


if __name__ == "__main__":
    P, DV = load()
    print(f"SHORT-TERM REVERSAL IN LARGE CAPS — {P.shape[1]} US equities, "
          f"{P.index[0].date()} -> {P.index[-1].date()}")
    print("Paper: 16.25% p.a. NET, Sharpe 1.09. Expect 0.6-0.7 after the haircut.\n")
    print("  THE PAPER'S CENTRAL CLAIM: the effect exists only in large caps.")
    print(f"  {'universe':<12}{'n wks':>7}{'gross/wk':>11}{'net/wk':>10}"
          f"{'CAGR':>9}{'Sharpe':>8}{'t':>7}")
    store = {}
    for nu in (40, 80, 129):
        T = run(P, DV, n_universe=nu)
        if len(T) < 50:
            continue
        store[nu] = T
        a, v, sh, t = stat(T.net)
        print(f"  top {nu:<8}{len(T):>7}{T.gross.mean()*10000:>10.1f}bp"
              f"{T.net.mean()*10000:>9.1f}bp{a*100:>8.2f}%{sh:>8.2f}{t:>+7.2f}")

    T = store.get(100) or store.get(80)
    if T is None:
        raise SystemExit
    print(f"\n  LEGS SEPARATELY (top 80)")
    for c, lab in (("long", "long: worst prior WEEK"),
                   ("short", "short: best prior MONTH")):
        a, v, sh, t = stat(T[c])
        print(f"    {lab:<28}{T[c].mean()*10000:>8.1f}bp/wk  CAGR {a*100:>6.2f}%"
              f"  t={t:+.2f}")

    print(f"\n  COST SENSITIVITY (top 80)")
    for bp in (5, 10, 20, 40):
        X = run(P, DV, n_universe=80, cost_bp=bp)
        a, v, sh, t = stat(X.net)
        print(f"    {bp:>3}bp round trip   net {X.net.mean()*10000:>6.1f}bp/wk"
              f"   CAGR {a*100:>6.2f}%   Sharpe {sh:>5.2f}")

    T = T.copy(); T["yr"] = pd.to_datetime(T.date).dt.year
    print(f"\n  BY YEAR (top 80)")
    for y, g in T.groupby("yr"):
        if len(g) < 10: continue
        a, v, sh, t = stat(g.net)
        print(f"    {y}  n={len(g):3d}  {g.net.mean()*10000:>6.1f}bp/wk"
              f"  CAGR {a*100:>7.2f}%  t={t:+.2f}")
    h = len(T) // 2
    for lab, g in (("first half ", T.iloc[:h]), ("second half", T.iloc[h:])):
        a, v, sh, t = stat(g.net)
        print(f"  {lab}  {g.net.mean()*10000:>6.1f}bp/wk  CAGR {a*100:>6.2f}%  t={t:+.2f}")
    cum = (1 + T.net.values).cumprod()
    dd = (cum / np.maximum.accumulate(cum) - 1).min()
    print(f"\n  cumulative {(cum[-1]-1)*100:+.1f}%   max drawdown {dd*100:.1f}%")
