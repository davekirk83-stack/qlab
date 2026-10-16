"""
THE COINS THAT DIED — removing the last structural bias.

Doc 123 put the book at 45.3% CAGR over five years with every year profitable,
and then named the reason not to believe it: the panel was built from Coinbase
products ONLINE TODAY. Every coin that delisted in those five years is absent.

For a book that buys dips at the lower band, that is the worst possible bias.
The missing observations are precisely the dips that never came back. A
mean-reversion strategy tested only on survivors is being asked to buy falling
knives in a world where no knife ever lands.

Coinbase exposes 327 delisted products, 89 of them USD pairs, and - tested
directly - still serves full historical candles for them. MIR-USD returns
complete data through 10 May 2022, the exact window in which Mirror Protocol
died alongside LUNA. So the bias is not merely measurable, it is removable.

WHAT THE DEAD PANEL CONTAINS, and why each matters:
  MIR    Mirror Protocol, died with the LUNA collapse
  MATIC  migrated to POL, so its series simply stops
  OMG, LOOM, QSP, SNT, VGX   the long tail of 2017-era tokens that faded
  RNDR, JUP, MOVE, RONIN     more recent delistings

These are not all catastrophes - some delisted for migration or low volume
rather than collapse - and that distinction matters for interpretation but
not for inclusion. The point is that the book would have traded them while
they were listed, and must be charged for whatever happened next.

HOW THE BOOK TREATS A DEATH. The series ends. Any open inventory is marked out
at the last available price, which is the honest treatment: in reality the
position would have been force-closed at or near delisting, often after a
collapse. No special handling is needed - the existing hold cap and break exit
do the work - but the resulting trades will be ugly, and they SHOULD be.

Writes to data_15m_dead/. Resumable.
"""
import warnings; warnings.filterwarnings("ignore")
import os, sys, time, json
import pandas as pd
import ingest_15m as IN

OUT = "/home/claude/qlab/data_15m_dead"


def dead_products():
    p = IN.get(f"{IN.BASE}/products")
    if not p: return []
    return sorted([x["id"] for x in p
                   if x.get("quote_currency") == "USD"
                   and (x.get("status") == "delisted" or x.get("trading_disabled"))])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    pids = dead_products()
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else len(pids)
    pids = pids[:lim]
    print(f"{len(pids)} delisted USD products. These are the observations the")
    print("survivor panel is missing, and for a dip-buying book they are the")
    print("ones that matter most.\n", flush=True)
    done = 0
    for i, pid in enumerate(pids, 1):
        sym = pid.replace("-", "")
        path = f"{OUT}/{sym}.csv"
        if os.path.exists(path):
            try:
                if len(pd.read_csv(path)) > 5000:
                    print(f"  [{i}/{len(pids)}] {pid:<14} already have it",
                          flush=True)
                    done += 1; continue
            except Exception:
                pass
        t0 = time.time()
        d = IN.fetch(pid)
        if d is None or len(d) < 3000:
            print(f"  [{i}/{len(pids)}] {pid:<14} too little "
                  f"({0 if d is None else len(d)})", flush=True)
            continue
        d.to_csv(path); done += 1
        print(f"  [{i}/{len(pids)}] {pid:<14} {len(d):>7,} bars  "
              f"{str(d.index[0])[:10]} -> {str(d.index[-1])[:10]}  "
              f"({time.time()-t0:.0f}s)", flush=True)
    print(f"\n{done} dead symbols written to {OUT}", flush=True)
