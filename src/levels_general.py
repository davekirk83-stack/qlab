"""
DO LEVELS WORK AT ALL? — a general test across instruments and asset classes.

DK: "Investigate all of this level finding and resistance and trendline research
for application to all charts."

Doc 37 showed levels sharpen the cascade entry. That is a narrow use. The broader
claim — the one every chartist makes — is that price RESPECTS levels generally:
it reverses at support and resistance more often than chance.

THE CONTROL THAT MAKES THIS HONEST
With enough lines drawn, price is always near something. So every real level is
matched against a FAKE level: a random price at the same distance from the market,
tested the same way. If real levels beat fakes, the effect is in the level. If not,
it is in the fact that price mean-reverts near wherever it happens to be.

This is the same discipline that killed four cascade variants earlier today.

MEASURED
  approach    price comes within tolerance of a level it has not just come from
  reject      price turns away without closing decisively through
  break       price closes through by more than the tolerance
  forward     return over N bars after the approach, signed so that a working
              SUPPORT gives positive numbers and a working RESISTANCE gives
              positive numbers when shorted

Universes: survivorship-clean ETFs (daily), crypto majors + alts (daily),
crypto perps (hourly). Horizontals and diagonals reported separately, because
DK specifically asked whether diagonals work too.
"""
import warnings; warnings.filterwarnings("ignore")
import os, glob
import numpy as np, pandas as pd
import structure as ST

RNG = np.random.default_rng(23)

CLEAN_ETF = set("""SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV ACWI
XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK
TLT IEF SHY LQD HYG AGG TIP BND EMB MUB
GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER URA
VNQ IYR VXX""".split())


def load_universe(which):
    out = {}
    if which == "etf":
        for s in sorted(CLEAN_ETF):
            p = f"/home/claude/qlab/data_wide/{s}.csv"
            if os.path.exists(p):
                d = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
                if len(d) > 600:
                    out[s] = d
    elif which == "crypto_daily":
        for p in sorted(glob.glob("/home/claude/qlab/data/*.csv"))[:14] + \
                 sorted(glob.glob("/home/claude/qlab/data_alt/*.csv"))[:40]:
            s = os.path.basename(p)[:-4]
            try:
                d = pd.read_csv(p); d["date"] = pd.to_datetime(d["date"], errors="coerce")
                d = d.dropna(subset=["date"]).set_index("date").sort_index()
            except Exception:
                continue
            if len(d) > 600 and not d.close.le(0).any():
                out[s] = d
    elif which == "crypto_hourly":
        for p in sorted(glob.glob("/home/claude/qlab/data_1h_33/*.csv")):
            s = os.path.basename(p)[:-4]
            d = pd.read_csv(p, parse_dates=["date"]).set_index("date").sort_index()
            if len(d) > 2000:
                out[s] = d
    return out


def approaches(df, levels, start, end, tol_atr=0.4, fwd=10):
    """Every bar in [start,end] where price comes within tolerance of a level.
    Returns records with the forward outcome, signed so positive = level held."""
    H, L, C = df.high.values, df.low.values, df.close.values
    a = ST.atr(df).bfill().values
    rec = []
    for lv in levels:
        p = lv["price"]
        if not np.isfinite(p) or p <= 0:
            continue
        test_n = 0          # how many times THIS level has already been tested
        for i in range(start, min(end, len(df) - fwd - 1)):
            tol = tol_atr * a[i]
            if tol <= 0:
                continue
            # approached from ABOVE -> testing it as SUPPORT
            if L[i] <= p + tol and C[i] > p and C[i - 1] > p + tol:
                fwd_ret = C[i + fwd] / C[i] - 1
                held = C[i + fwd] > p
                test_n += 1
                rec.append(dict(kind=lv["kind"], diagonal=lv["diagonal"],
                                strength=lv["strength"], side="support",
                                test_n=test_n, fwd=fwd_ret, held=held))
            # approached from BELOW -> testing it as RESISTANCE (sign flipped)
            elif H[i] >= p - tol and C[i] < p and C[i - 1] < p - tol:
                fwd_ret = -(C[i + fwd] / C[i] - 1)
                held = C[i + fwd] < p
                test_n += 1
                rec.append(dict(kind=lv["kind"], diagonal=lv["diagonal"],
                                strength=lv["strength"], side="resistance",
                                test_n=test_n, fwd=fwd_ret, held=held))
    return rec


def fake_levels(df, upto, real, band=0.25):
    """One fake level per real level, at a random price the same distance away."""
    px = df.close.values[upto]
    out = []
    for lv in real:
        d = abs(lv["price"] / px - 1)
        sign = 1 if RNG.random() < 0.5 else -1
        jitter = d * RNG.uniform(0.5, 1.5)
        p = px * (1 + sign * jitter)
        if p > 0 and abs(p / px - 1) <= band:
            out.append(dict(price=float(p), kind="FAKE", strength=lv["strength"],
                            diagonal=lv["diagonal"], age=lv["age"]))
    return out


def summarise(rec, lab, pad=30):
    if len(rec) < 60:
        print(f"  {lab:{pad}s} n={len(rec):6d}  too few"); return None
    t = pd.DataFrame(rec)
    r = t.fwd.values
    se = r.std(ddof=1) / np.sqrt(len(r))
    print(f"  {lab:{pad}s} n={len(r):6d}  fwd {r.mean()*100:+7.3f}%  "
          f"held {t.held.mean()*100:5.1f}%  t={r.mean()/se:+6.2f}")
    return dict(n=len(r), mean=r.mean(), held=t.held.mean(), t=r.mean()/se)


def run(which, fwd=10, split=0.5):
    panel = load_universe(which)
    print(f"\n{'='*86}")
    print(f"  {which.upper()}  —  {len(panel)} instruments")
    print(f"{'='*86}")
    real_rec, fake_rec = [], []
    for s, df in panel.items():
        n = len(df)
        cut = int(n * split)
        if cut < 300 or n - cut < 100:
            continue
        try:
            lv = ST.all_levels(df, cut)
        except Exception:
            continue
        if not lv:
            continue
        fk = fake_levels(df, cut, lv)
        real_rec += approaches(df, lv, cut + 1, n - fwd - 1, fwd=fwd)
        fake_rec += approaches(df, fk, cut + 1, n - fwd - 1, fwd=fwd)
    print(f"  levels drawn at the midpoint of each history, tested ONLY on the")
    print(f"  bars after that — {fwd}-bar forward outcome\n")
    a = summarise(real_rec, "REAL levels")
    b = summarise(fake_rec, "FAKE levels (control)")
    if a and b:
        d = a["mean"] - b["mean"]
        se = np.sqrt(a["mean"]**2 / max(a["n"], 1) + b["mean"]**2 / max(b["n"], 1)) or 1
        print(f"  {'REAL minus FAKE':30s} {d*100:+7.3f}pp   "
              f"held {(a['held']-b['held'])*100:+5.1f}pp")
    if real_rec:
        t = pd.DataFrame(real_rec)
        print()
        for lab, sub in (("  horizontal", t[~t.diagonal]), ("  diagonal", t[t.diagonal])):
            summarise(sub.to_dict("records"), lab)
        print()
        for lab, sub in (("  support tests", t[t.side == "support"]),
                         ("  resistance tests", t[t.side == "resistance"])):
            summarise(sub.to_dict("records"), lab)
        print()
        print("  DK: does REPEATED TESTING weaken a level?")
        for k in (1, 2, 3, 4):
            summarise(t[t.test_n == k].to_dict("records"), f"    test #{k}")
        summarise(t[t.test_n >= 5].to_dict("records"), "    test #5+")
        print()
        print("  by level strength:")
        for lo, hi, lab in ((0, 3, "weak (<3)"), (3, 6, "medium (3-5)"),
                            (6, 99, "strong (6+)")):
            summarise(t[(t.strength >= lo) & (t.strength < hi)].to_dict("records"),
                      f"    {lab}")
    return real_rec, fake_rec


if __name__ == "__main__":
    print("DO LEVELS WORK AT ALL? — real levels vs random fake levels")
    print("Positive 'fwd' = the level HELD (support bounced, resistance rejected).")
    for u in ("etf", "crypto_daily", "crypto_hourly"):
        run(u)
