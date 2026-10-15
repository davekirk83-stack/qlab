"""
CROSS-SECTIONAL BOOK ON A LIVE PANEL — the diversification fix, done properly.

THE PROBLEM THIS SOLVES
All registered books are long-biased crypto mean-reversion on the same
instruments. They will draw down together. Four books that correlate are one
book with extra steps.

WHY THE FIRST ATTEMPT WAS KILLED (xsec.py, audited 2026-10-15)
It scored +3.45% per 21-day period at t=+2.47 on 153 instruments, and it was
survivorship in reverse:
    2023  net +1.64%  t=+0.91   shorts that die within a year:  0%
    2024  net +4.15%  t=+1.91   shorts that die within a year: 98%
The short basket in 2024 was almost entirely coins on their way to delisting.
You cannot reliably borrow and short a coin that is about to be removed, and
the data ends because the instrument died, not because the trade closed. The
panel itself stops in 2024 — only 13 of 255 instruments still report — so the
book could not be run today even if the edge were real. Not registrable.

THIS VERSION
33 Binance USDT-M perpetuals that are ALL STILL TRADING TODAY. No delistings,
because the universe was drawn from the current listing. That removes the
survivorship mechanism by construction rather than by a filter. The cost is a
known forward-looking bias in the opposite direction — these are survivors,
so the LONG leg is flattered. Which is exactly why the market leg is removed
and the legs are reported separately: a long-only survivor bias cannot produce
a long-short edge unless the ranking does real work.

CONSTRUCTION
  rank      each instrument on a composite of elements doc 57 measured, ranked
            CROSS-SECTIONALLY each rebalance (so it is relative, not absolute)
  hold      swept, not chosen
  weights   equal long the top quintile, equal short the bottom, gross 2x,
            net 0 — market direction cancels
  costs     10bp round trip per leg per rebalance, charged on turnover
  demeaned  returns demeaned across the panel each bar, so market drift cannot
            masquerade as factor return

HONESTY
  - non-overlapping periods only
  - both legs reported alone, because a book carried entirely by one leg is
    a different and more fragile animal
  - split by year AND by half
  - the whole grid printed, so a single lucky cell is visible as such
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import elements as EL

DIR = os.environ.get("XPANEL","/home/claude/qlab/data_1h_33")
FEE = float(os.environ.get("XFEE","10"))/10000
_PRESET = os.environ.get("XSIGN", "reversal")
if _PRESET == "momentum":
    # cross-sectional momentum: the classic equity factor. Long what is
    # already strong and extended, short what is weak. Opposite sign to the
    # crypto reversal composite on every trend term.
    FEATS = {"dist_ema_200": +1, "range_pos_200": +1, "ret_20": +1,
             "bb_width_50": -1, "vol_rel": +1}
else:
    FEATS = {"bb_width_50": -1, "dist_ema_200": -1, "vol_rel": +1,
             "range_pos_200": -1, "ret_20": -1}


def load():
    px, sc = {}, {}
    for p in sorted(glob.glob(f"{DIR}/*.csv")):
        s = os.path.basename(p)[:-4]
        d = pd.read_csv(p)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date"]).set_index("date").sort_index()
        d = d[~d.index.duplicated()]
        if len(d) < int(os.environ.get("XMIN","3000")) or d.close.le(0).any():
            continue
        F = EL.build(d)
        if any(k not in F for k in FEATS):
            continue
        sc[s] = pd.DataFrame({k: F[k] for k in FEATS}, index=d.index)
        px[s] = d.close
    return pd.concat(sc, axis=1), pd.DataFrame(px)


def composite(S, R, feats):
    comp = None
    for k, sign in feats.items():
        X = S.xs(k, axis=1, level=1).reindex(R.index)
        r = X.rank(axis=1, pct=True) * sign
        comp = r if comp is None else comp + r
    return comp


def backtest(comp, R, hold, topq):
    rets = R.pct_change()
    rows, prev = [], pd.Series(dtype=float)
    for i in range(300, len(R) - hold, hold):
        row = comp.iloc[i].dropna()
        if len(row) < 15:
            continue
        k = max(3, int(len(row) * topq))
        L, Sh = row.nlargest(k).index, row.nsmallest(k).index
        w = pd.Series(0.0, index=row.index)
        w[L] = 1.0 / k; w[Sh] = -1.0 / k
        fwd = (rets.iloc[i + 1:i + 1 + hold][row.index].fillna(0) + 1).prod() - 1
        fwd = fwd - fwd.mean()                      # demean: remove the market
        gross = float((w * fwd).sum())
        turn = float((w - prev.reindex(w.index).fillna(0)).abs().sum())
        rows.append(dict(date=R.index[i], gross=gross, net=gross - turn * FEE,
                         long=float(fwd[L].mean()), short=float(-fwd[Sh].mean()),
                         turn=turn))
        prev = w
    return pd.DataFrame(rows)


def stat(v):
    v = np.asarray(v, float)
    se = v.std(ddof=1) / np.sqrt(len(v)) if len(v) > 1 else np.nan
    return v.mean(), (v.mean() / se if se and se == se else np.nan)


if __name__ == "__main__":
    S, R = load()
    print(f"CROSS-SECTIONAL BOOK — {R.shape[1]} live instruments, "
          f"{R.index[0].date()} -> {R.index[-1].date()}")
    print("All instruments still listed, so the short leg cannot be delistings.\n")
    comp = composite(S, R, FEATS)
    print(f"  {'hold(h)':>8}{'top%':>7}{'n':>6}{'gross':>10}{'NET':>10}"
          f"{'t':>8}{'long':>9}{'short':>9}{'turn':>7}")
    grid = []
    for hold in [int(x) for x in os.environ.get("XHOLDS","24,72,168,336,504").split(",")]:
        for topq in (0.2, 0.3):
            T = backtest(comp, R, hold, topq)
            if len(T) < 15:
                continue
            m, t = stat(T.net)
            lm, _ = stat(T.long); sm, _ = stat(T.short)
            grid.append((t, hold, topq, T))
            print(f"  {hold:>8}{topq*100:>6.0f}%{len(T):>6}"
                  f"{T.gross.mean()*100:>+9.3f}%{m*100:>+9.3f}%{t:>+8.2f}"
                  f"{lm*100:>+8.3f}%{sm*100:>+8.3f}%{T.turn.mean():>7.2f}")
    if not grid:
        print("  nothing ran"); raise SystemExit
    pos = sum(1 for g in grid if g[3].net.mean() > 0)
    print(f"\n  plateau: {pos}/{len(grid)} configurations net positive")
    t_req = float(np.sqrt(2 * np.log(max(len(grid), 2))))
    best = max(grid, key=lambda g: g[0])
    t, hold, topq, T = best
    print(f"  corrected t threshold for {len(grid)} configs: {t_req:.2f}")
    print(f"\n  BEST: hold {hold}h, top/bottom {topq*100:.0f}%   "
          f"t={t:+.2f} {'CLEARS' if t >= t_req else 'FAILS'} the corrected bar")
    print(f"  periods positive: {int((T.net > 0).sum())}/{len(T)}")
    cum = (1 + T.net.values).cumprod()
    dd = (cum / np.maximum.accumulate(cum) - 1).min()
    print(f"  cumulative {(cum[-1]-1)*100:+.1f}%   max drawdown {dd*100:.1f}%")
    T = T.copy(); T["yr"] = pd.to_datetime(T.date).dt.year
    print("\n  by year:")
    for y, g in T.groupby("yr"):
        if len(g) < 3: continue
        m, tt = stat(g.net)
        print(f"    {y}  n={len(g):3d}  net {m*100:+7.3f}%  t={tt:+5.2f}")
    h = len(T) // 2
    for lab, g in (("first half ", T.iloc[:h]), ("second half", T.iloc[h:])):
        m, tt = stat(g.net)
        print(f"  {lab}  net {m*100:+7.3f}%  t={tt:+5.2f}")
