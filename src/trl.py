"""
WHEN WILL WE ACTUALLY KNOW? — minimum track record length, and the
deflated Sharpe hurdle for 66 scored elements.

Two questions this programme has never been able to answer, now answerable
with Bailey & Lopez de Prado's statistics (found via esvhd/pypbo):

  1. Cascade v4's kill criterion says "100 closed trades or 6 months". That
     number was chosen by feel. MINIMUM TRACK RECORD LENGTH says how long a
     forward run must continue before a Sharpe is statistically
     distinguishable from zero, GIVEN the skew and kurtosis of its returns —
     and a 73%-win, fixed-target book has heavily negative skew, which makes
     it HARDER to prove, not easier.

  2. We scored 66 elements and kept the winners. The DEFLATED SHARPE RATIO
     raises the hurdle by expected_max(N) standard deviations of the
     cross-trial distribution, where N is the number of things tried. Doing
     this is the formal version of the best-of-N problem that both the
     LuxAlgo and the TradingView sweeps independently flagged.

PSR(SR*) = Phi( (SR - SR*) * sqrt(T-1) / sqrt(1 - skew*SR + SR^2*(kurt-1)/4) )
minTRL   = 1 + (1 - skew*SR + SR^2*(kurt-1)/4) * (Z_alpha / (SR - SR*))^2
DSR      = PSR with SR* = sigma_SR * E[max of N draws]
E[max_N] ~ (1-g)*Phi^-1(1 - 1/N) + g*Phi^-1(1 - 1/(N*e)),  g = Euler-Mascheroni
"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np
from scipy import stats

EULER = 0.5772156649


def expected_max(n):
    if n < 2:
        return 0.0
    return ((1 - EULER) * stats.norm.ppf(1 - 1.0 / n)
            + EULER * stats.norm.ppf(1 - 1.0 / (n * np.e)))


def psr(sr, T, skew, kurt, sr_star=0.0):
    den = np.sqrt(max(1 - skew * sr + (sr ** 2) * (kurt - 1) / 4.0, 1e-12))
    return stats.norm.cdf((sr - sr_star) * np.sqrt(max(T - 1, 1)) / den)


def min_trl(sr, skew, kurt, sr_star=0.0, conf=0.95):
    if sr <= sr_star:
        return np.inf
    z = stats.norm.ppf(conf)
    return 1 + (1 - skew * sr + (sr ** 2) * (kurt - 1) / 4.0) * (z / (sr - sr_star)) ** 2


if __name__ == "__main__":
    # cascade v4, from the out-of-sample measurement: 73.5% win,
    # +1.5% target against a 2.63% structural stop
    p, g, l = 0.735, 0.015, -0.0263
    mu = p * g + (1 - p) * l
    var = p * (g - mu) ** 2 + (1 - p) * (l - mu) ** 2
    sd = np.sqrt(var)
    sr = mu / sd
    skew = (p * (g - mu) ** 3 + (1 - p) * (l - mu) ** 3) / sd ** 3
    kurt = (p * (g - mu) ** 4 + (1 - p) * (l - mu) ** 4) / sd ** 4

    print("CASCADE v4 — per-trade return distribution implied by the "
          "out-of-sample result\n")
    print(f"  win rate          {p*100:.1f}%")
    print(f"  mean per trade    {mu*100:+.3f}%   (measured +0.652%)")
    print(f"  per-trade Sharpe  {sr:.4f}")
    print(f"  skew              {skew:+.3f}   kurtosis {kurt:.3f}")
    print(f"  -> a high-win, fixed-target book is NEGATIVELY skewed, which "
          f"makes it\n     HARDER to prove, not easier.\n")

    print("  MINIMUM TRACK RECORD LENGTH — trades needed before the Sharpe is")
    print("  distinguishable from zero\n")
    print(f"  {'confidence':>12}{'trades':>10}{'months @87/mo':>16}")
    for c in (0.90, 0.95, 0.99):
        n = min_trl(sr, skew, kurt, 0.0, c)
        print(f"  {c*100:>11.0f}%{n:>10.0f}{n/87:>16.1f}")

    print(f"\n  Our registered kill criterion is 100 trades. At 95% confidence "
          f"the\n  requirement is {min_trl(sr,skew,kurt,0,0.95):.0f} trades — "
          f"so 100 is "
          f"{'ADEQUATE' if min_trl(sr,skew,kurt,0,0.95)<=100 else 'TOO FEW'}.")

    print("\n" + "=" * 70)
    print("  DEFLATED SHARPE — the hurdle after trying 66 elements")
    print("=" * 70)
    print(f"  {'trials N':>10}{'E[max] in sd':>15}{'hurdle if sd=0.02':>20}")
    for n in (1, 5, 20, 66, 113):
        em = expected_max(n)
        print(f"  {n:>10}{em:>15.3f}{em*0.02:>20.4f}")
    print(f"\n  We scored 66 elements and ran 113 experiments. An element must")
    print(f"  clear roughly {expected_max(66):.2f} standard deviations of the")
    print(f"  cross-element Sharpe spread before it is more than the best of 66")
    print(f"  coin flips. Several of today's 'significant' elements will not.")
    print(f"\n  PSR that cascade v4's true Sharpe exceeds zero, at n trades:")
    for n in (3, 25, 50, 100, 200):
        print(f"    n={n:>4}   {psr(sr,n,skew,kurt)*100:>5.1f}%")
