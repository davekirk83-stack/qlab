"""Doc 198 — AuclairsDad's system, layer by layer, through THE GATE (DK 9 Nov 22:30: "keep working on auclair's dads system").
His blueprint (doc 90): REGIME (16 x 15-min regression: in trend when |t|>2 & R2>0.3, released when |t|<1) -> SETUP (coil: 20-bar range
<= 4 ATR) -> TRIGGER (ignition bar: range >= 1.25x the prior 20, delta share >= 0.05, HTF EMA20/50 agrees). Breakouts only WITH the regime;
mean reversion only when there is NO regime. Management as his panel: stop 45, breakeven +15, trail 1 ATR, target 9 ATR (Ignition v1.1).
US Tech 100 5-min, all hours except 12-15 NY; costs = the data's spread, +1 pt outside US cash hours."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
import gate as G, paperbook7 as P7
from gate_books import ign_prep, ign_manage, NY, sigframe

def regime(close):
    c15 = close.resample("15min").last().dropna(); n = 16; x = np.arange(n); xm = x - x.mean()
    def reg(v):
        y = v - v.mean(); beta = (xm * y).sum() / (xm ** 2).sum(); res = y - beta * xm; ss = (res ** 2).sum()
        se = np.sqrt(ss / (n - 2) / (xm ** 2).sum()) if ss > 0 else 1e-9; r2 = 1 - ss / (y ** 2).sum() if (y ** 2).sum() > 0 else 0
        return beta / se, r2
    vals = np.array([reg(c15.values[i - n + 1:i + 1]) if i >= n - 1 else (np.nan, np.nan) for i in range(len(c15))])
    rg = pd.DataFrame({"tt": vals[:, 0], "r2": vals[:, 1]}, index=c15.index).shift(1)
    T, R2 = rg.tt.values, rg.r2.values; st = np.zeros(len(rg)); cur = 0
    for i in range(len(rg)):
        if np.isnan(T[i]): st[i] = cur; continue
        if cur == 0 and abs(T[i]) > 2.0 and R2[i] > 0.3: cur = int(np.sign(T[i]))
        elif cur != 0 and (abs(T[i]) < 1.0 or np.sign(T[i]) != cur): cur = 0
        st[i] = cur
    return pd.Series(st, index=rg.index).reindex(close.index, method="ffill").fillna(0).values

d = ign_prep(); lt = d.index.tz_convert(NY); m = lt.hour * 60 + lt.minute
cash = (m >= P7.US_OPEN) & (m < P7.US_CLOSE); d.loc[~cash, "cost"] = d.loc[~cash, "cost"] + 1.0
EL = ~np.isin(lt.hour, P7.V11_SKIP_HOURS); d["eligible"] = EL
REG = regime(d.close); RNG20 = (d.high.rolling(20).max() - d.low.rolling(20).min()).shift(1).values
d["regime"] = REG

def ign_base(df, use_regime=False, use_coil=False):
    f = P7.features(df) if "sig" not in df else df
    s = f.sig.values; a = f.atr.values; el = pd.Series(EL, index=d.index).reindex(f.index).fillna(False).values
    ok = el & (s != 0) & np.isfinite(a)
    if use_regime: ok &= (pd.Series(REG, index=d.index).reindex(f.index).values == s)
    if use_coil: ok &= (pd.Series(RNG20, index=d.index).reindex(f.index).values <= 4.0 * a)
    ix = np.where(ok)[0]
    return sigframe(f.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)

def mr_noregime(df, z_in=2.0):
    c = df.close; mu = c.rolling(60).mean(); sd = c.rolling(60).std(); z = ((c - mu) / sd).values
    ds = (df.delta / df.vol.replace(0, np.nan)).values; a = df.atr.values
    rg = pd.Series(REG, index=d.index).reindex(df.index).values; el = pd.Series(EL, index=d.index).reindex(df.index).fillna(False).values
    s = np.where(z >= z_in, -1, np.where(z <= -z_in, 1, 0))
    ok = el & (s != 0) & (rg == 0) & (np.abs(ds) < 0.05) & np.isfinite(a)
    ix = np.where(ok)[0]; tgt = np.abs(c.values[ix] - mu.values[ix])
    return sigframe(df.index[ix], s[ix], "market", np.nan, np.full(len(ix), P7.STOP), tgt, 36, dist=True)

R = []
for name, fn, kw in (("AD ignition all-hours (base)", lambda x: ign_base(x), {"manage": ign_manage}),
                     ("AD ignition + REGIME", lambda x: ign_base(x, True), {"manage": ign_manage}),
                     ("AD ignition + REGIME + COIL", lambda x: ign_base(x, True, True), {"manage": ign_manage}),
                     ("AD mean reversion, NO regime", mr_noregime, {})):
    r = G.judge(name, d, fn, **kw); R.append(r); print(G.line(r), flush=True)
    t = pd.read_csv(f"{G.OUT}/{name.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    for lab, g in (("dev", t[t.t < cut]), ("hold", t[t.t >= cut])):
        h = len(g) // 2
        if len(g) > 2: print(f"   {lab:4s} n{len(g):4d} pts/trade {g.pts.mean():+6.2f} total {g.pts.sum():+7.0f} halves {g.pts.iloc[:h].mean():+.2f}/{g.pts.iloc[h:].mean():+.2f} t {g.pts.mean()/g.pts.std()*np.sqrt(len(g)):+.2f}", flush=True)
open(f"{G.OUT}/ad_stack.txt", "w").write("\n".join(G.line(r) for r in R) + "\n")
