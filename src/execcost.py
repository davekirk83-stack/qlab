"""
DEPTH AS AN EXECUTION TOOL — what an order ACTUALLY costs.

DK: "Can we use this liquidity as a tool in our work?"

It does not predict direction (doc 60). But direction was never the only thing
worth knowing, and depth answers something we have been GUESSING at all along.

THE GUESS WE HAVE BEEN MAKING
Every registered book carries an assumed slippage of 10bp. That number has
decided verdicts:
  doc 51  VWAP rejected on costs
  doc 52  cascade found at risk on costs, then recovered
  doc 56  cascade breakeven computed at ~24bp of slippage against a 0.96%
          entry bar -- but 24bp was an inference, not a measurement
A single assumed constant has been the hinge, and we have a year of real book
depth sitting on disk that can replace it with an actual number.

HOW THE COST IS COMPUTED
Binance bookDepth gives resting notional within 0.2, 1, 2, 3, 4 and 5 percent
of mid, each side. Cumulate outward and you have the fill curve: to absorb a
notional N, price must travel to the band where cumulative depth reaches N.
Interpolating between bands gives the penetration depth, and the average fill
price of a market order that size is roughly half that penetration away from
mid -- the standard linear-book approximation, which is conservative because
real books are denser near touch than the 0.2% band suggests.

    slippage(N) ~ 0.5 * depth_percent_required(N)

THE QUESTION THAT MATTERS MOST
Not "what does an order cost on average" but "what does it cost WHEN WE TRADE".
The cascade book buys after a 3% collapse. That is precisely when the book is
thinnest and everyone else is hitting it. If execution cost at cascade lows is
double the average, the cascade's margin is not what doc 56 says it is.

So the comparison is explicitly conditional:
    baseline     a random bar
    cascade      the bar after a 3% five-minute collapse, which is the
                 registered book's actual entry condition
    recovery     the base-then-bid entry point the book really uses (doc 56),
                 which is some bars LATER and may be a different world

CAPACITY
The same curve answers a question never asked in this programme: how much
money can each book take before it eats its own edge? Reported as the notional
at which slippage reaches 10bp, 25bp and 50bp.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd

DEPTH = "/home/claude/qlab/data_depth_full"
M1 = "/home/claude/qlab/data_1m"
BANDS = [0.2, 1.0, 2.0, 3.0, 4.0, 5.0]
SIZES = [1e4, 5e4, 1e5, 5e5, 1e6, 5e6]


def load(sym):
    p, m = f"{DEPTH}/{sym}.csv", f"{M1}/{sym}.csv"
    if not (os.path.exists(p) and os.path.exists(m)):
        return None
    d = pd.read_csv(p, parse_dates=["ts"]).set_index("ts").sort_index()
    k = pd.read_csv(m); k["dt"] = pd.to_datetime(k.t, unit="ms")
    k = k.set_index("dt").sort_index(); k = k[~k.index.duplicated()]
    px = k.resample("5min").agg(close=("close", "last"), low=("low", "min")).dropna()
    j = d.join(px, how="inner")
    return j if len(j) > 5000 else None


def cum_bid(j):
    """Cumulative resting notional on the BID side, outward by band."""
    out = np.zeros((len(j), len(BANDS)))
    run = np.zeros(len(j))
    for bi, b in enumerate(BANDS):
        col = f"d-{b:g}"
        if col in j.columns:
            run = run + np.nan_to_num(j[col].values)
        out[:, bi] = run
    return out


def slip_bp(cum, size):
    """Penetration depth in percent for an order of `size`, then halve it
    for the average fill. Returns basis points. NaN if the book cannot fill."""
    n = cum.shape[0]
    out = np.full(n, np.nan)
    for bi, b in enumerate(BANDS):
        need = np.isnan(out) & (cum[:, bi] >= size)
        if not need.any():
            continue
        prev_d = BANDS[bi - 1] if bi else 0.0
        prev_c = cum[:, bi - 1] if bi else np.zeros(n)
        span = np.maximum(cum[:, bi] - prev_c, 1e-9)
        frac = np.clip((size - prev_c) / span, 0, 1)
        out[need] = (prev_d + frac * (b - prev_d))[need]
    return out * 100 / 2.0      # percent -> bp, halved for average fill


def capacity(cum_row, target_bp):
    """Notional fillable within target_bp of average slippage."""
    pct = target_bp * 2 / 100.0
    for bi, b in enumerate(BANDS):
        if b >= pct:
            prev_d = BANDS[bi - 1] if bi else 0.0
            prev_c = cum_row[bi - 1] if bi else 0.0
            if b <= prev_d:
                return prev_c
            f = (pct - prev_d) / (b - prev_d)
            return prev_c + f * (cum_row[bi] - prev_c)
    return cum_row[-1]


if __name__ == "__main__":
    print("EXECUTION COST FROM REAL BOOK DEPTH — replacing the 10bp assumption\n")
    rows, caps = [], []
    for f in sorted(glob.glob(f"{DEPTH}/*.csv")):
        s = os.path.basename(f)[:-4]
        j = load(s)
        if j is None:
            continue
        cum = cum_bid(j)
        C = j.close.values
        n = len(C)
        # cascade condition: the registered book's actual trigger
        r5 = np.full(n, np.nan); r5[1:] = C[1:] / C[:-1] - 1
        casc = np.flatnonzero(r5 <= -0.03)
        casc = casc[(casc > 288) & (casc < n - 100)]
        # the entry the book really uses: ~20 bars after the low, post-base
        rec = casc + 20
        rec = rec[rec < n]
        base = np.arange(288, n - 100, 72)
        for size in SIZES:
            sb = slip_bp(cum, size)
            for lab, idx in (("baseline", base), ("cascade low", casc),
                             ("post-base entry", rec)):
                if len(idx) < 20:
                    continue
                v = sb[idx]; v = v[np.isfinite(v)]
                unfill = 1 - len(v) / len(idx)
                if len(v) < 20:
                    continue
                rows.append(dict(sym=s, size=size, cond=lab,
                                 med=np.median(v), p90=np.percentile(v, 90),
                                 unfill=unfill))
        for t in (10, 25, 50):
            cc = np.array([capacity(cum[i], t) for i in base[::8]])
            caps.append(dict(sym=s, bp=t, med=np.median(cc)))

    R = pd.DataFrame(rows); K = pd.DataFrame(caps)

    print("=" * 92)
    print("  MEDIAN SLIPPAGE (bp) BY ORDER SIZE AND CONDITION — 20 symbols, 1 year")
    print("=" * 92)
    print(f"  {'order':>10}{'baseline':>12}{'cascade low':>14}"
          f"{'post-base':>12}{'casc/base':>11}{'unfilled@casc':>15}")
    for size in SIZES:
        S = R[R["size"] == size]
        g = {c: S[S.cond == c].med.median() for c in
             ("baseline", "cascade low", "post-base entry")}
        uf = S[S.cond == "cascade low"].unfill.median()
        if not np.isfinite(g["baseline"]):
            continue
        ratio = g["cascade low"] / g["baseline"] if g["baseline"] else np.nan
        print(f"  ${size:>9,.0f}{g['baseline']:>12.1f}{g['cascade low']:>14.1f}"
              f"{g['post-base entry']:>12.1f}{ratio:>10.2f}x{uf*100:>14.1f}%")

    print("\n" + "=" * 92)
    print("  CAPACITY — notional absorbable within a given slippage, median bar")
    print("=" * 92)
    print(f"  {'symbol':<12}{'@10bp':>14}{'@25bp':>14}{'@50bp':>14}")
    piv = K.pivot_table(index="sym", columns="bp", values="med")
    for s in piv.index:
        print(f"  {s:<12}" + "".join(f"${piv.loc[s,t]:>13,.0f}" for t in (10, 25, 50)))
    print(f"\n  {'MEDIAN COIN':<12}" +
          "".join(f"${piv[t].median():>13,.0f}" for t in (10, 25, 50)))
    print(f"  {'BTC':<12}" +
          "".join(f"${piv.loc['BTCUSDT',t]:>13,.0f}" for t in (10, 25, 50))
          if "BTCUSDT" in piv.index else "")


# ---------------------------------------------------------------- stress
def stress_report():
    SIZES=[5e4,1e5,5e5]
    rows=[]
    for f in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s=os.path.basename(f)[:-4]; j=E.load(s)
        if j is None: continue
        cum=E.cum_bid(j); C=j.close.values; n=len(C)
        r5=np.full(n,np.nan); r5[1:]=C[1:]/C[:-1]-1
        sets={"baseline":np.arange(288,n-100,72)}
        for th,lab in ((-0.01,"drop 1%"),(-0.02,"drop 2%"),(-0.03,"cascade 3%")):
            k=np.flatnonzero(r5<=th); sets[lab]=k[(k>288)&(k<n-100)]
            sets[lab+" +20b"]=np.clip(sets[lab]+20,0,n-1)
        for size in SIZES:
            sb=E.slip_bp(cum,size)
            for lab,idx in sets.items():
                if len(idx)==0: continue
                v=sb[idx]; fin=np.isfinite(v)
                rows.append(dict(sym=s,size=size,cond=lab,n=len(idx),
                                 unfill=1-fin.mean(),
                                 med=np.median(v[fin]) if fin.sum() else np.nan))
    R=pd.DataFrame(rows)
    print("POOLED ACROSS 20 SYMBOLS — median slippage (bp), bid side\n")
    order=["baseline","drop 1%","drop 1% +20b","drop 2%","drop 2% +20b",
           "cascade 3%","cascade 3% +20b"]
    for size in SIZES:
        S=R[R["size"]==size]
        print(f"  order ${size:,.0f}")
        b=None
        for c in order:
            T=S[S.cond==c]
            if not len(T): continue
            w=T.n.values; m=np.nansum(T.med.values*w)/np.nansum(w)
            uf=np.nansum(T.unfill.values*w)/np.nansum(w)
            if c=="baseline": b=m
            r=f"{m/b:5.2f}x" if b else "   -  "
            print(f"    {c:<18} events {int(T.n.sum()):>6}   {m:>6.1f}bp  {r}"
                  f"   unfillable {uf*100:4.1f}%")
        print()


def capacity_report():
    # doc 56: edge +0.316pp over control, 65.8% win, stop 2.63% of price,
    # maker 2bp in, maker 2bp on target, taker 5bp + slippage on the stop.
    EDGE_BP, WIN, STOPPCT = 31.6, 0.658, 2.63
    SIZES=[5e4,1e5,2.5e5,5e5,1e6,2.5e6,5e6]
    
    # stop-out condition: price still falling -- measure the book DURING a drop
    rows=[]
    for f in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s=os.path.basename(f)[:-4]; j=E.load(s)
        if j is None: continue
        cum=E.cum_bid(j); C=j.close.values; n=len(C)
        r5=np.full(n,np.nan); r5[1:]=C[1:]/C[:-1]-1
        k=np.flatnonzero(r5<=-0.015); k=k[(k>288)&(k<n-100)]
        if len(k)==0: continue
        for size in SIZES:
            sb=E.slip_bp(cum,size); v=sb[k]; v=v[np.isfinite(v)]
            if len(v): rows.append(dict(sym=s,size=size,n=len(v),med=np.median(v)))
    R=pd.DataFrame(rows)
    
    print("CASCADE v3 CAPACITY — cost of the STOP exit at size\n")
    print("  Entry is a resting maker bid, so entry pays no slippage.")
    print("  Stops are taker, and fire while price is still falling.\n")
    print(f"  {'position':>12}{'stop slip':>12}{'cost/trade':>13}"
          f"{'as % of edge':>15}{'net edge':>12}")
    for size in SIZES:
        S=R[R["size"]==size]
        if not len(S): continue
        w=S.n.values; slip=np.sum(S.med.values*w)/np.sum(w)
        # expected cost per trade, in bp of price
        cost = WIN*2 + (1-WIN)*(5+slip) + 2          # target maker, stop taker+slip, entry maker
        base = WIN*2 + (1-WIN)*(5+10) + 2            # doc 56's assumption: 10bp slip
        extra = cost - base
        net = EDGE_BP - extra
        print(f"  ${size:>11,.0f}{slip:>11.1f}bp{cost:>12.1f}bp"
              f"{extra/EDGE_BP*100:>14.1f}%{net:>11.1f}bp")
    print(f"\n  (doc 56 assumed 10bp stop slippage; edge measured at {EDGE_BP}bp/trade)")
    print(f"  Stop is {STOPPCT}% of price, so even 50bp of slippage is "
          f"{50/100/STOPPCT:.2f}R — fees stay small in R terms.")
