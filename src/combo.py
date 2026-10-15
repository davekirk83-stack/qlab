"""
THE NOVEL COMBINATION: a 2% cascade, conditioned on element state.

Two findings meet here.

  doc 67  close_in_bar, force and lower_wick CONDITION the cascade book:
          perfectly monotone quintile structure, top-minus-bottom spread
          +1.186% at t=+4.14 with 7/7 symbols agreeing. None of these predict
          anything on their own — close_in_bar scored +0.004 as a standalone
          element. They only work as conditioners, which is why doc 57's
          scoring missed them.

  today   the 3% drop threshold was arbitrary. At 2% the edge is unchanged
          (+0.236% vs +0.232%) with 3.5x the trades and t=+7.95 vs +3.40.

And one finding from outside: the on-chain study of 13,182 real profitable
entries found the TIMING signal is volatility and volume (range percentile
d=+0.96, relative volume d=+0.89) while DIRECTION is mean reversion. Our
cascade already is a volatility event faded — so the conditioner to test is
the one the whales appear to use: how big is this bar, and how much volume
came with it.

WHAT IS COMBINED
  trigger    5-minute drop of 2% (the new knee)
  filters    each element at the entry bar, kept only if the quintile
             structure was monotone in doc 67 or matches the whale evidence
  measured   trades per month AND edge per trade, together, because a filter
             that doubles the edge and kills 90% of the trades is worse than
             useless for a stack that needs frequency

The honest risk: these filters were FOUND on this data. A filter chosen for
its top quintile will look good on the sample that chose it. So every
combination is also reported on the 31 symbols that were never used to
develop anything, held separately.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/qlab/src")
import elements as EL

MAKER, TAKER, SLIP = 1.2 / 10000, 4.0 / 10000, 5.0 / 10000
STACK, LEV = 2000.0, 2.0
LIFT, HOLD, DEPTHB, MAXH = 0.008, 10, 0.004, 60
DROP, WIN, TP = 0.02, 5, 0.015

INS = "/home/claude/qlab/data_1m/*.csv"
OOS = "/home/claude/qlab/data_1m_oos/*.csv"


def find_base(C, L, i, n, mw=60):
    lo = L[i]; k = i
    while k < min(i + mw, n - 1):
        if L[k] < lo: lo = L[k]
        if C[k] >= lo * (1 + LIFT): break
        k += 1
    if k >= min(i + mw, n - 1) or C[k] < lo * (1 + LIFT): return None
    j = k; h = 0
    while j < min(k + mw, n - 1):
        if L[j] < lo: return None
        h += 1
        if h >= HOLD: return j, lo
        j += 1
    return None


def harvest(pattern, seen=None):
    rows, months, nsym = [], 0.0, 0
    for p in sorted(glob.glob(pattern)):
        s = os.path.basename(p)[:-4]
        if seen is not None and s in seen:
            continue
        d = pd.read_csv(p)
        if "t" not in d.columns or len(d) < 50000:
            continue
        d["dt"] = pd.to_datetime(d.t, unit="ms")
        d = d.set_index("dt").sort_index()
        hr = d.resample("1h").agg(open=("open", "first"), high=("high", "max"),
                                  low=("low", "min"), close=("close", "last"),
                                  volume=("volume", "sum")).dropna()
        if len(hr) < 400:
            continue
        try:
            F = EL.build(hr)
        except Exception:
            continue
        hidx = hr.index
        C, H, L = d.close.values, d.high.values, d.low.values
        n = len(C); nsym += 1
        months += (d.index[-1] - d.index[0]).days / 30.44
        i = WIN
        while i < n - 2 * MAXH:
            if C[i] / C[i - WIN] - 1 > -DROP:
                i += 1; continue
            b = find_base(C, L, i, n)
            if b is None:
                i += WIN; continue
            j, lo = b
            bid = max(C[j] * (1 - DEPTHB), lo * 1.0002)
            fill = None
            for q in range(j + 1, min(j + 1 + MAXH, n)):
                if L[q] < lo: break
                if L[q] <= bid: fill = q; break
            if fill is None:
                i = j + 1; continue
            px = bid * (1 + MAKER); stop = lo * (1 - 0.0005); tgt = px * (1 + TP)
            if stop >= px:
                i = j + 1; continue
            r = None
            for q in range(fill + 1, min(fill + 1 + MAXH, n)):
                if L[q] <= stop: r = (stop * (1 - SLIP - TAKER)) / px - 1; break
                if H[q] >= tgt: r = (tgt * (1 - MAKER)) / px - 1; break
            if r is None:
                q = min(fill + MAXH, n - 1); r = (C[q] * (1 - MAKER)) / px - 1
            k = hidx.searchsorted(d.index[fill]) - 1
            rec = {"sym": s, "R": r}
            if 250 <= k < len(hidx):
                for key in ("close_in_bar", "force", "lower_wick", "vol_rel",
                            "range_pctile_50", "wr_exhaust_dn", "atr_pct"):
                    if key in F:
                        v = F[key][int(k)]
                        rec[key] = v if np.isfinite(v) else np.nan
            rows.append(rec)
            i = fill + MAXH
    T = pd.DataFrame(rows)
    T.attrs["months"] = months / max(nsym, 1)
    T.attrs["nsym"] = nsym
    return T


def rank_within(T, col):
    return T.groupby("sym")[col].transform(
        lambda v: v.rank(pct=True) if v.notna().sum() > 5 else np.nan)


def score(T, mask, lab, base_months):
    S = T[mask] if mask is not None else T
    S = S.dropna(subset=["R"])
    if len(S) < 40:
        print(f"  {lab:<46} too few ({len(S)})"); return
    r = S.R.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    per_month = len(S) / base_months
    usd = per_month * STACK * LEV * r.mean()
    keep = len(S) / len(T) * 100
    print(f"  {lab:<46}{len(S):>7}{keep:>7.0f}%{per_month:>9.1f}"
          f"{r.mean()*100:>+9.3f}%{r.mean()/se:>+7.2f}{(r>0).mean()*100:>7.1f}%"
          f"{usd:>9,.0f}")


if __name__ == "__main__":
    ins_syms = {os.path.basename(p)[:-4] for p in glob.glob(INS)}
    T = harvest(INS)
    O = harvest(OOS, seen=ins_syms)
    for tag, X in (("IN-SAMPLE (18 symbols)", T), ("OUT-OF-SAMPLE (31 unseen)", O)):
        m = X.attrs["months"]
        print("=" * 100)
        print(f"  {tag}   {X.attrs['nsym']} symbols, {m:.1f} months each, "
              f"{len(X)} raw cascade trades")
        print("=" * 100)
        print(f"  {'filter':<46}{'n':>7}{'kept':>7}{'/month':>9}"
              f"{'edge':>10}{'t':>7}{'win':>8}{'$/mo':>9}")
        score(X, None, "no filter (2% cascade)", m)
        for col in ("close_in_bar", "force", "lower_wick", "vol_rel",
                    "range_pctile_50", "wr_exhaust_dn"):
            if col not in X.columns:
                continue
            q = rank_within(X, col)
            score(X, q >= 0.5, f"{col} >= median", m)
            score(X, q >= 0.7, f"{col} top 30%", m)
        # the combination the whale study points at: big bar AND high volume
        if {"range_pctile_50", "vol_rel"} <= set(X.columns):
            a = rank_within(X, "range_pctile_50"); b = rank_within(X, "vol_rel")
            score(X, (a >= 0.5) & (b >= 0.5), "WHALE: big bar AND high volume", m)
        if {"close_in_bar", "vol_rel"} <= set(X.columns):
            a = rank_within(X, "close_in_bar"); b = rank_within(X, "vol_rel")
            score(X, (a >= 0.5) & (b >= 0.5), "close_in_bar AND high volume", m)
        print()
