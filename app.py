import requests
import streamlit as st

st.set_page_config(
    page_title="Credit Risk Scorecard", page_icon="💳", layout="centered"
)


# --- 1. HELPER FUNCTIONS & NARRATIVE GENERATORS ---
def format_reason_code(reason_dict):
  variable = reason_dict.get("variable")
  points = reason_dict.get("points_lost")

  descriptions = {
      "PAY_1": "Recent repayment delay or severe delinquency status observed",
      "PAY_2": "Prior repayment delay recorded in the second previous cycle",
      "PAY_3": "Delinquency or irregular payment pattern in the third cycle",
      "PAY_4": "Irregular payment pattern noted four months prior",
      "PAY_5": "Payment delay recorded five months prior",
      "PAY_6": "Payment delay recorded six months prior",
      "LIMIT_BAL": "Total credit limit balance is relatively low",
      "AGE": "Age bracket risk factor",
      "EDUCATION": "Education level risk tier",
      "PAY_AMT1": (
          "Insufficient payment amount relative to balance in the latest cycle"
      ),
      "PAY_AMT2": "Low payment amount recorded in the second previous cycle",
      "PAY_AMT3": "Low payment amount recorded in the third previous cycle",
      "PAY_AMT4": "Low payment amount recorded in the fourth previous cycle",
      "PAY_AMT5": "Low payment amount recorded in the fifth previous cycle",
      "PAY_AMT6": "Low payment amount recorded in the sixth previous cycle",
      "BILL_AMT1": "High revolving balance relative to credit limit",
  }

  base_msg = descriptions.get(
      variable, f"Negative impact from factor: {variable}"
  )
  return f"{base_msg} (Impact: -{points} pts)"


def get_lending_recommendation(score, pd_val, risk_band):
  pd_pct = pd_val * 100

  if pd_pct <= 5.0 or risk_band == "Low Risk":
    return {
        "decision": "APPROVED",
        "advice": (
            f"Low default probability ({pd_pct:.2f}%). The applicant"
            " demonstrates strong creditworthiness. Recommended for standard"
            " loan terms."
        ),
    }
  elif pd_pct <= 20.0 or risk_band == "Medium Risk":
    return {
        "decision": "CONDITIONAL APPROVAL / MANUAL REVIEW",
        "advice": (
            f"Moderate default probability ({pd_pct:.2f}%). While risky, it falls"
            " within an acceptable risk tolerance band for conditional lending."
            " Recommended to request income proof, reduce the credit limit, or"
            " apply risk-adjusted higher interest rates."
        ),
    }
  else:
    return {
        "decision": "DECLINED",
        "advice": (
            f"High probability of default ({pd_pct:.2f}%) and severe"
            " repayment risks detected. Issuing a loan carries a high risk of"
            " financial loss. Adverse action notice recommended."
        ),
    }


def get_borrower_action_plan(reason_codes):
  advice_set = set()

  for reason in reason_codes:
    var = (
        reason.get("variable") if isinstance(reason, dict) else str(reason)
    )

    if any(
        p in var for p in ["PAY_1", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
    ):
      advice_set.add(
          "🚨 **Bring Delinquent Accounts Current:** Your recent payment"
          " history has the highest impact on your score. Focus immediately"
          " on clearing any past-due amounts and ensuring future bills are"
          " paid on time."
      )
    elif "LIMIT_BAL" in var:
      advice_set.add(
          "💳 **Improve Credit Utilization:** Your credit limit is relatively"
          " low compared to your balances. Avoid maxing out your cards, keep"
          " your revolving utilization below 30%, and inquire about a credit"
          " limit increase."
      )
    elif any(
        pa in var
        for pa in [
            "PAY_AMT1",
            "PAY_AMT2",
            "PAY_AMT3",
            "PAY_AMT4",
            "PAY_AMT5",
            "PAY_AMT6",
        ]
    ):
      advice_set.add(
          "💰 **Increase Monthly Payments:** Consistently paying only the"
          " minimum keeps balances high. Try paying significantly more than"
          " the minimum due to lower your overall principal faster."
      )

  if not advice_set:
    advice_set.add(
        "✨ **Maintain Healthy Habits:** Continue making on-time payments, keep"
        " credit card balances low, and avoid applying for multiple new credit"
        " lines in a short period."
    )

  return list(advice_set)


def generate_credit_narrative(score, pd_val, risk_band):
  pd_pct = pd_val * 100

  if pd_pct <= 5.0:
    severity = "very low"
    comparison = (
        "This is an excellent position, well below prime portfolio averages"
        " where PD estimates typically sit below 2–3%."
    )
    outlook = (
        "Loan approval is highly probable with access to the most competitive"
        " market interest rates and premium product tiers."
    )
  elif pd_pct <= 15.0:
    severity = "moderate"
    comparison = (
        "This reflects a balanced risk tier. While acceptable for lending, it"
        " sits above top-tier prime thresholds."
    )
    outlook = (
        "Loan approval is generally feasible, though lenders may apply"
        " risk-adjusted pricing or request minor income verification."
    )
  elif pd_pct <= 30.0:
    severity = "elevated"
    comparison = (
        "This is on the higher side, reflecting past stress or irregular"
        " repayment indicators in the profile history."
    )
    outlook = (
        "Standard unsecured loan approvals become difficult; many institutions"
        " set stricter risk cutoffs or require collateral/guarantors."
    )
  else:
    severity = "critical"
    comparison = (
        "This indicates significant default vulnerability, placing the"
        " borrower in a high-risk category."
    )
    outlook = (
        "Standard automated approvals are unlikely, and lending carries a"
        " high probability of financial loss, typically triggering an adverse"
        " action notice."
    )

  narrative = (
      f"In the context of your **{score} credit score**, a **PD of"
      f" {pd_pct:.2f}%** means the lender's risk model estimates a"
      f" **{pd_pct:.2f}% chance of default** within the next 12 months. This"
      f" probability is considered **{severity}** and maps to the **{risk_band}"
      f"** tier. {comparison}\n\n"
      f"**What this means in practice:**\n"
      f"- **Approval & Terms:** {outlook}\n"
      f"- **Pricing Impact:** Lenders price default risk directly into the"
      f" cost of credit; higher PD values result in increased interest rates or"
      f" lower approved credit limits.\n"
      f"- **Underwriting Discretion:** Companion repayment behavioral tracks"
      f" heavily dictate final lending approval."
  )

  return narrative


# --- 2. UI LAYOUT ---
st.title("💳 Consumer Credit Risk Scorecard")
st.markdown(
    "Enter the client details below to calculate their credit score, Probability"
    " of Default (PD), and risk band."
)

with st.form("scorecard_form"):
  st.subheader("Financial & Demographic Details")
  col1, col2 = st.columns(2)

  with col1:
    limit_bal = st.number_input(
        "Limit Balance (LIMIT_BAL)", min_value=0.0, value=50000.0, step=5000.0
    )
    age = st.number_input("Age (AGE)", min_value=18, max_value=100, value=35)
    education = st.selectbox(
        "Education (EDUCATION)",
        options=[1, 2, 3, 4],
        format_func=lambda x: [
            "Graduate",
            "University",
            "High School",
            "Other",
        ][x - 1],
    )

  st.subheader("Recent Repayment Status (PAY_1 to PAY_6)")
  st.markdown(
      "*(-2: No consumption, -1: Paid duly, 1-8: Months of delay)*"
  )
  pay_cols = st.columns(6)
  pay_vals = []
  for i, col in enumerate(pay_cols, start=1):
    with col:
      val = st.number_input(f"PAY_{i}", value=0 if i == 1 else -1, step=1)
      pay_vals.append(val)

  st.subheader("Bill Amounts (BILL_AMT1 to BILL_AMT6)")
  bill_cols = st.columns(3)
  bill_vals = []
  for i, col in enumerate(bill_cols, start=1):
    with col:
      val = st.number_input(
          f"Bill Amt {i}", min_value=0.0, value=20000.0 - (i * 1000), step=1000.0
      )
      bill_vals.append(val)
  bill_cols_2 = st.columns(3)
  for i, col in enumerate(bill_cols_2, start=4):
    with col:
      val = st.number_input(
          f"Bill Amt {i}", min_value=0.0, value=15000.0 - (i * 1000), step=1000.0
      )
      bill_vals.append(val)

  st.subheader("Previous Payments (PAY_AMT1 to PAY_AMT6)")
  pay_amt_cols = st.columns(3)
  pay_amt_vals = []
  for i, col in enumerate(pay_amt_cols, start=1):
    with col:
      val = st.number_input(
          f"Pay Amt {i}", min_value=0.0, value=1500.0, step=500.0
      )
      pay_amt_vals.append(val)
  pay_amt_cols_2 = st.columns(3)
  for i, col in enumerate(pay_amt_cols_2, start=4):
    with col:
      val = st.number_input(
          f"Pay Amt {i}", min_value=0.0, value=1000.0, step=500.0
      )
      pay_amt_vals.append(val)

  submitted = st.form_submit_button("Calculate Score & Risk")

# --- 3. API SUBMISSION & RESULTS HANDLING ---
if submitted:
  payload = {
      "LIMIT_BAL": limit_bal,
      "EDUCATION": education,
      "AGE": age,
      "PAY_1": pay_vals[0],
      "PAY_2": pay_vals[1],
      "PAY_3": pay_vals[2],
      "PAY_4": pay_vals[3],
      "PAY_5": pay_vals[4],
      "PAY_6": pay_vals[5],
      "BILL_AMT1": bill_vals[0],
      "BILL_AMT2": bill_vals[1],
      "BILL_AMT3": bill_vals[2],
      "BILL_AMT4": bill_vals[3],
      "BILL_AMT5": bill_vals[4],
      "BILL_AMT6": bill_vals[5],
      "PAY_AMT1": pay_amt_vals[0],
      "PAY_AMT2": pay_amt_vals[1],
      "PAY_AMT3": pay_amt_vals[2],
      "PAY_AMT4": pay_amt_vals[3],
      "PAY_AMT5": pay_amt_vals[4],
      "PAY_AMT6": pay_amt_vals[5],
  }

  try:
    response = requests.post("http://127.0.0.1:8000/score", json=payload)
    if response.status_code == 200:
      res_data = response.json()

      st.success("Scoring Complete!")

      # 1. Metric Results
      col_res1, col_res2, col_res3 = st.columns(3)
      col_res1.metric("Credit Score", res_data.get("score"))
      col_res2.metric(
          "Probability of Default (PD)", f"{res_data.get('pd') * 100:.2f}%"
      )
      col_res3.metric("Risk Band", res_data.get("risk_band"))

      # 2. Executive Credit Risk Narrative
      st.markdown("---")
      st.subheader("📋 Comprehensive Risk & Portfolio Context")
      credit_narrative = generate_credit_narrative(
          res_data.get("score"), res_data.get("pd"), res_data.get("risk_band")
      )
      st.markdown(credit_narrative)

      # 3. Translated Reason Codes
      st.subheader("Top Reason Codes")
      for reason in res_data.get("reason_codes", []):
        if isinstance(reason, dict):
          clean_text = format_reason_code(reason)
        else:
          clean_text = str(reason)
        st.write(f"- {clean_text}")

      # 4. Automated Lender Recommendation
      rec = get_lending_recommendation(
          res_data.get("score"), res_data.get("pd"), res_data.get("risk_band")
      )

      st.markdown("---")
      st.subheader("💡 Automated Lending Recommendation")
      if rec["decision"] == "APPROVED":
        st.success(f"**Decision: {rec['decision']}**\n\n{rec['advice']}")
      elif rec["decision"] == "CONDITIONAL APPROVAL / MANUAL REVIEW":
        st.warning(f"**Decision: {rec['decision']}**\n\n{rec['advice']}")
      else:
        st.error(f"**Decision: {rec['decision']}**\n\n{rec['advice']}")

      # 5. Borrower Action Plan Expander
      with st.expander(
          "📖 Borrower Credit Improvement Plan (Share with Applicant)"
      ):
        st.markdown(
            "Based on this profile's risk factors, here are actionable steps"
            " the borrower can take to improve their creditworthiness over"
            " time:"
        )
        action_tips = get_borrower_action_plan(res_data.get("reason_codes", []))
        for tip in action_tips:
          st.markdown(f"- {tip}")

    else:
      st.error(f"API Error: {response.text}")
  except requests.exceptions.ConnectionError:
    st.error(
        "Could not connect to the FastAPI server. Make sure it is running via"
        " `uvicorn src.app:app --reload`."
    )
