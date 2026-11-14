"""Analysis tab for STRATOS: exhaustive strategic analysis of the active scenario.

Everything shown comes from `game_engine.analyze_landscape` (one pass over all m**n assignments) and, for the current
assignment, from the engine's own `social_welfare` / `potential` / `is_nash`. Nothing is hard-coded. The tab degrades
gracefully: in mock mode or above the engine's enumeration cap it explains why the analysis is unavailable instead of
attempting it.
"""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import app_helpers as H
from app_helpers import ACCENT, BG, BORDER, MUTED, PANEL, PANEL2, STATUS, TEXT


def scenario_key(scenario: dict) -> str:
    """Stable cache key: the canonical JSON of the numbers that define the game (names included)."""
    core = {k: scenario[k] for k in ("students", "projects", "pref", "w", "gamma")}
    return json.dumps(core, sort_keys=True, default=str)


@st.cache_data(show_spinner=False, max_entries=6)
def cached_landscape(key: str) -> dict:
    """analyze_landscape keyed on the scenario's canonical JSON, so a changed scenario can never see a stale result."""
    import game_engine

    return game_engine.analyze_landscape(json.loads(key))


def enumeration_cap(engine) -> int:
    return getattr(engine, "MAX_ENUMERATION_PROFILES", 100_000)


def describe_profile(profile: list, scenario: dict) -> str:
    """'Project A: Asha, Bram | Project B: Chen | ...' (empty teams omitted)."""
    parts = []
    for t, name in enumerate(scenario["projects"]):
        members = [scenario["students"][i] for i, p in enumerate(profile) if p == t]
        if members:
            parts.append(f"{name}: {', '.join(members)}")
    return " | ".join(parts)


# ---------------------------------------------------------------------------------------------- charts
def welfare_comparison_chart(rows: list) -> go.Figure:
    """rows: [(label, welfare, colour)] top to bottom."""
    labels = [r[0] for r in rows]
    fig = go.Figure(go.Bar(
        y=labels, x=[r[1] for r in rows], orientation="h", marker_color=[r[2] for r in rows],
        text=[H._fmt(r[1]) for r in rows], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}<br>social welfare = %{x}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Social welfare W(s)")
    return H._base_layout(fig, "Social welfare: current assignment vs equilibria vs the optimum", height=280)


def equilibrium_welfare_chart(a: dict, current_welfare=None) -> go.Figure:
    levels = a["equilibrium_welfare_levels"]
    w_opt = a["optimal"]["welfare"]
    colors = [STATUS["good"] if abs(lv["welfare"] - w_opt) < H.EPS else ACCENT for lv in levels]
    fig = go.Figure(go.Bar(
        x=[lv["welfare"] for lv in levels], y=[lv["count"] for lv in levels], marker_color=colors,
        hovertemplate="welfare %{x}<br>%{y} equilibrium assignment(s)<extra></extra>",
    ))
    fig.add_vline(x=w_opt, line_dash="dash", line_color=STATUS["good"],
                  annotation_text="welfare optimum", annotation_font_color=STATUS["good"], annotation_position="top")
    if current_welfare is not None:
        fig.add_vline(x=current_welfare, line_dash="dot", line_color=STATUS["warning"],
                      annotation_text="current", annotation_font_color=STATUS["warning"], annotation_position="bottom")
    fig.update_xaxes(title="Social welfare of the equilibrium")
    fig.update_yaxes(title="Number of equilibria", dtick=1 if max(lv["count"] for lv in levels) < 10 else None)
    return H._base_layout(fig, "Welfare distribution among pure Nash equilibria", height=360)


def all_vs_equilibria_chart(a: dict) -> go.Figure:
    rows = a["welfare_distribution"]
    fig = go.Figure()
    fig.add_bar(x=[r["welfare"] for r in rows], y=[r["n_profiles"] for r in rows], name="All assignments",
                marker_color="#3b4b6e", hovertemplate="welfare %{x}<br>%{y} assignments<extra></extra>")
    fig.add_bar(x=[r["welfare"] for r in rows], y=[r["n_equilibria"] or None for r in rows], name="Equilibria",
                marker_color=ACCENT, hovertemplate="welfare %{x}<br>%{y} equilibria<extra></extra>")
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title="Social welfare W(s)")
    fig.update_yaxes(title="Number of assignments (log scale)", type="log")
    return H._base_layout(fig, "All assignments vs equilibria, by social welfare", height=360)


def welfare_potential_chart(a: dict, current=None) -> go.Figure:
    pts = a["welfare_potential_points"]
    fig = go.Figure()
    for is_eq, name, color, size, opacity in ((False, "Not an equilibrium", "#4b5c82", 6, 0.55),
                                              (True, "Pure Nash equilibrium", ACCENT, 10, 1.0)):
        sel = [p for p in pts if p["is_equilibrium"] == is_eq]
        if sel:
            fig.add_scatter(
                x=[p["potential"] for p in sel], y=[p["welfare"] for p in sel], mode="markers", name=name,
                marker=dict(color=color, size=size, opacity=opacity, line=dict(color=BG, width=0.5)),
                customdata=[p["count"] for p in sel],
                hovertemplate="potential Φ = %{x}<br>welfare W = %{y}<br>%{customdata} assignment(s)<extra>" + name + "</extra>",
            )
    opt = a["optimal"]
    if current is not None:
        fig.add_scatter(x=[current["potential"]], y=[current["welfare"]], mode="markers", name="Current assignment",
                        marker=dict(symbol="diamond", size=15, color=STATUS["warning"], line=dict(color=TEXT, width=1.5)),
                        hovertemplate="current<br>Φ = %{x}<br>W = %{y}<extra></extra>")
    if a.get("optimum_potential") is not None:
        fig.add_scatter(x=[a["optimum_potential"]], y=[opt["welfare"]], mode="markers", name="Welfare optimum",
                        marker=dict(symbol="star", size=16, color=STATUS["good"], line=dict(color=TEXT, width=1)),
                        hovertemplate="welfare optimum<br>Φ = %{x}<br>W = %{y}<extra></extra>")
    fig.update_xaxes(title="Potential Φ(s)")
    fig.update_yaxes(title="Social welfare W(s)")
    return H._base_layout(fig, "Welfare vs potential: equilibria are not simply the high-welfare assignments", height=430)


# ---------------------------------------------------------------------------------------------- tab
def _ratio_metric(col, label: str, value, defined: bool, help_text: str) -> None:
    col.metric(label, f"{value:.4g}" if defined and value is not None else "undefined", help=help_text)


def render_analysis_tab(bundle, engine, scenario: dict, profile: list, set_profile) -> None:
    st.subheader("Strategic analysis of the whole scenario")
    st.markdown(
        "Exhaustively checks **every** possible assignment, so the figures below describe the entire game, not just the "
        "assignment you built. All values are computed by the engine from the active scenario."
    )
    if bundle.using_mock or not hasattr(engine, "analyze_landscape"):
        H.render_mock_badge()
        st.warning(
            "The Analysis tab needs the real `game_engine.py` (`analyze_landscape`). It is disabled while the mock "
            "engine is active so that no mock number is ever presented as an exhaustive result.",
            icon="⚠️",
        )
        return

    n, m = len(scenario["students"]), len(scenario["projects"])
    total, cap = m ** n, enumeration_cap(engine)
    if total > cap:
        st.warning(
            f"**Exhaustive analysis is unavailable for this scenario.** It has {m}^{n} = {total:,} possible assignments, "
            f"which is above the safe enumeration limit of {cap:,}. The number of assignments grows exponentially "
            "(every extra student multiplies it by the number of projects), so STRATOS refuses to start a computation "
            "that could freeze the app.",
            icon="🧮",
        )
        st.markdown(
            f"* Reduce the scenario to at most about {cap:,} assignments (for example 10 students with 3 projects, or "
            "8 students with 4 projects) to enable this tab.\n"
            "* The **Assignment**, **Equilibrium** and **Simulation** tabs still work: they check one assignment at a "
            "time, which costs only O(n²·m) utility evaluations per check."
        )
        return

    try:
        with st.spinner(f"Evaluating all {total:,} assignments…"):
            a = cached_landscape(scenario_key(scenario))
    except engine.StratosError as exc:
        st.error(f"Analysis failed: {exc}")
        return

    cur_w = engine.social_welfare(profile, scenario)
    cur_phi = engine.potential(profile, scenario)
    cur_nash = engine.is_nash(profile, scenario)["is_nash"]
    opt = a["optimal"]
    opt_is_eq = any(a["optimal_is_equilibrium"])

    # ---- A. landscape
    st.markdown("### 1 · Equilibrium landscape")
    c = st.columns(4)
    c[0].metric("Possible assignments", f"{a['n_profiles']:,}", help=f"{m}^{n}: every student chooses one of {m} projects.")
    c[1].metric("Pure Nash equilibria", a["n_equilibria"], help="Assignments where no student gains by switching alone.")
    c[2].metric("Share that are equilibria", f"{100 * a['equilibrium_share']:.2f}%")
    c[3].metric("Distinct equilibrium welfare levels", a["n_equilibrium_welfare_levels"])
    c = st.columns(3)
    c[0].metric("Best equilibrium welfare", H._fmt(a["best_equilibrium"]["welfare"]) if a["best_equilibrium"] else "—")
    c[1].metric("Worst equilibrium welfare", H._fmt(a["worst_equilibrium"]["welfare"]) if a["worst_equilibrium"] else "—")
    c[2].metric("Maximum possible welfare", H._fmt(opt["welfare"]),
                help=f"Reached by {len(a['optimal_profiles'])} assignment(s); {sum(a['optimal_is_equilibrium'])} of them stable.")
    if a["n_equilibria"] >= 1:
        st.caption(
            "At least one pure equilibrium is guaranteed here because the game is an exact potential game "
            "(a maximiser of Φ is always an equilibrium) -- and the exhaustive search confirms it."
        )
    st.plotly_chart(equilibrium_welfare_chart(a, cur_w), width="stretch")

    # ---- B. welfare comparison
    st.markdown("### 2 · Social welfare comparison")
    rows = [("Current assignment", cur_w, STATUS["warning"])]
    if a["worst_equilibrium"]:
        rows += [("Worst equilibrium", a["worst_equilibrium"]["welfare"], "#7aa2f7"),
                 ("Best equilibrium", a["best_equilibrium"]["welfare"], ACCENT)]
    rows.append(("Maximum possible welfare", opt["welfare"], STATUS["good"]))
    st.plotly_chart(welfare_comparison_chart(rows), width="stretch")
    st.markdown(
        f"The current assignment is **{'a pure Nash equilibrium' if cur_nash else 'not a pure Nash equilibrium'}** "
        f"with welfare {H._fmt(cur_w)} (potential {H._fmt(cur_phi)})."
    )
    if opt_is_eq and all(a["optimal_is_equilibrium"]):
        st.success("Every welfare-maximising assignment of this scenario is also stable: here efficiency and stability coincide.", icon="✅")
    else:
        stable_opt = sum(a["optimal_is_equilibrium"])
        st.info(
            f"**Why the optimum may not be stable.** {len(a['optimal_profiles'])} assignment(s) reach the maximum welfare "
            f"{H._fmt(opt['welfare'])}; {stable_opt} of them {'is' if stable_opt == 1 else 'are'} an equilibrium. Welfare counts "
            "everybody's utility, but a student only compares their *own* utility before and after a move. A move that "
            "helps the mover can hurt teammates by more, and a socially best arrangement can ask one student to stay "
            "where they could do better alone.",
            icon="ℹ️",
        )
        for k, prof in enumerate(a["optimal_profiles"]):
            if not a["optimal_is_equilibrium"][k]:
                devs = engine.is_nash(prof, scenario)["deviations"]
                if devs:
                    d = max(devs, key=lambda x: x["gain"])
                    st.markdown(
                        f"* The optimum `{describe_profile(prof, scenario)}` is unstable: **{scenario['students'][d['student']]}** "
                        f"gains {H._fmt(d['gain'])} by moving to *{scenario['projects'][d['to_project']]}*."
                    )
                break

    # ---- C/D. PoS and PoA
    st.markdown("### 3 · Price of stability and price of anarchy")
    defined = a["ratio_status"] == "defined"
    c = st.columns(2)
    _ratio_metric(c[0], "Price of stability  W(s*) / max_NE W", a["price_of_stability"], defined,
                  "How much welfare is lost, at best, by insisting on stability. 1.0 means some optimum is stable.")
    _ratio_metric(c[1], "Price of anarchy  W(s*) / min_NE W", a["price_of_anarchy"], defined,
                  "How bad the worst stable assignment is relative to the optimum.")
    st.latex(r"\mathrm{PoS}=\frac{W(s^*)}{\max_{s\in NE}W(s)}\qquad \mathrm{PoA}=\frac{W(s^*)}{\min_{s\in NE}W(s)}")
    if defined:
        st.caption(f"Defined because {a['ratio_note']}. Welfare gap between the optimum and the best / worst equilibrium: "
                   f"{H._fmt(a['welfare_gap_best_equilibrium'])} / {H._fmt(a['welfare_gap_worst_equilibrium'])}.")
    else:
        st.warning(
            f"**Ratios undefined for this scenario.** {a['ratio_note'][0].upper()}{a['ratio_note'][1:]} "
            f"Absolute welfare gaps (optimum − best equilibrium = {H._fmt(a['welfare_gap_best_equilibrium'])}, "
            f"optimum − worst equilibrium = {H._fmt(a['welfare_gap_worst_equilibrium'])}) remain meaningful.",
            icon="➗",
        )

    # ---- E. Pareto
    st.markdown("### 4 · Pareto analysis of the equilibria")
    c = st.columns(3)
    c[0].metric("Pareto-optimal equilibria", a["n_pareto_optimal_equilibria"])
    c[1].metric("Pareto-dominated equilibria", a["n_pareto_dominated_equilibria"])
    c[2].metric("Equilibria in total", a["n_equilibria"])
    st.markdown(
        "**Nash stability is not Pareto efficiency.** An equilibrium is *Pareto-dominated* if some assignment (stable or "
        "not) makes **every** student at least as well off and at least one strictly better off -- yet students cannot "
        "reach it by deviating one at a time. Here Pareto-optimality is checked against **all** assignments."
    )
    dominated = [e for e in a["equilibria"] if not e["pareto_optimal"]]
    if dominated:
        drows = []
        for e in dominated:
            better = sum(1 for x, y in zip(e["dominated_by_utilities"], e["utilities"]) if x > y + H.EPS)
            drows.append({"Dominated equilibrium": describe_profile(e["profile"], scenario), "Welfare": e["welfare"],
                          "A dominating assignment": describe_profile(e["dominated_by"], scenario),
                          "Its welfare": sum(e["dominated_by_utilities"]), "Students strictly better off": better})
        st.dataframe(pd.DataFrame(drows), width="stretch", hide_index=True)
    else:
        st.caption("No equilibrium is Pareto-dominated in this scenario.")

    # ---- F. visual analytics
    st.markdown("### 5 · Visual analytics")
    cur = {"welfare": cur_w, "potential": cur_phi}
    a_plot = dict(a, optimum_potential=engine.potential(opt["profile"], scenario))
    st.plotly_chart(welfare_potential_chart(a_plot, cur), width="stretch")
    st.caption(
        "Every dot is a distinct (welfare, potential) pair; hover shows how many assignments share it. The potential "
        "Φ is not welfare: a unilateral move changes Φ by exactly the mover's gain, so equilibria are the local "
        "maxima of Φ under single-student moves, not the welfare maxima."
    )
    with st.expander("All assignments vs equilibria by welfare (log scale)"):
        st.plotly_chart(all_vs_equilibria_chart(a), width="stretch")
    st.caption("The change of Φ and W *during* best-response dynamics is plotted in the Simulation tab.")

    # ---- equilibria table
    st.markdown("### 6 · Every pure Nash equilibrium")
    table = [{"#": k + 1, "Teams": describe_profile(e["profile"], scenario), "Welfare": e["welfare"],
              "Potential": e["potential"], "Pareto-optimal": "yes" if e["pareto_optimal"] else "no"}
             for k, e in enumerate(a["equilibria"])]
    st.dataframe(pd.DataFrame(table), width="stretch", hide_index=True)
    options = {f"Equilibrium #{k + 1} (welfare {H._fmt(e['welfare'])})": e["profile"] for k, e in enumerate(a["equilibria"])}
    options["Welfare optimum"] = opt["profile"]
    label = st.selectbox("Load an assignment into the Assignment tab", list(options), key="analysis_load_choice")
    if st.button("Load into Assignment tab", key="analysis_load_button"):
        set_profile(list(options[label]))
        st.rerun()

    with st.expander("Scalability and method"):
        st.markdown(
            f"Enumeration evaluates all {m}^{n} = {total:,} assignments (cap {cap:,}); each costs O(n²·m), so the work "
            "grows exponentially with the number of students. Results are cached per scenario. Equilibrium search, "
            "optimum, ratios and the Pareto check all come from a single pass, so the figures agree with each other and "
            "with `python game_engine.py --report`."
        )
