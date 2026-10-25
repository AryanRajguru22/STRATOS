"""
Reusable frontend helpers for the STRATOS Streamlit app.

Owned by: Harsh (frontend / Streamlit UI only).

This module never implements its OWN game-theoretic model. Aryan owns
`game_engine.py` and `sample_data.py`, and the team's frozen interface
contract (`docs/TEAM_WORK_ALLOCATION.md`, Section 8, INTERFACE_VERSION
"1.0") specifies their exact function names, signatures, and the
utility/potential formulas (Section 4.1-4.3).

`load_engine_bundle()` imports the real modules when present. When they
are not (e.g. local frontend development before integration), it falls
back to `_MockEngine` / `_MockSampleData` below, which mirror that same
documented contract and formulas exactly -- verified against the team's
own hand-checked tiny example in Section 8.4 -- so the UI code is written
once against the contract and needs no changes when the real engine
lands. The mock is still a mock: it is not Aryan's actual implementation,
carries no test coverage of its own, and every figure derived from it is
visibly labelled as such in the UI.
"""

from __future__ import annotations

import importlib.util
import random
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Brand / palette constants (validated categorical + sequential + diverging
# palette; see dataviz skill reference palette for provenance).
# ---------------------------------------------------------------------------

APP_TITLE = "STRATOS"
APP_SUBTITLE = "Strategic Behavior in University Course / Project Team Formation"

CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SEQUENTIAL_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING_BLUE_RED = ["#184f95", "#86b6ef", "#f0efec", "#ec835a", "#e34948"]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

GRID_LINE = "#e1e0d9"

# Skill taxonomy exactly as documented in TEAM_WORK_ALLOCATION.md Section 4
# ("Each student has a skill set S_i from {Programming, Analysis, Design,
# Communication}"). Used only to label mock students for display.
SKILL_OPTIONS = ["Programming", "Analysis", "Design", "Communication"]

EPS = 1e-9


# ---------------------------------------------------------------------------
# Engine bundle: real modules when importable, contract-mirroring mock
# otherwise. The app must run standalone either way.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EngineBundle:
    engine: object
    sample_data: object
    using_mock: bool
    missing: list = field(default_factory=list)


def load_engine_bundle() -> EngineBundle:
    """Use the real game_engine/sample_data when both import cleanly;
    otherwise fall back to the contract-mirroring mock below. Never
    guesses at behaviour beyond the documented contract."""
    game_engine_spec = importlib.util.find_spec("game_engine")
    sample_data_spec = importlib.util.find_spec("sample_data")

    if game_engine_spec is not None and sample_data_spec is not None:
        try:
            import game_engine  # type: ignore
            import sample_data  # type: ignore

            return EngineBundle(engine=game_engine, sample_data=sample_data, using_mock=False, missing=[])
        except Exception:
            pass  # fall through to mock on any import-time failure

    missing = []
    if game_engine_spec is None:
        missing.append("game_engine.py")
    if sample_data_spec is None:
        missing.append("sample_data.py")
    return EngineBundle(engine=_MockEngine, sample_data=_MockSampleData, using_mock=True, missing=missing)


# ---------------------------------------------------------------------------
# Mock engine: mirrors the frozen contract (Section 4.1-4.5, 8.3) exactly.
# ---------------------------------------------------------------------------

class _MockEngine:
    """Contract-mirroring mock. NOT Aryan's implementation -- swapped out
    automatically by load_engine_bundle() once game_engine.py exists."""

    INTERFACE_VERSION = "1.0-mock"

    class StratosError(ValueError):
        pass

    class ScenarioError(StratosError):
        pass

    class ProfileError(StratosError):
        pass

    @staticmethod
    def validate_scenario(scenario: dict) -> None:
        E = _MockEngine.ScenarioError
        required = {"students", "projects", "pref", "w", "gamma"}
        missing = required - scenario.keys()
        if missing:
            raise E(f"scenario missing required key(s): {sorted(missing)}")

        students, projects = scenario["students"], scenario["projects"]
        pref, w, gamma = scenario["pref"], scenario["w"], scenario["gamma"]
        n, m = len(students), len(projects)

        if n < 1:
            raise E("scenario.students must have at least 1 student")
        if m < 2:
            raise E("scenario.projects must have at least 2 projects")
        if any(not s for s in students) or len(set(students)) != n:
            raise E("scenario.students must be non-empty and unique")
        if any(not p for p in projects) or len(set(projects)) != m:
            raise E("scenario.projects must be non-empty and unique")
        if isinstance(gamma, bool) or not isinstance(gamma, (int, float)) or gamma < 0:
            raise E("scenario.gamma must be a non-negative number")
        if len(pref) != n or any(len(row) != m for row in pref):
            raise E("scenario.pref must be an n x m matrix")
        for row in pref:
            for v in row:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    raise E("scenario.pref values must be numeric")
        if len(w) != n or any(len(row) != n for row in w):
            raise E("scenario.w must be an n x n matrix")
        for i in range(n):
            if w[i][i] != 0:
                raise E(f"scenario.w diagonal must be zero (row {i})")
            for j in range(n):
                if isinstance(w[i][j], bool) or not isinstance(w[i][j], (int, float)):
                    raise E("scenario.w values must be numeric")
                if abs(w[i][j] - w[j][i]) > EPS:
                    raise E(f"scenario.w must be symmetric (entries {i},{j} and {j},{i} differ)")

    @staticmethod
    def validate_profile(profile: list, scenario: dict) -> None:
        E = _MockEngine.ProfileError
        n, m = len(scenario["students"]), len(scenario["projects"])
        if len(profile) != n:
            raise E(f"profile must have length {n}, got {len(profile)}")
        for idx, t in enumerate(profile):
            if isinstance(t, bool) or not isinstance(t, int):
                raise E(f"profile[{idx}] must be an int")
            if not (0 <= t < m):
                raise E(f"profile[{idx}]={t} out of range 0..{m - 1}")

    @staticmethod
    def crowding_cost(k: int, scenario: dict):
        return scenario["gamma"] * (k - 1) ** 2

    @staticmethod
    def teams(profile: list, scenario: dict) -> list:
        m = len(scenario["projects"])
        result: list = [[] for _ in range(m)]
        for i, t in enumerate(profile):
            result[t].append(i)
        return result

    @staticmethod
    def utility(i: int, profile: list, scenario: dict):
        pref, w = scenario["pref"], scenario["w"]
        t = profile[i]
        team_size = sum(1 for tj in profile if tj == t)
        compat = sum(w[i][j] for j, tj in enumerate(profile) if tj == t and j != i)
        return pref[i][t] + compat - _MockEngine.crowding_cost(team_size, scenario)

    @staticmethod
    def utilities(profile: list, scenario: dict) -> list:
        return [_MockEngine.utility(i, profile, scenario) for i in range(len(profile))]

    @staticmethod
    def social_welfare(profile: list, scenario: dict):
        return sum(_MockEngine.utilities(profile, scenario))

    @staticmethod
    def potential(profile: list, scenario: dict):
        pref, w = scenario["pref"], scenario["w"]
        n = len(profile)
        pref_term = sum(pref[i][profile[i]] for i in range(n))
        pair_term = sum(w[i][j] for i in range(n) for j in range(i + 1, n) if profile[i] == profile[j])
        crowd_term = sum(
            sum(_MockEngine.crowding_cost(k, scenario) for k in range(1, len(team) + 1))
            for team in _MockEngine.teams(profile, scenario)
        )
        return pref_term + pair_term - crowd_term

    @staticmethod
    def best_response(i: int, profile: list, scenario: dict) -> dict:
        m = len(scenario["projects"])
        current = profile[i]
        current_u = _MockEngine.utility(i, profile, scenario)
        options = []
        best_t, best_u = current, current_u
        for t in range(m):
            trial = list(profile)
            trial[i] = t
            u = _MockEngine.utility(i, trial, scenario)
            options.append({"project": t, "utility": u})
            if u > best_u + EPS:
                best_u, best_t = u, t
        return {"student": i, "current": current, "best": best_t, "improves": best_t != current, "options": options}

    @staticmethod
    def profitable_deviations(profile: list, scenario: dict) -> list:
        n, m = len(profile), len(scenario["projects"])
        deviations = []
        for i in range(n):
            current_u = _MockEngine.utility(i, profile, scenario)
            for t in range(m):
                if t == profile[i]:
                    continue
                trial = list(profile)
                trial[i] = t
                new_u = _MockEngine.utility(i, trial, scenario)
                gain = new_u - current_u
                if gain > EPS:
                    deviations.append(
                        {
                            "student": i,
                            "from_project": profile[i],
                            "to_project": t,
                            "current_utility": current_u,
                            "new_utility": new_u,
                            "gain": gain,
                        }
                    )
        deviations.sort(key=lambda d: (d["student"], d["to_project"]))
        return deviations

    @staticmethod
    def is_nash(profile: list, scenario: dict) -> dict:
        _MockEngine.validate_scenario(scenario)
        _MockEngine.validate_profile(profile, scenario)
        deviations = _MockEngine.profitable_deviations(profile, scenario)
        return {
            "is_nash": len(deviations) == 0,
            "utilities": _MockEngine.utilities(profile, scenario),
            "deviations": deviations,
        }

    @staticmethod
    def random_profile(scenario: dict, seed=None) -> list:
        rng = random.Random(seed)
        m = len(scenario["projects"])
        return [rng.randrange(m) for _ in range(len(scenario["students"]))]

    @staticmethod
    def best_response_dynamics(scenario: dict, start: list, order: str = "round_robin", seed=None, max_rounds: int = 100) -> dict:
        _MockEngine.validate_scenario(scenario)
        _MockEngine.validate_profile(start, scenario)
        n = len(start)
        s = list(start)
        steps = []
        converged = False
        rng = random.Random(seed)
        rounds_used = 0

        for round_idx in range(1, max_rounds + 1):
            rounds_used = round_idx
            indices = list(range(n))
            if order == "random":
                rng.shuffle(indices)
            changed = False
            for i in indices:
                current_u = _MockEngine.utility(i, s, scenario)
                br = _MockEngine.best_response(i, s, scenario)
                if br["improves"]:
                    best_u = next(opt["utility"] for opt in br["options"] if opt["project"] == br["best"])
                    steps.append(
                        {
                            "round": round_idx,
                            "student": i,
                            "from_project": s[i],
                            "to_project": br["best"],
                            "gain": best_u - current_u,
                        }
                    )
                    s[i] = br["best"]
                    changed = True
            if not changed:
                converged = True
                break

        is_nash_final = _MockEngine.is_nash(s, scenario)["is_nash"]
        return {
            "converged": converged,
            "rounds": rounds_used,
            "start_profile": list(start),
            "final_profile": s,
            "steps": steps,
            "is_nash_final": is_nash_final,
        }


class _MockSampleData:
    """Contract-mirroring mock for sample_data.py. Reproduces the exact
    hand-verified tiny example from Section 8.4 and provides a randomly
    generated (but fixed-seed, reproducible) stand-in default scenario --
    NOT Aryan's real fictional dataset."""

    @staticmethod
    def get_tiny_scenario() -> dict:
        return {
            "students": ["Student A", "Student B"],
            "projects": ["Project 0", "Project 1"],
            "pref": [[5, 1], [1, 5]],
            "w": [[0, 2], [2, 0]],
            "gamma": 1,
            "skills": {},
        }

    @staticmethod
    def get_default_scenario() -> dict:
        return generate_custom_mock_scenario(num_students=8, num_projects=3, gamma=1, seed=42)


def generate_custom_mock_scenario(num_students: int, num_projects: int, gamma: float, seed: int) -> dict:
    """Frontend-only convenience, not part of the frozen contract: builds
    an adjustable-size mock scenario in the exact contract shape so the UI
    can be exercised at scales other than the fixed tiny/default examples."""
    rng = random.Random(seed)
    name_pool = [
        "Aarav", "Meera", "Rohan", "Isha", "Kabir", "Diya", "Vihaan", "Ananya",
        "Arjun", "Sara", "Ishaan", "Tara", "Aditi", "Dev", "Nisha", "Rahul",
        "Priya", "Karan", "Neha", "Yash",
    ]
    project_pool = [
        "Market Microstructure Sim", "Auction Design Lab", "Matching Markets Tool",
        "Voting Systems Explorer", "Bargaining Bot", "Cooperative Game Visualizer",
        "Mechanism Design Studio", "Network Formation Game",
    ]
    shuffled_names = name_pool[:]
    rng.shuffle(shuffled_names)
    students = [shuffled_names[i % len(shuffled_names)] + (f" {i // len(shuffled_names) + 1}" if i >= len(shuffled_names) else "") for i in range(num_students)]
    projects = [project_pool[i % len(project_pool)] for i in range(num_projects)]

    skills = {name: sorted(rng.sample(SKILL_OPTIONS, k=rng.randint(1, 2))) for name in students}
    pref = [[rng.randint(0, 10) for _ in range(num_projects)] for _ in range(num_students)]

    w = [[0] * num_students for _ in range(num_students)]
    for i in range(num_students):
        for j in range(i + 1, num_students):
            val = rng.randint(-2, 3)
            w[i][j] = val
            w[j][i] = val

    return {"students": students, "projects": projects, "pref": pref, "w": w, "gamma": gamma, "skills": skills}


# ---------------------------------------------------------------------------
# Styling
# ---------------------------------------------------------------------------

def apply_custom_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background-color: #f9f9f7; }
        .stratos-mock-badge {
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 999px;
            background-color: #fab21922;
            color: #8a6400;
            border: 1px solid #fab21955;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            margin-bottom: 0.6rem;
        }
        .stratos-section-note {
            color: #52514e;
            font-size: 0.92rem;
            line-height: 1.5;
        }
        .stratos-header-card {
            padding: 1.1rem 1.4rem;
            border-radius: 12px;
            background: linear-gradient(135deg, #2a78d611, #1baf7a11);
            border: 1px solid #e1e0d9;
            margin-bottom: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mock_badge(text: str = "Mock engine mirror -- not Aryan's verified implementation") -> None:
    st.markdown(f'<span class="stratos-mock-badge">⚠ {text}</span>', unsafe_allow_html=True)


def render_app_header(bundle: EngineBundle) -> None:
    st.markdown('<div class="stratos-header-card">', unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.markdown(f"**{APP_SUBTITLE}**")
    st.markdown(
        '<p class="stratos-section-note">'
        "STRATOS models course project-team formation as a potential game: students "
        "are players who each pick one project, utility combines preference, teammate "
        "compatibility, and a crowding cost, and we check whether an assignment is "
        "<b>stable against unilateral deviations</b> (a pure Nash equilibrium) -- not "
        "whether it is optimal."
        "</p>",
        unsafe_allow_html=True,
    )
    if not bundle.using_mock:
        st.success("Real engine detected: `game_engine.py` and `sample_data.py` loaded.", icon="✅")
        notice = getattr(bundle.sample_data, "SYNTHETIC_DATA_NOTICE", None)
        if notice:
            st.caption(f"ℹ️ {notice}")
    else:
        st.info(
            "Running in **standalone frontend mode** -- "
            + " and ".join(f"`{m}`" for m in bundle.missing)
            + " not found yet. All figures below use a local mock that mirrors the frozen "
            "interface contract in `docs/TEAM_WORK_ALLOCATION.md` (Section 8), verified against "
            "its hand-checked example -- it is still a mock, not Aryan's real engine.",
            icon="ℹ️",
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# DataFrame builders for display
# ---------------------------------------------------------------------------

def students_df(scenario: dict) -> pd.DataFrame:
    skills = scenario.get("skills") or {}
    return pd.DataFrame(
        {
            "Student": scenario["students"],
            "Skills": [", ".join(skills.get(name, [])) or "—" for name in scenario["students"]],
        }
    )


def projects_df(scenario: dict) -> pd.DataFrame:
    return pd.DataFrame({"Project": scenario["projects"]})


def preference_df(scenario: dict) -> pd.DataFrame:
    return pd.DataFrame(scenario["pref"], index=scenario["students"], columns=scenario["projects"])


def compatibility_df(scenario: dict) -> pd.DataFrame:
    return pd.DataFrame(scenario["w"], index=scenario["students"], columns=scenario["students"])


def teams_df(teams: list, scenario: dict) -> pd.DataFrame:
    rows = []
    for project_idx, members in enumerate(teams):
        names = [scenario["students"][i] for i in members] or ["(empty)"]
        rows.append({"Project": scenario["projects"][project_idx], "Team size": len(members), "Members": ", ".join(names)})
    return pd.DataFrame(rows)


def utilities_df(profile: list, scenario: dict, utilities: list) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Student": scenario["students"],
            "Assigned project": [scenario["projects"][t] for t in profile],
            "Utility": utilities,
        }
    )


def deviations_df(deviations: list, scenario: dict) -> pd.DataFrame:
    if not deviations:
        return pd.DataFrame(columns=["Student", "From", "To", "Current utility", "New utility", "Gain"])
    return pd.DataFrame(
        [
            {
                "Student": scenario["students"][d["student"]],
                "From": scenario["projects"][d["from_project"]],
                "To": scenario["projects"][d["to_project"]],
                "Current utility": d["current_utility"],
                "New utility": d["new_utility"],
                "Gain": d["gain"],
            }
            for d in deviations
        ]
    )


def dynamics_steps_df(steps: list, scenario: dict) -> pd.DataFrame:
    if not steps:
        return pd.DataFrame(columns=["Round", "Student", "From", "To", "Gain"])
    return pd.DataFrame(
        [
            {
                "Round": s["round"],
                "Student": scenario["students"][s["student"]],
                "From": scenario["projects"][s["from_project"]],
                "To": scenario["projects"][s["to_project"]],
                "Gain": s["gain"],
            }
            for s in steps
        ]
    )


def profile_at_step(start: list, steps: list, k: int) -> list:
    """Reconstructs the profile after applying the first k recorded
    best_response_dynamics steps to the start profile."""
    s = list(start)
    for step in steps[:k]:
        s[step["student"]] = step["to_project"]
    return s


def replay_welfare_potential_trace(engine, scenario: dict, start: list, steps: list) -> pd.DataFrame:
    """Replays best_response_dynamics' recorded steps to chart welfare and
    potential at every intermediate profile, including the start state."""
    s = list(start)
    rows = [{"step": 0, "welfare": engine.social_welfare(s, scenario), "potential": engine.potential(s, scenario)}]
    for idx, step in enumerate(steps, start=1):
        s = list(s)
        s[step["student"]] = step["to_project"]
        rows.append({"step": idx, "welfare": engine.social_welfare(s, scenario), "potential": engine.potential(s, scenario)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Plotly chart builders (consistent palette, single axis, legend present)
# ---------------------------------------------------------------------------

def _base_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color="#0b0b0b", family="system-ui, -apple-system, 'Segoe UI', sans-serif"),
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE)
    fig.update_yaxes(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE)
    return fig


def preference_heatmap(scenario: dict) -> go.Figure:
    df = preference_df(scenario)
    fig = px.imshow(
        df.values,
        x=list(df.columns),
        y=list(df.index),
        color_continuous_scale=SEQUENTIAL_BLUE,
        labels=dict(color="Preference (0-10)"),
        aspect="auto",
    )
    return _base_layout(fig, "Student → Project preferences (higher = more preferred)")


def compatibility_heatmap(scenario: dict) -> go.Figure:
    df = compatibility_df(scenario)
    bound = max(1.0, float(df.values.max()), float(-df.values.min()))
    fig = px.imshow(
        df.values,
        x=list(df.columns),
        y=list(df.index),
        color_continuous_scale=DIVERGING_BLUE_RED,
        range_color=[-bound, bound],
        labels=dict(color="Compatibility w[i][j]"),
        aspect="auto",
    )
    return _base_layout(fig, "Teammate compatibility matrix (red = friction, blue = synergy)")


def utility_bar_chart(profile: list, scenario: dict, utilities: list) -> go.Figure:
    df = utilities_df(profile, scenario, utilities)
    fig = px.bar(df, x="Student", y="Utility", color_discrete_sequence=[CATEGORICAL[0]])
    fig.update_traces(marker_color=CATEGORICAL[0])
    return _base_layout(fig, "Utility per student under the current assignment")


def dynamics_trace_chart(trace_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trace_df["step"], y=trace_df["welfare"], name="Social welfare", mode="lines+markers", line=dict(color=CATEGORICAL[0], width=2)))
    fig.add_trace(go.Scatter(x=trace_df["step"], y=trace_df["potential"], name="Potential (Φ)", mode="lines+markers", line=dict(color=CATEGORICAL[2], width=2)))
    fig.update_xaxes(title="Step (0 = start)")
    fig.update_yaxes(title="Value")
    return _base_layout(fig, "Welfare and potential along best-response dynamics")
