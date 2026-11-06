src=open("/home/claude/qlab-git/src/level_filters_test.py").read()
head=src.split('log("PART 1')[0].replace("runs/level_filters_test.txt","runs/shock_pause_test.txt")
exec(head)
log("SHOCK PAUSE on the Range v3 ladder (doc 190, DK 6 Nov 17:48: 'we don't want to be fighting developments in the news blindly')")
log("Shock = a 15-min bar whose range >= 3x the mean range of the previous 96 bars. S1: no rungs AGAINST the shock for 2h. S2: no rungs either side for 2h. S3: S1 for 4h.")
MK = {"US Tech 100": ("data_nq_cache/nq_5m.csv", 1.0, ("America/New_York", 9.5, 16)),
      "US 500": ("data_ign/USA500IDXUSD_5m.csv", 0.4, ("America/New_York", 9.5, 16)),
      "FTSE 100": ("data_ign/GBRIDXGBP_5m.csv", 1.0, ("Europe/London", 8, 16.5))}
def gate(tz, h0, h1):
    def ind(d, sym=None):
        ema, lob, hib, a, allow = P8._orig_ind(d, sym); t = d.index.tz_convert(tz); h = t.hour + t.minute / 60
        return ema, lob, hib, a, allow & ((h >= h0) & (h < h1))
    return ind
for name, (f, sp, (tz, h0, h1)) in MK.items():
    b = to15(load5(f)); b = b[b.index >= "2025-10-20"]; px = float(b.close.median())
    P6.MK, P6.TAKER, P6.SLIP = sp / 2 / px, sp / 2 / px, sp * 0.5 / px
    rng = (b.high - b.low); rr = (rng / rng.rolling(96).mean().shift(1)).values; n = len(b)
    up = (rr >= 3) & (b.close.values > b.open.values); dn = (rr >= 3) & (b.close.values < b.open.values)
    def blk(ev, bars):
        o = np.zeros(n, bool)
        for k in np.flatnonzero(ev): o[k:k + 1 + bars] = True
        return o
    V = {"S0 baseline": None,
         "S1 no fading, 2h": {"L": blk(dn, 8), "S": blk(up, 8)},
         "S2 no rungs, 2h": {"L": blk(up | dn, 8), "S": blk(up | dn, 8)},
         "S3 no fading, 4h": {"L": blk(dn, 16), "S": blk(up, 16)}}
    log(f"\n{name}: {int(up.sum()+dn.sum())} shock bars in the year")
    P6.indicators = gate(tz, h0, h1)
    for lab, BLK in V.items():
        P6._MED = {}; closed, _ = step_blk(name, b, {}, str(b.index[250]), [10**6], BLK=BLK); rows = []
        for c in closed:
            o = pd.Timestamp(c[2]); o = o.tz_localize("UTC") if o.tzinfo is None else o
            if o < pd.Timestamp("2025-11-01", tz="UTC"): continue
            rows.append((o, c[4] - FUND * 0, c[5]))
        E = pd.DataFrame(rows, columns=["t", "r", "how"])
        cells = [f"{s} n{len(x):3} sum {100*x.r.sum():+6.2f}% worst {100*x.r.min():+.2f}%" for s, x in (("dev", E[E.t < SPLIT]), ("hold", E[E.t >= SPLIT]))]
        log(f"  {lab:20} " + " || ".join(cells))
    P6.indicators = P8._orig_ind
log("done")
