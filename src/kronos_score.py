"""Score runs/kronos/*.csv: Kronos vs naive baselines on 1-bar and 1-hour returns, and a sign-trading rule net of costs."""
import glob, os, numpy as np, pandas as pd
COST = {"BTC": 0.0011, "ETH": 0.0011, "NQ": 0.00006}   # round trip: paperbook6 crypto costs; IG US Tech 100 1-pt spread + slippage
for f in sorted(glob.glob("/home/claude/qlab/runs/kronos/*.csv")):
    s = os.path.basename(f)[:-4]; r = pd.read_csv(f)
    if len(r) < 30: continue
    a1 = r.act1/r["last"] - 1; a4 = r.act4/r["last"] - 1; p1 = r.pred1/r["last"] - 1; p4 = r.pred4/r["last"] - 1; mom = r["last"]/r.prev4 - 1
    def hit(p, a): m = p != 0; return 100*(np.sign(p[m]) == np.sign(a[m])).mean()
    def trade(p, a, c, thr=0.0):
        m = p.abs() > thr; x = np.sign(p[m])*a[m] - c; return len(x), x.mean()*100, (x.mean()/x.std()*np.sqrt(len(x)) if len(x) > 2 else np.nan)
    h = len(r)//2
    print(f"\n== {s}: {len(r)} forecasts ({r.t0.iloc[0][:10]} -> {r.t0.iloc[-1][:10]})")
    print(f"  direction hit, next 1h:  Kronos {hit(p4, a4):.1f}%   momentum {hit(mom, a4):.1f}%   reversal {hit(-mom, a4):.1f}%   (coin-flip 50)")
    print(f"  direction hit, next bar: Kronos {hit(p1, a1):.1f}%")
    print(f"  corr(pred 1h, actual 1h) {np.corrcoef(p4, a4)[0,1]:+.3f}   (H1 {np.corrcoef(p4[:h], a4[:h])[0,1]:+.3f}, H2 {np.corrcoef(p4[h:], a4[h:])[0,1]:+.3f})")
    print(f"  forecast size: median |pred 1h| {p4.abs().median()*100:.3f}%  vs median |actual 1h| {a4.abs().median()*100:.3f}%   cost {COST[s]*100:.3f}%")
    for thr in (0.0, COST[s]):
        n, m, t = trade(p4, a4, COST[s], thr); n0, m0, t0 = trade(p4, a4, 0.0, thr)
        print(f"  trade sign(pred) for 1h, |pred| > {thr*100:.3f}%: n {n}  net {m:+.3f}%/trade t {t:+.1f}  | gross {m0:+.3f}%")
    n, m, t = trade(mom, a4, COST[s]); print(f"  baseline momentum trade:   n {n}  net {m:+.3f}%/trade t {t:+.1f}")
