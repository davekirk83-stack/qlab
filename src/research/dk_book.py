"""THE DK BOOK — DK's own way of trading BTC, built and tested as ONE system (DK 27 Nov 16:15: "I want you to build it").
Every rule is taken from his own words and trades (project doc 234 / 230 / 225 / 252):
  WHERE     resting bids at the obvious liquidity: live long-liquidation clusters with more clusters below (doc 224/225 levels)
  WHEN      in a flush ("cascade buying"): price >= 6% under its 72h high, or the market above its 200-day (bull)
  HOW       "I bid in small chunks over a period": 4 resting bids at the cluster, -1%, -2%, -3% sized 10/20/30/40% (maker, no fee), 2 days
  STOP      "just beyond the obvious wick": 1% under the deepest bid (4% under the cluster)
  ADD       "add incrementally to build an initial position, and then add to it on confirmation": on a 4h close back above the
            cluster with the 4h MACD histogram rising (his 21 Nov trigger), add half the ladder size at market; stop moves to 0.5% under the low
  BANK      "take profit on the bounce" / "took about a third off": a third at +1.5% over the average (maker)
  FREE SWING "stops at b/e ... It's a free swing": after the partial the stop goes to breakeven
  TARGET    the rest at the nearest short-liquidation cluster above (what he aims for: "just under where his liquidation map ends"),
            at least +3% over the average; 7-day limit
  RE-ENTRY  "buys again after each stop-run sweep ... stop under the new low": once per campaign, after a stop-out, the first 15-min
            close back above the old stop within 8h buys half size at market, stop 0.5% under the sweep low, same exits
  EVENTS    "avoid holding positions during a CPI announcement": no fills 08:15-10:30 NY on CPI days, flat before 08:30
Data: BTC 15-min 2021-01 .. 2026-11 (Binance), clusters estimated from volume (doc 224). Costs: Revolut X maker 0%, taker 0.09% + 0.05% slip.
Result per campaign = % of the ladder budget. Ablations switch ONE of his rules off at a time to show what each adds to the whole."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, io, contextlib, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
with contextlib.redirect_stdout(io.StringIO()): import liq_book as LB
H, L, C, O, N, IX, BULL = LB.H, LB.L, LB.C, LB.O, LB.N, LB.IX, LB.BULL
TAKER, SLIP = 0.0009, 0.0005
E = LB.events(cpi=True)
hi72 = pd.Series(H).rolling(288, min_periods=50).max().values
U = LB.U
# 4h confirmation series on the 15-min grid: true on the 15-min bar that completes a 4h bar whose close > open-of-check level is evaluated in-loop
c15 = pd.Series(C, index=U); c4 = c15.resample("4h").last().dropna()
m = c4.ewm(span=12, adjust=False).mean() - c4.ewm(span=26, adjust=False).mean(); hist = m - m.ewm(span=9, adjust=False).mean()
END4 = np.zeros(N, bool); C4 = np.full(N, np.nan); HUP = np.zeros(N, bool)
pos = U.searchsorted(c4.index + pd.Timedelta("4h") - pd.Timedelta("15min"))
for k, p in enumerate(pos):
    if 0 <= p < N and k > 0: END4[p] = True; C4[p] = c4.values[k]; HUP[p] = hist.values[k] > hist.values[k - 1]
CPIJ = LB.CPI_J

def next_cpi(j):
    i = np.searchsorted(CPIJ, j + 1); return CPIJ[i] if i < len(CPIJ) else 10 ** 9

def manage(k0, kend, qty, cost, stop, near, opt, lvl, filling=None):
    """run a position from bar k0; filling = (rungs, weights, last_fill_bar) for the ladder. Returns (pnl_frac_of_budget, exit_bar, stopped, low)."""
    pnl = 0.0; part = False; added = False; low = 1e18; ncpi = next_cpi(k0)
    for k in range(k0, kend + 1):
        if filling:
            rungs, wts, lastb, done = filling
            for r in range(len(rungs)):
                if not done[r] and k <= lastb and L[k] <= rungs[r] and not LB.CPI_BLOCK[k]:
                    done[r] = True; qty += wts[r]; cost += wts[r] * rungs[r]
        if qty <= 0:
            if filling and k > filling[2]: return None
            continue
        low = min(low, L[k]); avg = cost / qty
        if L[k] <= stop:                                                       # stop first (conservative)
            px = stop * (1 - SLIP); pnl += qty * (px * (1 - TAKER) - avg); return pnl, k, True, low
        if k >= ncpi - 1:                                                      # flat before the CPI release
            pnl += qty * (C[k] * (1 - SLIP) * (1 - TAKER) - avg); return pnl, k, False, low
        if opt["part"] and not part and H[k] >= avg * 1.015 and k > k0:
            q = qty / 3; pnl += q * (avg * 1.015 - avg); qty -= q; cost = avg * qty; part = True
            if opt["be"]: stop = max(stop, avg)
        tgt = max(near if (opt["near"] and near) else 0, avg * 1.03)
        if k > k0 and H[k] >= tgt:
            pnl += qty * (tgt - avg); return pnl, k, False, low
        if opt["add"] and not added and END4[k] and C4[k] > lvl and HUP[k]:
            q = 0.5; px = C[k] * (1 + SLIP) * (1 + TAKER); qty += q; cost += q * px; added = True
            stop = max(stop, low * 0.995) if not part else stop
    avg = cost / qty; pnl += qty * (C[kend] * (1 - SLIP) * (1 - TAKER) - avg); return pnl, kend, False, low

def campaign(j, lvl, near, opt):
    rungs = [lvl * f for f in ((1.0, 0.99, 0.98, 0.97) if opt["ladder"] else (1.0,))]
    wts = (0.1, 0.2, 0.3, 0.4) if opt["ladder"] else (1.0,)
    stop = min(rungs) * 0.99; kend = min(N - 1, j + 96 * 7)
    r = manage(j, kend, 0.0, 0.0, stop, near, opt, lvl, filling=(rungs, wts, min(N - 1, j + 192), [False] * len(rungs)))
    if r is None: return None
    pnl, kx, stopped, low = r; pnl /= lvl                                     # fraction of the ladder budget
    if stopped and opt["reentry"]:
        sw = low
        for k in range(kx + 1, min(N - 1, kx + 32)):
            sw = min(sw, L[k])
            if C[k] > stop:                                                    # reclaim of the old stop after the sweep
                e = C[k] * (1 + SLIP) * (1 + TAKER); st2 = sw * 0.995
                r2 = manage(k + 1, min(N - 1, k + 96 * 3), 0.5, 0.5 * e, st2, near, dict(opt, add=False), lvl)
                if r2: pnl += r2[0] / lvl; kx = r2[1]
                break
    return pnl * 100, kx

BASE = dict(ladder=True, part=True, be=True, near=True, add=True, reentry=True, flush=True)
def run(opt, label):
    rows = []; busy = -1
    for j, lvl, tgt, near in E.values:
        j = int(j)
        if j <= busy: continue
        if opt["flush"] and not (BULL[j] or C[j] <= hi72[j] * 0.94): continue
        r = campaign(j, lvl, near, opt)
        if r is None: continue
        rows.append((IX[j], r[0])); busy = max(r[1], j + 96)
    t = pd.Series([x for _, x in rows], index=pd.to_datetime([a for a, _ in rows]))
    y = t.groupby(t.index.year).sum(); h = len(t) // 2; eq = t.cumsum(); dd = (eq - eq.cummax()).min()
    return dict(version=label, n=len(t), per_yr=round(len(t) / ((t.index[-1] - t.index[0]).days / 365.25), 1), win=round((t > 0).mean(), 2),
                mean_pct=round(t.mean(), 3), h1=round(t[:h].mean(), 3), h2=round(t[h:].mean(), 3), last12m=round(t[t.index >= t.index[-1] - pd.Timedelta("365D")].mean(), 3),
                yrs_pos=f"{(y > 0).sum()}/{len(y)}", worst_yr=round(y.min(), 2), total_pct=round(t.sum(), 1), max_dd_pct=round(dd, 1)), t

if __name__ == "__main__":
    out = []; series = {}
    tests = [("DK BOOK (all his rules)", {})] + [(f"without: {k}", {k: False}) for k in ("ladder", "part", "be", "near", "add", "reentry", "flush")] + \
            [("LIQ book as running (doc 225: no ladder, no partial/BE/add/re-entry)", dict(ladder=False, part=False, be=False, add=False, reentry=False))]
    for lab, ch in tests:
        r, t = run(dict(BASE, **ch), lab); out.append(r); series[lab] = t; print(r, flush=True)
    R = pd.DataFrame(out); R.to_csv("runs/research/dk_book.csv", index=False); series["DK BOOK (all his rules)"].to_csv("runs/research/dk_book_trades.csv")
    pd.set_option("display.width", 250); print(R.to_string(index=False))
    t = series["DK BOOK (all his rules)"]; print("\nDK BOOK by year (% of ladder budget):", t.groupby(t.index.year).sum().round(1).to_dict())

# ---- Level source 2 (no proxy): DK's "resting limit bids just under the obvious overnight/session low" (doc 234) ----
U_h = U.hour.values; U_m = U.minute.values
def low_events(lookback=96, within=0.03):
    ev = []
    for j in np.where((U_h == 7) & (U_m == 0))[0]:                   # each London morning, 07:00 UTC
        if j < 2000 or j >= N - 96 * 8: continue
        lvl = L[j - lookback:j].min() * 0.997                         # just under the obvious low
        if C[j - 1] <= lvl * (1 + within): ev.append((j, lvl, 0.0, 0.0))
    return pd.DataFrame(ev, columns=["j", "lvl", "tgt", "near"])
def run_events(EV, opt, label):
    global E
    keep = E; E = EV
    try: return run(opt, label)
    finally: E = keep
