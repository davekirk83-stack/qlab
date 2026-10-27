"""Doc 147b: the saucer system at real spot-exchange costs. Per side: 0.15% (as tested), 0.30%, 0.45% (Kraken Pro taker 0.40% + slip),
0.65% (Coinbase Advanced taker 0.60% + slip). Entries are buy stops and exits are at the close -> taker both ways."""
import numpy as np, saucer_refine_test as S
data = {f: S.load(f) for f in S.TEN}; Bs = {f: S.build(data[f]) for f in S.TEN}
out = []
for uname, U, dy in (("BTC+ETH base (book 9)", S.TEN[:2], False), ("BTC+ETH + daily", S.TEN[:2], True), ("10 coins + daily (book 10)", S.TEN, True)):
    for c in (0.0015, 0.0030, 0.0045, 0.0065):
        S.COST = c; rows = []
        for hold in (False, True):
            t = [r for f in U for tt, r in S.run(data[f], Bs[f], False, dy) if (tt >= S.HOLD) == hold]; s = S.stats(t)
            rows.append(f"{'HOLD' if hold else 'DEV'} n{s['n']} PF {s['pf']:.2f} mean {s['mean']:+.2f}% total {s['tot']:+.1f}%")
        out.append(f"{uname:28} cost {100*c:.2f}%/side | " + " | ".join(rows)); print(out[-1], flush=True)
open("runs/saucer_cost_test.txt", "w").write("\n".join(out) + "\n")
