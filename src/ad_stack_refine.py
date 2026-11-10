"""Doc 227 — AuclairsDad's stack made to work on the IG runner (DK 22:35: "go back to auclair's dad's system and make it work").
His layers (doc 90/198): REGIME (16 x 15-min regression, in when |t|>2 & R2>0.3, out when |t|<1) -> COIL (20-bar range <= 4 ATR) -> IGNITION
trigger (Ignition v1.1 bar). Management v1.1 (stop max(45, 1.5 ATR), breakeven +15, trail 1 ATR, target 9 ATR). US Tech 100 5-min Dukascopy,
costs = data spread, +1 pt outside US cash hours. Here: restricted to the hours the IG runner is actually up (London 07:55 to 17:00 NY),
ex US lunch, and the walk-forward weekday switch (Tue/Wed off, doc 201) — the version that can trade on IG tomorrow."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.environ.setdefault("QLAB_ROOT", os.getcwd())
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ad_stack_gate.py")).read(); exec(src[:src.index("R = []")])
lon = d.index.tz_convert("Europe/London"); lm = lon.hour * 60 + lon.minute; nym = m
RUNNER = (lm >= 8 * 60) & (nym < 17 * 60)
def variant(hours, skip_days, regime_on=True, coil_on=True):
    def fn(x):
        f = P7.features(x) if "sig" not in x else x; s = f.sig.values; a = f.atr.values
        idx = pd.Series(np.arange(len(d)), index=d.index).reindex(f.index).values
        ok = (s != 0) & np.isfinite(a) & ~np.isnan(idx)
        ii = np.nan_to_num(idx).astype(int)
        ok &= EL[ii] & hours[ii]
        if skip_days: ok &= ~np.isin(lt[ii].dayofweek, skip_days)
        if regime_on: ok &= REG[ii] == s
        if coil_on: ok &= RNG20[ii] <= 4.0 * a
        ix = np.where(ok)[0]
        return sigframe(f.index[ix], s[ix].astype(int), "market", np.nan, np.maximum(P7.STOP, P7.V11_STOP_ATR * a[ix]), P7.TGT_ATR * a[ix], P7.CAP, dist=True)
    return fn
ALL = np.ones(len(d), bool); USH = cash
for name, fn in (("AD stack, runner hours (London 08:00 to 17:00 NY)", variant(RUNNER, ())),
                 ("AD stack, runner hours, Tue/Wed off", variant(RUNNER, (1, 2))),
                 ("AD stack, all hours, Tue/Wed off", variant(ALL, (1, 2))),
                 ("AD stack, US cash hours only", variant(USH, ())),
                 ("Ignition v1.1 alone, runner hours (no regime/coil)", variant(RUNNER, (), False, False))):
    r = G.judge(name, d, fn, manage=ign_manage)
    t = pd.read_csv(f"{G.OUT}/{name.replace(' ', '_').replace('/', '-')}_trades.csv", parse_dates=["t"]); cut = pd.Timestamp(r["holdout_from"], tz="UTC")
    days = (d.index[-1] - d.index[0]).days / 365.25
    print(f"{name}: n {len(t)} ({len(t) / days:.0f}/yr), pts/trade {t.pts.mean():+.2f}, total {t.pts.sum():+.0f} pts, win {100 * (t.pts > 0).mean():.0f}% | "
          f"dev {t[t.t < cut].pts.mean():+.2f} (n{(t.t < cut).sum()}), hold-out {t[t.t >= cut].pts.mean():+.2f} (n{(t.t >= cut).sum()}) | gate: {r.get('verdict', '')}", flush=True)
    m_ = t.groupby(t.t.dt.to_period("M")).pts.sum(); print(f"   months positive {(m_ > 0).sum()}/{len(m_)}, worst month {m_.min():+.0f} pts", flush=True)
