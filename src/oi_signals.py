"""
Positioning signals from real futures data (Binance Vision archive).

This is the first input class in the whole programme that is NOT a
transformation of price. Fields available at 5-minute resolution:

  sum_open_interest                 contracts outstanding
  sum_open_interest_value           same, in USD
  count_toptrader_long_short_ratio  top traders, by ACCOUNT
  sum_toptrader_long_short_ratio    top traders, by POSITION SIZE
  count_long_short_ratio            all accounts
  sum_taker_long_short_vol_ratio    aggressive buy vs sell flow

The mechanisms being tested, each stated before the test:

  CROWDING      When the retail crowd is heavily one-sided and the top traders
                are not, the crowd is the liquidity. Fade it.
  SMART MONEY   Top traders by position SIZE are the ones with capital at risk.
                Follow their skew, not the account-count skew.
  OI + PRICE    Rising OI with rising price = new longs (continuation).
                Falling OI with rising price = shorts covering (exhaustion).
                This is the classic four-quadrant read, and it is testable.
  FLOW          Sustained aggressive buying that price has not yet reflected.
  SQUEEZE FUEL  Extreme OI plus extreme one-sided positioning = the conditions
                for a liquidation cascade. Direction is toward the crowded side's
                pain, i.e. against them.
"""
import numpy as np, pandas as pd

OI_DIR = "/home/claude/qlab/data_oi"


def load_oi(sym, resample="1h"):
    df = pd.read_csv(f"{OI_DIR}/{sym}.csv", parse_dates=["create_time"])
    df = df.set_index("create_time").sort_index()
    num = df.select_dtypes("number")
    return num.resample(resample).last().dropna(how="all")


def join_price(oi, price_df):
    """Align positioning to price bars. Positioning is lagged one bar so a
    decision never uses data from its own bar."""
    p = price_df.copy()
    j = p.join(oi.reindex(p.index, method="ffill").shift(1), how="inner")
    return j.dropna(subset=["close"])


def _z(s, n=96):
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    return ((s - m) / sd.replace(0, np.nan)).fillna(0.0)


# ---------------------------------------------------------------- signals
def s_fade_crowd(df, k=1.5):
    """Retail heavily long while top traders are not -> fade the crowd (go short
    is the mirror; here the long leg is retail heavily SHORT)."""
    retail = _z(df["count_long_short_ratio"])
    top = _z(df["sum_toptrader_long_short_ratio"])
    return ((retail < -k) & (top > 0)).astype(float)


def s_follow_smart(df, k=1.0):
    """Top traders by position size skewing long, beyond their own norm."""
    return (_z(df["sum_toptrader_long_short_ratio"]) > k).astype(float)


def s_oi_price_up(df, k=0.5):
    """Rising OI + rising price = new money entering long. Continuation."""
    doi = _z(df["sum_open_interest"].pct_change(4).fillna(0.0))
    dpx = df.close.pct_change(4).fillna(0.0)
    return ((doi > k) & (dpx > 0)).astype(float)


def s_short_cover(df, k=0.5):
    """Falling OI + rising price = shorts covering. Exhaustion, not strength."""
    doi = _z(df["sum_open_interest"].pct_change(4).fillna(0.0))
    dpx = df.close.pct_change(4).fillna(0.0)
    return ((doi < -k) & (dpx > 0)).astype(float)


def s_taker_flow(df, k=1.0):
    """Sustained aggressive buying."""
    return (_z(df["sum_taker_long_short_vol_ratio"]) > k).astype(float)


def s_squeeze_fuel(df, k=1.5):
    """Extreme OI and crowd heavily SHORT -> fuel for an upward squeeze."""
    oi = _z(df["sum_open_interest"])
    retail = _z(df["count_long_short_ratio"])
    return ((oi > k) & (retail < -k)).astype(float)


def s_divergence(df, k=1.0):
    """Top traders and the crowd on opposite sides, top traders long."""
    top = _z(df["sum_toptrader_long_short_ratio"])
    retail = _z(df["count_long_short_ratio"])
    return ((top - retail) > k).astype(float)


SIGNALS = {
    "fade_crowd":   (s_fade_crowd,   [(1.0,), (1.5,), (2.0,)]),
    "follow_smart": (s_follow_smart, [(0.5,), (1.0,), (1.5,)]),
    "oi_price_up":  (s_oi_price_up,  [(0.0,), (0.5,), (1.0,)]),
    "short_cover":  (s_short_cover,  [(0.5,), (1.0,)]),
    "taker_flow":   (s_taker_flow,   [(0.5,), (1.0,), (1.5,)]),
    "squeeze_fuel": (s_squeeze_fuel, [(1.0,), (1.5,)]),
    "divergence":   (s_divergence,   [(0.5,), (1.0,), (1.5,)]),
}
