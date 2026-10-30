"""Ichimoku daily cloud gate (doc 165). cloud_above(dy) -> boolean Series on dy's index: True on day D when day D-1's close was above
day D-1's plotted cloud (classic 9/26/52/26, spans shifted 26). Known at D's open, so causal. dy needs high, low, close."""
import numpy as np, pandas as pd
def cloud_above(dy):
    mid = lambda n: (dy.high.rolling(n).max() + dy.low.rolling(n).min()) / 2
    A = ((mid(9) + mid(26)) / 2).shift(26); B = mid(52).shift(26)
    return (dy.close > np.maximum(A, B)).where(B.notna(), False).astype(bool).shift(1, fill_value=False)
