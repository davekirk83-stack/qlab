"""
QLAB — generator + rejection engine.

Design principle (from the closure of the previous programme):
the edge is not in generating strategies, it is in rejecting them.
Everything here is built so that a candidate must survive, not so that it can be found.

Trial counting is cumulative and persistent. Every candidate evaluated
increments the ledger, including failures, including parser errors.
The deflated Sharpe is computed against the LIFETIME trial count, not the run's.
"""
import os, json, hashlib, numpy as np, pandas as pd
from scipy.stats import norm, ttest_1samp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
LEDGER = os.path.join(ROOT, "ledger", "trials.json")

HOLDOUT_START = "2025-01-01"   # opened once, at the end, never before

# Round-trip cost as fraction of notional. Conservative.
COSTS = {}
DEFAULT_COST = 0.0015


# ---------------------------------------------------------------- ledger
def ledger_load():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER))
    return {"cumulative_trials": 0, "runs": [], "survivors": []}


def ledger_bump(n, note):
    L = ledger_load()
    L["cumulative_trials"] += int(n)
    L["runs"].append({"n": int(n), "note": note,
                      "cumulative_after": L["cumulative_trials"]})
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(L, open(LEDGER, "w"), indent=1)
    return L["cumulative_trials"]


# ---------------------------------------------------------------- data
def load(sym, holdout=False):
    df = pd.read_csv(f"{DATA}/{sym}.csv", parse_dates=["date"]).sort_values("date")
    df = df.set_index("date")
    df = df[~df.index.duplicated(keep="first")]
    return df[df.index >= HOLDOUT_START] if holdout else df[df.index < HOLDOUT_START]


def universe():
    return sorted(f[:-4] for f in os.listdir(DATA) if f.endswith(".csv"))


def cost(sym):
    return COSTS.get(sym, DEFAULT_COST)


# ---------------------------------------------------------------- signals
# Each returns a RAW position series. The evaluator shifts it by one bar,
# so nothing here may peek. Any .rolling() is backward-looking by construction.

def s_tsmom(df, lb):
    return (df.close / df.close.shift(lb) - 1 > 0).astype(float)

def s_tsmom_skip(df, lb, skip):
    return (df.close.shift(skip) / df.close.shift(lb) - 1 > 0).astype(float)

def s_ema(df, f, s):
    return (df.close.ewm(span=f, adjust=False).mean()
            > df.close.ewm(span=s, adjust=False).mean()).astype(float)

def s_donchian(df, lb):
    return (df.close > df.high.rolling(lb).max().shift(1)).astype(float)

def s_zscore(df, lb, k):
    m = df.close.rolling(lb).mean(); sd = df.close.rolling(lb).std()
    return ((df.close - m) / sd < -k).astype(float)

def s_rsi(df, lb, th):
    d = df.close.diff()
    up = d.clip(lower=0).rolling(lb).mean()
    dn = (-d.clip(upper=0)).rolling(lb).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    return (rsi < th).astype(float)

def s_volbreak(df, lb, k):
    rng = (df.high - df.low).rolling(lb).mean()
    return (df.close > df.close.shift(1) + k * rng).astype(float)

def s_tom(df, a, b):
    d = df.index.day
    return pd.Series(((d >= a) | (d <= b)).astype(float), index=df.index)

def s_dow(df, day):
    return pd.Series((df.index.dayofweek == day).astype(float), index=df.index)

def s_accel(df, short, long_):
    r1 = df.close / df.close.shift(short) - 1
    r2 = df.close / df.close.shift(long_) - 1
    return ((r1 > 0) & (r1 > r2 * short / long_)).astype(float)

def s_lowvol(df, lb, q):
    rv = df.close.pct_change().rolling(lb).std()
    return (rv < rv.rolling(252).quantile(q)).astype(float)

def s_range_pos(df, lb, th):
    lo = df.low.rolling(lb).min(); hi = df.high.rolling(lb).max()
    pos = (df.close - lo) / (hi - lo)
    return (pos > th).astype(float)


# ---------------------------------------------------------------- filters
# A filter multiplies a base signal. This is where combinatorics lives.
def f_none(df):   return pd.Series(1.0, index=df.index)
def f_trend200(df): return (df.close > df.close.rolling(200).mean()).astype(float)
def f_trend50(df):  return (df.close > df.close.rolling(50).mean()).astype(float)
def f_vol_calm(df):
    rv = df.close.pct_change().rolling(20).std()
    return (rv < rv.rolling(252).median()).astype(float)
def f_vol_wild(df):
    rv = df.close.pct_change().rolling(20).std()
    return (rv > rv.rolling(252).median()).astype(float)


# ---------------------------------------------------------------- evaluator
def run_one(df, posfn, c, hold=None, vol_target=None):
    """Returns (net return series, position series). No lookahead: shift(1)."""
    pos = posfn(df).fillna(0.0)
    if hold:                                   # fixed holding period variant
        pos = pos.rolling(hold, min_periods=1).max()
    pos = pos.shift(1).fillna(0.0)
    ret = df.close.pct_change().fillna(0.0)
    if vol_target:
        rv = ret.rolling(20).std().replace(0, np.nan)
        pos = pos * (vol_target / (rv * np.sqrt(252))).clip(0, 2).fillna(0)
    turn = pos.diff().abs().fillna(pos.abs())
    return pos * ret - turn * c, pos


def stats(r, pos):
    r = r.dropna()
    if len(r) < 100 or r.std() == 0:
        return None
    eq = (1 + r).cumprod()
    on = (pos.abs() > 1e-9)
    entries = int((on & ~on.shift(1).fillna(False)).sum())
    trades = max(entries, 1)
    exposure = float(on.mean())
    exposure_days = float(on.sum())
    return dict(
        sharpe=float(r.mean() / r.std() * np.sqrt(252)),
        cagr=float(eq.iloc[-1] ** (252 / len(r)) - 1),
        maxdd=float((eq / eq.cummax() - 1).min()),
        trades=trades, entries=entries, exposure_days=exposure_days,
        days=len(r), exposure=exposure,
        total=float(eq.iloc[-1] - 1),
    )


def random_benchmark(df, c, exposure, trades, n=200, seed=0):
    """Matched random entry: same exposure and roughly the same turnover."""
    rng = np.random.default_rng(seed)
    ret = df.close.pct_change().fillna(0.0)
    N = len(ret)
    if N < 100 or exposure <= 0:
        return np.array([])
    out = []
    flip = max(trades, 1) / N
    for _ in range(n):
        raw = (rng.random(N) < flip).cumsum() % 2
        p = pd.Series(raw, index=ret.index).astype(float)
        if p.mean() == 0:
            continue
        p = p * (exposure / max(p.mean(), 1e-9))
        p = p.clip(0, 1)
        turn = p.diff().abs().fillna(0)
        rr = p * ret - turn * c
        if rr.std() > 0:
            out.append(rr.mean() / rr.std() * np.sqrt(252))
    return np.array(out)


def emc(n_trials, sr_std):
    """Expected max Sharpe from pure noise over n_trials (Bailey/Lopez de Prado)."""
    g = 0.5772156649
    if n_trials < 2 or sr_std <= 0:
        return 0.0
    z1 = norm.ppf(1 - 1.0 / n_trials)
    z2 = norm.ppf(1 - 1.0 / (n_trials * np.e))
    return sr_std * ((1 - g) * z1 + g * z2)


def deflated_sharpe(sr, sr_exp_max, n_obs, skew=0.0, kurt=3.0):
    den = np.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-9))
    return float(norm.cdf((sr - sr_exp_max) * np.sqrt(max(n_obs - 1, 1)) / den))


def buyhold_benchmark(df, c, exposure):
    """Same market exposure, no timing: hold a constant fraction of the period.
    This is the benchmark that matters for high-exposure strategies, where a
    matched-random entry degenerates toward the strategy itself."""
    ret = df.close.pct_change().fillna(0.0)
    pos = pd.Series(float(min(max(exposure, 0.0), 1.0)), index=ret.index)
    r = pos * ret            # one entry, one exit: cost is negligible
    if r.std() == 0:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))


def timing_gate(per, panel, costfn, obs_sharpe, rand_pct):
    """G6, corrected.
    Low exposure  (<0.5): matched-random is informative -> require 95th pct.
    High exposure (>=0.5): require beating same-exposure buy-and-hold on Sharpe,
                           since random entry is no longer a discriminating test.
    """
    exp = float(np.mean([v["exposure"] for v in per.values()]))
    if exp < 0.5:
        return rand_pct >= 0.95, f"random pct {rand_pct:.2f} (exp {exp:.2f})"
    bh = float(np.mean([buyhold_benchmark(panel[k], costfn(k), per[k]["exposure"])
                        for k in per]))
    return obs_sharpe > bh, f"sharpe {obs_sharpe:.2f} vs buy&hold {bh:.2f} (exp {exp:.2f})"
