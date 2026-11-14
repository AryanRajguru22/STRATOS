"""Tests for the additive analysis API: utility_breakdown, analyze_landscape, the pruned Pareto search, scenario_io."""
import itertools
import json
import random

import pytest

import game_engine as g
import sample_data as sd
import scenario_io as sio

DEFAULT = sd.get_default_scenario()
TINY = sd.get_tiny_scenario()


def random_scenario(n, m, seed, gamma=1, lo=-2, hi=3, floats=False):
    rng = random.Random(seed)
    pref = [[(rng.uniform(0, 10) if floats else rng.randint(0, 10)) for _ in range(m)] for _ in range(n)]
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w[i][j] = w[j][i] = (rng.uniform(lo, hi) if floats else rng.randint(lo, hi))
    return {"students": [f"S{i}" for i in range(n)], "projects": [f"P{t}" for t in range(m)],
            "pref": pref, "w": w, "gamma": gamma}


# ------------------------------------------------------------------------------------ utility_breakdown
def test_A01_breakdown_components_add_up_to_engine_utility_on_every_default_profile():
    for s in itertools.product(range(3), repeat=8):
        utils = g.utilities(s, DEFAULT)
        for i in range(8):
            b = g.utility_breakdown(i, s, DEFAULT)
            assert b["preference"] + b["compatibility"] - b["crowding"] == b["total"] == utils[i]


def test_A01_breakdown_hand_example_tiny():
    b = g.utility_breakdown(1, [0, 0], TINY)  # student 1 on project 0: pref 1, teammate S0 (w=2), c(2)=1
    assert (b["preference"], b["compatibility"], b["crowding"], b["total"], b["team_size"]) == (1, 2, 1, 2, 2)
    assert b["teammates"] == [{"student": 0, "weight": 2}]
    lone = g.utility_breakdown(1, [0, 1], TINY)
    assert (lone["preference"], lone["compatibility"], lone["crowding"], lone["total"]) == (5, 0, 0, 5)


@pytest.mark.parametrize("seed", range(5))
def test_A01_breakdown_matches_utility_on_random_float_scenarios(seed):
    sc = random_scenario(6, 3, seed, gamma=1.5, floats=True)
    rng = random.Random(seed)
    for _ in range(40):
        s = [rng.randrange(3) for _ in range(6)]
        for i in range(6):
            assert g.utility_breakdown(i, s, sc)["total"] == pytest.approx(g.utility(i, s, sc), abs=1e-9)


def test_A01_breakdown_rejects_bad_input():
    with pytest.raises(g.StratosError):
        g.utility_breakdown(5, [0, 0], TINY)
    with pytest.raises(g.ProfileError):
        g.utility_breakdown(0, [0, 3], TINY)


# ------------------------------------------------------------------------------------ pruned Pareto search
def brute_force_pareto(sc, profile):
    n = len(sc["students"])
    m = len(sc["projects"])
    u = g.utilities(profile, sc)
    for q in itertools.product(range(m), repeat=n):
        v = g.utilities(q, sc)
        if all(v[i] >= u[i] - g.EPS for i in range(n)) and any(v[i] > u[i] + g.EPS for i in range(n)):
            return False
    return True


@pytest.mark.parametrize("seed,floats", [(1, False), (2, False), (3, True), (4, True), (5, False)])
def test_A02_pruned_pareto_search_equals_brute_force(seed, floats):
    sc = random_scenario(5, 3, seed, gamma=1, floats=floats)
    result = g.enumerate_equilibria(sc)
    for e in result["equilibria"]:
        assert e["pareto_optimal"] == brute_force_pareto(sc, e["profile"])


def test_A02_dominated_by_witness_really_dominates():
    a = g.analyze_landscape(DEFAULT)
    dominated = [e for e in a["equilibria"] if not e["pareto_optimal"]]
    assert len(dominated) == 3
    for e in dominated:
        u, v = e["utilities"], g.utilities(e["dominated_by"], DEFAULT)
        assert v == e["dominated_by_utilities"]
        assert all(v[i] >= u[i] for i in range(8)) and any(v[i] > u[i] for i in range(8))
    assert all(e["dominated_by"] is None for e in a["equilibria"] if e["pareto_optimal"])


# ------------------------------------------------------------------------------------ analyze_landscape
def test_A03_default_landscape_headline_figures():
    a = g.analyze_landscape(DEFAULT)
    assert (a["n_profiles"], a["n_equilibria"]) == (6561, 23)
    assert a["equilibrium_share"] == pytest.approx(23 / 6561)
    assert a["optimal"]["welfare"] == 29 and len(a["optimal_profiles"]) == 2
    assert a["optimal_is_equilibrium"].count(True) == 1
    assert (a["best_equilibrium"]["welfare"], a["worst_equilibrium"]["welfare"]) == (29, 16)
    assert a["price_of_stability"] == 1.0 and a["price_of_anarchy"] == pytest.approx(29 / 16)
    assert a["ratio_status"] == "defined"
    assert (a["n_pareto_optimal_equilibria"], a["n_pareto_dominated_equilibria"]) == (20, 3)
    assert a["n_equilibrium_welfare_levels"] == 12
    assert [lv["welfare"] for lv in a["equilibrium_welfare_levels"]] == [16, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 29]
    json.dumps(a)


def test_A03_landscape_agrees_with_enumerate_equilibria_everywhere():
    for sc in (TINY, DEFAULT, random_scenario(6, 3, 11), random_scenario(5, 4, 12, gamma=3)):
        a, e = g.analyze_landscape(sc), g.enumerate_equilibria(sc)
        assert a["n_profiles"] == e["n_profiles"] and a["n_equilibria"] == e["n_equilibria"]
        assert [x["profile"] for x in a["equilibria"]] == [x["profile"] for x in e["equilibria"]]
        assert [x["pareto_optimal"] for x in a["equilibria"]] == [x["pareto_optimal"] for x in e["equilibria"]]
        assert a["optimal_profiles"] == e["optimal_profiles"] and a["optimal"] == e["optimal"]
        for key in ("price_of_anarchy", "price_of_stability", "welfare_gap_best_equilibrium",
                    "welfare_gap_worst_equilibrium", "potential_maximizers"):
            assert a[key] == e[key]


def test_A03_distribution_and_scatter_account_for_every_profile():
    a = g.analyze_landscape(DEFAULT)
    assert sum(r["n_profiles"] for r in a["welfare_distribution"]) == 6561
    assert sum(r["n_equilibria"] for r in a["welfare_distribution"]) == 23
    assert sum(p["count"] for p in a["welfare_potential_points"]) == 6561
    assert sum(p["count"] for p in a["welfare_potential_points"] if p["is_equilibrium"]) == 23


def test_A03_every_scatter_point_matches_a_recomputed_profile():
    sc = random_scenario(5, 3, 21)
    a = g.analyze_landscape(sc)
    expected = {}
    for s in itertools.product(range(3), repeat=5):
        key = (g.social_welfare(s, sc), g.potential(s, sc), g.is_nash(s, sc)["is_nash"])
        expected[key] = expected.get(key, 0) + 1
    got = {(p["welfare"], p["potential"], p["is_equilibrium"]): p["count"] for p in a["welfare_potential_points"]}
    assert got == expected


def test_A03_tiny_landscape_by_hand():
    a = g.analyze_landscape(TINY)
    assert a["n_equilibria"] == 1 and a["equilibria"][0]["profile"] == [0, 1]
    assert a["optimal"]["welfare"] == 10 and a["optimal_is_equilibrium"] == [True]
    assert (a["price_of_anarchy"], a["price_of_stability"]) == (1.0, 1.0)
    assert a["n_pareto_optimal_equilibria"] == 1 and a["n_pareto_dominated_equilibria"] == 0


def test_A04_ratios_undefined_when_equilibrium_welfare_not_positive_but_gaps_reported():
    sc = dict(DEFAULT, gamma=3)  # INTERFACE.md: equilibrium welfare is no longer positive at gamma = 3
    a = g.analyze_landscape(sc)
    assert a["n_equilibria"] >= 1
    if a["ratio_status"] == "undefined":
        assert a["price_of_anarchy"] is None and a["price_of_stability"] is None
        assert "strictly positive" in a["ratio_note"]
    assert a["welfare_gap_best_equilibrium"] is not None and a["welfare_gap_worst_equilibrium"] is not None
    e = g.enumerate_equilibria(sc)
    assert (a["price_of_anarchy"], a["price_of_stability"]) == (e["price_of_anarchy"], e["price_of_stability"])


def test_A04_all_negative_welfare_scenario_has_undefined_ratios():
    sc = {"students": ["a", "b"], "projects": ["x", "y"], "pref": [[-5, -6], [-6, -5]], "w": [[0, 0], [0, 0]],
          "gamma": 1}
    a = g.analyze_landscape(sc)
    assert a["ratio_status"] == "undefined" and a["price_of_anarchy"] is None
    assert a["optimal"]["welfare"] < 0


def test_A05_enumeration_cap_is_respected_not_frozen():
    big = random_scenario(12, 5, 1)  # 5^12 = 244,140,625
    with pytest.raises(g.StratosError, match="enumeration limit"):
        g.analyze_landscape(big)
    with pytest.raises(g.StratosError, match="enumeration limit"):
        g.analyze_landscape(DEFAULT, max_profiles=100)


def test_A05_a_scenario_just_under_the_cap_is_analysed_quickly():
    import time
    sc = random_scenario(10, 3, 42)  # 59,049 profiles; was ~50 s before the pruned Pareto search
    t0 = time.perf_counter()
    a = g.analyze_landscape(sc)
    assert a["n_profiles"] == 59049 and a["n_equilibria"] >= 1
    assert time.perf_counter() - t0 < 30


def test_A06_equilibrium_exists_in_every_small_random_scenario():
    for seed in range(25):
        sc = random_scenario(random.Random(seed).randint(2, 6), random.Random(seed + 99).randint(2, 3), seed,
                             gamma=random.Random(seed).choice([0, 1, 2.5]))
        assert g.analyze_landscape(sc)["n_equilibria"] >= 1, seed


def test_A06_potential_maximisers_are_equilibria_on_random_scenarios():
    for seed in range(15):
        a = g.analyze_landscape(random_scenario(5, 3, seed, floats=bool(seed % 2)))
        assert a["potential_maximizers"]["all_are_equilibria"]


# ------------------------------------------------------------------------------------ scenario_io
def test_S01_round_trip_default_and_tiny():
    for sc in (DEFAULT, TINY):
        text = sio.scenario_to_json(sc, title="x")
        back = sio.scenario_from_json(text)
        for key in ("students", "projects", "pref", "w", "gamma"):
            assert back[key] == sc[key]
        assert json.loads(text)["synthetic"] is True


def test_S01_bytes_and_bom_are_accepted():
    text = sio.scenario_to_json(TINY)
    assert sio.scenario_from_json(text.encode("utf-8"))["gamma"] == 1
    assert sio.scenario_from_json(b"\xef\xbb\xbf" + text.encode("utf-8"))["gamma"] == 1


def _doc(**changes):
    doc = json.loads(sio.scenario_to_json(TINY))
    doc.update(changes)
    return json.dumps(doc)


@pytest.mark.parametrize("label,text,fragment", [
    ("not json", "{nope", "not valid JSON"),
    ("list", "[1,2]", "JSON object"),
    ("nan", '{"students":["a","b"],"projects":["x","y"],"pref":[[1,NaN],[1,1]],"w":[[0,0],[0,0]],"gamma":1}', "not allowed"),
    ("wrong format", None, "unsupported format"),
    ("wrong version", None, "unsupported version"),
    ("unknown key", None, "unknown key"),
    ("asymmetric", None, "symmetric"),
    ("diagonal", None, "diagonal"),
    ("bad gamma", None, "gamma"),
    ("bool pref", None, "number"),
    ("ragged", None, "entries"),
    ("duplicate names", None, "duplicate"),
    ("one project", None, "at least 2"),
])
def test_S02_invalid_files_are_rejected_with_a_clear_message(label, text, fragment):
    changes = {
        "wrong format": dict(format="other"), "wrong version": dict(version=99), "unknown key": dict(extra=1),
        "asymmetric": dict(w=[[0, 1], [2, 0]]), "diagonal": dict(w=[[1, 2], [2, 0]]), "bad gamma": dict(gamma=-1),
        "bool pref": dict(pref=[[True, 1], [1, 5]]), "ragged": dict(pref=[[5], [1, 5]]),
        "duplicate names": dict(students=["a", "a"]), "one project": dict(projects=["x"], pref=[[5], [1]]),
    }.get(label)
    with pytest.raises(sio.ScenarioFileError, match=fragment):
        sio.scenario_from_json(text if text is not None else _doc(**changes))


def test_S02_size_limits_and_errors_are_stratos_errors():
    big = random_scenario(12, 5, 3)
    text = sio.scenario_to_json(big)
    assert len(sio.scenario_from_json(text)["students"]) == 12
    with pytest.raises(sio.ScenarioFileError, match="exceeds the limit of 8"):
        sio.scenario_from_json(text, max_students=8)
    with pytest.raises(sio.ScenarioFileError, match="projects exceeds"):
        sio.scenario_from_json(text, max_projects=3)
    with pytest.raises(sio.ScenarioFileError, match="too large"):
        sio.scenario_from_json("x" * (sio.MAX_FILE_BYTES + 1))
    with pytest.raises(sio.ScenarioFileError, match="UTF-8"):
        sio.scenario_from_json(b"\xff\xfe\x00")
    assert issubclass(sio.ScenarioFileError, g.StratosError)


def test_S02_export_refuses_an_invalid_scenario():
    with pytest.raises(g.ScenarioError):
        sio.scenario_to_json(dict(TINY, w=[[0, 1], [2, 0]]))
