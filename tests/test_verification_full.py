"""Full-coverage verification of the engine against the independent oracle (tests/oracle/independent_check.py).

The oracle uses exact rational arithmetic and never imports the engine for its own numbers. Where tests/test_oracle.py
compares a fixed-seed sample of profiles per scenario, these tests compare EVERY one of the 3^8 = 6,561 profiles of the
default scenario, and also verify the exhaustive analyses added for the Analysis tab (distributions, best-response
basins, parameter sensitivity) and the guarantee that sensitivity analysis never mutates the baseline scenario.
"""
import copy
import importlib.util
import itertools
import os
import statistics
from fractions import Fraction as F

import pytest

import game_engine as ge
import sample_data as sd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def oc():
    spec = importlib.util.spec_from_file_location("independent_check", os.path.join(ROOT, "tests", "oracle", "independent_check.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sc():
    return sd.get_default_scenario()


@pytest.fixture(scope="module")
def ora(oc):
    return oc.analyse(oc.DEFAULT)


def test_V01_oracle_and_engine_describe_the_same_default_game(oc, sc):
    """The oracle re-types the scenario; make sure it is the same game, or every later comparison is meaningless."""
    assert oc.DEFAULT["pref"] == sc["pref"] and oc.DEFAULT["gamma"] == sc["gamma"]
    assert [[F(x) for x in r] for r in oc.DEFAULT["w"]] == [[F(x) for x in r] for r in sc["w"]]


def test_V02_strategy_space_is_exactly_3_to_the_8_with_no_duplicates(oc, ora, sc):
    P = ora["profiles"]
    assert len(P) == len(set(P)) == 3 ** 8 == 6561
    assert set(P) == set(itertools.product(range(3), repeat=8))
    assert ge.analyze_landscape(sc)["n_profiles"] == 6561 == ge.analyze_distributions(sc)["n_profiles"]


def test_V03_every_one_of_the_6561_profiles_agree_with_the_oracle(oc, ora, sc):
    """utilities, welfare, potential, team sizes, Nash classification and the exact set of profitable deviations."""
    bad = []
    for p in ora["profiles"]:
        lp = list(p)
        nash = ge.is_nash(lp, sc)
        mine = {(i, t, g_) for i, t, g_ in oc.deviations(oc.DEFAULT, p)}
        theirs = {(d["student"], d["to_project"], F(d["gain"])) for d in nash["deviations"]}
        if ([F(x) for x in ge.utilities(lp, sc)] != ora["U"][p]
                or F(ge.social_welfare(lp, sc)) != ora["W"][p]
                or F(ge.potential(lp, sc)) != ora["Phi"][p]
                or [len(t) for t in ge.teams(lp, sc)] != oc.team_sizes(oc.DEFAULT, p)
                or nash["is_nash"] != (p in set(ora["eq"]))
                or mine != theirs):
            bad.append(p)
    assert bad == []


def test_V04_equilibrium_set_welfare_optimum_and_ratios_match_exactly(ora, sc):
    L = ge.analyze_landscape(sc)
    assert {tuple(e["profile"]) for e in L["equilibria"]} == set(ora["eq"])
    assert len(ora["eq"]) == L["n_equilibria"] == 23
    assert F(L["optimal"]["welfare"]) == ora["wmax"] == 29
    assert {tuple(p) for p in L["optimal_profiles"]} == set(ora["opt"])
    assert F(L["price_of_anarchy"]) == ora["poa"] == F(29, 16) and F(L["price_of_stability"]) == ora["pos"] == 1
    assert {tuple(e["profile"]) for e in L["equilibria"] if e["pareto_optimal"]} == {p for p, ok in ora["pareto"].items() if ok}


def test_V05_max_profitable_deviation_is_zero_at_every_equilibrium_and_positive_elsewhere(oc, ora, sc):
    eq = set(ora["eq"])
    for p in ora["profiles"][::7]:  # every 7th profile (937 cases) keeps this fast; V03 already checks all of them
        gains = [g_ for _, _, g_ in oc.deviations(oc.DEFAULT, p)]
        assert (max(gains, default=0) == 0) == (p in eq)
    for p in eq:
        assert not ge.is_nash(list(p), sc)["deviations"]


def test_V06_distributions_match_independent_computation(oc, ora, sc):
    d = ge.analyze_distributions(sc)
    P = ora["profiles"]
    W = sorted(ora["W"].values())
    assert d["welfare"]["min"] == W[0] and d["welfare"]["max"] == W[-1]
    assert F(d["welfare"]["mean"]).limit_denominator(10 ** 6) == sum(W, F(0)) / len(W)
    assert F(d["welfare"]["median"]) == statistics.median(W)
    assert {tuple(p) for p in d["welfare"]["min_profiles"]} == {p for p in P if ora["W"][p] == W[0]}
    shapes = {}
    for p in P:
        key = tuple(sorted((x for x in oc.team_sizes(oc.DEFAULT, p) if x), reverse=True))
        shapes[key] = shapes.get(key, 0) + 1
    assert {tuple(r["shape"]): r["n_profiles"] for r in d["team_shapes"]} == shapes
    assert sum(r["n_profiles"] for r in d["largest_team"]) == 6561
    hist = {}
    for p in P:
        for u in ora["U"][p]:
            hist[u] = hist.get(u, 0) + 1
    assert {F(r["utility"]): r["n_student_profiles"] for r in d["utility_histogram"]} == hist
    for i, row in enumerate(d["per_student"]):
        col = [ora["U"][p][i] for p in P]
        assert (F(row["min"]), F(row["max"])) == (min(col), max(col))
    # equilibrium_project_counts: each equilibrium contributes exactly one project per student
    for i in range(8):
        assert sum(d["equilibrium_project_counts"][i]) == 23


@pytest.mark.parametrize("order", ["round_robin", "random"])
def test_V07_best_response_basins_match_the_oracles_own_dynamics(oc, ora, sc, order):
    b = ge.analyze_basins(sc, order=order)
    ends, steps = {}, []
    for k, p in enumerate(ora["profiles"]):  # the engine seeds the random order with the start's enumeration index
        final, moves, conv, rnd, _ = oc.dynamics(oc.DEFAULT, p, order=order, seed=k)
        assert conv
        ends[final] = ends.get(final, 0) + 1
        steps.append(moves)
    assert {tuple(e["profile"]): e["basin_size"] for e in b["endpoints"]} == ends
    assert sum(ends.values()) == b["n_runs"] == 6561
    assert b["max_steps"] == max(steps) and F(b["mean_steps"]).limit_denominator(10 ** 6) == F(sum(steps), 6561)
    assert b["n_not_converged"] == 0 and b["n_final_not_nash"] == 0
    assert set(ends) <= set(ora["eq"]) and all(e["is_equilibrium"] for e in b["endpoints"])


def test_V08_potential_bound_on_run_length(sc):
    """No cycles: each move raises Phi by the mover's gain (> 0), so a run has at most Phi_max - Phi_min moves."""
    d = ge.analyze_distributions(sc)
    L = ge.analyze_landscape(sc)
    phis = [p["potential"] for p in L["welfare_potential_points"]]
    bound = max(phis) - min(phis)
    assert ge.analyze_basins(sc)["max_steps"] <= bound


def test_V09_sensitivity_rows_match_the_oracle_on_scaled_copies(oc, sc):
    for parameter, value in (("gamma", 0), ("gamma", 1.5), ("gamma", 3), ("compatibility_scale", 0.5), ("compatibility_scale", 2),
                             ("preference_scale", 0.75), ("preference_scale", 0)):
        row = ge.sensitivity_sweep(sc, parameter, [value])[0]
        g = copy.deepcopy(oc.DEFAULT)
        if parameter == "gamma":
            g["gamma"] = value
        elif parameter == "compatibility_scale":
            g["w"] = [[F(x) * F(value) for x in r] for r in g["w"]]
        else:
            g["pref"] = [[F(x) * F(value) for x in r] for r in g["pref"]]
        a = oc.analyse(g)
        assert row["n_equilibria"] == len(a["eq"]), (parameter, value)
        assert F(row["optimal_welfare"]) == a["wmax"], (parameter, value)
        assert row["n_optimal_profiles"] == len(a["opt"])
        assert row["n_stable_optima"] == sum(p in set(a["eq"]) for p in a["opt"])
        eqw = [a["W"][p] for p in a["eq"]]
        assert (F(row["best_equilibrium_welfare"]), F(row["worst_equilibrium_welfare"])) == (max(eqw), min(eqw))


def test_V10_sensitivity_never_mutates_the_baseline_and_baseline_row_is_the_established_result(sc):
    before = copy.deepcopy(sc)
    base_landscape = ge.analyze_landscape(sc)
    rows = ge.sensitivity_sweep(sc, "gamma", [0, 1, 2, 3])
    assert sc == before and ge.analyze_landscape(sc) == base_landscape
    row = next(r for r in rows if r["value"] == 2)
    assert (row["n_equilibria"], row["optimal_welfare"], row["worst_equilibrium_welfare"], row["n_stable_optima"]) == (23, 29, 16, 1)
    for parameter in ("compatibility_scale", "preference_scale"):  # factor 1 reproduces the baseline exactly
        r1 = ge.sensitivity_sweep(sc, parameter, [1])[0]
        assert (r1["n_equilibria"], r1["optimal_welfare"], r1["worst_equilibrium_welfare"]) == (23, 29, 16)
    assert sc == before


def test_V11_sensitivity_variant_is_an_independent_copy_and_validates_input(sc):
    v = ge.sensitivity_variant(sc, "compatibility_scale", 2)
    v["w"][0][1] = 999
    v["students"].append("x")
    v["skills"]["Asha"].append("zzz")
    assert sc == sd.get_default_scenario()
    assert all(v["w"][i][j] == 2 * sc["w"][i][j] for i in range(8) for j in range(8) if (i, j) != (0, 1))
    for bad in (("gamma", -1), ("nope", 1), ("gamma", "2"), ("gamma", True), ("gamma", float("nan"))):
        with pytest.raises(ge.StratosError):
            ge.sensitivity_variant(sc, *bad)
    with pytest.raises(ge.StratosError):
        ge.analyze_basins(sc, order="sideways")
    with pytest.raises(ge.StratosError):
        ge.analyze_basins(sd.get_default_scenario(), max_profiles=100)


def test_V12_baseline_regression_pins(sc):
    """The established default-scenario results, asserted in one place (README table)."""
    L = ge.analyze_landscape(sc)
    assert (L["n_profiles"], L["n_equilibria"]) == (6561, 23)
    assert L["optimal"]["welfare"] == 29 and len(L["optimal_profiles"]) == 2 and sum(L["optimal_is_equilibrium"]) == 1
    assert L["worst_equilibrium"]["welfare"] == 16 and L["best_equilibrium"]["welfare"] == 29
    assert (L["price_of_stability"], L["price_of_anarchy"]) == (1.0, 29 / 16)
    assert (L["n_pareto_optimal_equilibria"], L["n_pareto_dominated_equilibria"]) == (20, 3)
    assert sc["gamma"] == 2 and sc["pref"][0] == [8, 6, 2]


def test_V13_distribution_and_basin_results_on_a_game_with_a_known_answer():
    """Tiny game solved by hand: unique equilibrium (0, 1), reached from all 4 starts; all profiles have 2 teams of 1 or 1 of 2."""
    tiny = sd.get_tiny_scenario()
    b = ge.analyze_basins(tiny)
    assert [(e["profile"], e["basin_size"]) for e in b["endpoints"]] == [([0, 1], 4)]
    d = ge.analyze_distributions(tiny)
    assert {tuple(r["shape"]): r["n_profiles"] for r in d["team_shapes"]} == {(2,): 2, (1, 1): 2}
    assert d["welfare"]["min"] == 2 and d["welfare"]["max"] == 10  # welfares are 8, 10, 2, 8 by hand (MODEL: TINY_HAND)


def test_V14_saved_analysis_report_is_not_stale(sc):
    """docs/results/analysis_report.json must equal a fresh computation (regenerate: python scripts/generate_results.py)."""
    import json
    path = os.path.join(ROOT, "docs", "results", "analysis_report.json")
    if not os.path.exists(path):
        pytest.skip("analysis_report.json not generated yet")
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["distributions"] == json.loads(json.dumps(ge.analyze_distributions(sc)))
    for order in ge.VALID_ORDERS:
        assert saved["basins"][order] == json.loads(json.dumps(ge.analyze_basins(sc, order=order))), order
    assert saved["sensitivity"]["gamma"] == json.loads(json.dumps(ge.sensitivity_sweep(sc, "gamma", [0.5 * k for k in range(11)])))
