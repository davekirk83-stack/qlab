"""DK book, both directions (his documented shorts: "I swung short at 64792", "short from 64600", "I went short at 61825 ... stops at b/e
... It's a free swing", a third off near the next liquidity). Mirror of dk_book.py: resting SELLS in chunks just above the obvious high
(24h high +0.3%, +1%, +2%, +3%; 10/20/30/40) when BTC is below its 200-day or has pumped >= 6% off its 72h low; stop 1% above the top rung;
a third off at -1.5%; then stop to breakeven; rest at -3%; 7 days; flat before CPI. Long side = dk_book.py 'lows' version.
Shorts need a venue that can short (IG BTC CFD / PrimeXBT, not Revolut X spot): costed at the same 0.09% + 0.05% per market leg (maker legs 0)."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import dk_book as D
H, L, C, N, U, IX = D.H, D.L, D.C, D.N, D.U, D.IX; TAKER, SLIP = D.TAKER, D.SLIP
lo72 = pd.Series(L).rolling(288, min_periods=50).min().values
def short_campaign(j, lvl, opt):
    rungs = [lvl * f for f in (1.0, 1.01, 1.02, 1.03)] if opt["ladder"] else [lvl]; wts = (0.1, 0.2, 0.3, 0.4) if opt["ladder"] else (1.0,)
    stop = max(rungs) * 1.01; kend = min(N - 1, j + 96 * 7); lastb = min(N - 1, j + 192); done = [False] * len(rungs)
    qty = cost = pnl = 0.0; part = False; ncpi = D.next_cpi(j)
    for k in range(j, kend + 1):
        for r in range(len(rungs)):
            if not done[r] and k <= lastb and H[k] >= rungs[r] and not D.LB.CPI_BLOCK[k]: done[r] = True; qty += wts[r]; cost += wts[r] * rungs[r]
        if qty <= 0:
            if k > lastb: return None
            continue
        avg = cost / qty
        if H[k] >= stop: return (pnl + qty * (avg - stop * (1 + SLIP) * (1 + TAKER))) / lvl * 100, k
        if k >= ncpi - 1: return (pnl + qty * (avg - C[k] * (1 + SLIP) * (1 + TAKER))) / lvl * 100, k
        if opt["part"] and not part and L[k] <= avg * 0.985 and k > j:
            q = qty / 3; pnl += q * (avg * 0.015); qty -= q; cost = avg * qty; part = True
            if opt["be"]: stop = min(stop, avg)
        if k > j and L[k] <= avg * 0.97: return (pnl + qty * (avg * 0.03)) / lvl * 100, k
    avg = cost / qty; return (pnl + qty * (avg - C[kend] * (1 + SLIP) * (1 + TAKER))) / lvl * 100, kend
def high_events(lookback=96, within=0.03):
    ev = []
    for j in np.where((D.U_h == 7) & (D.U_m == 0))[0]:
        if j < 2000 or j >= N - 96 * 8: continue
        lvl = H[j - lookback:j].max() * 1.003
        if C[j - 1] >= lvl * (1 - within): ev.append((j, lvl))
    return ev
def run_short(opt, label, ctx="bear_or_pump"):
    rows = []; busy = -1
    for j, lvl in high_events():
        if j <= busy: continue
        bear = not D.BULL[j]; pump = C[j] >= lo72[j] * 1.06
        if ctx == "bear_or_pump" and not (bear or pump): continue
        if ctx == "bear" and not bear: continue
        r = short_campaign(j, lvl, opt)
        if r is None: continue
        rows.append((IX[j], r[0])); busy = max(r[1], j + 96)
    return pd.Series([x for _, x in rows], index=pd.to_datetime([a for a, _ in rows]))
def summ(t, label):
    y = t.groupby(t.index.year).sum(); h = len(t) // 2; eq = t.sort_index().cumsum()
    return dict(version=label, n=len(t), win=round((t > 0).mean(), 2), mean_pct=round(t.mean(), 3), h1=round(t.sort_index()[:h].mean(), 3), h2=round(t.sort_index()[h:].mean(), 3),
                yrs=" ".join(f"{k}:{v:+.0f}" for k, v in y.items()), total=round(t.sum(), 1), max_dd=round((eq - eq.cummax()).min(), 1))
if __name__ == "__main__":
    full = dict(D.BASE, near=False); simple = dict(full, part=False, be=False, add=False, reentry=False)
    EV = D.low_events(); rows = []
    _, longs_full = D.run_events(EV, full, "x"); _, longs_simple = D.run_events(EV, simple, "x")
    for ctx in ("bear_or_pump", "bear"):
        sf = run_short(full, "", ctx); ss = run_short(simple, "", ctx)
        rows += [summ(sf, f"SHORTS full rules ({ctx})"), summ(ss, f"SHORTS ladder + TP3% ({ctx})"),
                 summ(pd.concat([longs_full, sf]), f"DK BOOK BOTH SIDES, full rules ({ctx})"), summ(pd.concat([longs_simple, ss]), f"DK BOOK BOTH SIDES, ladder + TP3% ({ctx})")]
    rows += [summ(longs_full, "LONGS full rules"), summ(longs_simple, "LONGS ladder + TP3%")]
    R = pd.DataFrame(rows); R.to_csv("runs/research/dk_book_2side.csv", index=False); pd.set_option("display.width", 300); print(R.to_string(index=False))
