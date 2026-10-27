"""Doc 145e: the saucer trend system (145c engine, unchanged) on DK's timeframes: 15m, 1h, 4h (3h already in 145d).
Arms BASE and DAILY (v9.1 filter). Same sealed holdout (2025-04-01), random-entry control (50 draws). Trials added: 3 TF x 2 arms x 2 universes = 12."""
import sys, numpy as np, pandas as pd
import saucer_refine_test as S
TF = sys.argv[1]
def load(f):
    d = pd.read_csv(f"data_15m/{f}.csv"); d["t"] = pd.to_datetime(d.t, utc=True)
    d = d.set_index("t")[["open","high","low","close"]].astype(float)
    agg = {"open":"first","high":"max","low":"min","close":"last"}
    x = d.resample(TF).agg(agg).dropna() if TF != "15min" else d.copy()
    dy = d.resample("1D").agg(agg).dropna(); mp = (dy.high + dy.low) / 2
    ok = (dy.close > mp.ewm(alpha=1/13, adjust=False).mean().shift(8)).shift(1)
    x["dailyok"] = ok.reindex(x.index.floor("1D")).fillna(False).values.astype(bool)
    return x
data = {f: load(f) for f in S.TEN}; Bs = {f: S.build(data[f]) for f in S.TEN}
seg = lambda trs, hold: [r for t, r in trs if (t >= S.HOLD) == hold]
out = []
for uname, U in (("BTC+ETH", S.TEN[:2]), ("10 coins", S.TEN)):
    for arm, dy in (("BASE", False), ("DAILY", True)):
        real = {f: S.run(data[f], Bs[f], False, dy) for f in U}; rows = []
        els = {f: S.eligible(data[f], Bs[f], dy) for f in U}
        for hold in (False, True):
            s = S.stats(sum((seg(real[f], hold) for f in U), [])); tots = []
            for k in range(50):
                rng = np.random.default_rng(k); pooled = []
                for f in U:
                    el = els[f]; el = el[(data[f].index[el] >= S.HOLD) == hold]; m = len(seg(real[f], hold))
                    pick = set(rng.choice(el, size=min(m, len(el)), replace=False)) if m and len(el) else set()
                    pooled += seg(S.run(data[f], Bs[f], False, dy, rnd=pick), hold)
                tots.append(S.stats(pooled)["tot"])
            tots = np.array(tots)
            rows.append(f"{'HOLD' if hold else 'DEV '} n{s['n']:5} win {s['win']:3.0f}% PF {s['pf']:.2f} mean {s['mean']:+.2f}% total {s['tot']:+7.1f}% | random {np.median(tots):+7.1f}%, beats {100*(tots < s['tot']).mean():3.0f}%")
        out.append(f"{TF:5} {uname:8} {arm:5} " + "\n                     ".join(rows)); print(out[-1], flush=True)
open(f"runs/saucer_tf_{TF}.txt", "w").write("\n".join(out) + "\n")
