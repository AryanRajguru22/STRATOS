"""
STRATOS — Strategic Behavior in University Course / Project Team Formation.

Streamlit frontend entry point. Owned by Harsh (frontend only).

This file wires up layout, navigation, and session state against the
team's frozen interface contract (`docs/TEAM_WORK_ALLOCATION.md`,
Section 8): a `scenario` dict (students/projects/pref/w/gamma/skills)
and a `profile` (one project index per student), evaluated through
`game_engine` functions (`is_nash`, `best_response_dynamics`, ...).

All data generation, mock-engine fallback, and chart-building logic
lives in `app_helpers.py` so this file stays a thin UI layer. When
`game_engine.py` / `sample_data.py` are not available, `app_helpers`
transparently swaps in a contract-mirroring mock -- this file never
has to know which one is active.

Aryan's `game_engine.py` / `sample_data.py` and Ayush's report/PPT files
are out of scope here and are never created or modified by this file.
"""

import streamlit as st

import app_helpers as helpers

st.set_page_config(
    page_title="STRATOS — Team Formation Game Theory",
    page_icon="\U0001f3b2",
    layout="wide",
)

helpers.apply_custom_styles()

bundle = helpers.load_engine_bundle()
engine = bundle.engine
sample_data = bundle.sample_data


def build_scenario(preset: str) -> dict:
    if preset == "Tiny hand-verified example":
        return sample_data.get_tiny_scenario()
    if preset == "Default scenario":
        return sample_data.get_default_scenario()
    return helpers.generate_custom_mock_scenario(
        num_students=st.session_state.custom_num_students,
        num_projects=st.session_state.custom_num_projects,
        gamma=st.session_state.custom_gamma,
        seed=st.session_state.custom_seed,
    )


def set_profile(new_profile: list) -> None:
    """Overwrites the profile programmatically (Reset/Random/regenerate).
    Bumps profile_version so the per-student selectboxes below -- keyed on
    it -- pick up the new values instead of keeping their own prior state."""
    st.session_state.profile = new_profile
    st.session_state.profile_version = st.session_state.get("profile_version", 0) + 1
    st.session_state.pop("last_dynamics_result", None)


def reset_profile_for_scenario(scenario: dict) -> None:
    set_profile([0] * len(scenario["students"]))


with st.sidebar:
    st.header("Scenario")
    preset_options = ["Tiny hand-verified example", "Custom mock scenario"]
    if not bundle.using_mock:
        preset_options.insert(1, "Default scenario")
    preset = st.selectbox("Scenario preset", preset_options, key="scenario_preset")

    if preset == "Custom mock scenario":
        st.caption("Adjustable, clearly-mocked scenario for exploring the UI at other sizes.")
        st.slider("Number of students", 4, 12, value=8, key="custom_num_students")
        st.slider("Number of projects", 2, 5, value=3, key="custom_num_projects")
        st.slider("Crowding parameter (gamma)", 0.0, 5.0, value=1.0, step=0.5, key="custom_gamma")
        st.number_input("Random seed", min_value=0, max_value=9999, value=42, key="custom_seed")

    regenerate_clicked = st.button("\U0001f504 Regenerate scenario", use_container_width=True)
    need_init = "scenario" not in st.session_state or st.session_state.get("active_preset") != preset
    if regenerate_clicked or need_init:
        st.session_state.scenario = build_scenario(preset)
        st.session_state.active_preset = preset
        reset_profile_for_scenario(st.session_state.scenario)

    st.divider()
    st.caption("Best-response dynamics (used in the Simulation tab)")
    order_choice = st.radio("Student order each sweep", ["round_robin", "random"], key="order_choice")
    dynamics_seed = st.number_input("Dynamics seed", min_value=0, max_value=9999, value=7, key="dynamics_seed")
    max_rounds = st.slider("Max sweeps", 5, 200, value=50, key="max_rounds")

scenario = st.session_state.scenario
n_students = len(scenario["students"])
n_projects = len(scenario["projects"])

helpers.render_app_header(bundle)

tab_scenario, tab_assignment, tab_equilibrium, tab_simulation = st.tabs(
    ["\U0001f4cb Scenario", "\U0001f91d Assignment", "⚖️ Equilibrium", "\U0001f500 Simulation"]
)

# ---------------------------------------------------------------------------
# Tab 1: Scenario
# ---------------------------------------------------------------------------
with tab_scenario:
    st.subheader("Players, resources, and parameters")
    st.markdown(
        "**Students are players.** Each picks exactly one **project**. Utility combines "
        "(1) the student's own preference for that project, (2) teammate **compatibility** "
        "with everyone else on the same project, and (3) a **crowding cost** that grows with "
        "team size. Preferences and compatibility are shown below; try switching presets or "
        "the crowding parameter `gamma` to see how the scenario changes."
    )
    if bundle.using_mock:
        helpers.render_mock_badge("Mock scenario data -- mirrors the contract shape, not Aryan's real dataset")

    col_students, col_projects = st.columns(2)
    with col_students:
        st.markdown("**Students**")
        st.dataframe(helpers.students_df(scenario), use_container_width=True, hide_index=True)
    with col_projects:
        st.markdown("**Projects**")
        st.dataframe(helpers.projects_df(scenario), use_container_width=True, hide_index=True)
        st.metric("Crowding parameter (gamma)", scenario["gamma"])

    st.markdown("**Preferences** -- higher is more preferred (0–10 scale).")
    st.plotly_chart(helpers.preference_heatmap(scenario), use_container_width=True)

    st.markdown("**Teammate compatibility** -- symmetric, zero on the diagonal.")
    st.plotly_chart(helpers.compatibility_heatmap(scenario), use_container_width=True)
    with st.expander("How to read these charts"):
        st.markdown(
            "The preference heatmap shows each student's reported value for each project. "
            "The compatibility heatmap shows `w[i][j]`: blue means two students work well "
            "together if placed on the same team, red means friction; it never affects "
            "students on different teams."
        )

# ---------------------------------------------------------------------------
# Tab 2: Assignment
# ---------------------------------------------------------------------------
with tab_assignment:
    st.subheader("Build an assignment")
    st.markdown(
        "Choose a project for every student to build a **profile** `s = (s_0, ..., s_{n-1})`. "
        "Every profile built here is valid by construction -- each selector only offers real "
        "projects -- so it always passes `validate_profile`."
    )
    if bundle.using_mock:
        helpers.render_mock_badge()

    control_cols = st.columns([1, 1, 1, 2])
    with control_cols[0]:
        assignment_seed = st.number_input("Seed", min_value=0, max_value=9999, value=1, key="assignment_seed", label_visibility="collapsed")
    with control_cols[1]:
        if st.button("\U0001f3b2 Random", use_container_width=True):
            set_profile(engine.random_profile(scenario, seed=assignment_seed))
    with control_cols[2]:
        if st.button("↺ Reset", use_container_width=True):
            set_profile([0] * n_students)

    profile = st.session_state.profile
    profile_version = st.session_state.get("profile_version", 0)
    st.markdown("**Per-student assignment**")
    assignment_cols = st.columns(min(4, n_students))
    new_profile = list(profile)
    for i, name in enumerate(scenario["students"]):
        with assignment_cols[i % len(assignment_cols)]:
            choice = st.selectbox(
                name,
                options=list(range(n_projects)),
                format_func=lambda t: scenario["projects"][t],
                index=profile[i],
                key=f"assign_{i}_{st.session_state.active_preset}_{profile_version}",
            )
            new_profile[i] = choice
    st.session_state.profile = new_profile
    profile = new_profile

    try:
        engine.validate_profile(profile, scenario)
    except engine.StratosError as exc:
        st.error(str(exc))
        st.stop()

    st.divider()
    st.subheader("Evaluation panel")
    teams = engine.teams(profile, scenario)
    utilities = engine.utilities(profile, scenario)
    welfare = engine.social_welfare(profile, scenario)
    potential = engine.potential(profile, scenario)

    metric_cols = st.columns(2)
    metric_cols[0].metric("Social welfare W(s)", round(welfare, 2))
    metric_cols[1].metric("Potential Φ(s)", round(potential, 2))

    eval_cols = st.columns(2)
    with eval_cols[0]:
        st.markdown("**Teams by project**")
        st.dataframe(helpers.teams_df(teams, scenario), use_container_width=True, hide_index=True)
    with eval_cols[1]:
        st.markdown("**Utility per student**")
        st.dataframe(helpers.utilities_df(profile, scenario, utilities), use_container_width=True, hide_index=True)

    st.plotly_chart(helpers.utility_bar_chart(profile, scenario, utilities), use_container_width=True)

# ---------------------------------------------------------------------------
# Tab 3: Equilibrium
# ---------------------------------------------------------------------------
with tab_equilibrium:
    st.subheader("Is this assignment stable?")
    st.markdown(
        "An assignment is a **pure Nash equilibrium** if no student can gain by unilaterally "
        "switching to a different project while everyone else stays put. Stable is **not** the "
        "same as optimal -- it only means nobody wants to move alone."
    )
    if bundle.using_mock:
        helpers.render_mock_badge()

    profile = st.session_state.profile
    try:
        result = engine.is_nash(profile, scenario)
    except engine.StratosError as exc:
        st.error(str(exc))
        st.stop()

    if result["is_nash"]:
        st.success(
            "This assignment is **stable against unilateral deviations** -- no student can "
            "improve their utility by moving alone.",
            icon="⚖️",
        )
    else:
        n_dev = len(result["deviations"])
        st.warning(
            f"This assignment is **not stable** -- {n_dev} student(s) have a profitable "
            "unilateral move.",
            icon="⚠️",
        )
        top = result["deviations"][0]
        st.markdown(
            f"For example, **{scenario['students'][top['student']]}** would gain "
            f"**{top['gain']:.2f}** utility by moving from *{scenario['projects'][top['from_project']]}* "
            f"to *{scenario['projects'][top['to_project']]}*."
        )
        st.markdown("**All profitable deviations**")
        st.dataframe(helpers.deviations_df(result["deviations"], scenario), use_container_width=True, hide_index=True)

    with st.expander("What does 'stable' mean here?"):
        st.markdown(
            "This checks every student against every alternative project, one student at a "
            "time (a unilateral deviation), using the same potential-game model as the "
            "Assignment tab. It never claims the assignment is welfare-optimal or "
            "Pareto-optimal -- only that it resists single-student deviations."
        )

# ---------------------------------------------------------------------------
# Tab 4: Simulation
# ---------------------------------------------------------------------------
with tab_simulation:
    st.subheader("Best-response dynamics")
    st.markdown(
        "Starting from the assignment on the **Assignment** tab, students take turns switching "
        "to their best project, one sweep at a time, until nobody wants to move (or the sweep "
        "limit is reached)."
    )
    if bundle.using_mock:
        helpers.render_mock_badge()

    start_profile = st.session_state.profile
    if st.button("▶️ Run dynamics", type="primary"):
        try:
            st.session_state.last_dynamics_result = engine.best_response_dynamics(
                scenario, start_profile, order=order_choice, seed=dynamics_seed, max_rounds=max_rounds
            )
        except engine.StratosError as exc:
            st.error(str(exc))
            st.stop()

    if "last_dynamics_result" not in st.session_state:
        st.info("Run dynamics to see how this assignment evolves.", icon="ℹ️")
    else:
        result = st.session_state.last_dynamics_result
        final_profile = result["final_profile"]

        # Re-verify the final state with a fresh is_nash call -- never trust
        # the dynamics' own 'converged'/'is_nash_final' flag on its own.
        try:
            final_check = engine.is_nash(final_profile, scenario)
        except engine.StratosError as exc:
            st.error(str(exc))
            st.stop()

        metric_cols = st.columns(3)
        metric_cols[0].metric("Sweeps run", result["rounds"])
        metric_cols[1].metric("Moves made", len(result["steps"]))
        if not result["converged"]:
            metric_cols[2].metric("Status", "Not converged")
            st.warning(f"Hit the sweep limit ({max_rounds}) before no student wanted to move.", icon="⚠️")
        elif final_check["is_nash"]:
            metric_cols[2].metric("Status", "Stable")
            st.success("Re-verified: the final assignment is a pure Nash equilibrium.", icon="✅")
        else:
            metric_cols[2].metric("Status", "Unstable")
            st.error(
                "The dynamics reported convergence, but a fresh `is_nash` check found "
                "profitable deviations -- do not trust 'converged' alone.",
                icon="❌",
            )

        st.markdown("**Move-by-move trace**")
        st.dataframe(helpers.dynamics_steps_df(result["steps"], scenario), use_container_width=True, hide_index=True)

        if result["steps"]:
            step_idx = st.slider("Inspect profile after move #", 0, len(result["steps"]), value=len(result["steps"]))
            step_profile = helpers.profile_at_step(result["start_profile"], result["steps"], step_idx)
            st.markdown(f"**Teams after {step_idx} move(s)**")
            st.dataframe(
                helpers.teams_df(engine.teams(step_profile, scenario), scenario),
                use_container_width=True,
                hide_index=True,
            )

        trace_df = helpers.replay_welfare_potential_trace(engine, scenario, result["start_profile"], result["steps"])
        st.plotly_chart(helpers.dynamics_trace_chart(trace_df), use_container_width=True)

st.divider()
st.caption(
    "STRATOS frontend — built with Streamlit. "
    + ("Using the real game_engine / sample_data." if not bundle.using_mock else "Running on a contract-mirroring mock pending game_engine.py / sample_data.py.")
    + " Report & presentation materials are maintained separately."
)
