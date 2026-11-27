"""BTC short-side swing book (DK 27 Nov 16:23, item 1). The one piece of DK's method that tested positive as a whole (doc 270):
resting SELLS in chunks just above the obvious 24h high, "a third off" on the first drop, then the stop to breakeven ("it's a free swing").
Full test: level source (24h high / estimated short-liquidation clusters), context, partial and target levels, venue costs, both halves, years.
Venue costs (shorts need IG or PrimeXBT, not Revolut X spot): 'perp' = maker 0.02% / taker 0.05% + 0.03% slip;
'ig' = 0.1% spread round trip on every trade + 0.05%/day holding cost (IG crypto CFD overnight funding is a sensitivity, not a quote).
Result = % of the ladder budget per campaign."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, io, contextlib, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import dk_book as D
H, L, C, N, IX, BULL, S = D.H, D.L, D.C, D.N, D.IX, D.BULL, D.LB.S
lo72 = pd.Series(L).rolling(288, min_periods=50).min().values
COSTS = {"perp": dict(maker=0.0002, taker=0.0005, slip=0.0003, spread=0.0, day=0.0), "ig": dict(maker=0.0, taker=0.0, slip=0.0, spread=0.001, day=0.0005)}
def campaign(j, lvl, o, cs):
    rungs = [lvl * f for f in (1.0, 1.01, 1.02, 1.03)]; wts = (0.1, 0.2, 0.3, 0.4)
    stop = rungs[-1] * (1 + o["stop"]); kend = min(N - 1, j + 96 * o["days"]); lastb = min(N - 1, j + 192); done = [False] * 4
    qty = cost = pnl = 0.0; part = False; ncpi = D.next_cpi(j); k1 = None
    fee_in = cs["maker"] + cs["spread"] / 2
    def out(px, k, market):
        f = (cs["taker"] + cs["slip"]) if market else cs["maker"]
        hold = 0 if k1 is None else (k - k1) / 96 * cs["day"]
        return pnl + qty * (avg - px * (1 + f + cs["spread"] / 2) - avg * hold)
    for k in range(j, kend + 1):
        for r in range(4):
            if not done[r] and k <= lastb and H[k] >= rungs[r] and not D.LB.CPI_BLOCK[k]:
                done[r] = True; qty += wts[r]; cost += wts[r] * rungs[r] * (1 - fee_in); k1 = k1 if k1 is not None else k
        if qty <= 0:
            if k > lastb: return None
            continue
        avg = cost / qty
        if H[k] >= stop: return out(stop, k, True) / lvl * 100, k
        if k >= ncpi - 1: return out(C[k], k, True) / lvl * 100, k
        if o["part"] and not part and L[k] <= avg * (1 - o["part"]) and k > j:
            q = qty * o["part_frac"]; px = avg * (1 - o["part"]); pnl += q * (avg - px * (1 + cs["maker"] + cs["spread"] / 2)); qty -= q; cost = avg * qty; part = True
            if o["be"]: stop = min(stop, avg)
        if k > j and L[k] <= avg * (1 - o["tgt"]): return out(avg * (1 - o["tgt"]), k, False) / lvl * 100, k
    avg = cost / qty; return out(C[kend], kend, True) / lvl * 100, kend
def events(src):
    ev = []
    if src == "24h high":
        for j in np.where((D.U_h == 7) & (D.U_m == 0))[0]:
            if 2000 <= j < N - 96 * 8:
                lvl = H[j - 96:j].max() * 1.003
                if C[j - 1] >= lvl * 0.97: ev.append((j, lvl))
    else:   # estimated short-liquidation clusters above price (doc 224), first tap
        for k in np.argsort(S.TS):
            j = S.TS[k]
            if 2000 <= j < N - 96 * 8: ev.append((j, S.LS[k]))
    return ev
def run(o, ctx, src, venue):
    rows = []; busy = -1; cs = COSTS[venue]
    for j, lvl in events(src):
        if j <= busy: continue
        bear = not BULL[j]; pump = C[j] >= lo72[j] * 1.06
        if ctx == "bear or pump" and not (bear or pump): continue
        if ctx == "bear" and not bear: continue
        if ctx == "pump" and not pump: continue
        r = campaign(j, lvl, o, cs)
        if r is None: continue
        rows.append((IX[j], r[0])); busy = max(r[1], j + 96)
    t = pd.Series([x for _, x in rows], index=pd.to_datetime([a for a, _ in rows])).sort_index()
    if len(t) < 20: return None
    y = t.groupby(t.index.year).sum(); h = len(t) // 2; eq = t.cumsum()
    return dict(n=len(t), win=round((t > 0).mean(), 2), mean=round(t.mean(), 3), h1=round(t[:h].mean(), 3), h2=round(t[h:].mean(), 3),
                last12m=round(t[t.index >= t.index[-1] - pd.Timedelta("365D")].mean(), 3), yrs_pos=f"{(y>0).sum()}/{len(y)}",
                years=" ".join(f"{k}:{v:+.0f}" for k, v in y.items()), total=round(t.sum(), 1), max_dd=round((eq - eq.cummax()).min(), 1))
BASE = dict(stop=0.01, days=7, part=0.015, part_frac=1/3, be=True, tgt=0.03)
if __name__ == "__main__":
    rows = []
    for src in ("24h high", "short clusters"):
        for ctx in ("bear or pump", "bear", "pump", "all"):
            for venue in ("perp", "ig"):
                r = run(BASE, ctx, src, venue)
                if r: rows.append(dict(src=src, ctx=ctx, venue=venue, variant="base (DK free swing)", **r)); print(rows[-1], flush=True)
    best_src, best_ctx = "24h high", "bear or pump"
    for lab, ch in (("partial at -1%", dict(part=0.01)), ("partial at -2%", dict(part=0.02)), ("half off, not a third", dict(part_frac=0.5)),
                    ("target -4%", dict(tgt=0.04)), ("target -2%", dict(tgt=0.02)), ("no breakeven", dict(be=False)), ("no partial", dict(part=0)),
                    ("stop 2% over top bid", dict(stop=0.02)), ("3-day limit", dict(days=3))):
        for venue in ("perp", "ig"):
            r = run(dict(BASE, **ch), best_ctx, best_src, venue)
            if r: rows.append(dict(src=best_src, ctx=best_ctx, venue=venue, variant=lab, **r)); print(rows[-1], flush=True)
    R = pd.DataFrame(rows); R.to_csv("runs/research/btc_short_book.csv", index=False); pd.set_option("display.width", 300)
    print(R.drop(columns=["years"]).to_string(index=False))
