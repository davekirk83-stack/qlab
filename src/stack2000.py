"""
WHAT OUR BOOKS ACTUALLY EARN ON A $2,000 STACK.

DK's operating brief, 2026-10-15:
  "$2000 to play with" · "x2, x5, even x10 on occasion" ·
  "frequent small gains are what we want to target, at least while we build
   our own stack."

Every number this programme has produced is a percentage or an R multiple.
Neither tells DK what he would actually have at the end of a year, and the
small-account study showed why that matters: at his scale fees take 17.6% of
realised PnL against 0.7% for a whale. A book that is fine in percentage terms
can be worthless in pounds.

THE ARITHMETIC THAT DECIDES IT
A round trip costs roughly 2 x fee on the NOTIONAL. Leverage multiplies both
the gain and the fee, so it does NOT improve the ratio between them — it only
raises the stake. What leverage does change is how much a fixed fee is worth
relative to equity, and how fast a bad run ends the experiment.

  gross per trade   = position x edge
  cost per trade    = position x (entry_fee + exit_fee)
  net per trade     = position x (edge - fees)
  return on equity  = leverage x (edge - fees)

So the whole question is whether EDGE exceeds FEES, and leverage is just a
multiplier on the answer, including when it is negative.

FEES USED — Hyperliquid, which is where the on-chain study came from
  maker 1.2bp, taker 4.0bp (measured directly from the small-account fills:
  effective 3.66bp, consistent with a mostly-taker mix)

RUIN
Also reported: how many consecutive losers at the book's own stop size it
takes to halve the stack at each leverage. Frequent small gains only compound
if the account survives the bad run, and at 10x that arithmetic is brutal.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np

STACK = 2000.0
MAKER, TAKER = 1.2 / 10000, 4.0 / 10000

# measured, net of the costs already modelled in each book's own study
BOOKS = [
    # name, edge % per trade, trades per month, entry, exit, stop % of position
    ("cascade v3 (base-then-bid)", 0.378, 12, "maker", "maker", 2.63),
    ("cascade v3-K (tapered exit)", 0.303, 12, "maker", "maker", 2.63),
    ("Keltner range pair",          0.289, 20, "maker", "maker", 4.00),
    ("Keltner range, long only",    0.392,  9, "maker", "maker", 4.00),
    ("TSMOM macro ETF (12m)",       0.650,  1, "taker", "taker", 8.00),
]


def fee(kind):
    return MAKER if kind == "maker" else TAKER


if __name__ == "__main__":
    print(f"ON A ${STACK:,.0f} STACK — Hyperliquid fees, maker {MAKER*1e4:.1f}bp "
          f"taker {TAKER*1e4:.1f}bp\n")
    for lev in (1, 2, 5, 10):
        pos = STACK * lev
        print("=" * 86)
        print(f"  LEVERAGE {lev}x   position size ${pos:,.0f}")
        print("=" * 86)
        print(f"  {'book':<30}{'edge':>8}{'cost':>8}{'net':>8}"
              f"{'$/trade':>10}{'$/month':>10}{'$/year':>10}{'% /yr':>8}")
        tot_m = 0.0
        for name, edge, n, ein, eout, stop in BOOKS:
            cost_pct = (fee(ein) + fee(eout)) * 100
            net_pct = edge - cost_pct
            per = pos * net_pct / 100
            mon = per * n
            tot_m += mon
            print(f"  {name:<30}{edge:>7.3f}%{cost_pct:>7.3f}%{net_pct:>7.3f}%"
                  f"{per:>10,.2f}{mon:>10,.0f}{mon*12:>10,.0f}"
                  f"{mon*12/STACK*100:>7.0f}%")
        print(f"  {'ALL FIVE COMBINED':<30}{'':>23}"
              f"{'':>10}{tot_m:>10,.0f}{tot_m*12:>10,.0f}"
              f"{tot_m*12/STACK*100:>7.0f}%")
        # survival
        worst = max(b[5] for b in BOOKS)
        n_half = np.log(0.5) / np.log(1 - lev * worst / 100) if lev * worst < 100 else 0
        print(f"\n  consecutive stop-outs to halve the stack "
              f"(at the widest stop, {worst:.2f}%): "
              f"{n_half:.0f}" if n_half else
              f"\n  a SINGLE stop-out at the widest stop ({worst:.2f}%) "
              f"wipes the account at {lev}x")
        print()

    print("=" * 86)
    print("  THE POINT")
    print("=" * 86)
    print(f"  Fees are a FIXED {((MAKER*2)*100):.3f}% of notional on a maker round trip")
    print(f"  and {((TAKER*2)*100):.3f}% taker. Leverage scales gross and cost together,")
    print("  so it never improves the edge-to-cost ratio — it only raises the stake.")
    print()
    for name, edge, n, ein, eout, stop in BOOKS:
        cm = (fee(ein) + fee(eout)) * 100
        print(f"  {name:<30} edge is {edge/cm:>5.1f}x its own cost"
              f"   ({'viable' if edge/cm > 3 else 'THIN' if edge/cm > 1.5 else 'DEAD'})")
    print()
    print("  If every entry were a TAKER instead of a maker:")
    for name, edge, n, ein, eout, stop in BOOKS:
        ct = (TAKER * 2) * 100
        print(f"  {name:<30} edge is {edge/ct:>5.1f}x cost"
              f"   ({'viable' if edge/ct > 3 else 'THIN' if edge/ct > 1.5 else 'DEAD'})")
