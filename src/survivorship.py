"""
HOW MUCH OF THE BOOK'S RESULT IS SURVIVORSHIP?

The 263-product universe was built from what Coinbase lists TODAY. Everything
delisted is invisible, and a dip-buying mean-reversion book is exactly the
strategy that bias flatters: the coins that dipped and never came back are not
in the file. The delisted data cannot be recovered from the exchange, so the
distortion has to be bounded another way.

THE TEST. If the edge is really survivorship, it should depend on how the
product eventually turned out. Buying dips works beautifully on something that
tripled over the sample and terribly on something that fell 95%. So:

  1. rank products by their TOTAL return over their own history
  2. run the book separately in each tercile
  3. if the edge is concentrated in the winners, the result is selection; if it
     is roughly flat across terciles - and in particular if it survives in the
     BOTTOM tercile, products that lost most of their value - then the
     mechanism is not just riding survivors

The bottom tercile is the real proxy for the delisted population. Products that
fell 80-95% and stayed listed are the closest thing available to the ones that
fell 95% and got removed.

  4. separately: an EARLY-COHORT test. Restrict to products that already
     existed in 2021 and run only on 2022 onwards. That removes the "listed
     recently because it is doing well" channel, which is the other half of
     the bias.

Neither test can recover the truly dead. Both bound how much of the result
depends on knowing the ending.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import system_on_history as SYS


def product_outcomes(data):
    rows = []
    for s, d in data.items():
        tot = float(d.close.iloc[-1] / d.close.iloc[0] - 1)
        dd = float((d.close / d.close.cummax() - 1).min())
        rows.append(dict(sym=s, total=tot, maxdd=dd,
                         start=d.index[0], years=(d.index[-1]-d.index[0]).days/365.25))
    return pd.DataFrame(rows).set_index("sym")


def block(G, tag, extra=""):
    if len(G) < 60:
        print(f"  {tag:<34}only {len(G)} trades"); return None
    m = G.ret.mean(); t = m/(G.ret.std(ddof=1)/np.sqrt(len(G)))
    c = G.ctrl.dropna()
    edge = m - (c.mean() if len(c) else 0)
    se = np.sqrt(G.ret.var(ddof=1)/len(G) + (c.var(ddof=1)/len(c) if len(c) else 0))
    print(f"  {tag:<34}n={len(G):>6}  {m*100:>+7.3f}%  t={t:>+6.2f}  "
          f"edge {edge*100:>+7.3f}% (t={edge/se:>+5.2f})  "
          f"win {(G.ret>0).mean()*100:>3.0f}%  {extra}")
    return dict(n=len(G), mean=m, t=t, edge=edge, te=edge/se)


if __name__ == "__main__":
    data = SYS.load()
    O = product_outcomes(data)
    print(f"{len(data)} products, median total return "
          f"{O.total.median()*100:+.0f}%, median max drawdown {O.maxdd.median()*100:.0f}%\n")
    T = SYS.trades(data)
    T["yr"] = T.ts.dt.year
    T = T.join(O, on="sym")

    print("=" * 100)
    print("TEST 1 — BY THE PRODUCT'S EVENTUAL OUTCOME")
    print("If the edge is survivorship, it lives in the winners and dies in the losers.\n")
    T["terc"] = pd.qcut(T.total.rank(method="first"), 3, labels=["bottom", "middle", "top"])
    res = {}
    for k in ["bottom", "middle", "top"]:
        G = T[T.terc == k]
        syms = G.sym.nunique()
        med = O.loc[G.sym.unique()].total.median()
        res[k] = block(G, f"{k} third by total return",
                       f"{syms} products, median outcome {med*100:+.0f}%")
    print()
    # the harshest cut: products that lost most of their value
    for thr in (-0.80, -0.90):
        bad = O[O.total <= thr].index
        G = T[T.sym.isin(bad)]
        block(G, f"products down {abs(thr)*100:.0f}%+ over their life",
              f"{G.sym.nunique()} products")

    print("\n" + "=" * 100)
    print("TEST 2 — EARLY COHORT ONLY")
    print("Products already listed before 2021, traded from 2022 onwards. Removes")
    print("the 'listed recently because it is doing well' channel.\n")
    early = O[O.start < pd.Timestamp("2021-01-01")].index
    print(f"  early cohort: {len(early)} products")
    G = T[T.sym.isin(early) & (T.yr >= 2022)]
    block(G, "early cohort, 2022 onwards")
    for y in sorted(G.yr.unique()):
        block(G[G.yr == y], f"  {y}")

    print("\n" + "=" * 100)
    print("TEST 3 — DOES IT WORK ON THE WORST YEARS OF THE WORST PRODUCTS?")
    print("The closest available proxy for the delisted population.\n")
    worst = O[O.total <= O.total.quantile(0.2)].index
    G = T[T.sym.isin(worst)]
    block(G, f"bottom quintile by outcome ({len(worst)} products)")
    for y in sorted(G.yr.unique()):
        if (G.yr == y).sum() >= 60:
            block(G[G.yr == y], f"  {y}")

    print("\n" + "=" * 100)
    print("READING")
    if res.get("bottom") and res.get("top"):
        gap = res["top"]["edge"] - res["bottom"]["edge"]
        print(f"  top-third edge minus bottom-third edge: {gap*100:+.3f}%")
        print("  A large positive gap means the result depends on knowing the ending.")
        print("  A small gap, with the bottom third still positive, means the")
        print("  mechanism works regardless of how the product ended up — which is")
        print("  the strongest statement available without the delisted data.")
