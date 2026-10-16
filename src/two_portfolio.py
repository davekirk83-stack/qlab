"""
THE TWO-SIDED BOOK ON THE EQUITY CURVE — the open item from doc 110.

Doc 110 established the two-sided range book on per-trade numbers: shorts
+0.4187% against longs +0.3955%, breadth 1.96x, and the two sides correlating
+0.005. What it never did was run the thing through a portfolio with finite
capital, which is where three questions live that per-trade cannot answer:

  SLOT CONTENTION. Doubling the signals does not double the trades taken if
  there are only 40 slots. The long and short sides compete for the same
  capital, and the second side may simply be crowding out the first.

  DOES THE DIVERSIFICATION SURVIVE SIZING? A +0.005 correlation between trade
  returns is not the same as a +0.005 correlation between daily P&L. Trades
  overlap in time; the equity curve is what feels that.

  THE ASYMMETRIC TAIL UNDER LEVERAGE. The short side's worst trade is -25.0%,
  which at 3x is -75% of posted margin. Per-trade reporting cannot say whether
  that lands on a day when five other shorts are also open.

CONFIGURATIONS
  long only                the registered book
  two-sided, shared slots  both sides competing for the same 40
  two-sided, split slots   20 reserved for each side, so neither crowds out
                           the other
  two-sided + margin stop  the 15% cap from doc 109 applied to both sides
  two-sided, short at half size   the asymmetric tail answered with size

All with worst-tick break fills (doc 107) and the containment switch (doc 105).
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import regime_detect as RD

MK, TAKER, SLIP = RD.MK, RD.TAKER, RD.SLIP
BID, ASK, CAP = RD.BID, RD.ASK, 48
START, FUND = 2000.0, 0.0001


def long_trades(d, allow, ema, lo_b, hi_b, a, sym, mstop):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); out = []; inv = []; oi = 0; sold = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        if inv and mstop is not None:
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            st = cost*(1-mstop/3.0)
            if L[i] <= st:
                out.append((sym, d.index[oi], d.index[i],
                            (st*(1-SLIP-TAKER))/(cost*(1+MK))-1, "L"))
                inv = []; sold = set(); continue
        broke = C[i] < lo_b[i]-1.5*a[i] or C[i] > hi_b[i]+1.5*a[i]
        if inv and (i-oi >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            out.append((sym, d.index[oi], d.index[i],
                        (L[i]*(1-SLIP-TAKER))/(cost*(1+MK))-1, "L"))
            inv = []; sold = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in sold: continue
                tgt = ema[i] if lvl == "mid" else hi_b[i]+lvl*a[i]
                if H[i] >= tgt and inv:
                    sz = sum(s for _, s in inv); sell = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    out.append((sym, d.index[oi], d.index[i],
                                ((tgt*(1-MK))/(cost*(1+MK))-1)*(sell/sz), "L"))
                    sold.add(k)
                    inv = [(p, s*(1-sell/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv: sold = set()
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = lo_b[i]+off*a[i]
                if L[i] < p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: oi = i
    return out


def short_trades(d, allow, ema, lo_b, hi_b, a, sym, mstop):
    C, H, L = d.close.values, d.high.values, d.low.values
    n = len(C); out = []; inv = []; oi = 0; cov = set()
    for i in range(250, n-1):
        if not np.isfinite(a[i]) or a[i] <= 0: continue
        ok = bool(allow[i]) if np.isfinite(allow[i]) else False
        if inv and mstop is not None:
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            st = cost*(1+mstop/3.0)
            if H[i] >= st:
                f = FUND*(i-oi)/32.0
                out.append((sym, d.index[oi], d.index[i],
                            (cost*(1-MK))/(st*(1+SLIP+TAKER))-1-f, "S"))
                inv = []; cov = set(); continue
        broke = C[i] > hi_b[i]+1.5*a[i] or C[i] < lo_b[i]-1.5*a[i]
        if inv and (i-oi >= CAP or broke or not ok):
            sz = sum(s for _, s in inv); cost = sum(p*s for p, s in inv)/sz
            f = FUND*(i-oi)/32.0
            out.append((sym, d.index[oi], d.index[i],
                        (cost*(1-MK))/(H[i]*(1+SLIP+TAKER))-1-f, "S"))
            inv = []; cov = set(); continue
        if not ok: continue
        if inv:
            for k, (frac, lvl) in enumerate(ASK):
                if k in cov: continue
                tgt = ema[i] if lvl == "mid" else lo_b[i]-lvl*a[i]
                if L[i] <= tgt and inv:
                    sz = sum(s for _, s in inv); buy = min(sz*frac, sz)
                    cost = sum(p*s for p, s in inv)/sz
                    f = FUND*(i-oi)/32.0
                    out.append((sym, d.index[oi], d.index[i],
                                ((cost*(1-MK))/(tgt*(1+MK))-1-f)*(buy/sz), "S"))
                    cov.add(k)
                    inv = [(p, s*(1-buy/sz)) for p, s in inv]
                    inv = [(p, s) for p, s in inv if s > 1e-9]
                    if not inv: cov = set()
        held = sum(s for _, s in inv)
        if held < 1.0:
            for frac, off in BID:
                p = hi_b[i]-off*a[i]
                if H[i] > p and held+frac <= 1.0+1e-9:
                    inv.append((p, frac)); held += frac
                    if len(inv) == 1: oi = i
    return out


def simulate(S, slots, lev, split=False, short_scale=1.0):
    S = S.sort_values("entry").reset_index(drop=True)
    eq = START; openp = []; curve = []; ei = 0
    taken = {"L": 0, "S": 0}; skipped = 0
    cap_side = {"L": slots//2, "S": slots//2} if split else None
    for t in sorted(set(S.entry) | set(S.exit)):
        still = []
        for p in openp:
            if p["exit"] <= t: eq += p["margin"]*p["ret"]*lev*p["sc"]
            else: still.append(p)
        openp = still
        if eq <= 0: return None, taken, skipped
        while ei < len(S) and S.entry.iloc[ei] <= t:
            r = S.iloc[ei]; ei += 1
            side = r["side"]
            if split:
                if sum(1 for p in openp if p["side"] == side) >= cap_side[side]:
                    skipped += 1; continue
            elif len(openp) >= slots:
                skipped += 1; continue
            sc = short_scale if side == "S" else 1.0
            openp.append({"exit": r["exit"], "ret": r["ret"], "side": side,
                          "margin": eq/slots, "sc": sc})
            taken[side] += 1
        curve.append((t, eq))
    if not curve: return None, taken, skipped
    E = pd.Series([c[1] for c in curve], index=[c[0] for c in curve])
    E = E[~E.index.duplicated(keep="last")]
    yrs = (E.index[-1]-E.index[0]).days/365.25
    if yrs <= 0 or E.iloc[-1] <= 0: return None, taken, skipped
    dly = E.resample("1D").last().ffill().pct_change().dropna()
    return {"cagr": (E.iloc[-1]/START)**(1/yrs)-1,
            "dd": (E/E.cummax()-1).min(),
            "sharpe": dly.mean()/dly.std()*np.sqrt(365) if dly.std() > 0 else np.nan,
            "final": E.iloc[-1], "worst_day": dly.min(),
            "daily": dly}, taken, skipped


if __name__ == "__main__":
    data = RD.load()
    base, stopped = [], []
    for s, d in data.items():
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        al = (v > v.expanding(500).median()).values
        base += long_trades(d, al, ema, lo_b, hi_b, a, s, None)
        base += short_trades(d, al, ema, lo_b, hi_b, a, s, None)
        stopped += long_trades(d, al, ema, lo_b, hi_b, a, s, 0.15)
        stopped += short_trades(d, al, ema, lo_b, hi_b, a, s, 0.15)
    cols = ["sym", "entry", "exit", "ret", "side"]
    S = pd.DataFrame(base, columns=cols)
    S = S[np.isfinite(S.ret)]
    SS = pd.DataFrame(stopped, columns=cols)
    SS = SS[np.isfinite(SS.ret)]
    L = S[S.side == "L"]
    print(f"{len(data)} symbols. {len(L):,} long signals, "
          f"{len(S)-len(L):,} short signals.\n")

    for lev in (1, 3):
        print("="*100)
        print(f"TWO-SIDED RANGE BOOK ON THE EQUITY CURVE — 40 slots, {lev}x, $2,000")
        print("="*100)
        print(f"  {'configuration':<34}{'taken L':>9}{'taken S':>9}{'skipped':>9}"
              f"{'CAGR':>9}{'maxDD':>9}{'Sharpe':>8}{'worst day':>11}{'final':>12}")
        CFG = [("long only (registered)", L, False, 1.0),
               ("two-sided, shared slots", S, False, 1.0),
               ("two-sided, split 20/20", S, True, 1.0),
               ("two-sided, short at half size", S, False, 0.5),
               ("two-sided + 15% margin stop", SS, False, 1.0),
               ("two-sided + stop, split 20/20", SS, True, 1.0)]
        for lbl, G, sp, sc in CFG:
            if len(G) < 200: continue
            r, tk, sk = simulate(G, 40, lev, split=sp, short_scale=sc)
            if r is None:
                print(f"  {lbl:<34}{'':>27}  WIPED OUT"); continue
            print(f"  {lbl:<34}{tk['L']:>9,}{tk['S']:>9,}{sk:>9,}"
                  f"{r['cagr']*100:>8.1f}%{r['dd']*100:>8.1f}%{r['sharpe']:>8.2f}"
                  f"{r['worst_day']*100:>+10.1f}%{r['final']:>11,.0f}")
        print()

    print("="*100)
    print("DOES THE DIVERSIFICATION SURVIVE AT THE DAILY LEVEL?")
    print("="*100)
    rL, _, _ = simulate(S[S.side == "L"], 40, 1)
    rS, _, _ = simulate(S[S.side == "S"], 40, 1)
    if rL and rS:
        j = pd.concat([rL["daily"].rename("L"), rS["daily"].rename("S")],
                      axis=1).dropna()
        print(f"  Correlation of DAILY P&L between the two sides: "
              f"{j.L.corr(j.S):+.3f}   ({len(j):,} days)")
        print(f"  Doc 110 reported +0.005 on per-trade returns. Trades overlap in")
        print(f"  time, so the daily number is the one the equity curve feels.")
        both = j[(j.L < 0) & (j.S < 0)]
        print(f"  Days both sides lost: {len(both)/len(j)*100:.0f}% "
              f"(independent would be ~{(j.L<0).mean()*(j.S<0).mean()*100:.0f}%)")
