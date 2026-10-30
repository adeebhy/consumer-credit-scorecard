"""Custom monotonic WoE binning (fine bins -> coarse bins). WoE = ln(%good / %bad), so higher = safer.
Numeric: start from fine quantile/unique-value bins, merge thin bins, enforce monotone bad-rate by merging
violating neighbours, then cap the bin count by merging the pair with the smallest WoE gap.
Categorical: group by category, merge thin categories into the nearest bad-rate neighbour (no monotone rule)."""
import numpy as np, pandas as pd

def _counts(ids, y, nb):
    good = np.bincount(ids[y == 0], minlength=nb).astype(float); bad = np.bincount(ids[y == 1], minlength=nb).astype(float)
    return good, bad

def _woe(good, bad):
    G, B = good.sum(), bad.sum()
    return np.log(((good + .5) / G) / ((bad + .5) / B))

class WoEBinner:
    def __init__(self, kind="num", max_bins=8, min_bin_frac=0.05, n_fine=20, monotone=True):
        self.kind, self.max_bins, self.min_frac, self.n_fine, self.monotone = kind, max_bins, min_bin_frac, n_fine, monotone

    # ---------- fit ----------
    def fit(self, x, y):
        x, y = np.asarray(x), np.asarray(y).astype(int); n = len(x)
        self.min_n = self.min_frac * n
        return self._fit_num(x.astype(float), y) if self.kind == "num" else self._fit_cat(x, y)

    def _fit_num(self, x, y):
        u = np.unique(x)
        cuts = u[:-1] if len(u) <= 25 else np.unique(np.quantile(x, np.linspace(0, 1, self.n_fine + 1)[1:-1]))
        while True:
            ids = np.searchsorted(cuts, x, side="left"); nb = len(cuts) + 1
            if nb == 1: break
            g, b = _counts(ids, y, nb); tot = g + b; br = b / np.maximum(tot, 1)
            small = np.where(tot < self.min_n)[0]
            if len(small):                                    # merge thinnest bin into closer neighbour
                i = small[np.argmin(tot[small])]
                cand = [j for j in (i - 1, i + 1) if 0 <= j < nb]
                j = min(cand, key=lambda j: abs(br[j] - br[i])); cuts = np.delete(cuts, min(i, j)); continue
            if self.monotone and nb > 2:
                d = np.sign(np.corrcoef(np.arange(nb), br)[0, 1]) or 1
                viol = np.where(np.diff(br) * d < 0)[0]
                if len(viol): cuts = np.delete(cuts, viol[0]); continue
            if nb > self.max_bins:
                w = _woe(g, b); cuts = np.delete(cuts, np.argmin(np.abs(np.diff(w)))); continue
            break
        self.cuts = cuts; return self._finalize(x, y)

    def _fit_cat(self, x, y):
        cats = pd.Series(x).astype(str); df = pd.DataFrame({"c": cats, "y": y})
        st = df.groupby("c").y.agg(["sum", "count"]); st["br"] = st["sum"] / st["count"]
        groups = {c: [c] for c in st.index}
        while True:
            gs = pd.DataFrame([(k, sum(st.loc[m, "count"]) , sum(st.loc[m, "sum"])) for k, m in groups.items()], columns=["k", "n", "bad"]).set_index("k")
            gs["br"] = gs.bad / gs.n; small = gs[gs.n < self.min_n]
            if small.empty or len(gs) == 1: break
            k = small.n.idxmin(); other = gs.drop(k).br.sub(gs.loc[k, "br"]).abs().idxmin()
            groups[other] += groups.pop(k)
        self.cat_map = {c: gi for gi, (k, m) in enumerate(groups.items()) for c in m}; self.unseen = 0
        return self._finalize(x, y)

    def _ids(self, x):
        x = np.asarray(x)
        if self.kind == "num": return np.searchsorted(self.cuts, x.astype(float), side="left")
        return np.array([self.cat_map.get(str(v), -1) for v in x])

    def _finalize(self, x, y):
        ids = self._ids(x); nb = ids.max() + 1; g, b = _counts(ids, y, nb); self.woe_ = _woe(g, b)
        G, B = g.sum(), b.sum(); self.iv_ = float(np.sum((g / G - b / B) * self.woe_))
        lab = []
        for i in range(nb):
            if self.kind == "num":
                lo = "-inf" if i == 0 else f"{self.cuts[i-1]:g}"; hi = "inf" if i == nb - 1 else f"{self.cuts[i]:g}"; lab.append(f"({lo}, {hi}]")
            else: lab.append("{" + ",".join(c for c, gi in self.cat_map.items() if gi == i) + "}")
        self.table_ = pd.DataFrame({"bin": lab, "count": (g + b).astype(int), "pct": (g + b) / (G + B), "bad_rate": b / np.maximum(g + b, 1), "woe": self.woe_})
        return self

    def transform(self, x):
        ids = self._ids(x); out = np.zeros(len(ids))
        m = ids >= 0; out[m] = self.woe_[ids[m]]; return out      # unseen category -> WoE 0 (neutral)
    def bin_index(self, x): return self._ids(x)
