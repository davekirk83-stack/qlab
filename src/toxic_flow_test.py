"""Toxic-flow extremes as exhaustion (avenue 3, after Kingfisher's 24 Oct 'almost all flow is toxic' at the low).
Binance 1-min bars with true taker buy volume (data_1m_delta, Sep 2025 - Oct 2026). Toxicity = 60-min taker imbalance
sum(delta)/sum(volume). Extreme = beyond the coin's own 0.5th / 99.5th percentile AND 60-min volume > 2x its 30-day median.
Signal fires at the minute the condition first holds (decision point, rule 183); 12-hour cooldown per coin and side.
Forward return from that minute's close at 1h / 4h / 12h. Sign convention: 'fade' = trade against the flow (buy seller-heavy extremes).
Control: random minutes with the same volume condition."""
import glob, os, numpy as np, pandas as pd
rng = np.random.default_rng(11); rows = []; ctrl = []
for f in sorted(glob.glob("/home/claude/qlab/data_1m_delta/*.csv")):
    s = os.path.basename(f)[:-4]; d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index, unit="ms", utc=True)
    dl = d.delta.rolling(60).sum(); vv = d.vol.rolling(60).sum(); tox = dl/vv
    vmed = vv.rolling(60*24*30, min_periods=60*24*5).median(); hot = vv > 2*vmed
    lo, hi = tox.quantile(0.005), tox.quantile(0.995); C = d.close.values; n = len(C)
    for side, cond in ((-1, (tox <= lo) & hot), (1, (tox >= hi) & hot)):
        idx = np.where(cond.values)[0]; last = -10**9
        for i in idx:
            if i - last < 720 or i + 720 >= n: continue
            last = i
            rows.append(dict(sym=s, t=d.index[i], side=side, tox=tox.iloc[i], r1=C[i+60]/C[i]-1, r4=C[i+240]/C[i]-1, r12=C[i+720]/C[i]-1))
    hot_i = np.where(hot.values)[0]; hot_i = hot_i[(hot_i > 60) & (hot_i < n-721)]
    for i in rng.choice(hot_i, size=min(200, len(hot_i)), replace=False):
        ctrl.append(dict(r1=C[i+60]/C[i]-1, r4=C[i+240]/C[i]-1, r12=C[i+720]/C[i]-1))
r = pd.DataFrame(rows).sort_values("t"); c = pd.DataFrame(ctrl)
print(f"signals {len(r)} on {r.sym.nunique()} coins ({r.t.min().date()} -> {r.t.max().date()}); control minutes {len(c)} (high-volume, random)")
for side, lab in ((-1, "SELLER-heavy extreme (Saturday's kind)"), (1, "BUYER-heavy extreme")):
    s = r[r.side == side]; h = len(s)//2; print(f"\n  {lab}: n {len(s)}")
    for k in ("r1", "r4", "r12"):
        x = -side*s[k]   # 'fade' return: buy after seller-heavy, sell after buyer-heavy
        print(f"    fade, {k[1:]:>2}h: {x.mean()*100:+.2f}%  t {x.mean()/x.std()*np.sqrt(len(x)):+.1f}  win {100*(x>0).mean():.0f}%  H1 {x.iloc[:h].mean()*100:+.2f} H2 {x.iloc[h:].mean()*100:+.2f}"
              f"   | raw price move {s[k].mean()*100:+.2f}%  (control {c[k].mean()*100:+.2f}%)")
b = r[(r.sym == "BTC") & (r.side == -1)]
print(f"\n  BTC seller-heavy extremes: n {len(b)}; fade 4h {(b.r4.mean())*100:+.2f}%  12h {(b.r12.mean())*100:+.2f}%  — dates: {', '.join(str(t.date()) for t in b.t.tail(8))}")
