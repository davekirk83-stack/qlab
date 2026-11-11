"""Doc 228 — Copy the champions (DK 11 Nov 06:47: "copying the techniques of the most successful publicly listed traders… If they are survivors
then that is a good thing"). Each trader's published signature set-up, coded from their own books, then MADE TO WORK on IG markets at IG's real
costs: the pre-specified refinements are the ones that made our live books work (200-day regime for longs, the market each method was built for,
exit variants from the trader's own writing). Standard test v3 for every version; the report is the best working version of each.

Traders (verified public records):
  Larry Williams  — 1987 Robbins World Cup (+11,376%); "Long-Term Secrets to Short-Term Trading": volatility breakout, Oops!, first profitable open exit.
  Linda Raschke   — 35+ years, CTA; "Street Smarts" (with Connors): Turtle Soup, 80-20s, Holy Grail.
  Toby Crabel     — Crabel Capital; "Day Trading with Short-Term Price Patterns and Opening Range Breakout": NR7 / NR4 breakout.
  Richard Dennis  — Turtle Traders: 20-day breakout (System 1), 2N stop, 10-day exit.
(Connors' RSI(2)/TPS — already live; Minervini's VCP needs single stocks, which failed at IG share costs in doc 219.)
Fills on daily bars: stop orders fill at the level, or the open if it gaps through; a stop and the entry on the same day = stopped (worst case)."""
import warnings; warnings.filterwarnings("ignore")
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fifty_ideas as F, std_books as SB, standard_test as ST
IDX = ["SPX", "NDX", "DJI", "RUT", "DAX", "FTSE", "N225"]; OTH = ["GOLD", "SILVER", "OIL", "COPPER", "TNOTE", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
FY = 0.06 / 365 * 1.4

def ema(x, n): return x.ewm(span=n, adjust=False).mean()
def trade(k, j, s, e, stop, ex, n=5):
    """Simulate one trade entered on day j at price e, side s, initial stop. ex: 'fpo' first profitable open (Williams), 'close' same-day close,
    'n' exit at the next open after n days, 'trail10' Turtle 10-day opposite extreme. Returns R in ATR(14) of day j-1."""
    d = F.D[k]; O, H, L, C, A = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values; N = len(C); a = A[j - 1]
    if not np.isfinite(a) or a <= 0: return None
    gapbad = k == "FTSE"                                     # Yahoo FTSE opens are faulty: never fill 'at the open'
    if (s == 1 and L[j] <= stop) or (s == -1 and H[j] >= stop): x, t = stop, j
    elif ex == "close": x, t = C[j], j
    else:
        x = None; t = j + 1
        while t < N:
            if ex == "fpo" and not gapbad and s * (O[t] - e) > 0: x = O[t]; break
            if (s == 1 and L[t] <= stop) or (s == -1 and H[t] >= stop): x = stop if gapbad else (min(stop, O[t]) if s == 1 else max(stop, O[t])); break
            if ex == "trail10" and t >= 10:
                lv = L[t - 10:t].min() if s == 1 else H[t - 10:t].max()
                if (s == 1 and L[t] <= lv) or (s == -1 and H[t] >= lv): x = lv; break
            if ex in ("n", "fpo") and t - j >= n:
                x = C[t] if gapbad or t + 1 >= N else O[t + 1]; break
            t += 1
        if x is None: return None
    cost = F.COST.get(k, .0005) * (e + x); fund = FY * e * (t - j) if s == 1 else 0
    return (s * (x - e) - cost - fund) / a, t

def run(k, gen, ex, n, regime, sides, rnd):
    """gen(d) -> list of (j, side, entry_level or None for 'at the open', stop). Signals with a random-entry benchmark when rnd is given."""
    d = F.D[k]; out = []; busy = -1; up = d.close > d.close.rolling(200).mean(); dn = ~up
    sig = gen(d)
    if rnd is not None:
        g = np.random.default_rng(); js = g.choice(np.arange(220, len(d) - 3), size=min(len(sig), len(d) - 230), replace=False)
        sig = [(int(j), s_, d.open.values[j], d.open.values[j] - s_ * abs(lv - st) if lv is not None else d.open.values[j] - s_ * d.atr.values[j - 1])
               for j, (_, s_, lv, st) in zip(sorted(js), sig)]
    for j, s, lv, st in sig:
        if j <= busy or j >= len(d) - 1 or s not in sides: continue
        if regime and ((s == 1 and not up.iloc[j - 1]) or (s == -1 and not dn.iloc[j - 1])): continue
        O, H, L = d.open.values[j], d.high.values[j], d.low.values[j]
        if lv is None: e = O
        else:
            if (s == 1 and H < lv) or (s == -1 and L > lv): continue      # the stop order never filled
            e = lv if k == "FTSE" else (max(lv, O) if s == 1 else min(lv, O))
        r = trade(k, j, s, e, st, ex, n)
        if r: out.append((d.index[j], r[0], k)); busy = r[1]
    return out

# ---------------- set-ups (all decided from bars up to j-1; level/stop for day j)
def williams_vb(kf=0.6):
    def g(d):
        O, H, L, C = d.open.values, d.high.values, d.low.values, d.close.values; R = H - L
        return [(j, 1, O[j] + kf * R[j - 1], O[j] - kf * R[j - 1]) for j in range(2, len(d))] + \
               [(j, -1, O[j] - kf * R[j - 1], O[j] + kf * R[j - 1]) for j in range(2, len(d))]
    return g
def williams_oops(d):
    O, H, L = d.open.values, d.high.values, d.low.values; a = d.atr.values; out = []
    for j in range(2, len(d)):
        if O[j] < L[j - 1]: out.append((j, 1, L[j - 1], L[j - 1] - a[j - 1]))
        if O[j] > H[j - 1]: out.append((j, -1, H[j - 1], H[j - 1] + a[j - 1]))
    return out
def raschke_turtle_soup(d):
    H, L, a = d.high.values, d.low.values, d.atr.values; out = []
    for j in range(25, len(d)):
        lo20 = L[j - 21:j - 1].min(); k_lo = j - 21 + int(np.argmin(L[j - 21:j - 1]))
        if L[j - 1] < lo20 and (j - 1 - k_lo) >= 4: out.append((j, 1, lo20, L[j - 1] - 0.1 * a[j - 1]))
        hi20 = H[j - 21:j - 1].max(); k_hi = j - 21 + int(np.argmax(H[j - 21:j - 1]))
        if H[j - 1] > hi20 and (j - 1 - k_hi) >= 4: out.append((j, -1, hi20, H[j - 1] + 0.1 * a[j - 1]))
    return out
def raschke_8020(d):
    O, H, L, C, a = d.open.values, d.high.values, d.low.values, d.close.values, d.atr.values; out = []
    for j in range(2, len(d)):
        r = H[j - 1] - L[j - 1]
        if r <= 0: continue
        po, pc = (O[j - 1] - L[j - 1]) / r, (C[j - 1] - L[j - 1]) / r
        if po >= 0.8 and pc <= 0.2: out.append((j, 1, L[j - 1], L[j - 1] - 0.5 * a[j - 1]))      # traded below yesterday's low, buy back above it
        if po <= 0.2 and pc >= 0.8: out.append((j, -1, H[j - 1], H[j - 1] + 0.5 * a[j - 1]))
    return out
def raschke_holy_grail(d):
    ad = SB.adx(d).values; e20 = ema(d.close, 20).values; H, L = d.high.values, d.low.values; out = []
    for j in range(30, len(d)):
        if ad[j - 1] > 30 and ad[j - 1] >= ad[j - 6]:
            if L[j - 1] <= e20[j - 1] < H[j - 1] and d.close.values[j - 1] > e20[j - 1] * 0.98: out.append((j, 1, H[j - 1], L[j - 1]))
            if H[j - 1] >= e20[j - 1] > L[j - 1] and d.close.values[j - 1] < e20[j - 1] * 1.02: out.append((j, -1, L[j - 1], H[j - 1]))
    return out
def crabel_nr7(look=7):
    def g(d):
        H, L = d.high.values, d.low.values; R = H - L; out = []
        for j in range(look + 1, len(d)):
            if R[j - 1] == R[j - look:j].min(): out += [(j, 1, H[j - 1], L[j - 1]), (j, -1, L[j - 1], H[j - 1])]
        return out
    return g
def turtle20(d):
    H, L, a = d.high.values, d.low.values, d.atr.values; out = []
    for j in range(22, len(d)):
        out.append((j, 1, H[j - 21:j - 1].max() + 1e-9 if H[j - 1] < H[j - 21:j - 1].max() else np.inf, 0))  # placeholder, replaced below
    out = []
    for j in range(22, len(d)):
        hi, lo = H[j - 20:j].max(), L[j - 20:j].min()
        out += [(j, 1, hi, hi - 2 * a[j - 1]), (j, -1, lo, lo + 2 * a[j - 1])]
    return out

BOOKS = {   # name: (set-up, markets, [(variant label, exit, n, regime, sides)])
    "Williams volatility breakout": (williams_vb(0.6), IDX + OTH, [("fpo, both", "fpo", 5, False, (1, -1)), ("fpo, long + 200d", "fpo", 5, True, (1,)),
                                                                   ("fpo, both + regime", "fpo", 5, True, (1, -1)), ("same-day close, long + 200d", "close", 0, True, (1,))]),
    "Williams Oops!": (williams_oops, IDX + OTH, [("same-day close, both", "close", 0, False, (1, -1)), ("fpo, both", "fpo", 5, False, (1, -1)),
                                                  ("fpo, long + 200d", "fpo", 5, True, (1,)), ("fpo, both + regime", "fpo", 5, True, (1, -1))]),
    "Raschke Turtle Soup": (raschke_turtle_soup, IDX + OTH, [("3 days, both", "n", 3, False, (1, -1)), ("fpo, both", "fpo", 5, False, (1, -1)),
                                                             ("fpo, long + 200d", "fpo", 5, True, (1,)), ("5 days, long + 200d", "n", 5, True, (1,))]),
    "Raschke 80-20": (raschke_8020, IDX + OTH, [("same-day close, both", "close", 0, False, (1, -1)), ("fpo, both", "fpo", 5, False, (1, -1)),
                                                ("fpo, long + 200d", "fpo", 5, True, (1,)), ("3 days, both + regime", "n", 3, True, (1, -1))]),
    "Raschke Holy Grail": (raschke_holy_grail, IDX + OTH, [("5 days, both", "n", 5, False, (1, -1)), ("10-day trail, both", "trail10", 60, False, (1, -1)),
                                                           ("5 days, both + regime", "n", 5, True, (1, -1)), ("10-day trail, long + 200d", "trail10", 60, True, (1,))]),
    "Crabel NR7 breakout": (crabel_nr7(7), IDX + OTH, [("same-day close, both", "close", 0, False, (1, -1)), ("fpo, both", "fpo", 5, False, (1, -1)),
                                                      ("3 days, both + regime", "n", 3, True, (1, -1)), ("fpo, long + 200d", "fpo", 5, True, (1,))]),
    "Turtles System 1 (20-day)": (turtle20, IDX + OTH, [("10-day exit, both", "trail10", 250, False, (1, -1)), ("10-day exit, both + regime", "trail10", 250, True, (1, -1)),
                                                       ("10-day exit, long + 200d", "trail10", 250, True, (1,))]),
}

def builder(gen, mk, ex, n, regime, sides):
    def b(cm=1.0, rnd=None):
        with SB.cost(cm): return SB.mk([r for k in mk for r in run(k, gen, ex, n, regime, sides, rnd)])
    return b

if __name__ == "__main__":
    core = SB.core(); best = []
    only = sys.argv[1:]
    for name, (gen, mk, vs) in BOOKS.items():
        if only and not any(o.lower() in name.lower() for o in only): continue
        print(f"\n=== {name}", flush=True); res = []
        for lab, ex, n, rg, sd in vs:
            out, t = ST.judge(f"{name} — {lab}", "champions (doc 228)", mk, builder(gen, mk, ex, n, rg, sd), core=core, random_runs=int(os.environ.get("CHAMP_RND", "40")), quiet=True)
            bym = t.groupby("m").R.mean(); good = sorted(bym[bym > 0].index)
            print(f"  {out['verdict']:4s} {lab:32s} n {out['n']:5d} ({out['n'] / 27:.0f}/yr) mean {out['mean']:+.3f} cl.t {out['clustered_t']:+.2f} | years+ {out['years_pos']} "
                  f"| last5y {out['last5y']:+.3f} last12m {out['last12m']:+.3f} | x1.5 {out['costs15']:+.3f} | rnd95 {out['random95']} | adds {out.get('adds', '')}", flush=True)
            res.append((out, lab, ex, n, rg, sd, t))
        # make it work: the best variant, then markets chosen WALK-FORWARD (each year trades only the markets that were positive in the earlier years)
        o, lab, ex, n, rg, sd, t = max(res, key=lambda r: (r[0]["verdict"] != "FAIL", r[0]["clustered_t"]))
        t = t.copy(); t["y"] = t.t.dt.year; keep = []
        for y in sorted(t.y.unique()):
            past = t[t.y < y]
            if past.y.nunique() < 8: continue
            okm = past.groupby("m").R.mean(); okm = set(okm[okm > 0].index); keep.append(t[(t.y == y) & t.m.isin(okm)])
        if keep:
            w = pd.concat(keep); l5 = w[w.y >= 2021].R.mean()
            print(f"  -> best: {lab}; + walk-forward market choice: n {len(w)} mean {w.R.mean():+.3f} (all markets same years {t[t.y >= w.y.min()].R.mean():+.3f}) "
                  f"| last 5y {l5:+.3f} | years + {(w.groupby('y').R.sum() > 0).sum()}/{w.y.nunique()}", flush=True)
        best.append((name, lab, o))
