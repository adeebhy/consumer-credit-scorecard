"""FastAPI scoring service.  Run:  uvicorn src.app:app --reload     (from the repo root)"""
import os, joblib, numpy as np, pandas as pd
from fastapi import FastAPI
from pydantic import create_model
from src.features import engineer, ST, BILLS, PAYS

ART = os.environ.get("SCORECARD_PATH", "data/processed/scorecard.joblib")
art = joblib.load(ART); sc = art["scorecard"]
FIELDS = ["LIMIT_BAL", "AGE", "EDUCATION"] + ST + BILLS + PAYS
Applicant = create_model("Applicant", **{f: (float, ...) for f in FIELDS})
app = FastAPI(title="Credit Scorecard API", version="1.0")

def _band(pd_):  return "Low" if pd_ < 0.10 else ("Medium" if pd_ < 0.30 else "High")

@app.get("/health")
def health(): return dict(status="ok", variables=list(sc.points), base_score=600, pdo=20)

@app.post("/score")
def score(a: Applicant):
    df = engineer(pd.DataFrame([a.model_dump()]))
    s = float(sc.score(df)[0]); p = float(sc.pd_from_score(s))
    # adverse-action style reason codes: variables where this applicant lost the most points vs. the best bin
    loss = {v: float(pts[np.clip(sc.b[v].bin_index(df[v].values), 0, len(pts) - 1)][0] - pts.max()) for v, pts in sc.points.items()}
    reasons = [dict(variable=v, points_lost=round(-l, 1)) for v, l in sorted(loss.items(), key=lambda kv: kv[1])[:3]]
    return dict(score=round(s), pd=round(p, 4), risk_band=_band(p), reason_codes=reasons)
