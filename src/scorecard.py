"""Scorecard scaling: Score = Offset + Factor * ln(odds_good). Factor = PDO/ln2, Offset = base_score - Factor*ln(base_odds).
Points per bin = Offset/n - Factor*(intercept/n + coef_i*WoE_bin)  (model is fit on P(default), so ln(odds_good) = -logit)."""
import numpy as np, pandas as pd

class Scorecard:
    def __init__(self, binners: dict, coefs: dict, intercept: float, base_score=600, base_odds=50, pdo=20, lo=300, hi=850):
        self.b, self.coefs, self.intercept = binners, coefs, intercept
        self.factor = pdo / np.log(2); self.offset = base_score - self.factor * np.log(base_odds); self.lo, self.hi = lo, hi
        n = len(coefs); rows = []
        self.points = {}
        for v, bn in binners.items():
            if v not in coefs: continue
            pts = self.offset / n - self.factor * (intercept / n + coefs[v] * bn.woe_)
            self.points[v] = pts
            for lab, p, w in zip(bn.table_["bin"], pts, bn.woe_): rows.append((v, lab, round(w, 4), round(p, 1)))
        self.table = pd.DataFrame(rows, columns=["variable", "bin", "woe", "points"])

    def score(self, df: pd.DataFrame):
        s = sum(self.points[v][np.clip(self.b[v].bin_index(df[v].values), 0, len(self.points[v]) - 1)] for v in self.points)
        return np.clip(s, self.lo, self.hi)

    def pd_from_score(self, s):
        """Invert scaling: ln(odds_good) = (score - offset)/factor  ->  PD = 1/(1+odds_good)."""
        return 1 / (1 + np.exp((np.asarray(s) - self.offset) / self.factor))
