"""
ALGORITHMIC EXECUTION FOOTPRINT — the part you can see on the chart.

DK: "Like it or not these are a major market feature now and you can sometimes
see it in the chart."

Correct, and it needs no special data feed. A TWAP or VWAP algorithm working a
large parent order slices it into many child orders of similar size at regular
intervals. That leaves a signature humans do not leave:

    UNIFORM VOLUME      consecutive bars trade near-identical size. Discretionary
                        flow is bursty; a scheduler is not.
    UNIFORM RANGE       bar ranges cluster tightly — the algo is not chasing,
                        it is filling to a schedule.
    STAIRCASE PRICE     price drifts one direction in small, equal steps rather
                        than impulsively.
    LOW RANGE/MOVE      lots of volume, little net travel: someone is absorbing.

Each is measured as a coefficient of variation over a rolling window: low CV =
machine-like. The composite "footprint score" is how many of them are in their
most uniform decile at once.

THE TRADABLE QUESTION, and there are two opposed hypotheses

  CONTINUATION  a parent order is not finished. If a programme is pushing price
                one way, it keeps pushing until it is done, so the move extends.
  EXHAUSTION    the programme is a known, finite size. When it completes, the
                pressure vanishes and price snaps back.

These predict opposite trades, so the test is directional and both are measured:
the forward move in the direction the footprint is pushing, and against it.

Controls: matched random entries, hold-40 / stop-1.5-ATR (doc 44). Because the
footprint is a STATE rather than an EVENT, it is deduplicated hard — a state
that persists for 200 bars must count once, not 200 times. This is the doc 38
state-vs-event error, which fired on 55.4% of SPY bars.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import structure as ST
from levels_general import load_universe

RNG = np.random.default_rng(1717)
HOLD = 40
WIN = 20            # bars over which uniformity is assessed


def cv(x, win):
    s = pd.Series(x)
    m = s.rolling(win).mean()
    sd = s.rolling(win).std()
    return (sd / m.replace(0, np.nan)).values


def footprint(df, win=WIN):
    """Returns the component uniformity measures and a composite score."""
    C, H, L = df.close.values, df.high.values, df.low.values
    rng = H - L
    vol = df.volume.values if "volume" in df.columns else np.full(len(C), np.nan)
    out = {}
    out["cv_volume"] = cv(vol, win)
    out["cv_range"] = cv(rng, win)
    # staircase: net travel relative to the sum of absolute bar moves.
    # A clean one-way grind has |net| close to the sum; chop has it near zero.
    d = np.diff(C, prepend=C[0])
    net = pd.Series(d).rolling(win).sum().abs().values
    gross = pd.Series(np.abs(d)).rolling(win).sum().values
    out["directionality"] = net / np.where(gross > 0, gross, np.nan)
    # absorption: volume high, travel low
    a = ST.atr(df).bfill().values
    vz = (pd.Series(vol) / pd.Series(vol).rolling(200).mean()).values
    with np.errstate(invalid="ignore", divide="ignore"):
        out["absorption"] = vz / np.where(a > 0, (net / a), np.nan)
    return out


def pct_rank(x, win=500):
    return pd.Series(x).rolling(win, min_periods=200)\
             .apply(lambda v: (v[-1] > v[:-1]).mean(), raw=True).values


def hold_exit(df, bar, entry, stop, hold=HOLD, short=False):
    H, L, C = df.high.values, df.low.values, df.close.values
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    last = bar + hold
    if last > len(C) - 1:
        return None
    for j in range(bar + 1, last + 1):
        if (not short and L[j] <= stop) or (short and H[j] >= stop):
            return -1.0
    d = (C[last] - entry) if not short else (entry - C[last])
    return float(d / risk)


def dedupe(idx, gap=HOLD):
    out, last = [], -10**9
    for i in idx:
        if i - last >= gap:
            out.append(i); last = i
    return out


def run(which):
    panel = load_universe(which)
    rows = []
    for s, df in panel.items():
        if len(df) < 1200 or "volume" not in df.columns:
            continue
        f = footprint(df)
        C = df.close.values
        a = ST.atr(df).bfill().values
        n = len(C)
        # uniform = LOW cv; so rank and take the bottom decile
        uv = pct_rank(f["cv_volume"])
        ur = pct_rank(f["cv_range"])
        dr = f["directionality"]
        # composite: both volume AND range unusually uniform, and price grinding
        comp = (uv <= 0.10) & (ur <= 0.10) & (dr >= 0.5)
        # which way is the programme pushing?
        d20 = np.full(n, np.nan)
        d20[WIN:] = C[WIN:] - C[:-WIN]

        idx = [i for i in np.flatnonzero(comp)
               if 600 < i < n - HOLD - 2 and a[i] > 0 and np.isfinite(d20[i])]
        for i in dedupe(idx):
            push_up = d20[i] > 0
            # CONTINUATION: trade WITH the push
            stop = C[i] - 1.5 * a[i] if push_up else C[i] + 1.5 * a[i]
            rc = hold_exit(df, i, C[i], stop, short=not push_up)
            # EXHAUSTION: trade AGAINST it
            stop2 = C[i] + 1.5 * a[i] if push_up else C[i] - 1.5 * a[i]
            re = hold_exit(df, i, C[i], stop2, short=push_up)
            if rc is not None and re is not None:
                rows.append(dict(sym=s, grp="REAL", cont=rc, exh=re,
                                 up=bool(push_up)))
        for _ in range(len(dedupe(idx))):
            q = int(RNG.integers(600, max(601, n - HOLD - 2)))
            if a[q] <= 0 or not np.isfinite(d20[q]):
                continue
            push_up = d20[q] > 0
            stop = C[q] - 1.5 * a[q] if push_up else C[q] + 1.5 * a[q]
            rc = hold_exit(df, q, C[q], stop, short=not push_up)
            stop2 = C[q] + 1.5 * a[q] if push_up else C[q] - 1.5 * a[q]
            re = hold_exit(df, q, C[q], stop2, short=push_up)
            if rc is not None and re is not None:
                rows.append(dict(sym=s, grp="CONTROL", cont=rc, exh=re,
                                 up=bool(push_up)))
    return pd.DataFrame(rows)


def line(lab, r, base=None, pad=30):
    r = np.asarray(r, dtype=float); r = r[np.isfinite(r)]
    if len(r) < 40:
        print(f"  {lab:{pad}s} n={len(r):5d}  too few"); return None
    se = r.std(ddof=1) / np.sqrt(len(r))
    d = f"   vs control {r.mean()-base:+6.3f}R" if base is not None else ""
    print(f"  {lab:{pad}s} n={len(r):5d}  {r.mean():+6.3f}R  t={r.mean()/se:+6.2f}  "
          f"win {float((r>0).mean())*100:5.1f}%{d}")
    return r.mean()


if __name__ == "__main__":
    print("ALGO EXECUTION FOOTPRINT — uniform volume + uniform range + grinding price")
    print("Two opposed hypotheses: the programme CONTINUES, or it EXHAUSTS.\n")
    for which in ("crypto_hourly", "etf"):
        T = run(which)
        print("=" * 92)
        print(f"  {which.upper()}   footprint bars detected: "
              f"{int((T.grp=='REAL').sum()) if len(T) else 0}")
        print("=" * 92)
        if len(T) < 100:
            print("  too few\n"); continue
        R = T[T.grp == "REAL"]; K = T[T.grp == "CONTROL"]
        bc = line("control, with the push", K.cont.values)
        line("CONTINUATION (with push)", R.cont.values, bc)
        print()
        be = line("control, against", K.exh.values)
        line("EXHAUSTION (against push)", R.exh.values, be)
        print()
        print("  split by push direction (symmetry check — doc 47 rule 2):")
        for u, lab in ((True, "programme pushing UP"), (False, "pushing DOWN")):
            line(f"    {lab}, continuation", R[R.up == u].cont.values,
                 K[K.up == u].cont.values.mean() if (K.up == u).sum() > 40 else None)
        print()
