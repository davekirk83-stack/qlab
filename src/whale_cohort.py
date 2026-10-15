"""
HOW PROFITABLE ACCOUNTS ACTUALLY EXECUTE — 90 accounts, every fill on-chain.

DK: "I want you to see exactly what a successful and profitable trade looks
     like as technique and execution." ... "losing is far easier, so skew your
     learning towards winners."

Taken as instructed: the winners are the subject, the losers appear only as a
contrast column where it sharpens the reading.

COHORTS, from the 47,016-account Hyperliquid leaderboard
  WINNERS  equity > $200k, lifetime volume > $5m, profitable all-time AND over
           the last month AND over the last week, all-time ROI > 100%.
           325 qualify; the top 45 by PnL-per-dollar-traded were pulled.
  LOSERS   same size and volume floors, losing all-time AND over the last
           month, all-time ROI < -30%. 247 qualify; worst 45 pulled.

Ranking winners by PnL per dollar of VOLUME rather than by PnL matters: it is
edge per unit of turnover, which cannot be bought with leverage or size.

Each account's 2,000 most recent fills. That is a window, not a career — hours
for the fastest accounts, weeks for the slowest — so these are execution
habits, not lifetime results.
"""
import warnings; warnings.filterwarnings("ignore")
import json, glob, os
import numpy as np, pandas as pd


def account(path):
    try:
        f = json.load(open(path))
    except Exception:
        return None
    if not f or len(f) < 50:
        return None
    d = pd.DataFrame(f)
    for c in ("px", "sz", "closedPnl", "fee", "startPosition"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d.time, unit="ms")
    d = d.sort_values("ts").reset_index(drop=True)
    d["notional"] = d.px * d.sz
    span_h = max((d.ts.max() - d.ts.min()).total_seconds() / 3600, 1e-6)
    gap = d.ts.diff().dt.total_seconds().dropna()

    # adding while underwater: an Open fill on a position whose running
    # realised PnL on that coin is negative over the window
    adds_losing = tot_adds = 0
    for coin, g in d.groupby("coin"):
        g = g.sort_values("ts")
        run = 0.0
        for _, r in g.iterrows():
            if "Open" in str(r.dir):
                tot_adds += 1
                if run < 0:
                    adds_losing += 1
            run += r.closedPnl if np.isfinite(r.closedPnl) else 0.0

    return dict(
        fills=len(d),
        span_h=span_h,
        instruments=d.coin.nunique(),
        top_coin_share=d.coin.value_counts(normalize=True).iloc[0] * 100,
        med_slice=d.notional.median(),
        mean_slice=d.notional.mean(),
        slice_skew=(d.notional.max() / max(d.notional.median(), 1e-9)),
        passive_pct=(~d.crossed).mean() * 100,
        passive_notional_pct=(d[~d.crossed].notional.sum()
                              / max(d.notional.sum(), 1e-9)) * 100,
        fills_per_h=len(d) / span_h,
        med_gap_s=gap.median() if len(gap) else np.nan,
        traded=d.notional.sum(),
        pnl=d.closedPnl.sum(),
        fee=d.fee.sum(),
        fee_bp=d.fee.sum() / max(d.notional.sum(), 1e-9) * 10000,
        add_while_losing=(adds_losing / tot_adds * 100) if tot_adds else np.nan,
    )


def cohort(tag):
    rows = []
    for p in sorted(glob.glob(f"/tmp/fills/{tag}_*.json")):
        a = account(p)
        if a:
            a["addr"] = os.path.basename(p)[len(tag) + 1:-5]
            rows.append(a)
    return pd.DataFrame(rows)


def line(lab, w, l, fmt="{:.1f}", key=None):
    a = w[key].median(); b = l[key].median() if len(l) else np.nan
    print(f"  {lab:<38}{fmt.format(a):>14}{fmt.format(b) if b==b else 'n/a':>14}")


if __name__ == "__main__":
    W, L = cohort("win"), cohort("lose")
    print(f"WINNERS n={len(W)}   losers n={len(L)}   (medians)\n")
    print(f"  {'':<38}{'WINNERS':>14}{'losers':>14}")
    print("  " + "-" * 66)
    print("  CONCENTRATION")
    line("instruments traded in the window", W, L, "{:.0f}", "instruments")
    line("share of fills in their top instrument", W, L, "{:.0f}%", "top_coin_share")
    print("\n  SLICING")
    line("median notional per fill", W, L, "${:,.0f}", "med_slice")
    line("mean notional per fill", W, L, "${:,.0f}", "mean_slice")
    line("largest fill / median fill", W, L, "{:,.0f}x", "slice_skew")
    line("seconds between fills", W, L, "{:.1f}s", "med_gap_s")
    line("fills per hour", W, L, "{:,.0f}", "fills_per_h")
    print("\n  PASSIVE vs AGGRESSIVE")
    line("passive share of fills", W, L, "{:.1f}%", "passive_pct")
    line("passive share of notional", W, L, "{:.1f}%", "passive_notional_pct")
    print("\n  ADDING TO LOSERS")
    line("opens made while that coin is in the red", W, L, "{:.1f}%", "add_while_losing")
    print("\n  COST")
    line("effective fee rate", W, L, "{:.2f}bp", "fee_bp")
    print()
    print("  DISPERSION AMONG WINNERS — the point is how WIDE these are")
    for k, lab, f in (("passive_pct", "passive share of fills", "{:.0f}%"),
                      ("med_slice", "median slice", "${:,.0f}"),
                      ("instruments", "instruments traded", "{:.0f}"),
                      ("fills_per_h", "fills per hour", "{:,.0f}"),
                      ("add_while_losing", "opens while in the red", "{:.0f}%")):
        v = W[k].dropna()
        print(f"    {lab:<30} 10th {f.format(v.quantile(.1)):>10}"
              f"   median {f.format(v.median()):>10}"
              f"   90th {f.format(v.quantile(.9)):>10}")
    print(f"\n  WINNERS WHO ARE MOSTLY PASSIVE (>50% maker): "
          f"{(W.passive_pct > 50).mean()*100:.0f}%")
    print(f"  WINNERS WHO TRADE ONE INSTRUMENT ONLY:        "
          f"{(W.instruments == 1).mean()*100:.0f}%")
    print(f"  WINNERS WITH >80% OF FILLS IN ONE INSTRUMENT: "
          f"{(W.top_coin_share > 80).mean()*100:.0f}%")
    print(f"  LOSERS  with >80% in one instrument:          "
          f"{(L.top_coin_share > 80).mean()*100:.0f}%")
