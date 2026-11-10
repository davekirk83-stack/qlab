"""Doc 219 — the gap-down result was strongly NEGATIVE for buyers (n 2990, clustered t −3.46): test the other side, i.e. bad-news drift
(post-earnings drift after negative surprises, Bernard & Thomas 1989). SHORT at the next open after a >= 5% gap down on >= 2x volume,
hold 5 / 20 days, stop 3 ATR. Costs 0.1%/side; funding charged on shorts too (conservative: an IG short receives the benchmark less admin).
Survivorship bias (today's members only) works AGAINST shorts here, so this is a hard test."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stock_books as SB, review2_new_books as N, fifty_ideas as F, standard_test as S, std_books as B
def short_gap(hold, need_up=True):
    def b(cm=1.0, rnd=None):
        rows = []
        for k in SB.SH:
            d = F.D[k]; e = (d.open / d.close.shift(1) - 1 <= -0.05) & SB.vol2(d) & (SB.up(d).shift(1) if need_up else True)
            old = F.COST[k]; F.COST[k] = old * cm
            try: rows += N.run_side(k, (rnd or (lambda k, e: e))(k, e.fillna(False)), -1, None, hold, 3.0)
            finally: F.COST[k] = old
        return pd.DataFrame(rows, columns=["t", "R", "m"])
    return b
if __name__ == "__main__":
    C = B.core()
    for nm, b in [("S6 bad-news drift SHORT: gap down >= 5% on 2x volume (was above 200-day), 5 days", short_gap(5)),
                  ("S7 bad-news drift SHORT: same, 20 days", short_gap(20)),
                  ("S8 bad-news drift SHORT: any gap down >= 5% on 2x volume, 20 days", short_gap(20, False))]:
        o, t = S.judge(nm, "stock-event-short", ["shares"], b, core=C, random_runs=20)
        print("      by index:", " ".join(f"{g}:{x.R.mean():+.3f}(n{len(x)})" for g, x in t.groupby(t.m.map(SB.IDX))), "| by year:", " ".join(f"{y}:{v:+.0f}" for y, v in t.groupby(t.t.dt.year).R.sum().items()), flush=True)
