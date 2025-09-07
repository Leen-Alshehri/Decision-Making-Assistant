
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Decision Helper", layout="centered")

st.title("Smart Decision Making Assistant")

st.header("1. What's your decision about?")
problem = st.text_input("Enter the decision you're trying to make:", "")

st.header("2. Enter your decision criteria (from most to least important)")

if 'criteria' not in st.session_state:
    st.session_state.criteria = [""]

def add_criterion():
    st.session_state.criteria.append("")

def reset_criteria():
    st.session_state.criteria = [""]

for i in range(len(st.session_state.criteria)):
    st.session_state.criteria[i] = st.text_input(f"Criterion {i+1}", value=st.session_state.criteria[i], key=f"crit_{i}")

st.button("➕ Add Another Criterion", on_click=add_criterion)
st.button("🔄 Reset Criteria", on_click=reset_criteria)

st.header("3. What are your options?")
options_input = st.text_area("Enter options separated by commas (e.g., Option A, Option B, Option C):", "")
options = [o.strip() for o in options_input.split(",") if o.strip()]

criteria = [c.strip() for c in st.session_state.criteria if c.strip()]

if criteria and options:
    n = len(criteria)
    descending_weights = list(range(n, 0, -1))
    weight_sum = sum(descending_weights)
    weights = {criteria[i]: descending_weights[i] / weight_sum for i in range(n)}

    st.header("4. Weights (auto-assigned based on priority)")
    for crit in criteria:
        st.write(f"**{crit}** → Weight: {weights[crit]:.2f}")

    st.header("5. Rate each option for each criterion (0–10)")
    scores = {}
    for opt in options:
        scores[opt] = {}
        st.subheader(f"Ratings for: {opt}")
        for crit in criteria:
            score = st.slider(f"{opt} - {crit}", 0, 10, 5, key=f"{opt}-{crit}")
            scores[opt][crit] = score

    df = pd.DataFrame(scores).T
    weighted_scores = df.apply(lambda row: sum(row[crit] * weights[crit] for crit in criteria), axis=1)
    df["Final Score"] = weighted_scores
    best_option = weighted_scores.idxmax()

    st.header("Final Decision")
    st.dataframe(df.style.highlight_max(axis=0))

    st.success(f"Best option: **{best_option}** with a score of {weighted_scores[best_option]:.2f}")

    st.subheader("Score Comparison")
    st.bar_chart(weighted_scores)

    st.header("What-if Mode")
    st.markdown("To try different scenarios, reorder your criteria or adjust scores.")
else:
    st.info("Please enter at least one criterion and one option to continue.")
