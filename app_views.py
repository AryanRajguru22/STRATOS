"""Tab renderers for the STRATOS Streamlit app (Scenario, Assignment, Equilibrium, Simulation, Guide).

Each function receives a `ctx` (types.SimpleNamespace built in app.py) with: bundle, engine, scenario, n, m, scenario_label,
order, dynamics_seed, max_rounds, set_profile(profile). Every number shown is read from the engine; nothing is hard-coded.
The Analysis tab lives in app_analysis.py.
"""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import app_helpers as H

EPS = H.EPS


def _num(v) -> str:
    return H._fmt(round(v, 6) if isinstance(v, float) else v)


def _signed(v) -> str:
    return ("+" if v > 0 else "") + _num(v)


# ---------------------------------------------------------------------------------------------- Scenario
def render_scenario_tab(ctx) -> None:
    sc, engine = ctx.scenario, ctx.engine
    st.subheader("Players, resources, and parameters")
    if ctx.bundle.using_mock:
        H.render_mock_badge("Mock scenario data -- mirrors the contract shape, not the real dataset")
    st.markdown(
        f"**Active scenario: {ctx.scenario_label}.** "
        "Students are **players**; each picks exactly one **project** (their **strategy**). A complete choice by all "
        "students is an **assignment** (a *strategy profile*). Utility rewards preference and good teammates and "
        "penalises crowded teams."
    )
    if ctx.synthetic_note:
        st.info(ctx.synthetic_note, icon="🧪")

    c = st.columns(4)
    c[0].metric("Students (players)", ctx.n)
    c[1].metric("Projects (strategies)", ctx.m)
    c[2].metric("Crowding parameter γ", _num(sc["gamma"]), help="Cost of a team of size k is γ·(k−1)². Larger γ discourages big teams.")
    c[3].metric("Possible assignments", f"{ctx.m ** ctx.n:,}", help=f"{ctx.m}^{ctx.n}: every student independently picks one of {ctx.m} projects.")

    st.latex(r"u_i(s)=\underbrace{p_{i,s_i}}_{\text{preference}}+\underbrace{\sum_{j\ne i,\;s_j=s_i}w_{ij}}_{\text{compatibility with teammates}}-\underbrace{\gamma\,(n_{s_i}-1)^2}_{\text{crowding cost}}")

    col_students, col_projects = st.columns(2)
    with col_students:
        st.markdown("**Students**")
        st.dataframe(H.students_df(sc), width="stretch", hide_index=True)
    with col_projects:
        st.markdown("**Projects**")
        st.dataframe(H.projects_df(sc), width="stretch", hide_index=True)

    with st.expander("What does the crowding parameter γ do?"):
        st.markdown(
            "Each project's team of size *k* pays a cost `c(k) = γ·(k−1)²` that is **shared by every member** "
            "(a lone student pays nothing). Because it is convex, the 3rd member of a team costs more than the 2nd, "
            "which is what spreads students across projects. With γ = 0 nobody minds crowding."
        )
        cdf = H.crowding_df(sc)
        st.dataframe(cdf, width="stretch", hide_index=True)

    st.markdown("#### Preferences versus compatibility")
    st.caption(
        "Two different things: **preference** is one student's taste for one project (student × project). "
        "**Compatibility** is a pairwise relationship (student × student); it only matters when the two end up on the "
        "same project, and it is symmetric: w[i][j] = w[j][i]."
    )
    st.plotly_chart(H.preference_heatmap(sc), width="stretch")
    st.plotly_chart(H.compatibility_heatmap(sc), width="stretch")
    with st.expander("How to read these charts"):
        st.markdown(
            "* **Preference heatmap** -- brighter = the student likes that project more. Hover for exact values.\n"
            "* **Compatibility heatmap** -- blue = the two students help each other if they share a team, red = friction. "
            "The diagonal is blank (a student is not their own teammate). The matrix is symmetric by construction, which the "
            "potential-game guarantee requires."
        )


# ---------------------------------------------------------------------------------------------- Assignment
def _explain(engine, scenario, profile, i) -> None:
    b = engine.utility_breakdown(i, profile, scenario)
    engine_u = engine.utility(i, profile, scenario)
    name, proj = scenario["students"][i], scenario["projects"][b["project"]]
    mates = ", ".join(f"{scenario['students'][t['student']]} ({_signed(t['weight'])})" for t in b["teammates"]) or "nobody else"
    st.markdown(
        f"**{name}** is on **{proj}** with {mates}.\n\n"
        f"* Preference for {proj}: **{_signed(b['preference'])}**\n"
        f"* Compatibility with teammates: **{_signed(b['compatibility'])}**\n"
        f"* Crowding cost for a team of {b['team_size']}, γ·({b['team_size']}−1)² = "
        f"{_num(scenario['gamma'])}·{(b['team_size'] - 1) ** 2}: **−{_num(b['crowding'])}**\n"
        f"* **Total utility = {_num(b['total'])}**"
    )
    terms = {"a low preference for this project": b["preference"], "teammate friction": b["compatibility"],
             "crowding": -b["crowding"]}
    worst = min(terms, key=terms.get)
    best = max(terms, key=terms.get)
    if b["total"] >= 0:
        st.caption(f"The biggest positive contribution is {'the preference' if best == 'a low preference for this project' else best}.")
    if terms[worst] < 0:
        st.caption(f"What pulls utility down most: {worst}.")
    if abs(b["total"] - engine_u) <= EPS:
        st.caption("✓ The three terms add up exactly to the engine's utility.")
    else:
        st.error(f"Breakdown total {b['total']} differs from the engine utility {engine_u}!")


def render_assignment_tab(ctx) -> None:
    sc, engine, n, m = ctx.scenario, ctx.engine, ctx.n, ctx.m
    st.subheader("Build an assignment")
    st.markdown(
        "Choose a project for every student to build a **profile** `s = (s₀, …, sₙ₋₁)`. Every profile built here is valid "
        "by construction -- each selector only offers real projects."
    )
    if ctx.bundle.using_mock:
        H.render_mock_badge()

    control_cols = st.columns([1, 1, 1, 1.4, 2])
    with control_cols[0]:
        assignment_seed = st.number_input("Seed", min_value=0, max_value=9999, value=1, key="assignment_seed",
                                          label_visibility="collapsed", help="Seed for the Random button.")
    with control_cols[1]:
        if st.button("\U0001f3b2 Random", width="stretch"):
            ctx.set_profile(engine.random_profile(sc, seed=assignment_seed))
    with control_cols[2]:
        if st.button("↺ Reset", width="stretch", help="Put every student on project 0."):
            ctx.set_profile([0] * n)
    with control_cols[3]:
        demo = getattr(ctx.bundle.sample_data, "get_demo_start_profile", None)
        demo_ok = bool(demo) and ctx.scenario_kind == "default"
        if st.button("▶ Demo start", width="stretch", disabled=not demo_ok,
                     help="The fixed, deliberately unstable start used in the live demo (default scenario only)."):
            ctx.set_profile(demo())

    profile = st.session_state.profile
    st.markdown("**Per-student assignment**")
    assignment_cols = st.columns(min(4, n))
    new_profile = list(profile)
    for i, name in enumerate(sc["students"]):
        with assignment_cols[i % len(assignment_cols)]:
            new_profile[i] = st.selectbox(
                name, options=list(range(m)), format_func=lambda t: sc["projects"][t], index=profile[i],
                key=f"assign_{i}_{st.session_state.scenario_version}_{st.session_state.get('profile_version', 0)}",
            )
    st.session_state.profile = new_profile
    profile = new_profile

    try:
        engine.validate_profile(profile, sc)
    except engine.StratosError as exc:
        st.error(str(exc))
        return

    teams = engine.teams(profile, sc)
    utilities = engine.utilities(profile, sc)
    welfare = engine.social_welfare(profile, sc)
    potential = engine.potential(profile, sc)

    st.divider()
    st.subheader("Evaluation")
    sizes = [len(t) for t in teams]
    c = st.columns(5)
    c[0].metric("Social welfare W(s)", _num(welfare), help="Sum of all students' utilities.")
    c[1].metric("Potential Φ(s)", _num(potential), help="Exact potential: a unilateral move changes Φ by exactly the mover's utility change.")
    c[2].metric("Largest team", max(sizes))
    c[3].metric("Empty projects", sizes.count(0))
    c[4].metric("Utility range", f"{_num(min(utilities))} … {_num(max(utilities))}")

    st.markdown("**Teams**")
    st.markdown(H.team_cards_html(teams, sc), unsafe_allow_html=True)

    breakdowns = [engine.utility_breakdown(i, profile, sc) for i in range(n)]
    bdf = H.breakdown_df(breakdowns, sc, utilities)
    if not bdf["Sums exactly"].all():
        st.error("A utility breakdown does not add up to the engine's utility -- please report this as a bug.")
    st.markdown("**Utility breakdown** -- preference + compatibility − crowding = utility")
    st.dataframe(bdf.drop(columns=["Sums exactly"]), width="stretch", hide_index=True)
    st.plotly_chart(H.breakdown_chart(bdf), width="stretch")

    st.markdown("**Why is this student's utility high or low?**")
    who = st.selectbox("Explain a student", list(range(n)), format_func=lambda i: sc["students"][i], key="explain_student")
    _explain(engine, sc, profile, who)


# ---------------------------------------------------------------------------------------------- Equilibrium
def render_equilibrium_tab(ctx) -> None:
    sc, engine, n = ctx.scenario, ctx.engine, ctx.n
    st.subheader("Is this assignment stable?")
    st.markdown(
        "An assignment is a **pure Nash equilibrium** if no student can gain by switching to a different project "
        "**alone**, while everyone else stays put. A move counts as *profitable* only if it **strictly** raises the mover's "
        "utility -- a tie is not a reason to move. Stable is **not** the same as optimal."
    )
    if ctx.bundle.using_mock:
        H.render_mock_badge()
    profile = st.session_state.profile
    try:
        result = engine.is_nash(profile, sc)
    except engine.StratosError as exc:
        st.error(str(exc))
        return
    devs = result["deviations"]
    n_students = H.count_students_with_deviations(devs)
    if any(d["gain"] <= 0 for d in devs):  # invariant: only strictly positive gains are profitable
        st.error("The engine returned a non-positive gain as a profitable move -- please report this as a bug.")
        return

    c = st.columns(4)
    c[0].metric("Verdict", "Stable" if result["is_nash"] else "Unstable")
    c[1].metric("Students who can improve", n_students, help="Distinct students with at least one profitable move.")
    c[2].metric("Profitable moves in total", len(devs),
                help="One entry per (student, destination) pair, so a student with two good destinations counts twice here but once on the left.")
    c[3].metric("Students at a best response", n - n_students)

    if result["is_nash"]:
        st.success("This assignment is **stable against unilateral deviations** -- no student can improve their "
                   "utility by moving alone.", icon="⚖️")
    else:
        st.warning(f"This assignment is **not stable** -- {n_students} student(s) have a profitable unilateral move "
                   f"({len(devs)} profitable move(s) in total).", icon="⚠️")

    gains = H.gain_matrix(engine, profile, sc)
    ties = [(i, t) for i in range(n) for t in range(ctx.m) if t != profile[i] and abs(gains[i][t]) <= EPS]
    st.markdown("#### What each student would gain by moving alone")
    st.plotly_chart(H.deviation_gain_heatmap(gains, profile, sc), width="stretch")
    if result["is_nash"]:
        extra = (f" {len(ties)} move(s) are exact ties (gain 0): they do **not** break stability." if ties else "")
        st.markdown(
            "**Why it is stable:** in every row no cell is green -- each student's current project already gives them "
            "the highest utility they can get by moving alone." + extra
        )
    else:
        names = ", ".join(sorted({sc["students"][d["student"]] for d in devs}))
        st.markdown(
            f"**What prevents stability:** the green cells -- {names} could each do strictly better by switching alone. "
            "A student with several green cells has several profitable destinations but still counts as one student."
        )
        top = max(devs, key=lambda d: d["gain"])
        st.markdown(f"Largest single gain: **{sc['students'][top['student']]}** gains **{_num(top['gain'])}** by moving from "
                    f"*{sc['projects'][top['from_project']]}* to *{sc['projects'][top['to_project']]}* "
                    f"({_num(top['current_utility'])} → {_num(top['new_utility'])}).")

        st.markdown("#### Every profitable move")
        st.dataframe(H.deviations_df(devs, sc), width="stretch", hide_index=True)
        st.markdown("**Per student** -- profitable destinations versus students who can improve")
        st.dataframe(H.student_deviation_summary_df(profile, sc, result["utilities"], devs), width="stretch", hide_index=True)

        st.markdown("#### Try a move")
        labels = {f"{sc['students'][d['student']]}: {sc['projects'][d['from_project']]} → {sc['projects'][d['to_project']]} (+{_num(d['gain'])})": d
                  for d in devs}
        choice = st.selectbox("Apply one profitable move to the assignment", list(labels), key="apply_move_choice")
        if st.button("Apply move", key="apply_move_button"):
            d = labels[choice]
            new = list(profile)
            new[d["student"]] = d["to_project"]
            ctx.set_profile(new)
            st.rerun()

    with st.expander("What does 'stable' mean here?"):
        st.markdown(
            "This checks every student against every alternative project, one student at a time (a *unilateral* "
            "deviation), using the same utility as the Assignment tab. It does not claim the assignment is welfare-optimal "
            "or Pareto-optimal, does not consider groups of students moving together, and does not say how students "
            "would get here."
        )


# ---------------------------------------------------------------------------------------------- Simulation
def render_simulation_tab(ctx) -> None:
    sc, engine = ctx.scenario, ctx.engine
    st.subheader("Best-response dynamics")
    st.markdown(
        "Starting from the assignment on the **Assignment** tab, students take turns switching to their best project, "
        "one sweep at a time, until nobody wants to move (or the sweep limit is reached). Order, seed and the sweep limit "
        "are set in the sidebar."
    )
    st.caption(
        "This is a *simulated adjustment process*, not a prediction of how real students behave. It terminates because "
        "every accepted move strictly raises the potential Φ and there are finitely many assignments."
    )
    if ctx.bundle.using_mock:
        H.render_mock_badge()

    start_profile = st.session_state.profile
    settings = {"start": list(start_profile), "order": ctx.order, "seed": int(ctx.dynamics_seed), "max_rounds": int(ctx.max_rounds),
                "scenario_version": st.session_state.scenario_version}
    if st.button("▶️ Run dynamics", type="primary"):
        try:
            st.session_state.last_dynamics_result = engine.best_response_dynamics(
                sc, start_profile, order=ctx.order, seed=ctx.dynamics_seed, max_rounds=ctx.max_rounds
            )
            st.session_state.last_dynamics_meta = settings
            st.session_state.sim_step = None
        except engine.StratosError as exc:
            st.error(str(exc))
            return

    if "last_dynamics_result" not in st.session_state:
        st.info("Run dynamics to see how this assignment evolves.", icon="ℹ️")
        return
    result = st.session_state.last_dynamics_result
    meta = st.session_state.get("last_dynamics_meta", {})
    if meta.get("scenario_version") != settings["scenario_version"]:
        st.session_state.pop("last_dynamics_result", None)
        st.info("The scenario changed; run the dynamics again.", icon="ℹ️")
        return
    if meta and {k: meta.get(k) for k in ("start", "order", "seed", "max_rounds")} != {k: settings[k] for k in ("start", "order", "seed", "max_rounds")}:
        st.warning("The result below was computed from a **different assignment or settings** than the current ones. "
                   "Press **Run dynamics** to refresh it.", icon="🕒")

    final_profile = result["final_profile"]
    try:
        final_check = engine.is_nash(final_profile, sc)  # fresh check; never trust 'converged' alone
    except engine.StratosError as exc:
        st.error(str(exc))
        return

    steps = result["steps"]
    max_rounds = meta.get("max_rounds", ctx.max_rounds)
    start_w, start_phi = engine.social_welfare(result["start_profile"], sc), engine.potential(result["start_profile"], sc)
    final_w, final_phi = engine.social_welfare(final_profile, sc), engine.potential(final_profile, sc)

    c = st.columns(5)
    c[0].metric("Sweeps run", result["rounds"])
    c[1].metric("Moves made", len(steps))
    c[2].metric("Welfare start → end", f"{_num(start_w)} → {_num(final_w)}")
    c[3].metric("Potential start → end", f"{_num(start_phi)} → {_num(final_phi)}")
    if not result["converged"]:
        c[4].metric("Termination", "Sweep limit")
        st.warning(f"**Stopped at the sweep limit** ({max_rounds}) before a full sweep passed with no moves. The final "
                   f"assignment is {'nevertheless a Nash equilibrium' if final_check['is_nash'] else 'not yet a Nash equilibrium'} "
                   "(fresh check).", icon="⚠️")
    elif final_check["is_nash"]:
        c[4].metric("Termination", "Equilibrium")
        st.success("**Reached a pure Nash equilibrium** -- a full sweep passed with nobody wanting to move, and a fresh "
                   "`is_nash` check of the final assignment re-verified it.", icon="✅")
    else:
        c[4].metric("Termination", "Inconsistent")
        st.error("The dynamics reported convergence, but a fresh `is_nash` check found profitable deviations -- do not "
                 "trust 'converged' alone.", icon="❌")

    st.markdown("**Move-by-move trace**")
    st.dataframe(H.dynamics_steps_df(steps, sc, start_potential=start_phi), width="stretch", hide_index=True)
    if steps and all("potential" in s for s in steps):
        phis = [start_phi] + [s["potential"] for s in steps]
        exact = all(abs((phis[k + 1] - phis[k]) - steps[k]["gain"]) <= EPS for k in range(len(steps)))
        st.caption(("✓ " if exact else "✗ ") + "For every move, ΔΦ equals the mover's gain (exact potential)"
                   + (" and Φ strictly increases." if exact and all(b > a for a, b in zip(phis, phis[1:])) else "."))

    step_idx = len(steps)
    if steps:
        step_idx = st.slider("Inspect the assignment after move #", 0, len(steps), value=len(steps), key="sim_step_slider")
        if step_idx > 0:
            s = steps[step_idx - 1]
            st.markdown(f"Move {step_idx}: **{sc['students'][s['student']]}** switched from *{sc['projects'][s['from_project']]}* "
                        f"to *{sc['projects'][s['to_project']]}* (gain {_num(s['gain'])}).")
    step_profile = H.profile_at_step(result["start_profile"], steps, step_idx)
    cols = st.columns([3, 2])
    with cols[0]:
        st.markdown(H.team_cards_html(engine.teams(step_profile, sc), sc), unsafe_allow_html=True)
    with cols[1]:
        st.metric("Welfare at this step", _num(engine.social_welfare(step_profile, sc)))
        st.metric("Potential at this step", _num(engine.potential(step_profile, sc)))
        st.metric("Stable at this step?", "yes" if engine.is_nash(step_profile, sc)["is_nash"] else "no")

    trace_df = H.replay_welfare_potential_trace(engine, sc, result["start_profile"], steps)
    st.plotly_chart(H.dynamics_trace_chart(trace_df, highlight_step=step_idx), width="stretch")
    if st.button("Use the final assignment as the current assignment", key="adopt_final"):
        ctx.set_profile(list(final_profile))
        st.rerun()


# ---------------------------------------------------------------------------------------------- Guide
def render_guide_tab(ctx) -> None:
    st.subheader("How STRATOS works")
    st.markdown("A short, accurate tour of the game theory behind every number in the app.")
    with st.expander("The game: players, strategies, profiles, utility", expanded=True):
        st.markdown(
            "* **Player** -- a student. **Strategy** -- the one project the student chooses. **Strategy profile** -- "
            "everybody's choice, `s = (s₀, …, sₙ₋₁)`.\n"
            "* **Utility** of student *i*: preference for the chosen project + compatibility with the teammates who chose "
            "the same project − a crowding cost for the team's size."
        )
        st.latex(r"u_i(s)=p_{i,s_i}+\sum_{j\neq i,\,s_j=s_i}w_{ij}-c(n_{s_i}(s)),\qquad c(k)=\gamma(k-1)^2")
        st.markdown("`w` is **symmetric** (`w_ij = w_ji`) and `n_t(s)` is the number of students on project *t*.")
    with st.expander("Social welfare and the potential function"):
        st.latex(r"W(s)=\sum_i u_i(s)")
        st.latex(r"\Phi(s)=\sum_i p_{i,s_i}+\sum_{i<j,\;s_i=s_j}w_{ij}-\sum_t\sum_{k=1}^{n_t}c(k)")
        st.markdown(
            "Welfare adds up what everybody gets. The **potential** Φ is a different number built so that when *one* "
            "student changes project, Φ changes by **exactly** that student's change in utility. A game with such a Φ is "
            "an **exact potential game**."
        )
    with st.expander("Profitable deviation and pure Nash equilibrium"):
        st.markdown(
            "A **profitable unilateral deviation** is a switch by one student that *strictly* increases their own utility "
            "while everyone else keeps their project. A **pure Nash equilibrium** is an assignment with none. "
            "Ties are not profitable.\n\n"
            "A Nash equilibrium does **not** mean everyone is maximally happy: it only means no individual student can "
            "improve by switching alone."
        )
    with st.expander("Why an equilibrium exists and best-response dynamics stops"):
        st.markdown(
            "Φ takes finitely many values, so some assignment maximises it. From there any unilateral move would raise Φ "
            "(because ΔΦ = the mover's gain), so no move is profitable: a **pure Nash equilibrium exists**. "
            "Likewise, every accepted best-response move strictly increases Φ and the assignments are finite, so "
            "**best-response dynamics can never cycle and must terminate**. The proof is in `docs/MODEL.md`; it needs "
            "a symmetric `w` and a crowding cost that depends only on team size."
        )
    with st.expander("Stable but inefficient: PoS, PoA and Pareto"):
        st.markdown(
            "* A stable assignment can have low welfare, and the welfare-maximising assignment can be unstable.\n"
            "* **Price of stability** = optimum welfare ÷ best equilibrium welfare; **price of anarchy** = optimum welfare ÷ "
            "worst equilibrium welfare. Both are 1 when no welfare is lost. They are reported as *undefined* when the optimum "
            "or any equilibrium welfare is not strictly positive.\n"
            "* An assignment is **Pareto-optimal** if no other assignment helps someone without hurting anyone. Nash "
            "stability and Pareto efficiency are different properties."
        )
    with st.expander("Best-response dynamics"):
        st.markdown(
            "In each **sweep** every student, in round-robin or seeded-random order, switches to the project with the "
            "highest utility given the others -- but only for a strictly positive gain. The run stops when a full sweep "
            "has no move (an equilibrium) or the sweep limit is reached. It is a **simulation** of one adjustment process, "
            "not evidence of how real students behave."
        )
    with st.expander("Assumptions and limitations", expanded=True):
        st.markdown(
            "* **All data is synthetic**: names, preferences, skills and weights are fictional and illustrative.\n"
            "* Complete information and a **static** (one-shot) game.\n"
            "* Only **unilateral** deviations are analysed; coalitions of students moving together are out of scope.\n"
            "* Compatibility is additive and pairwise; crowding is soft (no hard capacity).\n"
            "* Exhaustive enumeration is **exponential** and capped at 100,000 assignments.\n"
            "* STRATOS is an educational model, not a university allocation system."
        )
