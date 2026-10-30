"""Gini, KS, AUC, PSI and CSI utilities."""
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve

def auc(y, s): return roc_auc_score(y, s)
def gini(y, s): return 2 * roc_auc_score(y, s) - 1
def ks(y, s):
    f, t, _ = roc_curve(y, s); return float(np.max(t - f))

def psi_from_counts(e, a, eps=1e-4):
    e, a = np.asarray(e, float) / np.sum(e), np.asarray(a, float) / np.sum(a)
    e, a = np.clip(e, eps, None), np.clip(a, eps, None); return float(np.sum((a - e) * np.log(a / e)))

def psi(expected, actual, bins=10):
    """Score PSI: bin edges are deciles of the EXPECTED (development) distribution."""
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)[1:-1]))
    e = np.bincount(np.searchsorted(edges, expected), minlength=len(edges) + 1)
    a = np.bincount(np.searchsorted(edges, actual), minlength=len(edges) + 1); return psi_from_counts(e, a)

def csi(binner, x_dev, x_new):
    """Characteristic Stability Index for one variable using the scorecard's own bins."""
    nb = len(binner.woe_)
    e = np.bincount(np.clip(binner.bin_index(x_dev), 0, nb - 1), minlength=nb); a = np.bincount(np.clip(binner.bin_index(x_new), 0, nb - 1), minlength=nb)
    return psi_from_counts(e, a)

def psi_flag(v): return "Stable" if v < .10 else ("Moderate drift - review" if v < .25 else "Significant drift - recalibrate/retrain")
