"""15 Nov: AD stack / Ignition swept looser (coil multiple, regime on/off, weekday filter) — trades/week vs £/week at live stakes.
Live NQ stake is capped by the 5x exposure rule at about £0.09/pt on a £500 pot, so £ = pts x 0.09."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ad_stack_gate.py")).read(); exec(src[:src.index("R = []")])
lon = d.index.tz_convert("Europe/London"); lm = lon.hour * 60 + lon.minute; nym = m
RUNNER = (lm >= 8 * 60) & (nym < 17 * 60); ALL = np.ones(len(d), bool)
def variant(hours, skip_days, regime_on=True, coil=4.0):
    def fn(x):
        f = P7.features(x) if "sig" not in x else x; s = f.sig.values; a = f.atr.values
        idx = pd.Series(np.arange(len(d)), index=d.index).reindex(f.index).values
        ok = (s != 0) & np.isfinite(a) & ~np.isnan(idx); ii = np.nan_to_num(idx).astype(int)
        ok &= EL[ii] & hours[ii]
        if skip_days: ok &= ~np.isin(lt[ii].dayofweek, skip_days)
        if regime_on: ok &= REG[ii] == s
        if coil: ok &= RNG20[ii] <= coil * a
        ix = np.where(ok)[0]
        return sigframe(f.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)
    return fn
weeks = (d.index[-1] - d.index[0]).days / 7; rows = []
for nm, hrs, skip, reg, coil in (("now: runner hrs, regime, coil 4", RUNNER, (), True, 4.0), ("all hrs, Tue/Wed off, regime, coil 4", ALL, (1, 2), True, 4.0),
                                 ("all hrs, regime, coil 4", ALL, (), True, 4.0), ("all hrs, regime, coil 6", ALL, (), True, 6.0),
                                 ("all hrs, regime, no coil", ALL, (), True, 0), ("all hrs, no regime, coil 4", ALL, (), False, 4.0),
                                 ("runner hrs, regime, coil 6", RUNNER, (), True, 6.0)):
    r = G.judge(nm, d, variant(hrs, skip, reg, coil), manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/{nm.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); half = len(t) // 2
    wk = t.groupby(t.t.dt.to_period("W")).pts.sum()
    rows.append(dict(setting=nm, n_wk=len(t) / weeks, win=(t.pts > 0).mean(), pts=t.pts.mean(), gbp_wk=t.pts.sum() * 0.09 / weeks,
                     wks_pos=(wk > 0).mean(), h1=t.pts[:half].mean(), h2=t.pts[half:].mean()))
    print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv("runs/sweep/ignition_sweep.csv", index=False); print(pd.DataFrame(rows).round(2).to_string(index=False))
