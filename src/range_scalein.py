"""
SCALE-IN GEOMETRY ON THE RANGE BOOK — the /CL room's shape (DK, 19 Oct: "additional lots it scaled
into at -12 and -17 pips before the hard stop at -26 pips, target +32 for all lots") against the
registered v2.2 ladder (doc 65: 15/25/30/30% at +0.30/+0.05/-0.25/-0.55 ATR; exits 40% mid, 40% band,
rest band+0.35). Three sources now point at adds-before-the-stop: his /CL algo, the Hyperliquid
winners (doc 73: 6.2 adds per trip, half at worse prices), laddered fills (doc 65).
Stop is the registered one: close beyond the band by 1.5 ATR, switch off, or 48 bars.
Registered 27-coin universe, 15-minute bars, both sides, chase fills, frozen containment medians.
Judged per episode AND on the equity curve ($2,000, 20 slots, 3x) — rule 155.
"""
import warnings; warnings.filterwarnings("ignore")
import json, os
import numpy as np, pandas as pd
import clean_portfolio as CP, regime_detect as RD

MED = json.load(open("/home/claude/qlab/runs/contain_median.json"))
UNI = json.load(open("/home/claude/qlab/runs/range_universe.json"))["registered_universe"] if os.path.exists("/home/claude/qlab/runs/range_universe.json") else None
D15 = "/home/claude/qlab/data_15m"

LADDERS = {
    "REGISTERED v2.2 (4 bids, 3 asks)": (RD.BID, RD.ASK),
    "CL: 3 equal lots at band / -0.7 / -1.0 ATR, ONE target at band": ([(1/3, 0.0), (1/3, -0.7), (1/3, -1.0)], [(1.0, 0.0)]),
    "CL lots, target at mid EMA": ([(1/3, 0.0), (1/3, -0.7), (1/3, -1.0)], [(1.0, "mid")]),
    "CL lots, registered asks": ([(1/3, 0.0), (1/3, -0.7), (1/3, -1.0)], RD.ASK),
    "registered bids, ONE target at band": (RD.BID, [(1.0, 0.0)]),
    "deeper: 25% x4 at +0.3/0/-0.5/-1.0": ([(0.25, 0.3), (0.25, 0.0), (0.25, -0.5), (0.25, -1.0)], RD.ASK),
    "front-loaded: 50/30/20 at +0.3/0/-0.5": ([(0.5, 0.3), (0.3, 0.0), (0.2, -0.5)], RD.ASK),
    "single lot at band, registered asks (no ladder)": ([(1.0, 0.0)], RD.ASK),
}


def load_all():
    syms = UNI if UNI else [f[:-4] for f in sorted(os.listdir(D15)) if f.endswith("USD.csv")]
    out = {}
    for s in syms:
        f = f"{D15}/{s}.csv"
        if not os.path.exists(f): continue
        d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, utc=True, format="ISO8601")
        d = d[~d.index.duplicated(keep="last")].sort_index()
        D, ema, lo_b, hi_b, a = RD.detectors(d)
        thr = MED.get(s, {}).get("median"); v = pd.Series(D["contain"]); allow = (v > (thr if thr is not None else v.expanding(500).median())).values
        out[s] = (d, allow, ema, lo_b, hi_b, a)
    return out


def run(B, bid, ask):
    CP.BID, CP.ASK = bid, ask
    rows = []
    for s, (d, allow, ema, lo_b, hi_b, a) in B.items():
        for side in ("L", "S"):
            rows += CP.episodes(d, allow, ema, lo_b, hi_b, a, None, "chase", side, s)
    R = pd.DataFrame(rows, columns=["sym", "entry", "exit", "ret", "side"]); return R[np.isfinite(R.ret)]


if __name__ == "__main__":
    B = load_all(); print(f"{len(B)} coins, 15-minute, {min(x[0].index.min() for x in B.values()).date()}..{max(x[0].index.max() for x in B.values()).date()}\n")
    print(f"  {'ladder':<58}{'eps':>7}{'per ep':>9}{'t':>6}{'win':>5}{'median':>8}{'worst':>7}{'CAGR':>8}{'maxDD':>8}{'Sharpe':>7}{'final':>9}")
    for name, (bid, ask) in LADDERS.items():
        R = run(B, bid, ask)
        t = R.ret.mean()/(R.ret.std(ddof=1)/np.sqrt(len(R)))
        r, taken, skipped = CP.simulate(R[["sym", "entry", "exit", "ret"]], 20, 3)
        sim = f"{r['cagr']*100:>+8.1f}%{r['dd']*100:>+8.1f}%{r['sharpe']:>7.2f}{r['final']:>9,.0f}" if r else "   BLEW UP"
        print(f"  {name:<58}{len(R):>7,}{R.ret.mean()*100:>+8.3f}%{t:>+6.1f}{(R.ret>0).mean()*100:>4.0f}%{R.ret.median()*100:>+7.3f}%{R.ret.min()*100:>+6.1f}%{sim}", flush=True)
        if name.startswith("REGISTERED") or name.startswith("CL: 3"):
            for yv in sorted(set(R.entry.dt.year)):
                Ry = R[R.entry.dt.year == yv]; ry, *_ = CP.simulate(Ry[["sym","entry","exit","ret"]], 20, 3)
                print(f"     {yv}: {len(Ry):>6} eps {Ry.ret.mean()*100:+.3f}%  CAGR {ry['cagr']*100:+.1f}%  maxDD {ry['dd']*100:+.1f}%" if ry else f"     {yv}: blew up")
