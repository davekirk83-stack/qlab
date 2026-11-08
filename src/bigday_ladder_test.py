"""Doc 191 — does the 10:00 'big-day' switch help the Range v3 ladder? Same harness as doc 190's shock pause (src/shock_pause_test.py).
BIG: on a session whose first 30 minutes' range >= 1.6x its 20-session mean, no new rungs either side from minute 30 to the close.
Variants: S0 baseline, S1 shock pause (no fading an abnormal 15-min bar for 2h), BIG, S1+BIG. Nov 2025-Oct 2026, dev/hold split as doc 190."""
src = open("/home/claude/qlab-git/src/level_filters_test.py").read()
head = src.split('log("PART 1')[0].replace("runs/level_filters_test.txt", "/home/claude/qlab-git/runs/bigday_ladder_test.txt")
exec(head)
log("BIG-DAY SWITCH on the Range v3 ladder — % of the ladder budget, dev / hold")
MK = {"US Tech 100": ("data_nq_cache/nq_5m.csv", 1.0, ("America/New_York", 9.5, 16)),
      "US 500": ("data_ign/USA500IDXUSD_5m.csv", 0.4, ("America/New_York", 9.5, 16)),
      "FTSE 100": ("data_ign/GBRIDXGBP_5m.csv", 1.0, ("Europe/London", 8, 16.5))}
def gate(tz, h0, h1):
    def ind(d, sym=None):
        ema, lob, hib, a, allow = P8._orig_ind(d, sym); t = d.index.tz_convert(tz); h = t.hour + t.minute / 60
        return ema, lob, hib, a, allow & ((h >= h0) & (h < h1))
    return ind
for name, (f, sp, (tz, h0, h1)) in MK.items():
    b5 = load5(f); b = to15(b5); b = b[b.index >= "2025-10-20"]; px = float(b.close.median())
    P6.MK, P6.TAKER, P6.SLIP = sp / 2 / px, sp / 2 / px, sp * 0.5 / px
    rng = (b.high - b.low); rr = (rng / rng.rolling(96).mean().shift(1)).values; n = len(b)
    up = (rr >= 3) & (b.close.values > b.open.values); dn = (rr >= 3) & (b.close.values < b.open.values)
    def blk(ev, bars):
        o = np.zeros(n, bool)
        for k in np.flatnonzero(ev): o[k:k + 1 + bars] = True
        return o
    lt = b.index.tz_convert(tz); hh = lt.hour + lt.minute / 60; day = lt.date
    sess = (hh >= h0) & (hh < h1); orb = sess & (hh < h0 + 0.5)
    or30 = pd.Series(np.where(orb, b.high.values, np.nan)).groupby(day).max() - pd.Series(np.where(orb, b.low.values, np.nan)).groupby(day).min()
    or30 = or30.dropna(); ref = or30.shift(1).rolling(20).mean(); bigday = set(or30.index[(or30 >= 1.6 * ref).values])
    BIG = np.array([(d in bigday) and (x >= h0 + 0.5) for d, x in zip(day, hh)])
    s1 = {"L": blk(dn, 8), "S": blk(up, 8)}
    V = {"S0 baseline": None, "S1 shock pause": s1, "BIG day switch": {"L": BIG, "S": BIG}, "S1 + BIG": {"L": s1["L"] | BIG, "S": s1["S"] | BIG}}
    log(f"\n{name}: big days {len(bigday)} of {len(or30)} sessions")
    P6.indicators = gate(tz, h0, h1)
    for lab, BLK in V.items():
        P6._MED = {}; closed, _ = step_blk(name, b, {}, str(b.index[250]), [10**6], BLK=BLK); rows = []
        for c in closed:
            o = pd.Timestamp(c[2]); o = o.tz_localize("UTC") if o.tzinfo is None else o
            if o < pd.Timestamp("2025-11-01", tz="UTC"): continue
            rows.append((o, c[4], c[5]))
        E = pd.DataFrame(rows, columns=["t", "r", "how"])
        cells = [f"{s} n{len(x):3} sum {100*x.r.sum():+6.2f}% worst {100*x.r.min():+.2f}%" for s, x in (("dev", E[E.t < SPLIT]), ("hold", E[E.t >= SPLIT]))]
        log(f"  {lab:16} " + " || ".join(cells))
    P6.indicators = P8._orig_ind
