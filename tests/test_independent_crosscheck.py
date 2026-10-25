"""Run scripts/independent_crosscheck.py inside the suite.

The cross-check recomputes the model from docs/MODEL.md with its own code (it does not import game_engine for its own
numbers) and then diffs the result with the production engine. These tests pin the headline figures of the default
scenario and fail if the engine and the independent computation ever disagree.
"""
import importlib.util
import os
from fractions import Fraction

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def xc():
    spec = importlib.util.spec_from_file_location("independent_crosscheck", os.path.join(ROOT, "scripts", "independent_crosscheck.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def analysis(xc):
    return xc.analyse(xc.default_game())


def test_X01_tiny_hand_table_is_reproduced(xc):
    assert xc.check_tiny() == []


def test_X02_default_scenario_headline_figures(analysis):
    assert analysis["n_profiles"] == 3 ** 8 == 6561
    assert analysis["n_equilibria"] == 23
    assert analysis["w_opt"] == 29
    assert analysis["price_of_stability"] == Fraction(1)
    assert analysis["price_of_anarchy"] == Fraction(29, 16) == Fraction(1.8125)
    assert (analysis["welfare_gap_best"], analysis["welfare_gap_worst"]) == (0, 13)


def test_X03_model_identities_hold_on_every_profile(analysis):
    assert analysis["welfare_identity_ok"] is True
    assert analysis["potential_identity_ok"] is True


def test_X04_round_robin_dynamics_from_every_start_ends_in_an_equilibrium(analysis):
    summary = analysis["round_robin_from_every_start"]
    assert summary["all_converge_to_nash"] and summary["terminals_subset_of_equilibria"]


def test_X05_engine_and_independent_computation_agree(xc, analysis):
    assert xc.compare_with_engine(analysis) == []
