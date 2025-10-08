
import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

st.set_page_config(page_title="Decision Helper", layout="wide")

st.title("Smart Decision Making Assistant")
st.caption(
    "Rank and score your options with transparent weighting, advanced analytics, and quick what-if scenarios."
)

st.header("1. What's your decision about?")
problem = st.text_input("Describe the decision you're trying to make:", "")

st.markdown("---")

st.header("2. Define and prioritise your criteria")

if "criteria" not in st.session_state:
    st.session_state.criteria = ["Cost", "Impact"]


def add_criterion():
    st.session_state.criteria.append("")


def reset_criteria():
    st.session_state.criteria = [""]
    st.session_state.pop("custom_weights", None)


criterion_cols = st.columns([3, 1, 1])
criterion_cols[0].markdown("**Criterion**")
criterion_cols[1].markdown("**Move Up**")
criterion_cols[2].markdown("**Move Down**")

indices_to_remove = []
for idx, value in enumerate(st.session_state.criteria):
    c1, c2, c3 = st.columns([3, 1, 1])
    st.session_state.criteria[idx] = c1.text_input(
        f"Criterion {idx + 1}", value=value, key=f"crit_{idx}"
    )
    if c2.button("⬆️", key=f"up_{idx}") and idx > 0:
        st.session_state.criteria[idx - 1], st.session_state.criteria[idx] = (
            st.session_state.criteria[idx],
            st.session_state.criteria[idx - 1],
        )
    if c3.button("⬇️", key=f"down_{idx}") and idx < len(st.session_state.criteria) - 1:
        st.session_state.criteria[idx + 1], st.session_state.criteria[idx] = (
            st.session_state.criteria[idx],
            st.session_state.criteria[idx + 1],
        )
    remove = c1.checkbox("Remove", key=f"remove_{idx}")
    if remove:
        indices_to_remove.append(idx)

for idx in sorted(indices_to_remove, reverse=True):
    st.session_state.criteria.pop(idx)

controls = st.columns(2)
controls[0].button("➕ Add Another Criterion", on_click=add_criterion, use_container_width=True)
controls[1].button("🔄 Reset Criteria", on_click=reset_criteria, use_container_width=True)

criteria = [c.strip() for c in st.session_state.criteria if c.strip()]

st.markdown("---")

st.header("3. List your options")
options_input = st.text_area(
    "Enter options separated by commas or on separate lines (e.g., Option A, Option B, Option C):",
    "",
)
options_normalised = options_input.replace("\n", ",")
options = [o.strip() for o in options_normalised.split(",") if o.strip()]

if criteria and options:
    weight_strategy = st.radio(
        "Choose a weighting strategy",
        ["Rank-based (auto)", "Custom weights"],
        horizontal=True,
    )

    if weight_strategy == "Rank-based (auto)":
        n = len(criteria)
        descending_weights = np.arange(n, 0, -1)
        weight_sum = descending_weights.sum()
        weights = {
            criteria[i]: float(descending_weights[i] / weight_sum) for i in range(n)
        }
        st.caption("Weights are assigned using the rank-sum method (higher priority = higher weight).")
    else:
        if "custom_weights" not in st.session_state:
            st.session_state.custom_weights = {
                crit: round(1.0 / len(criteria), 3) for crit in criteria
            }
        else:
            # Remove stale weights for deleted criteria
            for crit in list(st.session_state.custom_weights.keys()):
                if crit not in criteria:
                    st.session_state.custom_weights.pop(crit)
            # Add defaults for new criteria
            for crit in criteria:
                st.session_state.custom_weights.setdefault(
                    crit, round(1.0 / len(criteria), 3)
                )

        st.markdown("Adjust the sliders below – weights will automatically normalise to 1.0.")
        weight_inputs = {}
        for crit in criteria:
            weight_inputs[crit] = st.slider(
                f"Weight for {crit}",
                min_value=0.0,
                max_value=1.0,
                value=float(st.session_state.custom_weights.get(crit, 0.0)),
                step=0.01,
            )
        total_weight = sum(weight_inputs.values())
        if total_weight == 0:
            weights = {crit: 1.0 / len(criteria) for crit in criteria}
        else:
            weights = {crit: val / total_weight for crit, val in weight_inputs.items()}
        st.session_state.custom_weights.update(weight_inputs)
        st.info(
            f"Normalised weights: {', '.join(f'{crit} = {w:.2f}' for crit, w in weights.items())}"
        )

    st.header("4. Rate each option for each criterion")
    st.caption("Use a consistent 0–10 scale where 10 is the best possible performance.")

    if "score_matrix" not in st.session_state:
        st.session_state.score_matrix = pd.DataFrame(
            5, index=options, columns=criteria
        )

    score_matrix = st.session_state.score_matrix.reindex(
        index=options, columns=criteria, fill_value=5
    )

    entry_mode = st.radio(
        "How would you like to provide ratings?",
        ["Guided sliders", "Table editor"],
        horizontal=True,
    )

    if entry_mode == "Guided sliders":
        scores = {}
        for opt_index, opt in enumerate(options):
            with st.expander(f"Ratings for: {opt}", expanded=True):
                scores[opt] = {}
                for crit_index, crit in enumerate(criteria):
                    default_value = int(score_matrix.loc[opt, crit])
                    score = st.slider(
                        f"{opt} — {crit}",
                        min_value=0,
                        max_value=10,
                        value=default_value,
                        key=f"score_{opt_index}_{crit_index}",
                    )
                    scores[opt][crit] = score
                    score_matrix.loc[opt, crit] = score
        df = pd.DataFrame(scores).T
    else:
        st.info(
            "Edit the table directly. Values outside 0–10 will be clipped automatically when scoring."
        )
        edited = st.data_editor(
            score_matrix.astype(int),
            use_container_width=True,
            key="score_editor",
        )
        clipped = edited.clip(lower=0, upper=10).astype(int)
        if not edited.equals(clipped):
            st.warning("Some values were adjusted to stay within the 0–10 scale.")
        score_matrix = clipped
        df = score_matrix.copy()

    st.session_state.score_matrix = score_matrix

    weighted_scores = df.apply(
        lambda row: sum(row[crit] * weights[crit] for crit in criteria), axis=1
    )
    df["Final Score"] = weighted_scores
    sorted_scores = weighted_scores.sort_values(ascending=False)
    best_option = sorted_scores.index[0]
    runner_up = sorted_scores.index[1] if len(sorted_scores) > 1 else None

    st.markdown("---")
    st.header("Decision Intelligence Dashboard")

    summary_cols = st.columns(len(sorted_scores))
    for col, (opt, score) in zip(summary_cols, sorted_scores.items()):
        col.metric(opt, f"{score:.2f}", delta=None)

    st.success(
        f"**Recommended option:** {best_option} (score {sorted_scores[best_option]:.2f})"
    )
    if runner_up:
        difference = sorted_scores[best_option] - sorted_scores[runner_up]
        st.info(
            f"The top option is ahead of the runner-up ({runner_up}) by {difference:.2f} points."
        )

    contribution_matrix = df[criteria].mul(pd.Series(weights), axis=1)
    contribution_matrix["Contribution Sum"] = contribution_matrix.sum(axis=1)
    contribution_share = contribution_matrix[criteria].div(
        contribution_matrix["Contribution Sum"], axis=0
    ).fillna(0)

    tabs = st.tabs(["Scorecard", "Contribution Breakdown", "Scenario Planner"])

    with tabs[0]:
        st.subheader("Weighted Scorecard")
        st.dataframe(
            df.style.format({crit: "{:.1f}" for crit in criteria}).background_gradient(
                subset="Final Score", cmap="Blues"
            ),
            use_container_width=True,
        )
        csv_buffer = StringIO()
        df.to_csv(csv_buffer)
        st.download_button(
            label="⬇️ Download scores as CSV",
            data=csv_buffer.getvalue(),
            file_name="decision_scores.csv",
            mime="text/csv",
        )

    with tabs[1]:
        st.subheader("How each criterion contributes")
        st.caption(
            "Scores multiplied by their weights show the weighted contribution of each criterion."
        )
        st.dataframe(
            contribution_matrix.style.format("{:.2f}").highlight_max(axis=0),
            use_container_width=True,
        )
        st.markdown("**Contribution share by option**")
        st.dataframe(
            contribution_share.style.format("{:.0%}").highlight_max(axis=1),
            use_container_width=True,
        )
        st.bar_chart(contribution_matrix[criteria])

    with tabs[2]:
        st.subheader("Stress-test your decision")
        st.markdown(
            "Adjust importance multipliers to explore what-if scenarios. We renormalise the weights automatically."
        )
        multiplier_inputs = {}
        for crit in criteria:
            multiplier_inputs[crit] = st.slider(
                f"Multiplier for {crit}", 0.5, 1.5, 1.0, 0.05, key=f"mult_{crit}"
            )
        scenario_weights = {
            crit: weights[crit] * multiplier_inputs[crit] for crit in criteria
        }
        normaliser = sum(scenario_weights.values())
        scenario_weights = {
            crit: val / normaliser for crit, val in scenario_weights.items()
        }
        scenario_scores = df[criteria].apply(
            lambda row: sum(row[crit] * scenario_weights[crit] for crit in criteria), axis=1
        )
        scenario_df = pd.DataFrame(
            {
                "Base Score": weighted_scores,
                "Scenario Score": scenario_scores,
                "Change": scenario_scores - weighted_scores,
            }
        ).sort_values("Scenario Score", ascending=False)
        st.dataframe(
            scenario_df.style.format("{:.2f}").background_gradient(
                subset="Change", cmap="RdYlGn"
            ),
            use_container_width=True,
        )

        st.caption(
            "Tip: Push a multiplier up to emphasise a criterion or down to de-emphasise it and see how rankings respond."
        )

    with st.sidebar:
        st.header("Snapshot")
        if problem:
            st.markdown(f"**Decision:** {problem}")
        st.markdown("**Criteria weights**")
        for crit in criteria:
            st.progress(weights[crit], text=f"{crit}: {weights[crit]:.2f}")
        st.markdown("**Top options**")
        for opt, score in sorted_scores.items():
            st.write(f"{opt}: {score:.2f}")
else:
    st.info("Please enter at least one criterion and one option to continue.")
