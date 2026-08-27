"""Backtest statistics — the numbers a claimed Sharpe has to survive.

Conventions (fixed for the whole project, per desk-year-plan.md §2):
- Returns are DAILY portfolio returns on a fixed bankroll.
- Sharpe is annualized with sqrt(365): prediction markets trade every day.
- No Sharpe is quotable below the evidence bar: >=300 resolved bets,
  >=120 distinct return days, PSR >= 0.95 against SR=0.
- Deflated Sharpe (Bailey & Lopez de Prado 2014) charges for every strategy
  variant tried, including the dead ones in graveyard.md.
"""
import math
import statistics as st

ANN = 365


def sharpe(daily):
    """annualized Sharpe of a list of daily returns."""
    if len(daily) < 2:
        return 0.0
    mu, sd = st.mean(daily), st.pstdev(daily)
    return (mu / sd) * math.sqrt(ANN) if sd else 0.0


def _phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def psr(daily, sr_benchmark=0.0):
    """Probabilistic Sharpe Ratio: P(true SR > benchmark), adjusting for
    skew/kurtosis and sample length (Bailey & Lopez de Prado)."""
    n = len(daily)
    if n < 3:
        return 0.0
    sr_hat = sharpe(daily) / math.sqrt(ANN)           # per-period SR
    sb = sr_benchmark / math.sqrt(ANN)
    mu, sd = st.mean(daily), st.pstdev(daily)
    if sd == 0:
        return 0.0
    z = [(x - mu) / sd for x in daily]
    g3 = sum(v ** 3 for v in z) / n                    # skew
    g4 = sum(v ** 4 for v in z) / n                    # kurtosis (raw)
    denom = math.sqrt(max(1 - g3 * sr_hat + (g4 - 1) / 4 * sr_hat ** 2, 1e-12))
    stat = (sr_hat - sb) * math.sqrt(n - 1) / denom
    return _phi(stat)


def deflated_sharpe(daily, n_trials, trial_sr_var=None):
    """DSR: PSR against the expected max SR of n_trials random strategies.
    trial_sr_var: variance of per-period SR across tried variants (defaults to
    the observed strategy's SR variance proxy 1/n)."""
    n = len(daily)
    if n < 3 or n_trials < 1:
        return 0.0
    v = trial_sr_var if trial_sr_var is not None else 1.0 / n
    gamma = 0.5772156649
    e = ((1 - gamma) * _inv_phi(1 - 1 / n_trials)
         + gamma * _inv_phi(1 - 1 / (n_trials * math.e))) if n_trials > 1 else 0.0
    sr_max = math.sqrt(v) * e
    return psr(daily, sr_benchmark=sr_max * math.sqrt(ANN))


def _inv_phi(p):
    """inverse normal CDF (Acklam's approximation, plenty for DSR)."""
    if not 0 < p < 1:
        return 0.0
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def evidence_bar(n_bets, daily, min_bets=300, min_days=120, min_psr=0.95):
    """Is this result quotable at all? Returns (ok, reasons)."""
    reasons = []
    if n_bets < min_bets:
        reasons.append(f"bets {n_bets} < {min_bets}")
    if len(daily) < min_days:
        reasons.append(f"days {len(daily)} < {min_days}")
    p = psr(daily)
    if p < min_psr:
        reasons.append(f"PSR {p:.2f} < {min_psr}")
    return (not reasons), reasons
