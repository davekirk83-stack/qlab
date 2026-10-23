"""ETF-flow effect test (queued 22 Oct). Data: tftc.io data.json (CC BY 4.0), 714 sessions since Jan 2024.
Question: does yesterday's spot-ETF net flow say anything about the next 1/3/5 sessions of BTC?"""
import json, numpy as np, pandas as pd
d = json.load(open('/home/claude/qlab/data_etf/data.json'))['days']
df = pd.DataFrame([{'date': r['date'], 'flow': r['netFlowUsd']/1e6, 'px': r['btcCloseUsd']} for r in d]).dropna()
df['date'] = pd.to_datetime(df.date); df = df.set_index('date')
df['r0'] = df.px.pct_change()*100                       # same session (flow is reported after this close)
for k in (1, 3, 5): df[f'r{k}'] = df.px.pct_change(k).shift(-k)*100   # next k sessions after the flow is known
print(f"sessions {len(df)}  flow mean {df.flow.mean():.0f} sd {df.flow.std():.0f}  corr(flow, same-day ret) {df.flow.corr(df.r0):.2f}")
print(f"corr(flow, next1) {df.flow.corr(df.r1):.3f}  next3 {df.flow.corr(df.r3):.3f}  next5 {df.flow.corr(df.r5):.3f}")
def row(name, m):
    s = df[m]
    out = [f"{name:<34} n {len(s):4d}"]
    for k in (1, 3, 5):
        x = s[f'r{k}'].dropna(); t = x.mean()/x.std()*np.sqrt(len(x)) if len(x) > 2 else float('nan')
        out.append(f"next{k} {x.mean():+.2f}% (t {t:+.1f}, win {100*(x>0).mean():.0f}%)")
    print("  ".join(out))
row("all", df.flow.notna())
row("outflow < -400M", df.flow < -400)
row("outflow < -600M", df.flow < -600)
row("outflow bottom decile", df.flow <= df.flow.quantile(0.1))
row("inflow > 400M", df.flow > 400)
row("inflow top decile", df.flow >= df.flow.quantile(0.9))
# flip: big inflow then big outflow next session
flip = (df.flow < -400) & (df.flow.shift(1) > 400); row("big inflow -> big outflow flip", flip)
# halves
h = len(df)//2
for nm, sub in (("H1", df.iloc[:h]), ("H2", df.iloc[h:])):
    x = sub[sub.flow < -400]['r3'].dropna(); print(f"{nm} outflow<-400 next3 {x.mean():+.2f}% n {len(x)}  | all next3 {sub.r3.mean():+.2f}%")
# matched: does the outflow day's own move explain the next days? control = days with same-day return < -2%
row("same-day ret < -2% (any flow)", df.r0 < -2)
print(df.tail(3)[['flow','px','r0']])
