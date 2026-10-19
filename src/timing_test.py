"""
HIS ORDERING AS A TIMING INPUT — "(3) once momentum catches on the range-break algos activate,
(4) mean reversion buys where the other three take profit" (AuclairsDad via DK, 19 Oct).
Test: do Range v3 episodes that begin shortly AFTER an ignition bar in the OPPOSITE direction
(a breakout that has run and is now being faded) earn more than the rest? And after an ignition
in the SAME direction (we are fading a move that is still igniting) — worse?

Ignition on 15-minute bars from true taker delta (data_1m_delta, 18 perps): bar range >= 1.25x the
average of the prior 20 AND |delta share| >= 0.05 (his two gates); direction = sign of delta.
Range v3 episodes (registered bids, one mid target) from range_scalein over the same 13 months.
Split by: ignition within the prior K bars (K = 4, 12, 24) against / with the episode's side / none.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import regime_detect as RD
from range_scalein import load_all, run as run_range

D = "/home/claude/qlab/data_1m_delta"


def ignition15(c):
    d = pd.read_csv(f"{D}/{c}.csv"); d.index = pd.to_datetime(d.t, unit="ms", utc=True); d = d[["open","high","low","close","vol","delta"]]
    b = d[~d.index.duplicated()].resample("15min").agg(open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last"), vol=("vol","sum"), delta=("delta","sum")).dropna()
    rng = b.high - b.low; ign = rng/rng.shift(1).rolling(20).mean() >= 1.25
    ds = b.delta/b.vol.replace(0, np.nan)
    up = ign & (ds >= 0.05); dn = ign & (ds <= -0.05)
    return pd.Series(np.where(up, 1, np.where(dn, -1, 0)), index=b.index)


if __name__ == "__main__":
    B = load_all(); R = run_range(B, RD.BID, [(1.0, "mid")])
    out = []
    syms = [os.path.basename(f)[:-4] for f in sorted(glob.glob(f"{D}/*.csv"))]
    for s in syms:
        cb = s + "USD"
        if cb not in B: continue
        ig = ignition15(s); Rs = R[(R.sym == cb) & (R.entry >= ig.index.min()) & (R.entry <= ig.index.max())].copy()
        if not len(Rs): continue
        side = np.where(Rs.side == "L", 1, -1)
        for K in (4, 12, 24):
            last_up = ig[ig == 1].index.tz_convert(None); last_dn = ig[ig == -1].index.tz_convert(None); ent = Rs.entry.dt.tz_convert(None).values
            # most recent ignition before entry, within K bars
            pu = last_up.searchsorted(ent) - 1; pdn = last_dn.searchsorted(ent) - 1
            tu = np.where(pu >= 0, (ent - last_up.values[np.clip(pu, 0, None)]) / np.timedelta64(15, "m"), 1e9)
            td = np.where(pdn >= 0, (ent - last_dn.values[np.clip(pdn, 0, None)]) / np.timedelta64(15, "m"), 1e9)
            # for a LONG episode: ignition DOWN before it = "fading an exhausted breakout" (against); ignition UP = "with"
            against = np.where(side == 1, td, tu) <= K; withd = np.where(side == 1, tu, td) <= K
            Rs[f"against{K}"] = against; Rs[f"with{K}"] = withd
        out.append(Rs)
    R2 = pd.concat(out); print(f"{R2.sym.nunique()} coins with true delta, {len(R2):,} Range v3 episodes, {R2.entry.min().date()}..{R2.entry.max().date()}\n")
    def line(lbl, X):
        if len(X) < 100: print(f"  {lbl:<46}{len(X):>7} too few"); return
        t = X.ret.mean()/(X.ret.std(ddof=1)/np.sqrt(len(X)))
        print(f"  {lbl:<46}{len(X):>7,}{X.ret.mean()*100:>+8.3f}%{t:>+7.1f}{(X.ret>0).mean()*100:>6.0f}%{X.ret.median()*100:>+8.3f}%{(X.groupby('sym').ret.mean()>0).mean()*100:>7.0f}%", flush=True)
    print(f"  {'bucket':<46}{'n':>7}{'per ep':>9}{'t':>7}{'win':>7}{'median':>9}{'coins>0':>8}")
    line("ALL episodes", R2)
    for K in (4, 12, 24):
        a, w = R2[f"against{K}"], R2[f"with{K}"]
        line(f"ignition AGAINST the trade within {K} bars (fade)", R2[a & ~w])
        line(f"ignition WITH the trade within {K} bars", R2[w & ~a])
        line(f"both within {K} bars", R2[a & w])
        line(f"no ignition within {K} bars", R2[~a & ~w])
    for sd in ("L", "S"):
        X = R2[R2.side == sd]; a, w = X["against12"], X["with12"]
        line(f"  {sd} side: against within 12", X[a & ~w]); line(f"  {sd} side: none within 12", X[~a & ~w])
