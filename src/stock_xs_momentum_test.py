"""Doc 149b: a diversified stock book that has academic support — cross-sectional 12-1 month momentum (Jegadeesh-Titman), pre-registered 28 Oct 2026.
Universe: the same ~4,700 current US stocks (survivorship-biased: dead names missing; judged against the equal-weight universe, which shares it).
Each month-end: eligible = price >= $5 and 20-day median dollar volume >= $5m; rank by return from 12 months ago to 1 month ago; hold the top 20
equal-weight for one month. Costs 0.20% per side on turnover + 6.5%/yr financing (IG share spread bets). Variant: hold cash when SPY < its 200-day.
Dev 2006-2018, holdout 2019 on. Trials 2."""
import glob, os, numpy as np, pandas as pd
C, DV = {}, {}
for f in glob.glob("data_stk2/*.csv"):
    d = pd.read_csv(f, parse_dates=["t"]).set_index("t"); d = d[~d.index.duplicated()].dropna()
    if len(d) > 300:
        s = os.path.basename(f)[:-4]; C[s] = d.close; DV[s] = (d.close * d.volume).rolling(20).median()
C = pd.DataFrame(C); DV = pd.DataFrame(DV)
spy = pd.read_csv("data_eqd/SPY.csv", parse_dates=["t"]).set_index("t").adj
Cm = C.resample("ME").last(); DVm = DV.resample("ME").last()
mom = Cm.shift(1) / Cm.shift(12) - 1; nxt = (Cm.shift(-1) / Cm - 1).clip(lower=-0.95, upper=5)
spym = spy.resample("ME").last(); spyok = spym > spy.rolling(200).mean().resample("ME").last(); spyr = spym.shift(-1) / spym - 1
rows = []; prev = set()
for t in Cm.index[13:-1]:
    el = (Cm.loc[t] >= 5) & (DVm.loc[t] >= 5e6) & mom.loc[t].notna() & nxt.loc[t].notna()
    if el.sum() < 100: continue
    top = mom.loc[t][el].nlargest(20).index; held = set(top)
    turn = len(held ^ prev) / 40 if prev else 1.0; prev = held
    r = nxt.loc[t, top].mean() - 2 * 0.002 * turn - 0.065 / 12
    rows.append(dict(t=t, mom=r, mom_f=r if bool(spyok.get(t, True)) else 0.0, ew=nxt.loc[t][el].mean(), spy=spyr.get(t, np.nan), n=int(el.sum())))
R = pd.DataFrame(rows).set_index("t")
def st(x):
    x = x.dropna(); eq = (1 + x).cumprod(); yrs = len(x) / 12
    return f"{100*(eq.iloc[-1]**(1/yrs)-1):+6.1f}%/yr, Sharpe {x.mean()/x.std()*np.sqrt(12):.2f}, maxDD {100*(eq/eq.cummax()-1).min():.0f}%"
out = [f"months {len(R)}, eligible stocks median {int(R.n.median())}"]
for seg, m in (("DEV 2006-2018", R.index < "2019-01-01"), ("HOLD 2019-2026", R.index >= "2019-01-01")):
    out.append(seg)
    for k, lab in (("mom", "top-20 momentum"), ("mom_f", "top-20 momentum, cash when SPY < 200d"), ("ew", "equal-weight universe"), ("spy", "SPY")):
        out.append(f"  {lab:40} {st(R.loc[m, k])}")
    ex = R.loc[m, "mom"] - R.loc[m, "ew"]
    out.append(f"  momentum minus universe: {100*ex.mean()*12:+.1f}%/yr, t={ex.mean()/ex.std()*np.sqrt(len(ex)):.2f}, positive months {100*(ex>0).mean():.0f}%")
txt = "\n".join(out); print(txt); open("runs/stock_xs_momentum_test.txt", "w").write(txt + "\n")
