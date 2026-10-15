"""
CONDITIONING LAYER v2 — every calendar/session/event filter that SURVIVED testing.

Each entry states the measured effect and the sample. Rejected claims are listed
at the bottom so nobody re-tests them.
"""
import pandas as pd, numpy as np
from fomc import FOMC

def ny_open_utc(ts):
    y=ts.year
    mar=pd.Timestamp(f"{y}-03-01"); start=mar+pd.Timedelta(days=(6-mar.dayofweek)%7+7)
    nov=pd.Timestamp(f"{y}-11-01"); end=nov+pd.Timedelta(days=(6-nov.dayofweek)%7)
    return (13,30) if start<=ts.normalize()<end else (14,30)

def score(date, hour=None):
    """Returns (multiplier, notes). 0.0 blocks the trade."""
    d=pd.Timestamp(date); dn=d.normalize()
    mult=1.0; notes=[]

    # --- FOMC: the risk is in the anticipation, not the event
    diff=min(((dn-f).days for f in FOMC), key=abs)
    if -3<=diff<0:
        mult*=0.0; notes.append(f"BLOCKED: {abs(diff)}d pre-FOMC (win 31.8% vs 49.0%)")
    elif 0<diff<=3:
        mult*=1.10; notes.append("+ post-FOMC window (+10.5% vs +9.2%)")

    # --- month shape: strength builds through week 4, collapses in the last 3 days
    dim=dn.days_in_month
    if dn.day>=dim-2:
        mult*=0.0; notes.append("BLOCKED: last 3 days of month (-0.795%/day, 33% win)")
    elif 22<=dn.day<=28:
        mult*=1.20; notes.append("+ week 4 (replicated 3/3 periods)")
    elif dn.day<=3:
        mult*=1.05; notes.append("+ first 3 days of month (+0.123%/day)")

    # --- sell in May: Nov-Apr beat May-Oct on 12 of 13 instruments, 20y data
    if dn.month in (5,6,7,8,9,10):
        mult*=0.85; notes.append("- May-Oct (+26.5% vs +90.4% ann for Nov-Apr)")
    else:
        mult*=1.10; notes.append("+ Nov-Apr seasonal")

    # --- session: Asia earns, US loses (7,304 session-days)
    if hour is not None:
        if 0<=hour<8:   mult*=1.15; notes.append("+ Asia session (+12.9% ann)")
        elif 13<=hour<21: mult*=0.85; notes.append("- US session (-19.3% ann)")

    return mult, notes


# ---- separate fast trade: fade the NY opening move back to the open ----
NYO_FADE = dict(
    rule="After the NY cash open, if the first 15 min closes away from the open, "
         "fade it with the OPEN PRICE as the target.",
    hit_rate_60min=0.680, hit_rate_90min=0.728, median_minutes=15,
    note="Do NOT hold for a trend: 2h after the retrace it is a coin flip (49.6%). "
         "Target the open, take it, leave.",
    sample="3,652 session-days, 4 symbols, 15-min bars",
)

REJECTED = {
 "day of week": "-2.48pp out of sample",
 "month of year (as a filter)": "-6.27pp out of sample",
 "quarter": "-4.10pp out of sample",
 "US election cycle": "-4.14pp out of sample",
 "turn of month (as defined)": "-3.51pp out of sample",
 "US clears London high/low": "TRUE (70.8%) but no direction: 45.9% continue vs 53.8% reverse",
 "NY open reversal as a TREND": "retrace is real (68%) but does not develop (49.6%)",
 "month-end SURGE": "inverted - last 3 days are the WORST window (-0.795%/day)",
}
