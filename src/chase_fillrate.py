"""
MEASURING THE CHASE FILL RATE — the one assumption the result now rests on.

Doc 120 put the book at 24.8% CAGR with a chase order and 1.5% without one.
The entire difference is a 92% fill rate that I ASSUMED. That number is now
load-bearing and it has never been measured.

WHY A CHASE ORDER FILLS BETTER, mechanically. A static ladder rung sits deep -
0.55 ATR below the band might be 2% below mid - so the queue ahead of it is
everything resting between mid and that level, which the depth data says is
substantial. A CHASE order re-prices to sit one tick inside the best bid, so
the queue ahead of it is only what is resting AT THE TOUCH. That is a far
smaller number, and it is the whole mechanism.

THE OBSTACLE, stated plainly: the depth data's finest resolution is cumulative
dollars within 0.2% of mid. It does not resolve the touch itself. So the touch
queue has to be inferred as a FRACTION of that 0.2% band, and that fraction is
unknown.

SO THIS DOES NOT PRODUCE A POINT ESTIMATE AND SHOULD NOT. It sweeps the
fraction across an order of magnitude and reports the implied fill rate for
each, which converts "92%, assumed" into "between X and Y, measured under a
stated assumption". That is a weaker claim and a more honest one.

  touch share 1/2   the 0.2% band is nearly all at the touch - implausibly deep
  touch share 1/10  a tenth of the near-mid liquidity sits at the best bid
  touch share 1/25  thin touch, most liquidity standing back
  touch share 1/50  very thin touch

For each, the chase order fills when the sell flow arriving during the bar
exceeds the touch queue. Reported per symbol as well as pooled, because a
single pooled number would hide the fact that this will be far better on
BTC than on a thin alt - and the book trades both.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD

BID_COLS = ["d-0.2", "d-1", "d-2", "d-3", "d-4", "d-5"]
ORDER = 150.0
SHARES = [(0.50, "1/2  (implausibly deep touch)"),
          (0.10, "1/10 (moderate)"),
          (0.04, "1/25 (thin touch)"),
          (0.02, "1/50 (very thin touch)")]


def load_depth():
    out = {}
    for p in sorted(glob.glob("/home/claude/qlab/data_depth_full/*.csv")):
        s = os.path.basename(p)[:-4]
        D = pd.read_csv(p)
        D.index = pd.to_datetime(D.ts, utc=True)
        if "d-0.2" in D.columns:
            out[s] = pd.to_numeric(D["d-0.2"], errors="coerce")
    return out


if __name__ == "__main__":
    depth = load_depth()
    data = RD.load()
    common = sorted([s for s in data if s in depth])
    print(f"{len(common)} symbols. ${ORDER:.0f} order resting one tick inside the")
    print("best bid. It fills when sell flow arriving during the bar exceeds the")
    print("queue already resting at the touch.\n")
    print("The depth feed's finest level is cumulative dollars within 0.2% of mid,")
    print("so the touch queue is inferred as a FRACTION of that, swept below.\n")

    # per-bar arriving sell flow, during bars when the book would be bidding
    flow = {}
    for s in common:
        d = data[s]
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        v = pd.Series(D["contain"])
        al = (v > v.expanding(500).median()).values
        C, H, L = d.close.values, d.high.values, d.low.values
        usd = d.volume.values*C
        # a chase order is live on bars where price is descending toward the
        # band - the bars the ladder would be working
        live = al & (L < lo_b + 0.30*a)
        rng = np.maximum(H-L, 1e-12)
        down_share = np.clip((C-L)/rng, 0, 1)      # portion of the bar's flow
        sell = usd*down_share                      # that traded on the way down
        dep = depth[s].reindex(d.index, method="ffill").values
        ok = live & np.isfinite(dep) & np.isfinite(sell) & (dep > 0)
        if ok.sum() > 200: flow[s] = (sell[ok], dep[ok])
    print(f"{len(flow)} symbols with enough live bars.\n")
    print(f"  {'touch queue assumption':<34}{'pooled fill rate':>18}"
          f"{'best symbol':>14}{'worst symbol':>15}")
    summary = {}
    for share, lbl in SHARES:
        per = {}
        for s, (sell, dep) in flow.items():
            q = dep*share
            f = np.clip((sell-q)/ORDER, 0, 1)
            per[s] = float(np.mean(f))
        vals = np.array(list(per.values()))
        summary[share] = per
        bs = max(per.items(), key=lambda z: z[1])
        ws = min(per.items(), key=lambda z: z[1])
        print(f"  {lbl:<34}{vals.mean()*100:>17.0f}%"
              f"{bs[0][:9]+' '+format(bs[1]*100,'.0f')+'%':>14}"
              f"{ws[0][:9]+' '+format(ws[1]*100,'.0f')+'%':>15}")

    print("\n  BY SYMBOL at the 1/10 assumption — the book trades all of these,")
    print("  so a pooled average hides where the strategy will actually struggle:")
    per = summary[0.10]
    print(f"  {'symbol':<14}{'fill rate':>11}{'median touch queue $':>24}"
          f"{'median sell flow $':>22}")
    for s in sorted(per, key=lambda z: -per[z]):
        sell, dep = flow[s]
        print(f"  {s:<14}{per[s]*100:>10.0f}%{np.median(dep)*0.10:>23,.0f}"
              f"{np.median(sell):>21,.0f}")

    print("\n  WHAT THIS MEANS FOR DOC 120. That result assumed 92%. If the real")
    print("  figure is materially lower the book sits between its two bounds —")
    print("  1.5% CAGR queued and 24.8% chased — rather than at the top one.")
    v10 = np.mean(list(summary[0.10].values()))
    v25 = np.mean(list(summary[0.04].values()))
    print(f"  At 1/10 the implied rate is {v10*100:.0f}%, at 1/25 it is "
          f"{v25*100:.0f}%.")
