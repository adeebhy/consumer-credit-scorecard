"""Data loading, cleaning, feature engineering and the stratified split (UCI Taiwan credit-card default data)."""
import numpy as np, pandas as pd
from sklearn.model_selection import train_test_split

ST = [f"PAY_{i}" for i in range(1, 7)]            # repayment status, PAY_1 = most recent month (Sep), PAY_6 = Apr
BILLS = [f"BILL_AMT{i}" for i in range(1, 7)]; PAYS = [f"PAY_AMT{i}" for i in range(1, 7)]
ENG = ["util", "pay_to_bill", "max_delq", "n_delq", "bill_trend"]
NUM = ["LIMIT_BAL", "AGE"] + ST + BILLS + PAYS + ENG
CAT = ["EDUCATION", "SEX", "MARRIAGE"]
PROTECTED = ["SEX", "MARRIAGE"]                   # ECOA-protected: reported for IV, never used in the scorecard

def engineer(df):
    df = df.copy()
    df["util"] = (df[BILLS].mean(axis=1) / df.LIMIT_BAL).clip(-0.5, 2)
    df["pay_to_bill"] = (df[PAYS].sum(axis=1) / df[BILLS].clip(lower=1).sum(axis=1)).clip(0, 3)
    df["max_delq"] = df[ST].max(axis=1); df["n_delq"] = (df[ST] > 0).sum(axis=1)
    df["bill_trend"] = (df.BILL_AMT1 - df.BILL_AMT6) / df.LIMIT_BAL
    return df

def load(path="data/raw/UCI_Credit_Card.csv"):
    d = pd.read_csv(path).rename(columns={"PAY_0": "PAY_1", "default.payment.next.month": "default"}).drop(columns=["ID"])
    d["EDUCATION"] = d.EDUCATION.replace({0: 4, 5: 4, 6: 4}); d["MARRIAGE"] = d.MARRIAGE.replace({0: 3})
    return engineer(d)

def split(df, test_size=0.30, seed=42):
    return train_test_split(df, test_size=test_size, stratify=df.default, random_state=seed)
