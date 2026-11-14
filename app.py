"""
STRATOS -- Strategic Behavior in University Course / Project Team Formation.

Streamlit entry point: sidebar (scenario, dynamics settings), session state, and the tabs. Tab content lives in
`app_views.py` (Scenario, Assignment, Equilibrium, Simulation, Guide) and `app_analysis.py` (Analysis); chart and table
builders, engine loading and the clearly-labelled mock fallback live in `app_helpers.py`.

All game logic comes from `game_engine.py` / `sample_data.py` (set STRATOS_REQUIRE_REAL_ENGINE=1 to make any fallback a hard
failure). All student data is synthetic.
"""
import hashlib
import json
from types import SimpleNamespace

import streamlit as st

import app_analysis
import app_helpers as helpers
import app_views as views

st.set_page_config(page_title="STRATOS — Team Formation Game Theory", page_icon="\U0001f3b2", layout="wide")
helpers.apply_custom_styles()

bundle = helpers.load_engine_bundle()
engine = bundle.engine
sample_data = bundle.sample_data

try:  # scenario import/export needs the real engine's validators
    import scenario_io
except Exception:  # pragma: no cover - only when the engine is missing or broken
    scenario_io = None

PRESET_TINY = "Tiny hand-verified example"
PRESET_DEFAULT = "Default scenario"
PRESET_CUSTOM = "Custom synthetic scenario"
PRESET_IMPORT = "Imported JSON scenario"
MAX_STUDENTS, MAX_PROJECTS = 12, 5


def set_profile(new_profile: list) -> None:
    """Overwrite the assignment programmatically (Reset / Random / load / apply). Bumps profile_version so the per-student
    selectboxes (keyed on it) pick up the new values, and drops any simulation result tied to the old assignment."""
    st.session_state.profile = list(new_profile)
    st.session_state.profile_version = st.session_state.get("profile_version", 0) + 1
    st.session_state.pop("last_dynamics_result", None)
    st.session_state.pop("last_dynamics_meta", None)


def build_scenario(preset: str):
    """Return (scenario, label, kind, synthetic_note, error). Never returns an invalid scenario."""
    note = None
    if preset == PRESET_TINY:
        sc, label, kind = sample_data.get_tiny_scenario(), "Tiny hand-verified example (2 students, 2 projects)", "tiny"
    elif preset == PRESET_DEFAULT:
        sc, label, kind = sample_data.get_default_scenario(), "Default scenario (8 students, 3 projects)", "default"
    elif preset == PRESET_IMPORT:
        up = st.session_state.get("import_file")
        if up is None or scenario_io is None:
            return sample_data.get_tiny_scenario(), "Tiny example (no file imported yet)", "tiny", None, \
                "Upload a STRATOS scenario JSON file in the sidebar; showing the tiny example meanwhile."
        try:
            sc = scenario_io.scenario_from_json(up.getvalue(), MAX_STUDENTS, MAX_PROJECTS)
        except engine.StratosError as exc:
            return sample_data.get_tiny_scenario(), "Tiny example (import rejected)", "tiny", None, f"Import rejected: {exc}"
        label, kind = f"Imported scenario “{up.name}”", "imported"
        note = "Imported from a JSON file you supplied: synthetic experimental data, never real student records."
    else:
        sc = helpers.generate_custom_mock_scenario(
            num_students=st.session_state.custom_num_students, num_projects=st.session_state.custom_num_projects,
            gamma=st.session_state.custom_gamma, seed=st.session_state.custom_seed)
        label, kind = "Custom synthetic scenario", "custom"
        note = ("Randomly generated for experimentation from the seed in the sidebar: **not real student data** and not "
                "the default demonstration dataset.")
    if kind != "custom" and st.session_state.get("gamma_override_on"):
        sc = dict(sc, gamma=st.session_state.gamma_override)
        label += f", γ overridden to {sc['gamma']:g}"
        note = (note + " " if note else "") + "The crowding parameter γ was overridden from the preset value."
    elif kind in ("tiny", "default"):
        note = None
    try:
        engine.validate_scenario(sc)
    except engine.StratosError as exc:
        return sample_data.get_tiny_scenario(), "Tiny example (invalid scenario rejected)", "tiny", None, f"Invalid scenario: {exc}"
    return sc, label, kind, note, None


# ------------------------------------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Scenario")
    preset_options = [PRESET_TINY, PRESET_CUSTOM, PRESET_IMPORT]
    if not bundle.using_mock:
        preset_options.insert(1, PRESET_DEFAULT)
    preset = st.selectbox("Scenario preset", preset_options, key="scenario_preset")

    if preset == PRESET_CUSTOM:
        st.caption("Random synthetic scenario for experimentation (not real student data).")
        st.slider("Number of students", 4, MAX_STUDENTS, value=8, key="custom_num_students")
        st.slider("Number of projects", 2, MAX_PROJECTS, value=3, key="custom_num_projects")
        st.slider("Crowding parameter (gamma)", 0.0, 5.0, value=1.0, step=0.5, key="custom_gamma")
        st.number_input("Random seed", min_value=0, max_value=9999, value=42, key="custom_seed")
    elif preset == PRESET_IMPORT:
        st.file_uploader("Scenario JSON", type=["json"], key="import_file",
                         help="A file exported from this app, or one following the format in docs/INTERFACE.md.")
    if preset != PRESET_CUSTOM:
        if st.checkbox("Override the crowding parameter γ (experiment)", key="gamma_override_on"):
            st.slider("γ", 0.0, 5.0, value=2.0, step=0.5, key="gamma_override")

    regenerate_clicked = st.button("\U0001f504 Regenerate scenario", width="stretch",
                                   help="Rebuild the scenario from the settings above and reset the assignment.")

    # Rebuild whenever anything that defines the scenario changes -- never serve a stale scenario.
    up = st.session_state.get("import_file")
    signature = json.dumps({
        "preset": preset,
        "gamma": [st.session_state.get("gamma_override_on"), st.session_state.get("gamma_override")] if preset != PRESET_CUSTOM else None,
        "custom": [st.session_state.get(k) for k in ("custom_num_students", "custom_num_projects", "custom_gamma", "custom_seed")] if preset == PRESET_CUSTOM else None,
        "file": hashlib.sha256(up.getvalue()).hexdigest() if (preset == PRESET_IMPORT and up is not None) else None,
    }, sort_keys=True)
    if regenerate_clicked or "scenario" not in st.session_state or st.session_state.get("scenario_signature") != signature:
        sc_new, label_new, kind_new, note_new, err_new = build_scenario(preset)
        st.session_state.scenario = sc_new
        st.session_state.scenario_label = label_new
        st.session_state.scenario_kind = kind_new
        st.session_state.synthetic_note = note_new
        st.session_state.scenario_error = err_new
        st.session_state.scenario_signature = signature
        st.session_state.active_preset = preset
        st.session_state.scenario_version = st.session_state.get("scenario_version", 0) + 1
        set_profile([0] * len(sc_new["students"]))

    if st.session_state.get("scenario_error"):
        st.error(st.session_state.scenario_error)
    if scenario_io is not None:
        try:
            st.download_button("⬇ Export scenario (JSON)", data=scenario_io.scenario_to_json(st.session_state.scenario),
                               file_name="stratos_scenario.json", mime="application/json", width="stretch")
        except engine.StratosError as exc:  # pragma: no cover - the active scenario is validated on build
            st.error(f"Cannot export: {exc}")

    st.divider()
    st.caption("Best-response dynamics (used in the Simulation tab)")
    order_choice = st.radio("Student order each sweep", ["round_robin", "random"], key="order_choice")
    dynamics_seed = st.number_input("Dynamics seed", min_value=0, max_value=9999, value=7, key="dynamics_seed",
                                    help="Only affects the random order; round_robin is deterministic.")
    max_rounds = st.slider("Max sweeps", 5, 200, value=50, key="max_rounds")

scenario = st.session_state.scenario
ctx = SimpleNamespace(
    bundle=bundle, engine=engine, scenario=scenario, n=len(scenario["students"]), m=len(scenario["projects"]),
    scenario_label=st.session_state.scenario_label, scenario_kind=st.session_state.scenario_kind,
    synthetic_note=st.session_state.synthetic_note, order=order_choice, dynamics_seed=dynamics_seed,
    max_rounds=max_rounds, set_profile=set_profile,
)

helpers.render_app_header(bundle, active_label=st.session_state.scenario_label)

tabs = st.tabs(["\U0001f4cb Scenario", "\U0001f91d Assignment", "⚖️ Equilibrium", "\U0001f500 Simulation",
                "\U0001f4ca Analysis", "\U0001f4d6 Guide"])
with tabs[0]:
    views.render_scenario_tab(ctx)
with tabs[1]:
    views.render_assignment_tab(ctx)
with tabs[2]:
    views.render_equilibrium_tab(ctx)
with tabs[3]:
    views.render_simulation_tab(ctx)
with tabs[4]:
    app_analysis.render_analysis_tab(bundle, engine, scenario, st.session_state.profile, set_profile)
with tabs[5]:
    views.render_guide_tab(ctx)

st.divider()
st.caption(
    "STRATOS — Streamlit front end. "
    + ("Using the real game_engine / sample_data." if not bundle.using_mock
       else "RUNNING ON A MOCK that mirrors the interface contract; these results are not from the verified engine.")
    + " All data is synthetic."
)
