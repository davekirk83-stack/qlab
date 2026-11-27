"""Own idea 2: NQ -> BTC lead-lag. BTC has traded as a high-beta tech asset; when NQ makes a decisive move in US cash hours and BTC has not
followed yet, does BTC catch up? Signal at each 15-min close in 09:45-15:00 NY: NQ's return over the last 60 min >= k x its 60-min
stdev (trailing 20 days) AND BTC's 60-min return has the same sign but < half of NQ's in beta-adjusted terms (beta from trailing 20 days).
Trade BTC in NQ's direction at the next 15-min open; exit after H hours. Costs 0.10% round trip (taker both ways + slip).
Data: NQ 5m (IG, Oct 2025-Nov 2026) -> 15m; BTC 15m (Binance, same period)."""
import warnings; warnings.filterwarnings("ignore")
import glob, numpy as np, pandas as pd
nq = pd.read_csv("data_nq_cache/nq_5m.csv", index_col=0); nq.index = pd.to_datetime(nq.index, utc=True)
nq = nq.close.resample("15min").last()
fs = sorted(glob.glob("/tmp/claude-0/-home-claude/6103913e-5d93-5930-ba67-b97312457994/scratchpad/btc15/BTCUSDT-15m-202*.csv"))
bt = []
for f in fs:
    x = pd.read_csv(f, header=None).iloc[:, :5]; x.columns = "t o h l c".split(); x["t"] = pd.to_datetime(x.t // 1000 if x.t.iloc[0] > 1e14 else x.t, unit="ms", utc=True); bt.append(x.set_index("t"))
bt = pd.concat(bt).sort_index(); bt = bt[~bt.index.duplicated()]
df = pd.DataFrame({"nq": nq, "bc": bt.c, "bo": bt.o}).dropna(subset=["bc"]); df = df[df.index >= nq.dropna().index[0]]
df["nq"] = df.nq.ffill(limit=2)
ny = df.index.tz_convert("America/New_York"); mins = ny.hour * 60 + ny.minute
rn = np.log(df.nq).diff(4); rb = np.log(df.bc).diff(4)
r15n = np.log(df.nq).diff(); r15b = np.log(df.bc).diff()
cash = (mins >= 9 * 60 + 45) & (mins <= 15 * 60) & (ny.dayofweek < 5)
cs = pd.Series(cash, index=df.index)
rnc, r15nc, r15bc = rn[cs], r15n[cs], r15b[cs]
sd = rnc.rolling(22 * 20, min_periods=200).std().reindex(df.index).ffill()
beta = (r15nc.rolling(22 * 20, min_periods=200).cov(r15bc) / r15nc.rolling(22 * 20, min_periods=200).var()).reindex(df.index).ffill()
rows = []
for k in (1.5, 2.0, 2.5):
    for H in (1, 2, 4):
        sig = cash & (rn.abs() >= k * sd) & (np.sign(rb) != -np.sign(rn)) & (rb.abs() < 0.5 * beta.abs() * rn.abs())
        idx = np.where(sig.values)[0]; out = []; last = -10 ** 9
        for i in idx:
            if i - last < H * 4 or i + 1 + H * 4 >= len(df): continue
            s = np.sign(rn.iloc[i]); e = df.bo.iloc[i + 1]; x = df.bo.iloc[i + 1 + H * 4]
            out.append((df.index[i], s * (x / e - 1) - 0.001)); last = i
        t = pd.Series([v for _, v in out], index=[a for a, _ in out])
        if len(t) < 10: continue
        h = len(t) // 2
        rows.append(dict(k=k, hold_h=H, n=len(t), win=round((t > 0).mean(), 2), mean_pct=round(100 * t.mean(), 3), h1=round(100 * t[:h].mean(), 3), h2=round(100 * t[h:].mean(), 3)))
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv("runs/research/nq_btc_leadlag.csv", index=False)
