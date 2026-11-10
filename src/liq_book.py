"""LIQ book — BTC liquidation-cluster ladder (doc 225; DK 10 Nov 15:52-16:15: liquidation taps, "it can surely be put to use").
Built from doc 224's findings, on 15-min BTC (Binance 1-min 2020-26), with Revolut X's real fees: maker 0% (resting limits), taker 0.09% (+0.05% slip).
 entry : resting limit BUY at each live LONG liquidation cluster that still has other live long clusters below it within 10% (not 'cleared',
         addendum 2). Half at the cluster, half 1% lower (normal pierce, extra-dip check). Fill = first touch.
 skip  : the previous bar was toxic selling still accelerating (top-20% one-sidedness vs 30 days, sellers, rising) — addendum 1;
         optional: taps in the first 2h after the New York open (clusters get run there, addendum 5).
 target: resting limit SELL at the FARTHEST live SHORT cluster within 10% above at the tap (addendum 2); none -> skip.
 stop  : 3% under the cluster (90th-percentile overshoot, addendum 5), market (taker). Time exit 7 days (taker).
R = % return on the full two-rung position. Same-bar stop and target -> stop (conservative)."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import liq_session_test as S, toxicity_test as TX
H, L, C, O, N, IX = S.H, S.L, S.C, S.O, S.N, S.IX
TAKER, MAKER, SLIP, STOP, RUNG2, W = 0.0009, 0.0, 0.0005, 0.03, 0.01, 4 * 24 * 7
U = IX.tz_localize("UTC") if IX.tz is None else IX.tz_convert("UTC"); ny = U.tz_convert("America/New_York")
NYWIN = ((ny.hour * 60 + ny.minute) >= 570) & ((ny.hour * 60 + ny.minute) < 690) & (ny.dayofweek < 5)
import re
_cpi = re.search(r'CPI = """(.*?)"""', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_fade_test.py")).read(), re.S).group(1).split()
_cpi += """2020-01-14 2020-02-13 2020-03-11 2020-04-10 2020-05-12 2020-06-10 2020-07-14 2020-08-12 2020-09-11 2020-10-13 2020-11-12 2020-12-10
2021-01-13 2021-02-10 2021-03-10 2021-04-13 2021-05-12 2021-06-10 2021-07-13 2021-08-11 2021-09-14 2021-10-13 2021-11-10 2021-12-10""".split()
CPI_T = sorted(pd.Timestamp(d + " 08:30", tz="America/New_York").tz_convert("UTC") for d in set(_cpi))
CPI_J = np.searchsorted(U.values, np.array([t.to_datetime64() for t in CPI_T]))     # bar index of the release (bar starting at 08:30)
_dc = pd.Series(C, index=U).resample("1D").last(); _ma = _dc.rolling(200).mean()
BULL = pd.Series((_dc > _ma).shift(1).fillna(False).values, index=_dc.index).reindex(U.floor("1D")).fillna(False).values.astype(bool)   # yesterday's daily close vs its 200-day
CPI_BLOCK = np.zeros(N, bool)
for cj in CPI_J:
    if cj < N: CPI_BLOCK[max(0, cj - 1):cj + 8] = True                                # no fills from 08:15 to 10:30 New York
TOXACC = (np.nan_to_num(TX.RANK) >= 0.8) & (np.nan_to_num(TX.SIGN) < 0) & ~TX.COOL
def events(ny_filter=False, cpi=False, regime=False):
    ev = []
    for k in np.argsort(S.TL):
        j = S.TL[k]; lvl = S.LL[k]
        if j >= N - W - 2 or j < 2000: continue
        liveL = (S.SL <= j - 1) & (S.TL > j - 1); liveS = (S.SS <= j - 1) & (S.TS > j - 1)
        if not (liveL & (S.LL < lvl) & (S.LL > lvl * 0.90)).any(): continue
        up = S.LS[liveS & (S.LS > lvl) & (S.LS < lvl * 1.10)]
        if not len(up) or TOXACC[j - 1] or (ny_filter and NYWIN[j]) or (cpi and CPI_BLOCK[j]) or (regime and not BULL[j]): continue
        ev.append((j, lvl, up.max(), up.min()))
    e = pd.DataFrame(ev, columns=["j", "lvl", "tgt", "near"]).drop_duplicates(subset=["j"], keep="first")
    return e
def trade(j, lvl, tgt, cm=1.0, stop_f=STOP, hold=W, cpi=False):
    stop, r2 = lvl * (1 - stop_f), lvl * (1 - RUNG2); e = min(N - 1, j + hold)
    if cpi:
        nx = CPI_J[np.searchsorted(CPI_J, j + 1)] if np.searchsorted(CPI_J, j + 1) < len(CPI_J) else 10 ** 9
        if nx - 1 <= e: e = max(j, nx - 2)                                            # flat by the close of the 08:00-08:15 bar
    lo, hi = L[j:e + 1], H[j:e + 1]; hi = hi.copy(); hi[0] = -np.inf                 # no target on the fill bar
    ks = np.argmax(lo <= stop) if (lo <= stop).any() else 10 ** 9; kt = np.argmax(hi >= tgt) if (hi >= tgt).any() else 10 ** 9
    end = min(ks, kt, e - j); got2 = (lo[:end + 1] <= r2).any(); avg = (lvl + r2) / 2 if got2 else lvl; size = 1.0 if got2 else 0.5
    if ks <= kt and ks < 10 ** 9: px, fee = stop * (1 - SLIP), TAKER
    elif kt < 10 ** 9: px, fee = tgt, MAKER
    else: px, fee = C[e] * (1 - SLIP), TAKER
    return size * ((px * (1 - cm * fee)) / (avg * (1 + cm * MAKER)) - 1) * 100 - (cm - 1) * size * SLIP * 100, (end, ks <= kt and ks < 10 ** 9, kt < ks)
_E = {}
def target_px(lvl, tgt, near, mode):
    return {"farthest": tgt, "nearest": near, "2%": lvl * 1.02, "3%": lvl * 1.03, "1.5%": lvl * 1.015}[mode]
def build(cm=1.0, rnd=None, ny_filter=False, one_at_a_time=False, cpi=False, mode="farthest", stop_f=STOP, hold=W, regime=False):
    key = (ny_filter, cpi, regime)
    if key not in _E: _E[key] = events(ny_filter, cpi, regime)
    e = _E[key]; rows = []
    if rnd is not None:                                    # random-entry benchmark: same count, random bars, same target/stop distances
        g = np.random.default_rng(); js = g.integers(2000, N - W - 2, len(e)); k = g.permutation(len(e))
        for j, (lvl0, tgt0, nr0) in zip(js, e[["lvl", "tgt", "near"]].values[k]):
            p = O[j]; r, _ = trade(j, p, p * target_px(lvl0, tgt0, nr0, mode) / lvl0, cm, stop_f, hold, cpi); rows.append((IX[j], r))
    else:
        busy = -1
        for j, lvl, tgt, nr in e.values:
            j = int(j)
            if one_at_a_time and j <= busy: continue
            r, (end, _, _) = trade(j, lvl, target_px(lvl, tgt, nr, mode), cm, stop_f, hold, cpi); rows.append((IX[j], r)); busy = j + end
    return pd.DataFrame(rows, columns=["t", "R"]).assign(m="BTC")
if __name__ == "__main__" and "grid" in sys.argv:
    import standard_test as ST, itertools
    res = []
    for mode, st_, hd in itertools.product(["nearest", "1.5%", "2%", "3%", "farthest"], [0.02, 0.03, 0.04], [4 * 24, 4 * 24 * 3, 4 * 24 * 7]):
        b = lambda cm=1.0, rnd=None: build(cm, rnd, cpi=True, mode=mode, stop_f=st_, hold=hd)
        out, t = ST.judge(f"LIQ grid tgt {mode} stop {st_:.0%} hold {hd // 96}d +CPI", "liquidation clusters (crypto, Revolut X costs)", ["BTC"], b, random_runs=0, quiet=True)
        res.append((mode, st_, hd // 96, out["n"], out["mean"], out["clustered_t"], out["years_pos"], out["last5y"], out["last12m"], out["verdict"]))
    r = pd.DataFrame(res, columns=["target", "stop", "days", "n", "mean%", "clust_t", "years+", "last5y", "last12m", "verdict"])
    print(r.sort_values("clust_t", ascending=False).to_string(index=False)); r.to_csv("runs/gate/liq_grid.csv", index=False)
if __name__ == "__main__" and "regime" in sys.argv:
    import standard_test as ST
    for mode, st_, hd in (("nearest", 0.04, 288), ("3%", 0.04, 288), ("1.5%", 0.04, 672), ("farthest", 0.03, 672), ("3%", 0.03, 288)):
        for oat in (False, True):
            b = lambda cm=1.0, rnd=None: build(cm, rnd, cpi=True, regime=True, mode=mode, stop_f=st_, hold=hd, one_at_a_time=oat)
            out, t = ST.judge(f"LIQ +200d +CPI tgt {mode} stop {st_:.0%} hold {hd // 96}d{' one-at-a-time' if oat else ''}", "liquidation clusters (crypto, Revolut X costs)", ["BTC"], b, random_runs=40)
            y = t.groupby(t.t.dt.year).R.agg(["count", "mean"]); print("      by year:", "  ".join(f"{i}: n{int(r['count'])} {r['mean']:+.2f}%" for i, r in y.iterrows()), f"| win {100 * (t.R > 0).mean():.0f}%\n")
if __name__ == "__main__" and "grid" not in sys.argv and "regime" not in sys.argv:
    import standard_test as ST
    for nm, kw in (("LIQ ladder (all taps)", {}), ("LIQ ladder, no NY-open taps", {"ny_filter": True}), ("LIQ ladder, one position at a time", {"one_at_a_time": True})):
        b = lambda cm=1.0, rnd=None, kw=kw: build(cm, rnd, **kw)
        out, t = ST.judge(nm, "liquidation clusters (crypto, Revolut X costs)", ["BTC"], b, random_runs=40)
        y = t.groupby(t.t.dt.year).R.agg(["count", "mean", "sum"]); print("      by year:", "  ".join(f"{i}: n{int(r['count'])} {r['mean']:+.2f}% (sum {r['sum']:+.0f})" for i, r in y.iterrows()))
        print(f"      win {100 * (t.R > 0).mean():.0f}%, worst {t.R.min():+.2f}%, median {t.R.median():+.2f}%\n")
