"""Fear & Greed (alternative.me) and VIX vs BTC / QQQ forward returns (27 Oct 2026)."""
import json, pandas as pd, numpy as np
j = json.load(open("data_fng/fng.json"))["data"]
fng = pd.Series({pd.to_datetime(int(x["timestamp"]), unit="s").normalize(): int(x["value"]) for x in j}).sort_index()
v = pd.read_csv("data_vol/VIX.csv"); vix = pd.Series(v.CLOSE.values, index=pd.to_datetime(v.DATE, format="%m/%d/%Y")).sort_index()
d = pd.read_csv("data_daily/BTCUSD.csv"); btc = pd.Series(d.close.values, index=pd.DatetimeIndex(pd.to_datetime(d.t, unit="ms")).normalize()).sort_index()
q = pd.read_csv("data_wide/QQQ.csv"); qqq = pd.Series(q.close.values, index=pd.to_datetime(q.date)).sort_index()
out = []
def table(sig, px, bins, labels, name, h=(7, 30)):
    df = pd.DataFrame({"s": sig, "c": px}).dropna()
    for k in h: df[f"r{k}"] = df.c.shift(-k) / df.c - 1
    df["b"] = pd.cut(df.s, bins, right=False, labels=labels); df = df.dropna(subset=[f"r{h[-1]}"])
    g = df.groupby("b", observed=True)
    t = pd.DataFrame({"n": g.size(), **{f"{k}d med%": g[f"r{k}"].median() * 100 for k in h}, f"{h[-1]}d up%": g[f"r{h[-1]}"].apply(lambda x: (x > 0).mean() * 100)}).round(1)
    base = f"all: " + "  ".join(f"{k}d {df[f'r{k}'].median()*100:+.1f}%" for k in h) + f"  up {100*(df[f'r{h[-1]}']>0).mean():.0f}%"
    out.append(f"--- {name} ({df.index[0].date()}→{df.index[-1].date()})\n{t.to_string()}\n{base}")
vb, vl = [0, 15, 20, 25, 30, 200], ["<15", "15-20", "20-25", "25-30", "30+"]
table(vix.reindex(btc.index, method="ffill"), btc[btc.index >= "2015-01-01"], vb, vl, "VIX level -> BTC")
table(vix, qqq, vb, vl, "VIX level -> QQQ (trading days)", h=(5, 21))
spike = vix / vix.rolling(5).min() - 1
table(spike.reindex(btc.index, method="ffill"), btc[btc.index >= "2015-01-01"], [-1, 0.1, 0.25, 0.5, 10], ["<10%", "10-25%", "25-50%", "50%+"], "VIX 5d spike -> BTC")
table(spike, qqq, [-1, 0.1, 0.25, 0.5, 10], ["<10%", "10-25%", "25-50%", "50%+"], "VIX 5d spike -> QQQ", h=(5, 21))
# combined: fear (FNG<40) with VIX calm (<20) vs stressed (>=25)
df = pd.DataFrame({"f": fng, "v": vix.reindex(fng.index, method="ffill"), "c": btc}).dropna(); df["r30"] = df.c.shift(-30) / df.c - 1; df = df.dropna()
for lab, m in (("FNG<40 & VIX<20", (df.f < 40) & (df.v < 20)), ("FNG<40 & VIX>=25", (df.f < 40) & (df.v >= 25)),
               ("FNG>=60 & VIX<20", (df.f >= 60) & (df.v < 20)), ("FNG>=60 & VIX>=25", (df.f >= 60) & (df.v >= 25))):
    x = df[m].r30; out.append(f"{lab:18} n {len(x):4}  BTC 30d med {x.median()*100:+.1f}%  up {100*(x>0).mean():.0f}%")
out.append(f"Now: VIX {vix.iloc[-1]:.2f} ({vix.index[-1].date()}), 5d spike {spike.iloc[-1]*100:+.0f}%; FNG {fng.iloc[-1]} ({fng.index[-1].date()})")
txt = "\n".join(out); print(txt); open("runs/fng_vix_test.txt", "w").write(txt + "\n")
