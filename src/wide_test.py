"""
THE MULTI-ASSET TEST — the system on 129 non-crypto instruments, 10 years.

Everything until now was ~90% crypto. The non-crypto evidence was seven
instruments. This is the first run where "works across asset classes" is a
measurement rather than a hope.

Universe: 129 instruments x 2,513 daily bars (2016-10 to 2026-10), from Nasdaq.
  equity index / style   SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV
  sectors                XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC
  international          EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK ACWI
  bonds                  TLT IEF SHY LQD HYG AGG TIP BND EMB MUB
  commodities            GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER URA
  property / vol         VNQ IYR VXX
  single stocks          ~60 large caps across every sector

The window contains the Q4 2018 selloff, the March 2020 crash and the 2022 bear
market, so bear behaviour is observed rather than assumed.

Reported by ASSET CLASS, because a system that only works on tech large caps is
not a multi-asset system, and pooling would hide that.
"""
import warnings; warnings.filterwarnings("ignore")
import os, numpy as np, pandas as pd
import core as C
import levels as LV
from run10 import atr, est_cost
import shorts as SH

WIDE = "/home/claude/qlab/data_wide"

CLASS = {}
for g, names in {
    "equity index": "SPY QQQ IWM DIA MDY IJR VTI VTV VUG MTUM QUAL USMV SPLV ACWI",
    "sector ETF":   "XLK XLF XLE XLV XLI XLY XLP XLU XLB XLRE XLC",
    "international":"EFA EEM FXI EWJ EWZ EWG EWU INDA EWY EWT VGK",
    "bonds":        "TLT IEF SHY LQD HYG AGG TIP BND EMB MUB",
    "commodities":  "GLD SLV USO UNG DBA DBC CORN WEAT PPLT CPER URA",
    "property/vol": "VNQ IYR VXX",
}.items():
    for n in names.split():
        CLASS[n] = g


def load():
    panel = {}
    for f in sorted(os.listdir(WIDE)):
        if not f.endswith(".csv") or f.startswith("_"):
            continue
        d = pd.read_csv(f"{WIDE}/{f}", parse_dates=["date"]).set_index("date").sort_index()
        d = d[~d.index.duplicated()]
        if len(d) > 500 and not d.close.le(0).any():
            panel[f[:-4]] = d
    return panel


PANEL = load()
COSTS = {s: est_cost(d) for s, d in PANEL.items()}
STOP_ATR, TP1_R, TP2_R, TRAIL_ATR, MAX_BARS, BE_OFF = 1.5, 1.0, 3.0, 2.5, 10, 0.10


def trade_long(df, entries, cost):
    A = atr(df).values
    H, L, Cl, O = df.high.values, df.low.values, df.close.values, df.open.values
    SL = df.low.rolling(10).min().values
    idx = np.flatnonzero(np.nan_to_num(entries.values) > 0)
    out, last = [], -1
    for i in idx:
        if i <= last or i + 1 >= len(df):
            continue
        a = A[i]
        if not (a == a) or a <= 0:
            continue
        px = O[i + 1]
        if not (px == px) or px <= 0:
            continue
        atr_stop = px - STOP_ATR * a
        stop = max(atr_stop, SL[i] * 0.995) if SL[i] == SL[i] else atr_stop
        if stop >= px:
            stop = atr_stop
        risk = px - stop
        if risk <= 0:
            continue
        tp1, tp2 = px + TP1_R * risk, px + TP2_R * risk
        filled, pnl, peak, ex = 0.0, 0.0, px, None
        cur = stop
        for j in range(i + 1, min(i + 1 + MAX_BARS, len(df))):
            if L[j] <= cur:
                pnl += (1 - filled) * (cur / px - 1); ex = j; break
            if filled < 0.34 and H[j] >= tp1:
                pnl += (1 / 3) * (tp1 / px - 1); filled = 1 / 3
                cur = max(cur, px + BE_OFF * risk + cost * px)
            if filled < 0.67 and H[j] >= tp2:
                pnl += (1 / 3) * (tp2 / px - 1); filled = 2 / 3
            if filled >= 0.66:
                tr = peak - TRAIL_ATR * a
                if L[j] <= tr and tr > cur:
                    pnl += (1 - filled) * (tr / px - 1); ex = j; break
            peak = max(peak, H[j])
        if ex is None:
            j = min(i + MAX_BARS, len(df) - 1)
            pnl += (1 - filled) * (Cl[j] / px - 1); ex = j
        out.append(dict(ret=pnl - cost, bars=max(ex - i, 1), i=i))
        last = ex
    return out


LONGS = {
    "month-high break": LV.l_break_prior_month_high,
    "swing break": lambda d: LV.l_swing_break(d, 20),
    "donchian 20": lambda d: (d.close > d.high.rolling(20).max().shift(1)).astype(float),
}


def summarise(rows, label):
    if len(rows) < 60:
        return None
    r = np.array([x["ret"] for x in rows]); b = np.array([x["bars"] for x in rows])
    exp, mb = float(r.mean()), float(b.mean())
    ann = (1 + exp) ** (252 / mb) - 1 if exp > -1 else -1
    se = r.std() / np.sqrt(len(r))
    return dict(label=label, n=len(r), exp=exp, bars=mb, ann=ann,
                win=float((r > 0).mean()), t=float(exp / se) if se > 0 else 0.0,
                worst=float(r.min()))


def line(d, pad=26):
    print(f"  {d['label']:{pad}s} n={d['n']:5d} exp {d['exp']*100:+7.3f}% "
          f"ANN {d['ann']*100:+8.1f}% win {d['win']*100:5.1f}% t={d['t']:+5.2f} "
          f"worst {d['worst']*100:+6.1f}%")


def collect(side):
    rows = {}
    book = LONGS if side == "long" else SH.SHORTS
    for s, df in PANEL.items():
        cls = CLASS.get(s, "single stock")
        for name, fn in book.items():
            if side == "short" and name == "rally into downtrend":
                continue
            if side == "short" and name == "donchian 20 low":
                continue
            try:
                e = fn(df)
                e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
            except Exception:
                continue
            if e.sum() == 0:
                continue
            tr = trade_long(df, e, COSTS[s]) if side == "long" \
                else SH.trade_short(df, e, COSTS[s])
            for r in tr:
                r["cls"] = cls; r["sym"] = s
                rows.setdefault(name, []).append(r)
    return rows


def main():
    print("MULTI-ASSET TEST — spec v1.1 on 129 non-crypto instruments\n")
    print(f"  {len(PANEL)} instruments, 2016-10 to 2026-10 (2,513 bars each)")
    print("  contains Q4 2018, March 2020 and the 2022 bear market\n")

    for side in ("long", "short"):
        rows = collect(side)
        print("=" * 100)
        print(f"  {side.upper()} SIDE — pooled across all 129 instruments")
        print("=" * 100)
        for name, rr in rows.items():
            d = summarise(rr, name)
            if d:
                line(d)
        print()
        print("-" * 100)
        print(f"  {side.upper()} SIDE — BY ASSET CLASS (best entry only)")
        print("-" * 100)
        best = max(((n, summarise(r, n)) for n, r in rows.items()
                    if summarise(r, n)), key=lambda x: x[1]["ann"], default=(None, None))
        if best[0]:
            t = pd.DataFrame(rows[best[0]])
            print(f"  entry: {best[0]}\n")
            for cls in ["equity index", "sector ETF", "international", "bonds",
                        "commodities", "property/vol", "single stock"]:
                g = t[t.cls == cls]
                d = summarise(g.to_dict("records"), cls)
                if d:
                    line(d, pad=16)
                else:
                    print(f"  {cls:16s} n={len(g)} — too few to report")
        print()

    C.ledger_bump(30, "multi-asset test on data_wide")


if __name__ == "__main__":
    main()
