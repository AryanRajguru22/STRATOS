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

import html
import importlib.util
import os
import random
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Brand / palette constants (validated categorical + sequential + diverging
# palette; see dataviz skill reference palette for provenance).
# ---------------------------------------------------------------------------

APP_TITLE = "STRATOS"
APP_SUBTITLE = "Strategic Behavior in University Course / Project Team Formation"

# Dark navy design system (keep in sync with .streamlit/config.toml)
BG = "#0b1220"
PANEL = "#111a2e"
PANEL2 = "#1b2740"
BORDER = "#2a3957"
TEXT = "#e8eef9"
MUTED = "#9fb0cc"
ACCENT = "#38bdf8"

# One colour per project (categorical); validated for contrast on PANEL
CATEGORICAL = [
    "#38bdf8",  # cyan
    "#fbbf24",  # amber
    "#a78bfa",  # violet
    "#34d399",  # green
    "#f472b6",  # pink
    "#fb923c",  # orange
    "#60a5fa",  # blue
    "#f87171",  # red
]

SEQUENTIAL_BLUE = [[0.0, "#16243f"], [0.25, "#1d4a7a"], [0.5, "#2b78b5"], [0.75, "#38a8de"], [1.0, "#8fdcff"]]
DIVERGING_BLUE_RED = [[0.0, "#f87171"], [0.5, "#1b2740"], [1.0, "#38bdf8"]]

STATUS = {
    "good": "#34d399",
    "warning": "#fbbf24",
    "serious": "#fb923c",
    "critical": "#f87171",
}

GRID_LINE = "#26334f"

# Skill taxonomy exactly as documented in TEAM_WORK_ALLOCATION.md Section 4
# ("Each student has a skill set S_i from {Programming, Analysis, Design,
# Communication}"). Used only to label mock students for display.
SKILL_OPTIONS = ["Programming", "Analysis", "Design", "Communication"]

EPS = 1e-9


# ---------------------------------------------------------------------------
# Engine bundle: real modules when importable, contract-mirroring mock
# otherwise. The app must run standalone either way -- but "absent" and
# "present but broken" must never be conflated, and a broken real engine
# must never be swallowed silently (see REQUIRE_REAL_ENGINE_ENV below).
# ---------------------------------------------------------------------------

REQUIRE_REAL_ENGINE_ENV = "STRATOS_REQUIRE_REAL_ENGINE"


class EngineUnavailableError(RuntimeError):
    """Raised by load_engine_bundle() when STRATOS_REQUIRE_REAL_ENGINE is
    set and the real engine cannot be loaded, whether absent or broken."""


@dataclass(frozen=True)
class EngineBundle:
    engine: object
    sample_data: object
    using_mock: bool
    missing: list = field(default_factory=list)
    import_error: Optional[BaseException] = None
    """Set only when game_engine/sample_data were FOUND but raised during
    import -- as opposed to `missing`, which means they were not found at
    all. Keeping these separate is what lets the UI tell a genuine absence
    apart from a real bug in an existing file."""


def _require_real_engine() -> bool:
    return os.environ.get(REQUIRE_REAL_ENGINE_ENV, "").strip().lower() in ("1", "true", "yes")


def load_engine_bundle() -> EngineBundle:
    """Load the real game_engine/sample_data when they import cleanly;
    otherwise fall back to the contract-mirroring mock below. Never
    guesses at behaviour beyond the documented contract, and never
    mislabels a broken-but-present engine as merely "not found yet".

    Set STRATOS_REQUIRE_REAL_ENGINE=1 (or "true"/"yes") to turn ANY
    fallback -- absent or broken -- into a loud EngineUnavailableError
    instead of a silent mock. Default (unset): mock fallback is allowed,
    but a broken import is always reported distinctly from an absent one.
    """
    require_real = _require_real_engine()
    game_engine_spec = importlib.util.find_spec("game_engine")
    sample_data_spec = importlib.util.find_spec("sample_data")

    if game_engine_spec is not None and sample_data_spec is not None:
        try:
            import game_engine  # type: ignore
            import sample_data  # type: ignore

            return EngineBundle(engine=game_engine, sample_data=sample_data, using_mock=False, missing=[])
        except Exception as exc:
            if require_real:
                raise EngineUnavailableError(
                    f"{REQUIRE_REAL_ENGINE_ENV} is set, but game_engine/sample_data were found and "
                    f"failed to import: {exc!r}"
                ) from exc
            return EngineBundle(
                engine=_MockEngine,
                sample_data=_MockSampleData,
                using_mock=True,
                missing=[],
                import_error=exc,
            )

    missing = []
    if game_engine_spec is None:
        missing.append("game_engine.py")
    if sample_data_spec is None:
        missing.append("sample_data.py")

    if require_real:
        raise EngineUnavailableError(
            f"{REQUIRE_REAL_ENGINE_ENV} is set, but required module(s) were not found: {', '.join(missing)}"
        )

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
    def utility_breakdown(i: int, profile: list, scenario: dict) -> dict:
        t = profile[i]
        mates = [j for j, tj in enumerate(profile) if tj == t and j != i]
        compat = sum(scenario["w"][i][j] for j in mates)
        crowd = _MockEngine.crowding_cost(len(mates) + 1, scenario)
        return {"student": i, "project": t, "team_size": len(mates) + 1, "preference": scenario["pref"][i][t],
                "compatibility": compat, "crowding": crowd, "total": scenario["pref"][i][t] + compat - crowd,
                "teammates": [{"student": j, "weight": scenario["w"][i][j]} for j in mates]}

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
# Styling (dark navy design system; mirrored by .streamlit/config.toml)
# ---------------------------------------------------------------------------

def apply_custom_styles() -> None:
    st.markdown(
        f"""
        <style>
        .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1280px; }}
        h1, h2, h3, h4 {{ letter-spacing: -0.01em; }}
        h3 {{ font-size: 1.25rem !important; }}
        [data-testid="stMetric"] {{
            background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; padding: 0.7rem 0.95rem;
        }}
        [data-testid="stMetricLabel"] p {{ color: {MUTED}; font-size: 0.82rem; }}
        [data-testid="stMetricValue"] {{ font-size: 1.55rem; }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.25rem; border-bottom: 1px solid {BORDER}; }}
        .stTabs [data-baseweb="tab"] {{ padding: 0.55rem 1rem; border-radius: 8px 8px 0 0; }}
        .stratos-hero {{
            background: {PANEL}; border: 1px solid {BORDER}; border-left: 4px solid {ACCENT};
            border-radius: 12px; padding: 1.0rem 1.3rem; margin-bottom: 0.8rem;
        }}
        .stratos-hero h1 {{ margin: 0; padding: 0; font-size: 2.0rem; }}
        .stratos-hero .sub {{ color: {MUTED}; font-size: 0.98rem; margin-top: 0.15rem; }}
        .stratos-pill {{
            display: inline-block; padding: 0.12rem 0.65rem; border-radius: 999px; font-size: 0.76rem;
            font-weight: 600; letter-spacing: 0.02em; margin: 0.35rem 0.4rem 0 0; border: 1px solid {BORDER};
        }}
        .stratos-pill.good {{ color: {STATUS['good']}; background: {STATUS['good']}1f; border-color: {STATUS['good']}66; }}
        .stratos-pill.warn {{ color: {STATUS['warning']}; background: {STATUS['warning']}1f; border-color: {STATUS['warning']}66; }}
        .stratos-pill.info {{ color: {ACCENT}; background: {ACCENT}1a; border-color: {ACCENT}55; }}
        .stratos-mock-badge {{
            display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; background: {STATUS['warning']}22;
            color: {STATUS['warning']}; border: 1px solid {STATUS['warning']}66; font-size: 0.78rem; font-weight: 600;
            margin-bottom: 0.6rem;
        }}
        .stratos-note {{ color: {MUTED}; font-size: 0.92rem; line-height: 1.55; }}
        .stratos-grid {{ display: grid; gap: 0.7rem; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); margin: 0.4rem 0 0.8rem 0; }}
        .stratos-card {{ background: {PANEL}; border: 1px solid {BORDER}; border-top: 3px solid {ACCENT}; border-radius: 10px; padding: 0.7rem 0.9rem; }}
        .stratos-card .t {{ font-weight: 650; font-size: 0.98rem; }}
        .stratos-card .n {{ color: {MUTED}; font-size: 0.8rem; margin: 0.1rem 0 0.4rem 0; }}
        .stratos-chip {{ display: inline-block; background: {PANEL2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 0.05rem 0.5rem; margin: 0.12rem 0.2rem 0.12rem 0; font-size: 0.84rem; }}
        .stratos-empty {{ color: {MUTED}; font-style: italic; font-size: 0.88rem; }}
        .stratos-formula {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 10px; padding: 0.4rem 1rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mock_badge(text: str = "MOCK ENGINE -- not the verified implementation") -> None:
    st.markdown(f'<span class="stratos-mock-badge">⚠ {_esc(text)}</span>', unsafe_allow_html=True)


def _esc(value) -> str:
    return html.escape(str(value), quote=True)


def render_app_header(bundle: EngineBundle, active_label: str = "") -> None:
    pills = []
    if not bundle.using_mock:
        pills.append('<span class="stratos-pill good">● REAL ENGINE</span>')
    else:
        pills.append('<span class="stratos-pill warn">⚠ MOCK ENGINE -- results are NOT from the verified engine</span>')
    pills.append('<span class="stratos-pill info">SYNTHETIC DATA</span>')
    if active_label:
        pills.append(f'<span class="stratos-pill info">{_esc(active_label)}</span>')
    st.markdown(
        '<div class="stratos-hero"><h1>STRATOS</h1>'
        f'<div class="sub">{_esc(APP_SUBTITLE)}</div>{"".join(pills)}</div>',
        unsafe_allow_html=True,
    )
    notice = getattr(bundle.sample_data, "SYNTHETIC_DATA_NOTICE", None) or (
        "All student data and model weights are fictional and synthetic; they are not measurements of real students."
    )
    st.caption(f"ℹ️ {notice} STRATOS is an educational model of unilateral strategic behaviour, not a real allocation tool.")
    if bundle.using_mock and bundle.import_error is not None:
        st.error(
            "**`game_engine.py`/`sample_data.py` were found but failed to import** -- this is almost certainly a bug, "
            f"not an intentional absence. Falling back to the mock so the app can still run. Error: `{bundle.import_error!r}`",
            icon="🛑",
        )
        with st.expander("Full import error"):
            st.exception(bundle.import_error)
    elif bundle.using_mock:
        st.warning(
            "Running in **standalone mock mode** -- " + " and ".join(f"`{m}`" for m in bundle.missing)
            + " not found. Every figure uses a local mock that mirrors the interface contract; it is NOT the verified "
            "engine, and the Analysis tab is disabled.",
            icon="⚠️",
        )


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


def crowding_df(scenario: dict) -> pd.DataFrame:
    """c(k) = gamma * (k-1)^2 for k = 1..n, with the marginal cost c(k) - c(k-1)."""
    gamma = scenario["gamma"]
    n = len(scenario["students"])
    costs = [gamma * (k - 1) ** 2 for k in range(1, n + 1)]
    return pd.DataFrame({"Team size k": list(range(1, n + 1)), "Crowding cost c(k)": costs,
                         "Extra cost of the k-th member": [costs[0]] + [costs[k] - costs[k - 1] for k in range(1, n)]})


def teams_df(teams: list, scenario: dict) -> pd.DataFrame:
    rows = []
    for project_idx, members in enumerate(teams):
        names = [scenario["students"][i] for i in members] or ["(empty)"]
        rows.append({"Project": scenario["projects"][project_idx], "Team size": len(members), "Members": ", ".join(names)})
    return pd.DataFrame(rows)


def team_cards_html(teams: list, scenario: dict) -> str:
    """One card per project: colour, size and member chips. Every name is HTML-escaped (imported names are untrusted)."""
    cards = []
    for t, members in enumerate(teams):
        color = CATEGORICAL[t % len(CATEGORICAL)]
        chips = "".join(f'<span class="stratos-chip">{_esc(scenario["students"][i])}</span>' for i in members) \
            or '<span class="stratos-empty">no students</span>'
        cards.append(
            f'<div class="stratos-card" style="border-top-color:{color}"><div class="t">{_esc(scenario["projects"][t])}</div>'
            f'<div class="n">team size {len(members)}</div>{chips}</div>'
        )
    return f'<div class="stratos-grid">{"".join(cards)}</div>'


def utilities_df(profile: list, scenario: dict, utilities: list) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Student": scenario["students"],
            "Assigned project": [scenario["projects"][t] for t in profile],
            "Utility": utilities,
        }
    )


def breakdown_df(breakdowns: list, scenario: dict, utilities: list) -> pd.DataFrame:
    """Per-student utility split. 'Check' is True when preference + compatibility - crowding equals the engine utility."""
    rows = []
    for b, u in zip(breakdowns, utilities):
        rows.append(
            {
                "Student": scenario["students"][b["student"]],
                "Project": scenario["projects"][b["project"]],
                "Team size": b["team_size"],
                "Preference": b["preference"],
                "Compatibility": b["compatibility"],
                "Crowding (−)": b["crowding"],
                "Utility": u,
                "Sums exactly": abs(b["preference"] + b["compatibility"] - b["crowding"] - u) <= EPS,
            }
        )
    return pd.DataFrame(rows)


def count_students_with_deviations(deviations: list) -> int:
    """Number of distinct students with >=1 profitable deviation.

    NOT the same as len(deviations): the engine's `deviations` list has one
    entry per (student, target_project) pair, so a student with two
    profitable moves (e.g. to two different projects) contributes two
    entries. Counting entries overstates how many students are unhappy.
    """
    return len({d["student"] for d in deviations})


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


def student_deviation_summary_df(profile: list, scenario: dict, utilities: list, deviations: list) -> pd.DataFrame:
    """One row per student: how many profitable destinations they have, and the best one."""
    by_student: dict = {}
    for d in deviations:
        by_student.setdefault(d["student"], []).append(d)
    rows = []
    for i, name in enumerate(scenario["students"]):
        devs = by_student.get(i, [])
        best = max(devs, key=lambda d: (d["gain"], -d["to_project"])) if devs else None
        rows.append(
            {
                "Student": name,
                "Current project": scenario["projects"][profile[i]],
                "Utility now": utilities[i],
                "Profitable destinations": len(devs),
                "Best move": scenario["projects"][best["to_project"]] if best else "— (stays)",
                "Best gain": best["gain"] if best else 0,
                "At a best response": not devs,
            }
        )
    return pd.DataFrame(rows)


def gain_matrix(engine, profile: list, scenario: dict) -> list:
    """gain[i][t] = u_i(t, s_-i) - u_i(s): what student i would gain by moving to project t alone (0 for the current one)."""
    out = []
    for i in range(len(scenario["students"])):
        options = engine.best_response(i, profile, scenario)["options"]
        cur = options[profile[i]]["utility"]
        out.append([o["utility"] - cur for o in options])
    return out


def dynamics_steps_df(steps: list, scenario: dict, start_potential=None) -> pd.DataFrame:
    """Move-by-move table. Welfare/potential columns appear when the steps carry them (the real engine's do);
    'ΔΦ' is the change in potential since the previous step and must equal 'Gain' (exact potential)."""
    if not steps:
        return pd.DataFrame(columns=["Step", "Round", "Student", "From", "To", "Gain"])
    rows = []
    prev_phi = start_potential
    for idx, s in enumerate(steps, start=1):
        row = {
            "Step": idx,
            "Round": s["round"],
            "Student": scenario["students"][s["student"]],
            "From": scenario["projects"][s["from_project"]],
            "To": scenario["projects"][s["to_project"]],
            "Gain": s["gain"],
        }
        if "welfare" in s and "potential" in s:
            row["Welfare after"] = s["welfare"]
            row["Potential after"] = s["potential"]
            if prev_phi is not None:
                row["ΔΦ"] = s["potential"] - prev_phi
            prev_phi = s["potential"]
        rows.append(row)
    return pd.DataFrame(rows)


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
# Plotly chart builders (one dark template for every chart)
# ---------------------------------------------------------------------------

def _base_layout(fig: go.Figure, title: str, height: int | None = None) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, color=TEXT), x=0.0, xanchor="left"),
        plot_bgcolor=PANEL,
        paper_bgcolor=PANEL,
        font=dict(color=TEXT, family="system-ui, -apple-system, 'Segoe UI', sans-serif", size=13),
        margin=dict(l=50, r=24, t=58, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=TEXT)),
        hoverlabel=dict(bgcolor=PANEL2, font=dict(color=TEXT), bordercolor=BORDER),
        colorway=CATEGORICAL,
    )
    if height:
        fig.update_layout(height=height)
    fig.update_xaxes(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE, linecolor=GRID_LINE, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID_LINE, zerolinecolor=GRID_LINE, linecolor=GRID_LINE, tickfont=dict(color=MUTED))
    return fig


def _fmt(v) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


def preference_heatmap(scenario: dict) -> go.Figure:
    df = preference_df(scenario)
    z = df.values.tolist()
    fig = go.Figure(
        go.Heatmap(
            z=z, x=list(df.columns), y=list(df.index), colorscale=SEQUENTIAL_BLUE,
            text=[[_fmt(v) for v in row] for row in z], texttemplate="%{text}",
            hovertemplate="<b>%{y}</b> on <b>%{x}</b><br>preference = %{z}<extra></extra>",
            colorbar=dict(title=dict(text="preference", font=dict(color=TEXT)), tickfont=dict(color=MUTED)),
        )
    )
    fig.update_yaxes(autorange="reversed", title="Student")
    fig.update_xaxes(title="Project", side="top")
    return _base_layout(fig, "Preference p[i][t]: how much student i likes project t (higher = more)",
                        height=130 + 38 * len(z))


def compatibility_heatmap(scenario: dict) -> go.Figure:
    df = compatibility_df(scenario)
    n = len(df)
    z = [[None if i == j else df.values[i][j] for j in range(n)] for i in range(n)]
    flat = [v for row in z for v in row if v is not None]
    bound = max(1.0, max([abs(v) for v in flat], default=1.0))
    fig = go.Figure(
        go.Heatmap(
            z=z, x=list(df.columns), y=list(df.index), colorscale=DIVERGING_BLUE_RED, zmin=-bound, zmax=bound, zmid=0,
            text=[["" if v is None else _fmt(v) for v in row] for row in z], texttemplate="%{text}",
            hovertemplate="<b>%{y}</b> ↔ <b>%{x}</b><br>w = %{z} (same value in both directions; only counts "
                          "when they share a project)<extra></extra>",
            colorbar=dict(title=dict(text="w[i][j]", font=dict(color=TEXT)), tickfont=dict(color=MUTED)),
        )
    )
    fig.update_yaxes(autorange="reversed", title="Student")
    fig.update_xaxes(title="Student", side="top")
    return _base_layout(fig, "Compatibility w[i][j]: benefit (blue) or friction (red) of being on the same team",
                        height=150 + 40 * n)


def utility_bar_chart(profile: list, scenario: dict, utilities: list) -> go.Figure:
    df = utilities_df(profile, scenario, utilities)
    fig = go.Figure(go.Bar(
        x=df["Student"], y=df["Utility"], marker_color=[CATEGORICAL[t % len(CATEGORICAL)] for t in profile],
        customdata=df["Assigned project"], hovertemplate="<b>%{x}</b><br>project: %{customdata}<br>utility: %{y}<extra></extra>",
    ))
    fig.update_xaxes(title="Student")
    fig.update_yaxes(title="Utility u_i(s)")
    return _base_layout(fig, "Utility per student (bar colour = assigned project)")


def breakdown_chart(bdf: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=bdf["Student"], y=bdf["Preference"], name="Preference", marker_color=ACCENT,
                hovertemplate="<b>%{x}</b><br>preference %{y}<extra></extra>")
    fig.add_bar(x=bdf["Student"], y=bdf["Compatibility"], name="Teammate compatibility", marker_color=STATUS["good"],
                hovertemplate="<b>%{x}</b><br>compatibility %{y}<extra></extra>")
    fig.add_bar(x=bdf["Student"], y=-bdf["Crowding (−)"], name="Crowding cost (subtracted)", marker_color=STATUS["warning"],
                hovertemplate="<b>%{x}</b><br>crowding −%{customdata}<extra></extra>", customdata=bdf["Crowding (−)"])
    fig.add_scatter(x=bdf["Student"], y=bdf["Utility"], name="Total utility u_i", mode="markers",
                    marker=dict(color=TEXT, size=10, symbol="diamond", line=dict(color=BG, width=1)),
                    hovertemplate="<b>%{x}</b><br>utility %{y}<extra></extra>")
    fig.update_layout(barmode="relative")
    fig.update_xaxes(title="Student")
    fig.update_yaxes(title="Utility terms")
    return _base_layout(fig, "Where each student's utility comes from")


def deviation_gain_heatmap(gains: list, profile: list, scenario: dict) -> go.Figure:
    """Rows = students, columns = projects, cell = utility change if that student alone moved there.
    Positive = profitable deviation. The student's current project is outlined and always 0."""
    z = [[None if t == profile[i] else v for t, v in enumerate(row)] for i, row in enumerate(gains)]
    flat = [abs(v) for row in z for v in row if v is not None]
    bound = max(1.0, max(flat, default=1.0))
    text = [["current" if t == profile[i] else (f"+{_fmt(v)}" if v > EPS else _fmt(v)) for t, v in enumerate(row)]
            for i, row in enumerate(gains)]
    fig = go.Figure(go.Heatmap(
        z=z, x=scenario["projects"], y=scenario["students"], text=text, texttemplate="%{text}", zmin=-bound, zmax=bound,
        zmid=0, colorscale=[[0, STATUS["critical"]], [0.5, PANEL2], [1, STATUS["good"]]],
        hovertemplate="<b>%{y}</b> alone moves to <b>%{x}</b><br>utility change = %{z}<extra></extra>",
        colorbar=dict(title=dict(text="gain", font=dict(color=TEXT)), tickfont=dict(color=MUTED)),
    ))
    fig.update_yaxes(autorange="reversed", title="Student")
    fig.update_xaxes(title="Destination project", side="top")
    return _base_layout(fig, "What each student would gain by moving alone (green = profitable)", height=140 + 38 * len(gains))


def dynamics_trace_chart(trace_df: pd.DataFrame, highlight_step: int | None = None) -> go.Figure:
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                        subplot_titles=("Social welfare W(s) (can go down!)", "Potential Φ(s) (strictly increases with every move)"))
    fig.add_trace(go.Scatter(x=trace_df["step"], y=trace_df["welfare"], name="Social welfare", mode="lines+markers",
                             line=dict(color=CATEGORICAL[0], width=2), hovertemplate="step %{x}<br>W = %{y}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=trace_df["step"], y=trace_df["potential"], name="Potential (Φ)", mode="lines+markers",
                             line=dict(color=CATEGORICAL[2], width=2), hovertemplate="step %{x}<br>Φ = %{y}<extra></extra>"), row=2, col=1)
    if highlight_step is not None and highlight_step in set(trace_df["step"]):
        row = trace_df[trace_df["step"] == highlight_step].iloc[0]
        for r, col in ((1, "welfare"), (2, "potential")):
            fig.add_trace(go.Scatter(x=[highlight_step], y=[row[col]], mode="markers", showlegend=False, hoverinfo="skip",
                                     marker=dict(size=14, color="rgba(0,0,0,0)", line=dict(color=TEXT, width=2))), row=r, col=1)
    fig.update_xaxes(title="Move number (0 = start)", dtick=1 if len(trace_df) <= 20 else None, row=2, col=1)
    fig.update_annotations(font=dict(color=MUTED, size=12))
    fig.update_layout(showlegend=False)
    return _base_layout(fig, "Welfare and potential along best-response dynamics", height=430)
