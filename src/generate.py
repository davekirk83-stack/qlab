"""
Candidate generator. Produces the full search space as (name, builder) pairs.

A candidate is a PANEL strategy: the same rule applied to every instrument,
equal-weighted. This is deliberate.
  - It costs ONE trial, not one per instrument, so the trial count stays honest.
  - It forces breadth. A rule that only works on BTC fails here, which is correct:
    the previous programme's one surviving "edge" was 86% concentrated in BTC/ETH.
"""
import itertools, numpy as np, pandas as pd
import core as C

FAMILIES = {
    "tsmom":    (C.s_tsmom,      [(lb,) for lb in (20, 40, 60, 90, 120, 180, 250)]),
    "tsmom_sk": (C.s_tsmom_skip, [(lb, sk) for lb in (60, 120, 250) for sk in (5, 10, 21)]),
    "ema":      (C.s_ema,        [(f, s) for f in (5, 10, 20, 50) for s in (20, 50, 100, 200) if f < s]),
    "donch":    (C.s_donchian,   [(lb,) for lb in (10, 20, 40, 55, 100)]),
    "zscore":   (C.s_zscore,     [(lb, k) for lb in (10, 20, 50) for k in (1.0, 1.5, 2.0, 2.5)]),
    "rsi":      (C.s_rsi,        [(lb, th) for lb in (2, 5, 14) for th in (5, 10, 20, 30)]),
    "volbrk":   (C.s_volbreak,   [(lb, k) for lb in (10, 20, 50) for k in (0.5, 1.0, 1.5)]),
    "tom":      (C.s_tom,        [(a, b) for a in (26, 28, 30) for b in (2, 3, 5)]),
    "dow":      (C.s_dow,        [(d,) for d in range(5)]),
    "accel":    (C.s_accel,      [(s, l) for s in (5, 10, 20) for l in (60, 120, 250)]),
    "lowvol":   (C.s_lowvol,     [(lb, q) for lb in (20, 60) for q in (0.3, 0.5, 0.7)]),
    "rangep":   (C.s_range_pos,  [(lb, th) for lb in (20, 50, 100) for th in (0.6, 0.8, 0.9)]),
}

FILTERS = {
    "nofilt":  C.f_none,
    "tr200":   C.f_trend200,
    "tr50":    C.f_trend50,
    "calm":    C.f_vol_calm,
    "wild":    C.f_vol_wild,
}

HOLDS = [None, 5, 20]      # exit style: signal-off, or fixed N-bar hold


def candidates():
    out = []
    for fam, (fn, params) in FAMILIES.items():
        for p in params:
            for fname, ffn in FILTERS.items():
                for h in HOLDS:
                    name = f"{fam}({','.join(map(str,p))})|{fname}|hold={h}"
                    def make(fn=fn, p=p, ffn=ffn):
                        return lambda df: fn(df, *p) * ffn(df)
                    out.append((name, make(), h))
    return out


if __name__ == "__main__":
    c = candidates()
    print(f"{len(c)} candidates")
    print(f"{len(FAMILIES)} families x params x {len(FILTERS)} filters x {len(HOLDS)} exit styles")


# ---- second sweep: classical chart patterns ----
def pattern_candidates():
    import patterns as P
    out = []
    for pname, (fn, params) in P.PATTERNS.items():
        for p in params:
            for cname, cfn in P.CONFIRMS.items():
                for fname, ffn in FILTERS.items():
                    for h in (5, 10, 20):      # patterns need a holding period
                        name = f"{pname}({','.join(map(str,p))})|{cname}|{fname}|hold={h}"
                        def make(fn=fn, p=p, cfn=cfn, ffn=ffn):
                            return lambda df: fn(df, *p) * cfn(df) * ffn(df)
                        out.append((name, make(), h))
    return out
