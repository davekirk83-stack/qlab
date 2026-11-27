"""Doc 278 leads, tested on DK v2 longs (+ the 13:00 UTC level), judged like dk_v2_improve: BTC both halves AND the pooled 9 alts.
  L1  Brunel (crypto momentum after one-day abnormal returns): after an abnormal down move, price keeps falling to the END of that day.
      Abnormal = today's move so far (00:00 UTC open -> the ladder's start bar) below -k x the 14-day sigma of daily returns (k = 1.5, 2).
      Variants: (a) skip that ladder; (b) keep the ladder but no fills until the next UTC day starts ("don't bid the knife on the day").
      Plus (c) the same check on YESTERDAY's full-day return (the next day is "mixed" in the paper - expected to add nothing).
  L2  arXiv 2607.27070 (liquidation-cascade early warnings): taker order-flow variance COMPRESSES before cascades.
      Flow = per-15m taker imbalance (2 x taker-buy volume - volume) / volume (Binance kline col 9). Variance over the last 24h vs its
      trailing 30-day distribution; 'compressed' = in the bottom 20% (or 10%). Variant: stand aside (no new ladder) when compressed.
      The paper calls it a population-level regularity only, so the expectation is weak.
All rules use only data up to the ladder's start bar. Costs as v2 (Revolut X maker 0 / taker 0.14%)."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, glob, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import dk_v2_all_charts as A
src = open(os.path.join(HERE, "dk_v2_improve.py")).read().split('if __name__ == "__main__":')[0]
# hooks: o["block"][j] skips a ladder; o["fill_from"][j] = first bar a rung may fill
src = src.replace("        a = ATRP[j]; lvl = L[j - 96:j].min() * 0.997",
                  "        if o.get(\"block\") is not None and o[\"block\"][j]: continue\n        ff = o[\"fill_from\"][j] if o.get(\"fill_from\") is not None else j\n        a = ATRP[j]; lvl = L[j - 96:j].min() * 0.997")
src = src.replace("if not done[r] and k <= j + fillb and L[k] <= rungs[r]:", "if not done[r] and ff <= k <= max(j + fillb, ff + 96) and L[k] <= rungs[r]:")
src = src.replace("                if k > j + fillb: break", "                if k > max(j + fillb, ff + 96): break")
assert src.count("ff <= k") == 1 and src.count("o[\"block\"][j]") == 1
ns = {"__file__": os.path.join(HERE, "dk_v2_improve.py")}; exec(compile(src, "v2h", "exec"), ns); run, stats = ns["run"], ns["stats"]

def taker(sym):
    xs = []
    for f in sorted(glob.glob(f"{A.CO}/{sym}-15m-*.csv")):
        x = pd.read_csv(f, header=None, usecols=[0, 5, 9]); x.columns = ["t", "v", "tb"]
        x["t"] = pd.to_datetime(x.t // 1000 if x.t.iloc[0] > 1e14 else x.t, unit="ms", utc=True); xs.append(x.set_index("t"))
    x = pd.concat(xs).sort_index(); return x[~x.index.duplicated()].astype(float)

def features(d, sym):
    U = d.index; day = U.floor("1D")
    dopen = d.open.resample("1D").first(); dclose = d.close.resample("1D").last(); dret = dclose / dopen - 1
    sig = dret.rolling(14).std().shift(1)
    today = d.close.values / dopen.reindex(day).values - 1                                     # move so far today, at each bar's close
    # a ladder starting at bar j sees bars up to j-1 -> use the previous bar's 'today' move
    today_prev = np.r_[np.nan, today[:-1]]; sigv = sig.reindex(day).values
    yday = dret.shift(1).reindex(day).values
    nextday = (day + pd.Timedelta("1D")); nd_idx = U.searchsorted(nextday)
    t = taker(sym).reindex(U); imb = ((2 * t.tb - t.v) / t.v.replace(0, np.nan))
    var24 = imb.rolling(96, min_periods=80).var(); pct = var24.rolling(96 * 30, min_periods=96 * 20).rank(pct=True).shift(1).values
    return dict(today=today_prev, sig=sigv, yday=yday, nd=nd_idx, pct=pct)

def variants(F):
    N = len(F["today"]); V = {"v2 (base)": {}}
    for k in (1.5, 2.0):
        ab = F["today"] < -k * F["sig"]
        V[f"L1a skip ladder if today < -{k} sigma"] = {"block": np.nan_to_num(ab, nan=0).astype(bool)}
        V[f"L1b no fills until next day if today < -{k} sigma"] = {"fill_from": np.where(np.nan_to_num(ab, nan=0).astype(bool), F["nd"], np.arange(N))}
        V[f"L1c skip ladder if yesterday < -{k} sigma"] = {"block": np.nan_to_num(F["yday"] < -k * F["sig"], nan=0).astype(bool)}
    for q in (0.2, 0.1):
        V[f"L2 stand aside when taker-flow variance in bottom {int(q*100)}%"] = {"block": np.nan_to_num(F["pct"] < q, nan=0).astype(bool)}
    return V

if __name__ == "__main__":
    ALTS = ("ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT")
    res = {}
    for s in ("BTCUSDT",) + ALTS:
        d = A.coin(s); F = features(d, s)
        for lab, o in variants(F).items():
            res.setdefault(lab, {})[s] = run(d, dict(o, ny=True))
        print(s, "done", flush=True)
    rows = []
    for lab, per in res.items():
        b = per["BTCUSDT"]; alts = pd.concat([per[s] for s in ALTS]).sort_index()
        bm, bh1, bh2, bn = stats(b); am, ah1, ah2, an = stats(alts)
        rows.append(dict(change=lab, btc_n=bn, btc_mean=bm, btc_h1=bh1, btc_h2=bh2, btc_total=round(b.sum(), 1),
                         alts_n=an, alts_mean=am, alts_h1=ah1, alts_h2=ah2, alts_total=round(alts.sum(), 1)))
    R = pd.DataFrame(rows); base = R.iloc[0]
    R["keeps"] = (R.btc_mean > base.btc_mean) & (R.btc_h1 > 0) & (R.btc_h2 > 0) & (R.alts_mean > base.alts_mean) & (R.alts_h2 >= base.alts_h2)
    R.to_csv("runs/research/online_leads.csv", index=False); pd.set_option("display.width", 250); print(R.to_string(index=False))
    # what the skipped ladders would have made (were they losers?)
    for lab in [l for l in res if l.startswith(("L1a", "L2"))]:
        b0 = res["v2 (base)"]["BTCUSDT"]; b1 = res[lab]["BTCUSDT"]; gone = b0[~b0.index.isin(b1.index)]
        print(f"{lab}: BTC ladders removed {len(gone)}, their mean {gone.mean():+.3f}%" if len(gone) else f"{lab}: none removed")
