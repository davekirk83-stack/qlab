# 193 — Dealer-hedging forces (VolSignals' gamma / vanna / charm) tested on price and VIX alone (9 Nov 2026)

DK 9 Nov: "See if you can get anything good from this website without paying" (volsignals.com) then "Yes run the research now".
VolSignals' paid product is dealer-positioning data; the free material is teasers. Their three forces leave fingerprints in plain
price/VIX data, so those were tested (`src/dealer_flow_test.py`, `runs/dealer_flow_test.txt`). S&P 500 daily 1990-2009 / 2010-2026.

| Idea | Result | Verdict |
|---|---|---|
| Expiry Fridays pin (smaller range) | range 0.96x / 0.95x of normal vs 1.02x / 1.04x other days | real but small (~8% quieter), both periods |
| "Week after expiry" is weak | -0.17% (1990-2009) but +0.34% (2010-26) | gone — not tradeable |
| Vanna: VIX crush -> S&P drifts up | next day -0.05% both periods; 5 days -0.34% / +0.25% | not supported |
| VIX spike >= +15% -> S&P bounces | next day +0.44% / +0.19%; 5 days +0.72% / +0.17%, up 62-63% | supported both periods (fear spikes revert) |
| Charm: drift into the close on calm days | last 2h ~0 and ~50/50 on US 500 2025-26, US Tech 100 2020-21 and 2025-26 | not supported |

What carries over: (1) expiry Fridays are slightly quieter — mildly good for the range ladder, bad for breakout engines (to check when
the books have enough expiry-day trades); (2) VIX spikes revert — the same family as the capitulation-retest book (doc 191).
The vanna and charm "mechanical flows" do not show up in index prices at these horizons without the positioning data itself.
