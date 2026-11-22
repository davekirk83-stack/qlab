"""DK 20 Nov 09:33: "Look ahead at all major, repeatable calendar dates ... determine whether they are either positive or detrimental to our
trading books ... instruct the relevant books to sit out any days in which there is a likelihood of losing money." + 09:34: "We want to
limit our exposure to draw downs". Daily live books (RSI4L, RSI4, TPS, TOM) on 7 indices + gold, 2000-2026, honest daily simulator
(fifty_ideas / events_test). For each event: trades ENTERED when the event is within the next 1 trading day (known at entry) vs not,
and a walk-forward skip rule (a year skips only if, in all earlier years >= 8, event trades lost money and were worse than the rest),
reporting out-of-sample total and max drawdown (in ATR units) with and without the skip."""
import warnings; warnings.filterwarnings("ignore")
import os, sys, numpy as np, pandas as pd
sys.path.insert(0, "src"); import fifty_ideas as F
from events_test import run2, FOMC, nfp_days
IDX = F.D["SPX"].index
def tday_after(dates):   # map calendar dates to the first trading day on/after
    pos = IDX.searchsorted(pd.DatetimeIndex(dates)); pos = pos[pos < len(IDX)]; return pd.DatetimeIndex(IDX[pos])
def third_fri(y, m): d = pd.Timestamp(y, m, 1); return d + pd.Timedelta(days=(4 - d.dayofweek) % 7 + 14)
Y = range(2000, 2027)
opex = tday_after([third_fri(y, m) for y in Y for m in range(1, 13)])
quad = tday_after([third_fri(y, m) for y in Y for m in (3, 6, 9, 12)])
vix = tday_after([third_fri(y + (m == 12), 1 if m == 12 else m + 1) - pd.Timedelta(days=30) for y in Y for m in range(1, 13)])
nfp = nfp_days(IDX)
minutes = tday_after([d + pd.Timedelta(days=21) for d in FOMC])
gaps = pd.Series(IDX[1:], index=IDX[:-1]); bd = (gaps - gaps.index).dt.days
pre_hol = pd.DatetimeIndex([t for t, g in bd.items() if (g > 1 and t.dayofweek != 4) or g > 3])          # day before a weekday market holiday
post_hol = pd.DatetimeIndex([gaps[t] for t in pre_hol])
def tg(y): d = pd.Timestamp(y, 11, 1); return d + pd.Timedelta(days=(3 - d.dayofweek) % 7 + 21)
tg_wed = tday_after([tg(y) - pd.Timedelta(days=1) for y in Y]); tg_fri = tday_after([tg(y) + pd.Timedelta(days=1) for y in Y]); tg_mon = tday_after([tg(y) + pd.Timedelta(days=4) for y in Y])
xmas = pd.DatetimeIndex([t for t in IDX if (t.month == 12 and t.day >= 24) or (t.month == 1 and t.day <= 2)])
def eday(y): d = pd.Timestamp(y, 11, 2); return d + pd.Timedelta(days=(1 - d.dayofweek) % 7)   # first Tue after first Mon
elect = tday_after([eday(y) for y in Y if y % 2 == 0]); elect_after = tday_after([eday(y) + pd.Timedelta(days=1) for y in Y if y % 2 == 0])
pres = tday_after([eday(y) + pd.Timedelta(days=1) for y in Y if y % 4 == 0])
mend = pd.DatetimeIndex([t for t in IDX if t == (t + pd.offsets.BMonthEnd(0))])
qend = pd.DatetimeIndex([t for t in mend if t.month in (3, 6, 9, 12)])
jhole = tday_after([pd.Timestamp(y, 8, 20) + pd.Timedelta(days=(4 - pd.Timestamp(y, 8, 20).dayofweek) % 7) for y in Y])  # ~Fri of Jackson Hole week (approx)
EVENTS = {"FOMC decision": FOMC, "FOMC minutes (approx)": minutes, "Jobs report (1st Fri, approx)": nfp, "US monthly opex": opex,
          "Quad witching / S&P rebalance": quad, "VIX expiry": vix, "Day before US holiday": pre_hol, "Day after US holiday": post_hol,
          "Thanksgiving Wed": tg_wed, "Black Friday (half day)": tg_fri, "Monday after Thanksgiving": tg_mon, "Christmas-New Year (24 Dec-2 Jan)": xmas,
          "US election day (even years)": elect, "Day after US election": elect_after, "Day after presidential election": pres,
          "Month end (last business day)": mend, "Quarter end": qend, "Jackson Hole Friday (approx)": jhole}
up = lambda d: d.close > d.close.rolling(200).mean()
def r4(d): return F.rsi(d.close, 4)
BOOKS = {
  "RSI4L": (F.IXG, lambda d: (up(d) & (r4(d) < 35), r4(d) > 55, 10, 3.0, "C")),
  "RSI4":  (F.IXG, lambda d: (up(d) & (r4(d) < 25), r4(d) > 55, 10, 3.0, "C")),
  "TPS (1st rung)": (F.IXG, lambda d: (lambda r2: (up(d) & (r2 < 25) & (r2.shift(1) < 25), r2 > 70, 30, 5.0, "C"))(F.rsi(d.close, 2))),
  "TOM": (F.IXG, lambda d: (pd.Series(d.index == (d.index + pd.offsets.BMonthEnd(0)), index=d.index), None, 3, 5.0, "C")),
}
def maxdd(r): c = np.cumsum(r); return float((np.maximum.accumulate(np.r_[0, c]) - np.r_[0, c]).max())
out = []; verdicts = []
trades = {}
for b, (mk, fn) in BOOKS.items():
    rows = []
    for k in mk:
        d = F.D[k]; e, x, md, st, how = fn(d); idx = d.index; pos = {t: i for i, t in enumerate(idx)}
        for t0, t1, R in run2(k, e, 1, x, md, st, how):
            i = pos[t0]; win = idx[i + 1: i + 3]   # the next 2 trading days after the entry close (the first full day held + one more)
            rows.append(dict(t=t0, k=k, R=R, **{ev: bool(win.isin(ds).any()) for ev, ds in EVENTS.items()}))
    trades[b] = pd.DataFrame(rows).sort_values("t").reset_index(drop=True)
for b, t in trades.items():
    t["y"] = t.t.dt.year
    out.append(f"\n== {b}: {len(t)} trades, mean {t.R.mean():+.3f} ATR, total {t.R.sum():+.0f}, max DD {maxdd(t.R):.1f}")
    for ev in EVENTS:
        if b == "TOM" and ev in ("Month end (last business day)", "Quarter end"): continue
        a = t[t[ev]]; n = len(a)
        if n < 15: out.append(f"   {ev:36} n{n:4} (too few)"); continue
        allt = keept = 0.0; kept = []
        for Y_ in sorted(t.y.unique()):
            past, cur = t[t.y < Y_], t[t.y == Y_]; pa = past[past[ev]]
            skip = past.y.nunique() >= 8 and len(pa) >= 15 and pa.R.mean() < 0 and pa.R.mean() < past[~past[ev]].R.mean()
            kept.append(cur[~cur[ev]] if skip else cur)
        K = pd.concat(kept); oos = t[t.y >= t.y.min() + 8]; Ko = K[K.y >= t.y.min() + 8]
        late = a[a.y >= 2013]
        line = (f"   {ev:36} n{n:4} event {a.R.mean():+.3f} vs rest {t[~t[ev]].R.mean():+.3f} | 2013-26 {late.R.mean():+.3f} | "
                f"WF out-of-sample total {oos.R.sum():+.0f} -> {Ko.R.sum():+.0f}, max DD {maxdd(oos.R):.1f} -> {maxdd(Ko.R):.1f}")
        out.append(line)
        if Ko.R.sum() > oos.R.sum() + 0.5 or (maxdd(Ko.R) < 0.9 * maxdd(oos.R) and Ko.R.sum() >= 0.9 * oos.R.sum()):
            verdicts.append((b, ev, round(oos.R.sum(), 1), round(Ko.R.sum(), 1), round(maxdd(oos.R), 1), round(maxdd(Ko.R), 1), n, round(a.R.mean(), 3), round(late.R.mean(), 3)))
out.append("\n== QUALIFYING SKIPS (out-of-sample: more profit, or >=10% less drawdown keeping >=90% of profit)")
for v in verdicts: out.append(f"   {v[0]:15} skip '{v[1]}': total {v[2]} -> {v[3]}, max DD {v[4]} -> {v[5]} (n{v[6]}, event mean {v[7]:+}, 2013-26 {v[8]:+})")
if not verdicts: out.append("   none")
open("runs/research/calendar_study_daily.txt", "w").write("\n".join(out)); print("\n".join(out))
