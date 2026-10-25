"""
Smoke tests for the STRATOS frontend.

Owned by: Harsh (frontend only).

These tests check that the Streamlit app boots and that the frontend
helpers produce well-shaped data, independent of whether Aryan's
game_engine.py / sample_data.py exist yet (S-01..S-04 from the team's
test plan). They also cross-check the mock engine's utility/potential/
is_nash/best_response_dynamics formulas directly against the team's own
hand-verified tiny example (TEAM_WORK_ALLOCATION.md, Section 8.4), so a
future swap to the real engine has a known-correct baseline to compare
against. None of this asserts anything about Aryan's real engine.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app_helpers as helpers  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


# ---------------------------------------------------------------------------
# S-01..S-04: app-level smoke tests via Streamlit AppTest
# ---------------------------------------------------------------------------

def test_s01_app_starts_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception


def test_s01_app_renders_four_tabs():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert len(at.tabs) == 4


def test_s02_default_run_has_no_exception():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception
    assert len(at.error) == 0


def test_s03_simulation_runs_without_exception():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    run_buttons = [b for b in at.button if "Run dynamics" in (b.label or "")]
    assert run_buttons, "expected a 'Run dynamics' button in the Simulation tab"
    run_buttons[0].click().run(timeout=30)
    assert not at.exception


# ---------------------------------------------------------------------------
# Engine bundle / graceful fallback
# ---------------------------------------------------------------------------

def test_engine_bundle_reports_mock_when_modules_absent():
    bundle = helpers.load_engine_bundle()
    assert isinstance(bundle.using_mock, bool)
    if bundle.using_mock:
        assert set(bundle.missing) & {"game_engine.py", "sample_data.py"}


def test_s04_invalid_profile_raises_stratos_error_not_a_crash():
    bundle = helpers.load_engine_bundle()
    engine = bundle.engine
    scenario = bundle.sample_data.get_tiny_scenario()
    with pytest.raises(engine.StratosError):
        engine.validate_profile([0], scenario)  # wrong length for 2 students
    with pytest.raises(engine.StratosError):
        engine.validate_profile([0, 5], scenario)  # project index out of range


# ---------------------------------------------------------------------------
# Mock engine correctness, cross-checked against the hand-verified tiny
# example in TEAM_WORK_ALLOCATION.md Section 8.4.
# ---------------------------------------------------------------------------

@pytest.fixture
def tiny_scenario():
    return helpers._MockSampleData.get_tiny_scenario()


def test_tiny_scenario_matches_documented_numbers(tiny_scenario):
    assert tiny_scenario["pref"] == [[5, 1], [1, 5]]
    assert tiny_scenario["w"] == [[0, 2], [2, 0]]
    assert tiny_scenario["gamma"] == 1


@pytest.mark.parametrize(
    "profile, expected_utilities, expected_welfare, expected_potential, expected_is_nash",
    [
        ([0, 0], [6, 2], 8, 7, False),
        ([0, 1], [5, 5], 10, 10, True),
        ([1, 0], [1, 1], 2, 2, False),
        ([1, 1], [2, 6], 8, 7, False),
    ],
)
def test_mock_engine_matches_documented_tiny_example(
    tiny_scenario, profile, expected_utilities, expected_welfare, expected_potential, expected_is_nash
):
    E = helpers._MockEngine
    assert E.utilities(profile, tiny_scenario) == expected_utilities
    assert E.social_welfare(profile, tiny_scenario) == expected_welfare
    assert E.potential(profile, tiny_scenario) == expected_potential
    assert E.is_nash(profile, tiny_scenario)["is_nash"] == expected_is_nash


def test_mock_engine_is_nash_deviation_shape_matches_doc(tiny_scenario):
    result = helpers._MockEngine.is_nash([0, 0], tiny_scenario)
    assert result["deviations"] == [
        {"student": 1, "from_project": 0, "to_project": 1, "current_utility": 2, "new_utility": 5, "gain": 3}
    ]


def test_mock_engine_best_response_dynamics_matches_doc(tiny_scenario):
    result = helpers._MockEngine.best_response_dynamics(tiny_scenario, [0, 0])
    assert result["converged"] is True
    assert result["rounds"] == 2
    assert result["final_profile"] == [0, 1]
    assert len(result["steps"]) == 1
    assert result["steps"][0]["student"] == 1
    assert result["steps"][0]["from_project"] == 0
    assert result["steps"][0]["to_project"] == 1
    assert result["steps"][0]["gain"] == 3
    assert result["is_nash_final"] is True


def test_mock_engine_validate_scenario_rejects_asymmetric_w():
    bad = {
        "students": ["A", "B"],
        "projects": ["P0", "P1"],
        "pref": [[1, 2], [3, 4]],
        "w": [[0, 1], [2, 0]],  # asymmetric
        "gamma": 1,
    }
    with pytest.raises(helpers._MockEngine.ScenarioError):
        helpers._MockEngine.validate_scenario(bad)


def test_mock_engine_validate_scenario_rejects_negative_gamma():
    bad = {
        "students": ["A", "B"],
        "projects": ["P0", "P1"],
        "pref": [[1, 2], [3, 4]],
        "w": [[0, 1], [1, 0]],
        "gamma": -1,
    }
    with pytest.raises(helpers._MockEngine.ScenarioError):
        helpers._MockEngine.validate_scenario(bad)


# ---------------------------------------------------------------------------
# Mock scenario generator and DataFrame/chart builders
# ---------------------------------------------------------------------------

def test_generate_custom_mock_scenario_shape_and_validity():
    scenario = helpers.generate_custom_mock_scenario(num_students=6, num_projects=3, gamma=1.0, seed=1)
    helpers._MockEngine.validate_scenario(scenario)  # must not raise
    assert len(scenario["students"]) == 6
    assert len(scenario["projects"]) == 3
    assert len(scenario["pref"]) == 6 and all(len(row) == 3 for row in scenario["pref"])
    assert len(scenario["w"]) == 6 and all(len(row) == 6 for row in scenario["w"])


def test_dataframe_builders_do_not_error():
    scenario = helpers.generate_custom_mock_scenario(num_students=5, num_projects=3, gamma=1.0, seed=2)
    profile = [0, 1, 2, 0, 1]
    teams = helpers._MockEngine.teams(profile, scenario)
    utilities = helpers._MockEngine.utilities(profile, scenario)

    assert isinstance(helpers.students_df(scenario), pd.DataFrame)
    assert isinstance(helpers.projects_df(scenario), pd.DataFrame)
    assert isinstance(helpers.preference_df(scenario), pd.DataFrame)
    assert isinstance(helpers.compatibility_df(scenario), pd.DataFrame)
    assert isinstance(helpers.teams_df(teams, scenario), pd.DataFrame)
    assert isinstance(helpers.utilities_df(profile, scenario, utilities), pd.DataFrame)
    assert isinstance(helpers.deviations_df([], scenario), pd.DataFrame)


def test_profile_at_step_replays_moves_correctly():
    start = [0, 0]
    steps = [{"round": 1, "student": 1, "from_project": 0, "to_project": 1, "gain": 3}]
    assert helpers.profile_at_step(start, steps, 0) == [0, 0]
    assert helpers.profile_at_step(start, steps, 1) == [0, 1]


def test_charts_build_without_error():
    scenario = helpers.generate_custom_mock_scenario(num_students=5, num_projects=3, gamma=1.0, seed=3)
    profile = [0, 1, 2, 0, 1]
    utilities = helpers._MockEngine.utilities(profile, scenario)
    trace_df = helpers.replay_welfare_potential_trace(helpers._MockEngine, scenario, profile, [])

    assert helpers.preference_heatmap(scenario) is not None
    assert helpers.compatibility_heatmap(scenario) is not None
    assert helpers.utility_bar_chart(profile, scenario, utilities) is not None
    assert helpers.dynamics_trace_chart(trace_df) is not None
