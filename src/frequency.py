"""
CAN WE GET TO 5-20 TRADES A DAY WITHOUT LOSING THE EDGE?

DK: "I'd much rather we earned $10 five to twenty times a day than trying to
     get $200 wins a few times a week."

That is 150-600 trades a month. Our five books together produce about 54.
We are an order of magnitude short — on OPPORTUNITY COUNT, not on edge. The
per-trade economics already work: at 2x on $2,000 a $10 net gain is 0.25% of
notional, and cascade v3's net edge is 0.354% with maker fees at 0.024%.

So the question is not "find a better edge". It is "where does the trade count
come from, and what does the edge cost to get it".

THREE LEVERS, and each has a different failure mode
  UNIVERSE   more instruments. Should be close to free — the small-account
             study found profitable traders run 22 instruments to the whales'
             14. Failure mode: thin coins where the measured edge does not
             survive real spreads.
  THRESHOLD  a smaller trigger. A 3% five-minute drop is rare; a 1.5% drop is
             not. Failure mode: the edge IS the extremity, so a weaker trigger
             should mean a weaker edge. This is the one that matters.
  TIMEFRAME  the same shape on faster bars. Failure mode: cost in R rises as
             the stop tightens — doc 51's lesson, where an 8bp cost became
             0.84R against a 0.19% stop.

Measured across the full 49-symbol 1-minute panel (18 in-sample + 31 that were
held out), reporting for every combination: trades per month, net edge per
trade after real maker fees, and the resulting DOLLARS PER MONTH on a $2,000
stack at 2x — because trades per month and edge per trade only matter together.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

PANELS = ["/home/claude/qlab/data_1m/*.csv", "/home/claude/qlab/data_1m_oos/*.csv"]
MAKER, TAKER, SLIP = 1.2 / 10000, 4.0 / 10000, 5.0 / 10000
STACK, LEV = 2000.0, 2.0
LIFT, HOLD, DEPTHB, MAXH = 0.008, 10, 0.004, 60


def load_all():
    out = {}
    for pat in PANELS:
        for p in sorted(glob.glob(pat)):
            s = os.path.basename(p)[:-4]
            if s in out:
                continue
            d = pd.read_csv(p)
            if "t" not in d.columns or len(d) < 50000:
                continue
            d["dt"] = pd.to_datetime(d.t, unit="ms")
            out[s] = d.set_index("dt").sort_index()
    return out


def find_base(C, L, i, n, mw=60):
    lo = L[i]; k = i
    while k < min(i + mw, n - 1):
        if L[k] < lo: lo = L[k]
        if C[k] >= lo * (1 + LIFT): break
        k += 1
    if k >= min(i + mw, n - 1) or C[k] < lo * (1 + LIFT): return None
    j = k; h = 0
    while j < min(k + mw, n - 1):
        if L[j] < lo: return None
        h += 1
        if h >= HOLD: return j, lo
        j += 1
    return None


def run(panel, drop, win, tp, syms=None):
    rows = []
    months = 0
    names = list(panel.keys())[:syms] if syms else list(panel.keys())
    for s in names:
        d = panel[s]
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C)
        months += (d.index[-1] - d.index[0]).days / 30.44
        i = win
        while i < n - 2 * MAXH:
            if C[i] / C[i - win] - 1 > -drop:
                i += 1; continue
            b = find_base(C, L, i, n)
            if b is None:
                i += win; continue
            j, lo = b
            bid = max(C[j] * (1 - DEPTHB), lo * 1.0002)
            fill = None
            for q in range(j + 1, min(j + 1 + MAXH, n)):
                if L[q] < lo: break
                if L[q] <= bid: fill = q; break
            if fill is None:
                i = j + 1; continue
            px = bid * (1 + MAKER); stop = lo * (1 - 0.0005); tgt = px * (1 + tp)
            if stop >= px:
                i = j + 1; continue
            r = None
            for q in range(fill + 1, min(fill + 1 + MAXH, n)):
                if L[q] <= stop: r = (stop * (1 - SLIP - TAKER)) / px - 1; break
                if H[q] >= tgt: r = (tgt * (1 - MAKER)) / px - 1; break
            if r is None:
                q = min(fill + MAXH, n - 1); r = (C[q] * (1 - MAKER)) / px - 1
            rows.append(r)
            i = fill + MAXH
    if not rows:
        return None
    r = np.array(rows)
    se = r.std(ddof=1) / np.sqrt(len(r)) if len(r) > 1 else np.nan
    per_month = len(r) / (months / len(names)) if months else 0
    return dict(n=len(r), edge=r.mean() * 100, t=r.mean() / se if se else np.nan,
                win=(r > 0).mean() * 100, per_month=per_month,
                usd_month=per_month * STACK * LEV * r.mean())


if __name__ == "__main__":
    P = load_all()
    print(f"CASCADE SCALING — {len(P)} symbols of 1-minute data")
    print(f"Target: 150-600 trades/month. Currently ~12.\n")
    print(f"  {'drop':>6}{'win':>5}{'TP':>7}{'syms':>6}{'trades':>8}"
          f"{'/month':>8}{'edge':>9}{'t':>7}{'win%':>7}{'$/mo @2x':>10}")
    for drop, win in ((0.03, 5), (0.02, 5), (0.015, 5), (0.01, 5), (0.01, 15)):
        for tp in (0.015, 0.008, 0.005):
            r = run(P, drop, win, tp)
            if not r or r["n"] < 30:
                continue
            print(f"  {drop*100:>5.1f}%{win:>5}{tp*100:>6.1f}%{len(P):>6}"
                  f"{r['n']:>8}{r['per_month']:>8.1f}{r['edge']:>+8.3f}%"
                  f"{r['t']:>+7.2f}{r['win']:>6.1f}%{r['usd_month']:>10,.0f}")
    print(f"\n  universe effect, at drop 1.5% / TP 0.8%:")
    for k in (10, 20, 35, len(P)):
        r = run(P, 0.015, 5, 0.008, syms=k)
        if r:
            print(f"    {k:>3} symbols   {r['n']:>5} trades   "
                  f"{r['per_month']:>6.1f}/month   edge {r['edge']:+.3f}%   "
                  f"t={r['t']:+.2f}   ${r['usd_month']:,.0f}/mo")
