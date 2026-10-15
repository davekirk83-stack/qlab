"""
ICHIMOKU KINKO HYO — components tested separately, then combined.

DK: "I don't use ichimoku clouds but I know some people swear by them. Happy for
you to consider them also."

Two reasons to be careful rather than quick.

1. THE LOOKAHEAD TRAP. The cloud (Senkou A/B) is displaced 26 periods FORWARD.
   On a chart, the cloud sitting above today's candle was computed 26 bars ago.
   The bug is to compute Senkou from today's data and then read it as today's
   cloud — which uses 26 bars of future information. This is the same class of
   error that gave a false +2.64 Sharpe on the multi-timeframe work (the true
   figure was -0.55). So this file computes the cloud BOTH ways and reports both.
   If the buggy version looks dramatically better, that is the bug talking.

   Correct: the cloud in force at bar i was calculated at bar i-26, i.e. shift(+26).

   Chikou is the mirror: today's close plotted 26 bars BACK. Using it at bar i
   means comparing close[i] with price 26 bars ago, which is legitimate.

2. BUNDLING. The standard signal is "price above the cloud AND tenkan crosses
   kijun AND chikou clear of price". That is three filters sold as one, and
   bundling is how a worthless component hides behind a working one. Each is
   measured on its own first.

Management and objective as per spec v1 (annualised return on deployed capital).
Stop width 3.0 ATR, per the correction in doc 25.
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import core as C
import levels as LV
from bb import PANEL, COSTS, trade, summarise, line

TEN, KIJ, SPB, DISP = 9, 26, 52, 26
MGMT = dict(stop_atr=3.0, tp1_r=1.0, tp2_r=3.0, trail_atr=2.5,
            max_bars=10, be_offset_r=0.10)


def ichi(df, lookahead_bug=False):
    h, l, c = df.high, df.low, df.close
    def mid(n):
        return (h.rolling(n).max() + l.rolling(n).min()) / 2
    tenkan, kijun = mid(TEN), mid(KIJ)
    a_raw, b_raw = (tenkan + kijun) / 2, mid(SPB)
    if lookahead_bug:
        # WRONG: reads the cloud computed from today's data as today's cloud
        spa, spb = a_raw, b_raw
    else:
        # CORRECT: the cloud in force today was computed 26 bars ago
        spa, spb = a_raw.shift(DISP), b_raw.shift(DISP)
    top, bot = np.maximum(spa, spb), np.minimum(spa, spb)
    return dict(tenkan=tenkan, kijun=kijun, top=top, bot=bot,
                spa=spa, spb=spb, close=c)


def signals(df, bug=False):
    k = ichi(df, bug)
    c, tk, kj, top, bot = k["close"], k["tenkan"], k["kijun"], k["top"], k["bot"]
    above = c > top
    tkx = (tk > kj) & (tk.shift(1) <= kj.shift(1))
    s = {}
    s["A. price breaks above cloud"] = (above & ~above.shift(1).fillna(False))
    s["B. tenkan/kijun cross up"] = tkx
    s["C. chikou clear of price"] = ((c > c.shift(DISP))
                                     & (c.shift(1) <= c.shift(DISP + 1)))
    s["D. kumo twist bullish"] = ((k["spa"] > k["spb"])
                                  & (k["spa"].shift(1) <= k["spb"].shift(1)))
    s["E. bounce off cloud top"] = ((c > top) & (df.low <= top)
                                    & (c.shift(1) > top.shift(1)))
    # bundles
    s["TK cross + above cloud"] = tkx & above
    s["TK cross + above + chikou"] = tkx & above & (c > c.shift(DISP))
    s["FULL (all four)"] = (tkx & above & (c > c.shift(DISP))
                            & (k["spa"] > k["spb"]))
    return {n: v.astype(float).fillna(0.0) for n, v in s.items()}


def run(bug=False):
    rows = {}
    names = None
    for s, df in PANEL.items():
        if len(df) < 300:
            continue
        try:
            sg = signals(df, bug)
        except Exception:
            continue
        names = names or list(sg)
        for n, e in sg.items():
            if e.sum() == 0:
                continue
            rows.setdefault(n, []).extend(trade(df, e, COSTS[s], **MGMT))
    out = []
    for n in names or []:
        d = summarise(rows.get(n, []), n)
        if d:
            out.append(d)
    return out


def main():
    print("ICHIMOKU — components first, bundles second")
    print(f"  {len(PANEL)} instruments · management {MGMT}\n")

    print("=" * 96)
    print("CORRECT CLOUD  (senkou displaced +26: today's cloud was computed 26 bars ago)")
    print("=" * 96)
    good = run(bug=False)
    for d in good:
        line(d)

    print()
    print("=" * 96)
    print("LOOKAHEAD-BUG CLOUD  (senkou read without the shift — uses 26 bars of future)")
    print("=" * 96)
    bad = run(bug=True)
    for d in bad:
        line(d)

    print()
    print("=" * 96)
    print("THE DIFFERENCE — how much of any 'edge' is the bug?")
    print("=" * 96)
    gm = {d["label"]: d for d in good}
    bm = {d["label"]: d for d in bad}
    print(f"  {'signal':30s} {'correct':>12} {'with bug':>12} {'inflation':>12}")
    for n in gm:
        if n not in bm:
            continue
        g, b = gm[n]["ann"], bm[n]["ann"]
        print(f"  {n:30s} {g*100:+11.1f}% {b*100:+11.1f}% {(b-g)*100:+11.1f}pp")

    # benchmark
    print()
    inc = []
    for s, df in PANEL.items():
        try:
            e = LV.l_break_prior_month_high(df)
            e = pd.Series(np.nan_to_num(np.asarray(e, dtype=float)), index=df.index)
        except Exception:
            continue
        if e.sum():
            inc.extend(trade(df, e, COSTS[s], **MGMT))
    d = summarise(inc, "[incumbent] month high")
    if d:
        print("=" * 96)
        line(d)
        beat = [x for x in good if x["ann"] > d["ann"]]
        print(f"\n  ichimoku signals beating the incumbent: {len(beat)} of {len(good)}")
        for x in sorted(beat, key=lambda z: -z["ann"]):
            print(f"    {x['label']:30s} {(x['ann']-d['ann'])*100:+9.1f}pp")

    C.ledger_bump(len(good) + len(bad), "ichimoku components and bundles")


if __name__ == "__main__":
    main()
