"""
ENTRY QUALITY, MEASURED WITHOUT ANY EXIT SCHEME.

DK's correction, and it is right: "Without a good entry, you won't reach TP or
exit." Entries and exits are multiplicative, not additive. The entry selects the
distribution of paths you are exposed to; the exit decides how much of that
distribution you harvest. Ranking one against the other is a category error, and
concluding "exits are everything" from a fixed-exit test is circular — the 35%
of trades that ran to +2.31R did so because the PATHS allowed it.

The previous test was also confounded: entries were compared while holding a
fixed exit geometry (1.5 ATR stop, TP1 1R, TP2 3R, 10 bars) that had been tuned
on a different universe. A good entry paired with the wrong exit geometry tests
as worthless.

So: measure the entry on its own terms. No stop, no target, no time limit, no
position sizing. Just — conditional on this signal, what does the next N bars'
path distribution look like, versus the unconditional baseline for the same
instrument?

Measures, all scaled by ATR at the signal so instruments are comparable:

  MFE   maximum favourable excursion over N bars (how far it runs your way)
  MAE   maximum adverse excursion  (how far it goes against you first)
  P(+k before -k)  the barrier race: does it touch +k ATR before -k ATR?
        This is THE number. It is exit-free, it is what any stop/target
        structure actually monetises, and for a driftless random walk with
        symmetric barriers it is 0.50 by construction.
  edge ratio  MFE/MAE, the standard entry-quality statistic

Baseline is every other bar in the same instrument, so each name is its own
control and drift is differenced out.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import core as C
import levels as LV
import patterns as P
from run10 import atr
import wide_test as W

PANEL = W.PANEL
ETF = set(W.CLASS.keys())
HOR = 10
KS = (1.0, 2.0, 3.0)


def barrier_race(H, L, i, px, a, k, horizon):
    """Does price touch +k*ATR before -k*ATR within `horizon` bars?
    Returns 1 (up first), 0 (down first), or None (neither)."""
    up, dn = px + k * a, px - k * a
    for j in range(i + 1, min(i + 1 + horizon, len(H))):
        hit_up, hit_dn = H[j] >= up, L[j] <= dn
        if hit_up and hit_dn:
            return None            # ambiguous within the bar — discard, do not guess
        if hit_up:
            return 1
        if hit_dn:
            return 0
    return None


def profile(df, idx, horizon=HOR):
    """Path statistics for a set of entry indices. Exit-free."""
    A = atr(df).values
    H, L, O = df.high.values, df.low.values, df.open.values
    rows = []
    for i in idx:
        if i + 1 >= len(df) - horizon:
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        px = O[i + 1]
        if not (px == px) or px <= 0:
            continue
        seg_h = H[i + 1:i + 1 + horizon]
        seg_l = L[i + 1:i + 1 + horizon]
        if len(seg_h) < horizon:
            continue
        mfe = (seg_h.max() - px) / a
        mae = (px - seg_l.min()) / a
        r = dict(mfe=mfe, mae=mae)
        for k in KS:
            r[f"race{k}"] = barrier_race(H, L, i, px, a, k, horizon)
        rows.append(r)
    return rows


ENTRIES = {
    "month-high break": lambda d: LV.l_break_prior_month_high(d),
    "swing break": lambda d: LV.l_swing_break(d, 20),
    "donchian 20": lambda d: (d.close > d.high.rolling(20).max().shift(1)).astype(float),
    "flag": lambda d: P.p_flag(d, 2.0, 10, 5, 0.5),
    "pullback in uptrend": lambda d: C.s_rsi(d, 2, 10) * C.f_trend200(d),
    "quarter-high break": lambda d: LV.l_break_prior_quarter_high(d),
}


def summarise(rows, label):
    if len(rows) < 100:
        return None
    t = pd.DataFrame(rows)
    out = dict(label=label, n=len(t), mfe=t.mfe.mean(), mae=t.mae.mean())
    out["edge_ratio"] = out["mfe"] / out["mae"] if out["mae"] > 0 else np.nan
    for k in KS:
        v = t[f"race{k}"].dropna()
        out[f"p{k}"] = float(v.mean()) if len(v) > 50 else np.nan
        out[f"n{k}"] = len(v)
    return out


def line(d, base=None):
    s = (f"  {d['label']:22s} n={d['n']:6d}  MFE {d['mfe']:5.2f}  MAE {d['mae']:5.2f}  "
         f"ratio {d['edge_ratio']:5.3f}")
    for k in KS:
        p = d[f"p{k}"]
        s += f"   P(+{k:.0f}/-{k:.0f}) {p*100:5.1f}%" if p == p else f"   P(+{k:.0f}) n/a"
    print(s)
    if base:
        d2 = "  " + " " * 22 + "  vs baseline:"
        for k in KS:
            if d[f"p{k}"] == d[f"p{k}"] and base[f"p{k}"] == base[f"p{k}"]:
                gap = (d[f"p{k}"] - base[f"p{k}"]) * 100
                # binomial standard error on the signal sample
                se = np.sqrt(0.25 / max(d[f"n{k}"], 1)) * 100
                z = gap / se if se > 0 else 0
                d2 += f"  {gap:+5.1f}pp (z={z:+.1f})"
        print(d2)


def main():
    print("ENTRY QUALITY — measured with NO exit scheme at all\n")
    print(f"  {len(ETF & set(PANEL))} survivorship-clean ETFs, {HOR}-bar horizon")
    print("  MFE/MAE in ATR units. P(+k/-k) is the barrier race: does price touch")
    print("  +k ATR before -k ATR? For a driftless walk that is 50.0% by construction.")
    print("  Baseline = every other bar in the same instrument.\n")

    # baseline: all bars
    base_rows = []
    for s, df in PANEL.items():
        if s not in ETF or len(df) < 400:
            continue
        step = 7                      # sample every 7th bar to keep it comparable in size
        base_rows += profile(df, range(250, len(df) - HOR - 1, step))
    base = summarise(base_rows, "BASELINE (all bars)")
    print("=" * 118)
    line(base)
    print("=" * 118)

    res = []
    for name, fn in ENTRIES.items():
        idx_rows = []
        for s, df in PANEL.items():
            if s not in ETF or len(df) < 400:
                continue
            try:
                e = fn(df)
                e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
            except Exception:
                continue
            if e.sum() == 0:
                continue
            idx_rows += profile(df, np.flatnonzero(e.values > 0))
        d = summarise(idx_rows, name)
        if d:
            line(d, base); res.append(d)

    print()
    print("=" * 118)
    print("  VERDICT")
    print("=" * 118)
    print(f"  An entry adds value only if P(+k before -k) is materially above the")
    print(f"  baseline of {base['p1.0']*100:.1f}% / {base['p2.0']*100:.1f}% / "
          f"{base['p3.0']*100:.1f}% at 1/2/3 ATR.")
    print(f"  |z| > 2 is the bar for 'not chance'.\n")
    any_good = False
    for d in res:
        best = max((abs((d[f'p{k}'] - base[f'p{k}']) / (np.sqrt(0.25 / max(d[f'n{k}'], 1))))
                    for k in KS if d[f'p{k}'] == d[f'p{k}'] and base[f'p{k}'] == base[f'p{k}']),
                   default=0)
        if best > 2:
            any_good = True
            print(f"    {d['label']:22s} PASSES — max |z| = {best:.1f}")
    if not any_good:
        print("    No entry shifts the barrier race beyond chance.")
        print("    That is a verdict on THESE entries on THIS universe, not on")
        print("    entry timing in general.")

    C.ledger_bump(len(ENTRIES) * 3, "exit-free entry quality")


if __name__ == "__main__":
    main()
