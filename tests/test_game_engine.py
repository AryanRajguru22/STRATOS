"""Engine tests E-01 .. E-14 (see docs/TEAM_WORK_ALLOCATION.md, Section 11).

Expected values come from hand calculations (documented next to each fixture) or from mathematical identities,
never from "whatever the engine printed". The fixtures:

TINY  (2 students, 2 projects, gamma 1)  - hand table from Section 8 of the plan.
TRIO  (3 students, 2 projects, gamma 2)  - hand table below; unique equilibrium [0, 0, 1], welfare tie at 12.
COORD (2 students, 2 projects, gamma 1)  - two equilibria, one Pareto-dominated.
REPEL (2 students, 2 projects, gamma 0)  - all equilibrium welfare is 0, so price ratios are undefined.
"""
import copy
import itertools
import json
import math
import random

import pytest

import game_engine as g
import sample_data as sd

TINY = sd.get_tiny_scenario()

# TRIO hand calculation. c(1)=0, c(2)=2, c(3)=8 (gamma 2). w01=2, w02=-1, w12=3.
# profile: (utilities, welfare, potential, pure Nash?)
TRIO = {"students": ["a", "b", "c"], "projects": ["x", "y"], "pref": [[4, 0], [3, 1], [0, 5]],
        "w": [[0, 2, -1], [2, 0, 3], [-1, 3, 0]], "gamma": 2}
TRIO_TABLE = {
    (0, 0, 0): ([-3, 0, -6], -9, 1, False),
    (0, 0, 1): ([4, 3, 5], 12, 12, True),
    (0, 1, 0): ([1, 1, -3], -1, 2, False),
    (0, 1, 1): ([4, 2, 6], 12, 11, False),
    (1, 0, 0): ([0, 4, 1], 5, 4, False),
    (1, 0, 1): ([-3, 3, 2], 2, 5, False),
    (1, 1, 0): ([0, 1, 0], 1, 1, False),
    (1, 1, 1): ([-7, -2, -1], -10, 0, False),
}

# TINY hand table (Section 8): pref [[5,1],[1,5]], w01 = 2, gamma 1.
TINY_TABLE = {
    (0, 0): ([6, 2], 8, 7, False),
    (0, 1): ([5, 5], 10, 10, True),
    (1, 0): ([1, 1], 2, 2, False),
    (1, 1): ([2, 6], 8, 7, False),
}

# COORD hand table: pref [[0,0],[0,1]], w01 = 2, gamma 1 (c(2)=1).
COORD = {"students": ["a", "b"], "projects": ["x", "y"], "pref": [[0, 0], [0, 1]], "w": [[0, 2], [2, 0]], "gamma": 1}
COORD_TABLE = {
    (0, 0): ([1, 1], 2, 1, True),
    (0, 1): ([0, 1], 1, 1, False),
    (1, 0): ([0, 0], 0, 0, False),
    (1, 1): ([1, 2], 3, 2, True),
}

# REPEL: nobody wants teammates (w = -3), no crowding cost. Equilibria [0,1] and [1,0] both have welfare 0.
REPEL = {"students": ["a", "b"], "projects": ["x", "y"], "pref": [[0, 0], [0, 0]], "w": [[0, -3], [-3, 0]], "gamma": 0}

DEFAULT = sd.get_default_scenario()


def random_scenario(rng, floats=False):
    n, m = rng.randint(2, 6), rng.randint(2, 4)
    pick = (lambda a, b: round(rng.uniform(a, b), 3)) if floats else rng.randint
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w[i][j] = w[j][i] = pick(-3, 4)
    return {"students": [f"s{i}" for i in range(n)], "projects": [f"p{t}" for t in range(m)],
            "pref": [[pick(-5, 10) for _ in range(m)] for _ in range(n)], "w": w,
            "gamma": pick(0, 4)}


# ---------------------------------------------------------------------------------------------- E-01
@pytest.mark.parametrize("table_scenario", [(TINY, TINY_TABLE), (TRIO, TRIO_TABLE), (COORD, COORD_TABLE)],
                         ids=["tiny", "trio", "coord"])
def test_E01_hand_computed_tables(table_scenario):
    sc, table = table_scenario
    for prof, (utils, welfare, phi, nash) in table.items():
        p = list(prof)
        assert g.utilities(p, sc) == utils
        assert [g.utility(i, p, sc) for i in range(len(p))] == utils
        assert g.social_welfare(p, sc) == welfare
        assert g.potential(p, sc) == phi
        assert g.is_nash(p, sc)["is_nash"] is nash


def test_E01_crowding_cost_values():
    sc = dict(TINY, gamma=2)
    assert [g.crowding_cost(k, sc) for k in (1, 2, 3, 4)] == [0, 2, 8, 18]
    for bad in (0, -1, 1.5, True, "2", None):
        with pytest.raises(g.StratosError):
            g.crowding_cost(bad, sc)


# ---------------------------------------------------------------------------------------------- E-02
@pytest.mark.parametrize("bad", [[0], [0, 1, 0], [0, 2], [0, -1], [0, 1.0], [0, True], [0, "1"], [None, 0], "01",
                                 {"0": 1}, None, 5, [[0], [1]]])
def test_E02_invalid_profiles_raise_profile_error(bad):
    with pytest.raises(g.ProfileError):
        g.validate_profile(bad, TINY)
    with pytest.raises(g.ProfileError):
        g.utilities(bad, TINY)
    with pytest.raises(g.ProfileError):
        g.is_nash(bad, TINY)


def test_E02_valid_profile_forms_accepted():
    assert g.validate_profile([0, 1], TINY) is None
    assert g.validate_profile((0, 1), TINY) is None
    assert g.utilities((0, 1), TINY) == [5, 5]


def test_E02_invalid_student_index_and_parameters():
    for bad in (-1, 2, 1.0, True, None, "0"):
        with pytest.raises(g.StratosError):
            g.utility(bad, [0, 1], TINY)
        with pytest.raises(g.StratosError):
            g.best_response(bad, [0, 1], TINY)
    with pytest.raises(g.StratosError):
        g.best_response_dynamics(TINY, [0, 0], order="alphabetical")
    for bad_rounds in (0, -3, 1.5, True, None):
        with pytest.raises(g.StratosError):
            g.best_response_dynamics(TINY, [0, 0], max_rounds=bad_rounds)
    for bad_seed in (1.5, "1", True):
        with pytest.raises(g.StratosError):
            g.random_profile(TINY, bad_seed)
        with pytest.raises(g.StratosError):
            g.best_response_dynamics(TINY, [0, 0], seed=bad_seed)


# ---------------------------------------------------------------------------------------------- E-03
def _mut(fn):
    sc = copy.deepcopy(TRIO)
    fn(sc)
    return sc


BAD_SCENARIOS = {
    "not a dict": [1, 2],
    "missing students": _mut(lambda s: s.pop("students")),
    "missing projects": _mut(lambda s: s.pop("projects")),
    "missing pref": _mut(lambda s: s.pop("pref")),
    "missing w": _mut(lambda s: s.pop("w")),
    "missing gamma": _mut(lambda s: s.pop("gamma")),
    "no students": _mut(lambda s: s.update(students=[], pref=[], w=[])),
    "one project": _mut(lambda s: s.update(projects=["x"], pref=[[1], [2], [3]])),
    "students not a list": _mut(lambda s: s.update(students="abc")),
    "duplicate students": _mut(lambda s: s.update(students=["a", "a", "c"])),
    "duplicate projects": _mut(lambda s: s.update(projects=["x", "x"])),
    "empty student name": _mut(lambda s: s.update(students=["a", " ", "c"])),
    "non-string project": _mut(lambda s: s.update(projects=["x", 2])),
    "pref wrong rows": _mut(lambda s: s.update(pref=[[4, 0], [3, 1]])),
    "pref ragged": _mut(lambda s: s.update(pref=[[4, 0], [3], [0, 5]])),
    "pref wrong cols": _mut(lambda s: s.update(pref=[[4, 0, 1], [3, 1, 1], [0, 5, 1]])),
    "pref string value": _mut(lambda s: s["pref"][0].__setitem__(0, "4")),
    "pref bool value": _mut(lambda s: s["pref"][0].__setitem__(0, True)),
    "pref None value": _mut(lambda s: s["pref"][0].__setitem__(0, None)),
    "pref NaN": _mut(lambda s: s["pref"][0].__setitem__(0, float("nan"))),
    "pref infinity": _mut(lambda s: s["pref"][0].__setitem__(0, float("inf"))),
    "w ragged": _mut(lambda s: s.update(w=[[0, 2, -1], [2, 0], [-1, 3, 0]])),
    "w wrong size": _mut(lambda s: s.update(w=[[0, 2], [2, 0]])),
    "w asymmetric": _mut(lambda s: s["w"][0].__setitem__(1, 5)),
    "w non-zero diagonal": _mut(lambda s: s["w"][1].__setitem__(1, 1)),
    "gamma negative": _mut(lambda s: s.update(gamma=-0.5)),
    "gamma string": _mut(lambda s: s.update(gamma="2")),
    "gamma bool": _mut(lambda s: s.update(gamma=True)),
    "gamma NaN": _mut(lambda s: s.update(gamma=float("nan"))),
    "skills not a dict": _mut(lambda s: s.update(skills=["Design"])),
    "skills unknown student": _mut(lambda s: s.update(skills={"zed": ["Design"]})),
    "skills not strings": _mut(lambda s: s.update(skills={"a": [1]})),
}


@pytest.mark.parametrize("name", list(BAD_SCENARIOS))
def test_E03_invalid_scenarios_raise_scenario_error(name):
    bad = BAD_SCENARIOS[name]
    with pytest.raises(g.ScenarioError) as info:
        g.validate_scenario(bad)
    assert str(info.value)  # informative message, not empty
    with pytest.raises(g.ScenarioError):
        g.utilities([0, 0, 0], bad)


def test_E03_error_hierarchy_and_messages_name_the_field():
    assert issubclass(g.ScenarioError, g.StratosError) and issubclass(g.ProfileError, g.StratosError)
    assert issubclass(g.StratosError, ValueError)
    with pytest.raises(g.ScenarioError, match="symmetric"):
        g.validate_scenario(BAD_SCENARIOS["w asymmetric"])
    with pytest.raises(g.ScenarioError, match="gamma"):
        g.validate_scenario(BAD_SCENARIOS["gamma negative"])
    with pytest.raises(g.ProfileError, match="out of range"):
        g.validate_profile([0, 5], TINY)


def test_E03_valid_scenarios_pass_and_tolerate_float_noise():
    for sc in (TINY, TRIO, COORD, REPEL, DEFAULT):
        assert g.validate_scenario(sc) is None
    noisy = copy.deepcopy(TRIO)
    noisy["w"][0][1] += 1e-12  # below EPS: still symmetric
    assert g.validate_scenario(noisy) is None
    assert g.validate_scenario(dict(TRIO, gamma=0)) is None
    assert g.validate_scenario(dict(TRIO, gamma=1.5)) is None


def test_E03_default_scenario_structure():
    sc = DEFAULT
    assert len(sc["students"]) == 8 and len(sc["projects"]) == 3
    assert len(sc["pref"]) == 8 and all(len(r) == 3 for r in sc["pref"])
    for i in range(8):
        assert sc["w"][i][i] == 0
        for j in range(8):
            assert sc["w"][i][j] == sc["w"][j][i]
    assert sc["gamma"] >= 0 and set(sc["skills"]) == set(sc["students"])
    # compatibility is derived from skills exactly as documented: LAMBDA*|symmetric difference| - BETA
    for i, a in enumerate(sc["students"]):
        for j, b in enumerate(sc["students"]):
            if i != j:
                assert sc["w"][i][j] == sd.LAMBDA * len(set(sc["skills"][a]) ^ set(sc["skills"][b])) - sd.BETA
    assert sd.get_default_scenario() is not sd.get_default_scenario()  # fresh object each call
    assert sd.SYNTHETIC_DATA_NOTICE and "synthetic" in sd.SYNTHETIC_DATA_NOTICE


def test_E03_tiny_scenario_matches_plan_section_8():
    assert TINY["pref"] == [[5, 1], [1, 5]] and TINY["w"] == [[0, 2], [2, 0]] and TINY["gamma"] == 1


def test_E03_demo_start_is_valid_and_unstable():
    start = sd.get_demo_start_profile()
    assert g.validate_profile(start, DEFAULT) is None
    report = g.is_nash(start, DEFAULT)
    assert report["is_nash"] is False
    assert len(report["deviations"]) >= 2


# ---------------------------------------------------------------------------------------------- E-04
def test_E04_known_equilibria_by_enumeration():
    assert [e["profile"] for e in g.enumerate_equilibria(TINY)["equilibria"]] == [[0, 1]]
    assert [e["profile"] for e in g.enumerate_equilibria(TRIO)["equilibria"]] == [[0, 0, 1]]
    assert [e["profile"] for e in g.enumerate_equilibria(COORD)["equilibria"]] == [[0, 0], [1, 1]]
    assert [e["profile"] for e in g.enumerate_equilibria(REPEL)["equilibria"]] == [[0, 1], [1, 0]]


def test_E04_is_nash_reports_no_deviations_at_equilibrium():
    for sc, prof in ((TINY, [0, 1]), (TRIO, [0, 0, 1]), (COORD, [1, 1]), (COORD, [0, 0])):
        r = g.is_nash(prof, sc)
        assert r["is_nash"] is True and r["deviations"] == []
        assert r["utilities"] == g.utilities(prof, sc)


# ---------------------------------------------------------------------------------------------- E-05
def _dev(student, frm, to, cur, new):
    return {"student": student, "from_project": frm, "to_project": to, "current_utility": cur,
            "new_utility": new, "gain": new - cur}


def test_E05_exact_deviations_tiny():
    assert g.profitable_deviations([0, 0], TINY) == [_dev(1, 0, 1, 2, 5)]
    assert g.profitable_deviations([1, 0], TINY) == [_dev(0, 1, 0, 1, 6), _dev(1, 0, 1, 1, 6)]
    assert g.profitable_deviations([1, 1], TINY) == [_dev(0, 1, 0, 2, 5)]
    r = g.is_nash([0, 0], TINY)
    assert r["is_nash"] is False and r["utilities"] == [6, 2] and r["deviations"] == [_dev(1, 0, 1, 2, 5)]


def test_E05_exact_deviations_trio():
    # hand calculation at (0,0,0): moving to project 1 alone gives pref only (c(1)=0)
    assert g.profitable_deviations([0, 0, 0], TRIO) == [_dev(0, 0, 1, -3, 0), _dev(1, 0, 1, 0, 1), _dev(2, 0, 1, -6, 5)]
    # (0,1,1): only student 1 gains, by returning to project 0 (3 vs 2)
    assert g.profitable_deviations([0, 1, 1], TRIO) == [_dev(1, 1, 0, 2, 3)]


def test_E05_best_response_structure():
    br = g.best_response(1, [0, 0], TINY)
    assert br == {"student": 1, "current": 0, "best": 1, "improves": True,
                  "options": [{"project": 0, "utility": 2}, {"project": 1, "utility": 5}]}
    stay = g.best_response(1, [0, 1], TINY)
    assert stay["best"] == 1 and stay["improves"] is False and stay["current"] == 1


def test_E05_deviations_agree_with_best_response():
    for prof in itertools.product(range(2), repeat=3):
        devs = g.profitable_deviations(list(prof), TRIO)
        for i in range(3):
            br = g.best_response(i, list(prof), TRIO)
            assert br["improves"] == any(d["student"] == i for d in devs)


# ---------------------------------------------------------------------------------------------- E-06
def _matching_pennies(profile):
    a, b = profile
    return (1, -1) if a == b else (-1, 1)


def test_E06_matching_pennies_has_no_pure_equilibrium():
    assert g.pure_nash_equilibria([2, 2], _matching_pennies) == []


def test_E06_generic_checker_on_other_known_games():
    pd = {(0, 0): (3, 3), (0, 1): (0, 5), (1, 0): (5, 0), (1, 1): (1, 1)}  # prisoner's dilemma: defect/defect only
    assert g.pure_nash_equilibria([2, 2], lambda p: pd[p]) == [[1, 1]]
    stag = {(0, 0): (4, 4), (0, 1): (0, 3), (1, 0): (3, 0), (1, 1): (2, 2)}  # stag hunt: two pure equilibria
    assert g.pure_nash_equilibria([2, 2], lambda p: stag[p]) == [[0, 0], [1, 1]]
    rps = lambda p: (0, 0) if p[0] == p[1] else ((1, -1) if (p[0] - p[1]) % 3 == 1 else (-1, 1))  # noqa: E731
    assert g.pure_nash_equilibria([3, 3], rps) == []
    assert g.pure_nash_equilibria([1], lambda p: (7,)) == [[0]]


def test_E06_generic_checker_input_validation():
    for bad in ([], [0, 2], [2, True], "22", None, [2, 1.5]):
        with pytest.raises(g.StratosError):
            g.pure_nash_equilibria(bad, _matching_pennies)
    with pytest.raises(g.StratosError):
        g.pure_nash_equilibria([2, 2], lambda p: (1,))  # wrong number of payoffs


def test_E06_team_game_through_generic_checker_matches_enumeration():
    for sc in (TINY, TRIO, COORD, REPEL):
        counts = [len(sc["projects"])] * len(sc["students"])
        generic = g.pure_nash_equilibria(counts, lambda p, sc=sc: g.utilities(list(p), sc))
        assert generic == [e["profile"] for e in g.enumerate_equilibria(sc)["equilibria"]]


# ---------------------------------------------------------------------------------------------- E-07
@pytest.mark.parametrize("order", ["round_robin", "random"])
def test_E07_dynamics_end_in_equilibrium_on_default_scenario(order):
    for seed in range(200):
        start = g.random_profile(DEFAULT, seed)
        run = g.best_response_dynamics(DEFAULT, start, order=order, seed=seed)
        assert run["converged"] is True and run["rounds"] >= 1
        assert run["start_profile"] == start
        assert run["is_nash_final"] is True
        assert g.is_nash(run["final_profile"], DEFAULT)["is_nash"] is True  # independent re-check
        prev = start
        for k, step in enumerate(run["steps"], 1):
            assert step["step"] == k and step["gain"] > 0
            cur = step["profile"]
            changed = [i for i in range(8) if cur[i] != prev[i]]
            assert changed == [step["student"]]
            assert prev[step["student"]] == step["from_project"] and cur[step["student"]] == step["to_project"]
            # the mover's gain equals the exact increase of the potential (exact potential game)
            assert g.potential(cur, DEFAULT) - g.potential(prev, DEFAULT) == step["gain"]
            assert step["potential"] == g.potential(cur, DEFAULT) and step["welfare"] == g.social_welfare(cur, DEFAULT)
            assert step["utilities"] == g.utilities(cur, DEFAULT)
            prev = cur
        assert prev == run["final_profile"]


def test_E07_dynamics_on_hand_solved_games():
    run = g.best_response_dynamics(TINY, [0, 0])
    assert run["converged"] and run["rounds"] == 2 and run["final_profile"] == [0, 1] and run["is_nash_final"]
    assert [(s["student"], s["from_project"], s["to_project"], s["gain"]) for s in run["steps"]] == [(1, 0, 1, 3)]
    assert run["steps"][0]["potential"] == 10 and run["steps"][0]["welfare"] == 10
    run = g.best_response_dynamics(TRIO, [0, 0, 0])
    assert run["final_profile"] == [0, 0, 1] and run["is_nash_final"]  # the unique equilibrium of TRIO


def test_E07_trio_trace_by_hand():
    # Start (0,0,0). Sweep 1: student 0 compares x: -3 vs y: 0 -> moves to y, gain 3, profile (1,0,0).
    # Student 1 at (1,0,0): current u = 4 on x (team {1,2}); y gives 1+w10... only student 0 on y: 1+2-2 = 1 < 4: stays.
    # Student 2: current u = 1 on x; y gives 5 + w20(-1) - 2 = 2 > 1: moves, gain 1, profile (1,0,1).
    # Sweep 2: student 0 at (1,0,1): u = -3; x gives 4 + w01(2) - 2 = 4: moves, gain 7, profile (0,0,1).
    # Remaining students stay; sweep 3 has no moves.
    run = g.best_response_dynamics(TRIO, [0, 0, 0])
    assert [(s["round"], s["student"], s["from_project"], s["to_project"], s["gain"]) for s in run["steps"]] == [
        (1, 0, 0, 1, 3), (1, 2, 0, 1, 1), (2, 0, 1, 0, 7)]
    assert [s["profile"] for s in run["steps"]] == [[1, 0, 0], [1, 0, 1], [0, 0, 1]]
    assert run["rounds"] == 3 and run["converged"]


def test_E07_start_at_equilibrium_makes_no_moves():
    run = g.best_response_dynamics(TINY, [0, 1])
    assert run["steps"] == [] and run["rounds"] == 1 and run["converged"] and run["final_profile"] == [0, 1]


# ---------------------------------------------------------------------------------------------- E-08
def test_E08_enumeration_is_consistent_on_default_scenario():
    result = g.enumerate_equilibria(DEFAULT)
    assert result["n_profiles"] == 3 ** 8 == 6561
    eq = {tuple(e["profile"]) for e in result["equilibria"]}
    assert eq and result["n_equilibria"] == len(eq)
    # every profile classified by the public is_nash, one at a time, gives the same set
    by_check = {p for p in itertools.product(range(3), repeat=8) if g.is_nash(list(p), DEFAULT)["is_nash"]}
    assert eq == by_check
    # welfare optimum equals the maximum of the public welfare function over all profiles
    best = max(g.social_welfare(list(p), DEFAULT) for p in itertools.product(range(3), repeat=8))
    assert result["optimal"]["welfare"] == best
    assert g.social_welfare(result["optimal"]["profile"], DEFAULT) == best
    assert all(g.social_welfare(p, DEFAULT) == best for p in result["optimal_profiles"])
    assert result["optimal"]["profile"] == result["optimal_profiles"][0]
    for e in result["equilibria"]:
        assert e["utilities"] == g.utilities(e["profile"], DEFAULT)
        assert e["welfare"] == sum(e["utilities"]) and e["potential"] == g.potential(e["profile"], DEFAULT)
        assert e["welfare"] <= best
    # the potential maximisers are equilibria, and nothing has a larger potential
    pm = result["potential_maximizers"]
    top = max(g.potential(list(p), DEFAULT) for p in itertools.product(range(3), repeat=8))
    assert pm["potential"] == top and pm["all_are_equilibria"] is True
    assert all(tuple(p) in eq for p in pm["profiles"])


def test_E08_every_dynamics_endpoint_is_an_enumerated_equilibrium():
    eq = {tuple(e["profile"]) for e in g.enumerate_equilibria(DEFAULT)["equilibria"]}
    for seed in range(200):
        run = g.best_response_dynamics(DEFAULT, g.random_profile(DEFAULT, seed), seed=seed)
        assert tuple(run["final_profile"]) in eq


def test_E08_welfare_gaps_ratios_and_pareto_on_default():
    r = g.enumerate_equilibria(DEFAULT)
    ws = [e["welfare"] for e in r["equilibria"]]
    w_opt = r["optimal"]["welfare"]
    assert r["welfare_gap_best_equilibrium"] == w_opt - max(ws)
    assert r["welfare_gap_worst_equilibrium"] == w_opt - min(ws)
    if min(ws) > 0:
        assert r["price_of_anarchy"] == pytest.approx(w_opt / min(ws))
        assert r["price_of_stability"] == pytest.approx(w_opt / max(ws))
    else:
        assert r["price_of_anarchy"] is None and r["price_of_stability"] is None
    assert all(isinstance(e["pareto_optimal"], bool) for e in r["equilibria"])


def test_E08_pareto_flags_verified_independently():
    all_utils = {p: g.utilities(list(p), DEFAULT) for p in itertools.product(range(3), repeat=8)}
    for e in g.enumerate_equilibria(DEFAULT)["equilibria"]:
        u = e["utilities"]
        dominated = any(all(a >= b for a, b in zip(v, u)) and any(a > b for a, b in zip(v, u))
                        for v in all_utils.values())
        assert e["pareto_optimal"] is (not dominated)


def test_E08_price_of_anarchy_pareto_and_gaps_on_hand_solved_games():
    r = g.enumerate_equilibria(COORD)
    assert [e["pareto_optimal"] for e in r["equilibria"]] == [False, True]  # [0,0] is dominated by [1,1]
    assert r["optimal"] == {"profile": [1, 1], "welfare": 3, "utilities": [1, 2]}
    assert (r["welfare_gap_best_equilibrium"], r["welfare_gap_worst_equilibrium"]) == (0, 1)
    assert r["price_of_anarchy"] == pytest.approx(1.5) and r["price_of_stability"] == pytest.approx(1.0)
    assert r["potential_maximizers"] == {"potential": 2, "profiles": [[1, 1]], "all_are_equilibria": True}
    # [0,0] is an equilibrium but NOT a potential maximiser: equilibrium != potential maximisation
    assert [0, 0] in [e["profile"] for e in r["equilibria"]] and [0, 0] not in r["potential_maximizers"]["profiles"]

    r = g.enumerate_equilibria(TRIO)
    assert r["optimal"] == {"profile": [0, 0, 1], "welfare": 12, "utilities": [4, 3, 5]}
    assert r["optimal_profiles"] == [[0, 0, 1], [0, 1, 1]]  # welfare tie; first in enumeration order reported
    assert r["price_of_anarchy"] == pytest.approx(1.0) and r["welfare_gap_best_equilibrium"] == 0
    assert r["equilibria"][0]["pareto_optimal"] is True

    r = g.enumerate_equilibria(TINY)
    assert r["n_profiles"] == 4 and r["optimal"]["profile"] == [0, 1] and r["optimal"]["welfare"] == 10
    assert r["price_of_anarchy"] == pytest.approx(1.0) and r["price_of_stability"] == pytest.approx(1.0)
    assert r["welfare_gap_best_equilibrium"] == 0 and r["welfare_gap_worst_equilibrium"] == 0


def test_E08_every_profile_is_evaluated_exactly_once(monkeypatch):
    seen = []
    real = g._utilities

    def spy(M, s):
        seen.append(tuple(s))
        return real(M, s)

    monkeypatch.setattr(g, "_utilities", spy)
    result = g.enumerate_equilibria(DEFAULT)
    assert len(seen) == len(set(seen)) == result["n_profiles"] == 6561
    assert set(seen) == set(itertools.product(range(3), repeat=8))


def test_E08_ratios_are_none_when_some_equilibrium_has_non_positive_welfare_but_gaps_remain():
    sc = dict(DEFAULT, gamma=3)
    r = g.enumerate_equilibria(sc)
    ws = [e["welfare"] for e in r["equilibria"]]
    assert min(ws) <= 0 < r["optimal"]["welfare"]  # precondition: positive optimum, non-positive equilibrium
    assert r["price_of_anarchy"] is None and r["price_of_stability"] is None
    assert r["welfare_gap_best_equilibrium"] == r["optimal"]["welfare"] - max(ws)
    assert r["welfare_gap_worst_equilibrium"] == r["optimal"]["welfare"] - min(ws)


def test_E08_equal_utility_vectors_do_not_dominate_each_other():
    # Two identical students, w = 0, gamma = 1: [0,1] and [1,0] both give utilities (1, 1); [0,0] and [1,1] give (0, 0).
    # Equal payoff vectors are not strict domination, so both equilibria are Pareto-optimal.
    sym = {"students": ["a", "b"], "projects": ["x", "y"], "pref": [[1, 1], [1, 1]], "w": [[0, 0], [0, 0]], "gamma": 1}
    r = g.enumerate_equilibria(sym)
    assert [(e["profile"], e["utilities"], e["pareto_optimal"]) for e in r["equilibria"]] == [
        ([0, 1], [1, 1], True), ([1, 0], [1, 1], True)]


def test_E08_ratios_are_null_when_equilibrium_welfare_is_not_positive():
    r = g.enumerate_equilibria(REPEL)
    assert [e["welfare"] for e in r["equilibria"]] == [0, 0]
    assert r["price_of_anarchy"] is None and r["price_of_stability"] is None
    assert r["welfare_gap_best_equilibrium"] == 0 and r["welfare_gap_worst_equilibrium"] == 0


def test_E08_with_analysis_false_skips_pareto_and_ratios_only():
    r = g.enumerate_equilibria(COORD, with_analysis=False)
    assert all(e["pareto_optimal"] is None for e in r["equilibria"])
    assert r["price_of_anarchy"] is None and r["price_of_stability"] is None
    assert r["welfare_gap_worst_equilibrium"] == 1 and r["optimal"]["welfare"] == 3


def test_E08_enumeration_limit_guard():
    big = {"students": [f"s{i}" for i in range(12)], "projects": ["x", "y", "z"],
           "pref": [[0, 0, 0]] * 12, "w": [[0] * 12 for _ in range(12)], "gamma": 1}
    with pytest.raises(g.StratosError, match="limit"):
        g.enumerate_equilibria(big)
    assert g.enumerate_equilibria(TINY, max_profiles=4)["n_profiles"] == 4
    with pytest.raises(g.StratosError):
        g.enumerate_equilibria(TINY, max_profiles=3)


# ---------------------------------------------------------------------------------------------- E-09
@pytest.mark.parametrize("k", [1, 2, 3])
def test_E09_adding_a_teammate_changes_each_member_by_c_k_minus_c_k_plus_1(k):
    gamma = 3
    sc = {"students": ["a", "b", "c", "d"], "projects": ["x", "y"],
          "pref": [[5, 2], [1, 8], [4, 4], [0, 7]], "w": [[0] * 4 for _ in range(4)], "gamma": gamma}
    before = [0] * k + [1] * (4 - k)   # students 0..k-1 on x; the joiner is student k, currently on y
    after = [0] * (k + 1) + [1] * (3 - k)
    # hand formula: c(k) = gamma (k-1)^2, so the change is gamma*((k-1)^2 - k^2) = -gamma*(2k-1)
    for member in range(k):
        assert g.utility(member, after, sc) - g.utility(member, before, sc) == -gamma * (2 * k - 1)


def test_E09_crowding_cost_only_depends_on_team_size_not_identity():
    sc = {"students": ["a", "b", "c"], "projects": ["x", "y"], "pref": [[3, 3]] * 3, "w": [[0] * 3 for _ in range(3)],
          "gamma": 2}
    assert g.utilities([0, 0, 1], sc) == [3 - 2, 3 - 2, 3]
    assert g.utilities([0, 1, 0], sc) == [3 - 2, 3, 3 - 2]
    assert g.utilities([0, 0, 0], sc) == [3 - 8] * 3


# ---------------------------------------------------------------------------------------------- E-10
@pytest.mark.parametrize("project", [0, 1, 2])
def test_E10_large_gamma_breaks_up_the_all_in_one_team_profile(project):
    sc = dict(DEFAULT, gamma=1000)
    everyone = [project] * 8
    assert g.is_nash(everyone, sc)["is_nash"] is False
    assert len(g.profitable_deviations(everyone, sc)) == 16  # every student can profitably leave to either project


def test_E10_zero_gamma_allows_everyone_on_the_popular_project():
    r = g.enumerate_equilibria(dict(DEFAULT, gamma=0))
    assert [0] * 8 in [e["profile"] for e in r["equilibria"]]  # no crowding cost: sticking together can be stable


# ---------------------------------------------------------------------------------------------- E-11
def test_E11_same_seed_gives_identical_results_and_different_seeds_differ():
    assert g.random_profile(DEFAULT, 5) == g.random_profile(DEFAULT, 5)
    assert len({tuple(g.random_profile(DEFAULT, s)) for s in range(20)}) > 1
    start = g.random_profile(DEFAULT, 9)
    a = g.best_response_dynamics(DEFAULT, start, order="random", seed=4)
    b = g.best_response_dynamics(DEFAULT, start, order="random", seed=4)
    assert a == b
    assert g.best_response_dynamics(DEFAULT, start) == g.best_response_dynamics(DEFAULT, start)


def test_E11_ties_move_to_the_lowest_index_and_indifferent_students_stay():
    sc = {"students": ["solo"], "projects": ["x", "y", "z"], "pref": [[3, 5, 5]], "w": [[0]], "gamma": 1}
    run = g.best_response_dynamics(sc, [0])
    assert run["final_profile"] == [1] and run["steps"][0]["to_project"] == 1 and run["steps"][0]["gain"] == 2
    stay = g.best_response_dynamics(sc, [2])  # project 2 already ties for best: no strict gain, no move
    assert stay["steps"] == [] and stay["final_profile"] == [2] and stay["is_nash_final"]
    br = g.best_response(0, [2], sc)
    assert br["best"] == 2 and br["improves"] is False
    br = g.best_response(0, [0], sc)
    assert br["best"] == 1 and br["improves"] is True
    # a tie is still an equilibrium (weak definition): both [1] and [2] are
    assert [e["profile"] for e in g.enumerate_equilibria(sc)["equilibria"]] == [[1], [2]]


def test_E11_gains_below_tolerance_are_ignored():
    sc = {"students": ["solo"], "projects": ["x", "y"], "pref": [[1.0, 1.0 + 1e-12]], "w": [[0]], "gamma": 0}
    assert g.profitable_deviations([0], sc) == [] and g.is_nash([0], sc)["is_nash"] is True
    assert g.best_response(0, [0], sc)["improves"] is False


def _snapshot_calls(sc, prof):
    g.validate_scenario(sc)
    g.validate_profile(prof, sc)
    g.crowding_cost(2, sc)
    g.utility(0, prof, sc)
    g.utilities(prof, sc)
    g.social_welfare(prof, sc)
    g.potential(prof, sc)
    g.teams(prof, sc)
    g.best_response(0, prof, sc)
    g.profitable_deviations(prof, sc)
    g.is_nash(prof, sc)
    g.random_profile(sc, 1)
    g.best_response_dynamics(sc, prof)
    g.enumerate_equilibria(sc)


def test_E11_inputs_are_never_mutated():
    sc = copy.deepcopy(DEFAULT)
    prof = [0, 1, 2, 0, 1, 2, 0, 1]
    sc_before, prof_before = copy.deepcopy(sc), list(prof)
    _snapshot_calls(sc, prof)
    assert sc == sc_before and prof == prof_before
    tup = (0, 1, 2, 0, 1, 2, 0, 1)
    _snapshot_calls(sc, tup)
    assert tup == (0, 1, 2, 0, 1, 2, 0, 1) and sc == sc_before


def test_E11_outputs_do_not_alias_inputs():
    prof = [0, 0]
    run = g.best_response_dynamics(TINY, prof)
    assert run["start_profile"] is not prof
    run["final_profile"][0] = 1
    assert prof == [0, 0] and TINY == sd.get_tiny_scenario()


# ---------------------------------------------------------------------------------------------- E-12
def _closed_form_welfare(sc, prof):
    """W = sum pref + 2 * sum over same-team pairs of w - sum_t n_t c(n_t): a different formula from sum of utilities."""
    n = len(prof)
    total = sum(sc["pref"][i][prof[i]] for i in range(n))
    total += 2 * sum(sc["w"][i][j] for i in range(n) for j in range(i + 1, n) if prof[i] == prof[j])
    for t in range(len(sc["projects"])):
        size = sum(1 for x in prof if x == t)
        total -= size * sc["gamma"] * max(size - 1, 0) ** 2
    return total


def _deviate(prof, i, t):
    out = list(prof)
    out[i] = t
    return out


def test_E12_exact_potential_identity_and_welfare_on_default_scenario():
    rng = random.Random(12)
    for _ in range(1000):
        prof = [rng.randrange(3) for _ in range(8)]
        i, t = rng.randrange(8), rng.randrange(3)
        dev = _deviate(prof, i, t)
        du = g.utility(i, dev, DEFAULT) - g.utility(i, prof, DEFAULT)
        assert g.potential(dev, DEFAULT) - g.potential(prof, DEFAULT) == du
        assert g.social_welfare(prof, DEFAULT) == sum(g.utilities(prof, DEFAULT)) == _closed_form_welfare(DEFAULT, prof)


def test_E12_identity_holds_on_random_scenarios_integer_and_float():
    rng = random.Random(77)
    for floats in (False, True):
        for _ in range(40):
            sc = random_scenario(rng, floats)
            n, m = len(sc["students"]), len(sc["projects"])
            for _ in range(25):
                prof = [rng.randrange(m) for _ in range(n)]
                i, t = rng.randrange(n), rng.randrange(m)
                dev = _deviate(prof, i, t)
                du = g.utility(i, dev, sc) - g.utility(i, prof, sc)
                assert g.potential(dev, sc) - g.potential(prof, sc) == pytest.approx(du, abs=1e-9)
                assert g.social_welfare(prof, sc) == pytest.approx(_closed_form_welfare(sc, prof), abs=1e-9)


def test_E12_dynamics_and_enumeration_agree_on_random_small_scenarios():
    rng = random.Random(3)
    for _ in range(40):
        sc = random_scenario(rng)
        n, m = len(sc["students"]), len(sc["projects"])
        eq = {tuple(e["profile"]) for e in g.enumerate_equilibria(sc)["equilibria"]}
        assert eq, "an exact potential game always has a pure equilibrium"
        for seed in range(10):
            run = g.best_response_dynamics(sc, g.random_profile(sc, seed), seed=seed)
            assert run["converged"] and run["is_nash_final"] and tuple(run["final_profile"]) in eq


# ---------------------------------------------------------------------------------------------- E-13
def test_E13_exhausted_max_rounds_is_reported_honestly():
    start = sd.get_demo_start_profile()
    full = g.best_response_dynamics(DEFAULT, start)
    assert full["rounds"] > 1
    cut = g.best_response_dynamics(DEFAULT, start, max_rounds=1)
    assert cut["converged"] is False and cut["rounds"] == 1
    assert cut["steps"] == [s for s in full["steps"] if s["round"] == 1]
    assert cut["is_nash_final"] is g.is_nash(cut["final_profile"], DEFAULT)["is_nash"]  # independent of the flag
    # stopping after a sweep that moved is never reported as converged, even if the profile happens to be stable
    one_sweep = g.best_response_dynamics(TINY, [0, 0], max_rounds=1)
    assert one_sweep["converged"] is False and one_sweep["is_nash_final"] is True


# ---------------------------------------------------------------------------------------------- E-14
def test_E14_team_structure_invariants():
    rng = random.Random(14)
    for _ in range(100):
        prof = [rng.randrange(3) for _ in range(8)]
        t = g.teams(prof, DEFAULT)
        assert len(t) == 3 and sum(len(x) for x in t) == 8
        assert sorted(i for team in t for i in team) == list(range(8))
        assert all(team == sorted(team) for team in t)
    assert g.teams([0] * 8, DEFAULT) == [list(range(8)), [], []]  # empty teams are allowed


def test_E14_lone_student_gets_preference_minus_c1():
    for t in range(3):
        for i in range(8):
            prof = [(t + 1) % 3] * 8
            prof[i] = t
            if t != (t + 1) % 3:
                assert g.utility(i, prof, DEFAULT) == DEFAULT["pref"][i][t] - g.crowding_cost(1, DEFAULT)
    assert g.crowding_cost(1, DEFAULT) == 0
