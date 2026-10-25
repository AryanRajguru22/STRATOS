"""Integration tests I-01 .. I-06: the engine <-> app contract in docs/INTERFACE.md, plus the CLI report.

These check the shape and types that Harsh's Streamlit app relies on, error behaviour for invalid input,
consumption of engine output by pandas (as the UI will do), and the command-line report.
"""
import copy
import json
import os
import subprocess
import sys

import pytest

import game_engine as g
import sample_data as sd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = sd.get_default_scenario()
START = sd.get_demo_start_profile()


def _all_public_outputs(sc, prof):
    return {
        "crowding_cost": g.crowding_cost(2, sc),
        "utility": g.utility(0, prof, sc),
        "utilities": g.utilities(prof, sc),
        "social_welfare": g.social_welfare(prof, sc),
        "potential": g.potential(prof, sc),
        "teams": g.teams(prof, sc),
        "best_response": g.best_response(0, prof, sc),
        "profitable_deviations": g.profitable_deviations(prof, sc),
        "is_nash": g.is_nash(prof, sc),
        "random_profile": g.random_profile(sc, 3),
        "dynamics_rr": g.best_response_dynamics(sc, prof),
        "dynamics_random": g.best_response_dynamics(sc, prof, order="random", seed=1),
        "enumerate": g.enumerate_equilibria(sc),
        "generic": g.pure_nash_equilibria([2, 2], lambda p: (1, -1) if p[0] == p[1] else (-1, 1)),
    }


def _only_plain_types(value, path="result"):
    """Recursively assert the value contains only dict(str keys)/list/int/float/bool/str/None."""
    if value is None or isinstance(value, (bool, int, float, str)):
        assert type(value) in (type(None), bool, int, float, str), f"{path}: {type(value)} leaks a subclass"
    elif isinstance(value, list):
        for k, v in enumerate(value):
            _only_plain_types(v, f"{path}[{k}]")
    elif isinstance(value, dict):
        for k, v in value.items():
            assert isinstance(k, str), f"{path}: non-string key {k!r}"
            _only_plain_types(v, f"{path}.{k}")
    else:
        pytest.fail(f"{path}: unexpected type {type(value).__name__}")


# ---------------------------------------------------------------------------------------------- I-01
def test_I01_every_public_output_is_json_serialisable_plain_python():
    for name, out in _all_public_outputs(SC, START).items():
        _only_plain_types(out, name)
        assert json.loads(json.dumps(out)) == out, name


def test_I01_numpy_inputs_are_accepted_and_never_leak_into_outputs():
    np = pytest.importorskip("numpy")
    sc = copy.deepcopy(SC)
    sc["pref"] = [[np.int64(v) for v in row] for row in sc["pref"]]
    sc["w"] = [[np.int64(v) for v in row] for row in sc["w"]]
    sc["gamma"] = np.float64(2.0)
    prof = np.array(START)
    for name, out in _all_public_outputs(sc, prof).items():
        _only_plain_types(out, name)
        json.dumps(out)
    assert g.is_nash(prof, sc) == g.is_nash(START, SC)


def test_I01_numpy_matrices_and_arrays_are_accepted_as_scenario_fields():
    np = pytest.importorskip("numpy")
    sc = dict(SC, pref=np.array(SC["pref"]), w=np.array(SC["w"]), students=np.array(SC["students"]),
              projects=np.array(SC["projects"]), gamma=np.int64(SC["gamma"]))
    assert g.validate_scenario(sc) is None
    assert g.is_nash(START, sc) == g.is_nash(START, SC)
    assert g.enumerate_equilibria(sc) == g.enumerate_equilibria(SC)
    with pytest.raises(g.ScenarioError, match="8 rows"):
        g.validate_scenario(dict(SC, pref=np.array(SC["pref"])[:5]))  # wrong shape is still rejected


def test_I01_pandas_frames_and_series_are_accepted_as_scenario_fields():
    pd = pytest.importorskip("pandas")
    sc = dict(SC, pref=pd.DataFrame(SC["pref"]), w=pd.DataFrame(SC["w"]), students=pd.Series(SC["students"]),
              projects=pd.Series(SC["projects"]))
    assert g.validate_scenario(sc) is None
    assert g.is_nash(START, sc) == g.is_nash(START, SC)
    edited = pd.DataFrame(SC["pref"]).astype(float)  # a float column, as st.data_editor hands back after an edit
    edited.iloc[0, 0] = 9.5
    assert g.utility(0, [0] * 8, dict(SC, pref=edited)) == g.utility(0, [0] * 8, SC) + 1.5
    for name, out in _all_public_outputs(sc, START).items():
        _only_plain_types(out, name)


def test_I05_build_report_rejects_bad_run_counts():
    for bad in (0, -1, 1.5, True, None):
        with pytest.raises(g.StratosError, match="n_seeds"):
            g.build_report(sd.get_tiny_scenario(), n_seeds=bad, timing_runs=1)
        with pytest.raises(g.StratosError, match="timing_runs"):
            g.build_report(sd.get_tiny_scenario(), n_seeds=1, timing_runs=bad)


def test_I05_build_report_on_a_custom_scenario_omits_the_fixed_demo_section():
    report = g.build_report(sd.get_tiny_scenario(), n_seeds=3, timing_runs=1)
    assert report["demo"] is None and report["enumeration"]["n_profiles"] == 4
    json.dumps(report)


# ---------------------------------------------------------------------------------------------- I-02
def test_I02_schema_of_each_function_matches_interface_md():
    out = _all_public_outputs(SC, START)
    n, m = 8, 3
    assert isinstance(g.INTERFACE_VERSION, str) and g.INTERFACE_VERSION == "1.0"
    assert len(out["utilities"]) == n and all(isinstance(u, (int, float)) for u in out["utilities"])
    assert len(out["teams"]) == m and all(isinstance(t, list) for t in out["teams"])
    assert set(out["best_response"]) == {"student", "current", "best", "improves", "options"}
    assert [o["project"] for o in out["best_response"]["options"]] == [0, 1, 2]
    assert all(set(o) == {"project", "utility"} for o in out["best_response"]["options"])
    dev_keys = {"student", "from_project", "to_project", "current_utility", "new_utility", "gain"}
    assert out["profitable_deviations"] and all(set(d) == dev_keys for d in out["profitable_deviations"])
    assert [(d["student"], d["to_project"]) for d in out["profitable_deviations"]] == sorted(
        (d["student"], d["to_project"]) for d in out["profitable_deviations"])
    assert set(out["is_nash"]) == {"is_nash", "utilities", "deviations"} and isinstance(out["is_nash"]["is_nash"], bool)
    assert len(out["random_profile"]) == n and all(0 <= t < m for t in out["random_profile"])
    for key in ("dynamics_rr", "dynamics_random"):
        run = out[key]
        assert {"converged", "rounds", "start_profile", "final_profile", "steps", "is_nash_final"} <= set(run)
        assert isinstance(run["converged"], bool) and isinstance(run["is_nash_final"], bool)
        assert isinstance(run["rounds"], int) and run["steps"]
        step_keys = {"step", "round", "student", "from_project", "to_project", "gain", "profile", "potential",
                     "welfare"}
        assert all(step_keys <= set(s) for s in run["steps"])
    enum = out["enumerate"]
    assert {"n_profiles", "equilibria", "optimal", "welfare_gap_best_equilibrium", "welfare_gap_worst_equilibrium",
            "price_of_anarchy", "price_of_stability"} <= set(enum)
    assert enum["n_profiles"] == 6561
    assert all({"profile", "utilities", "welfare", "potential", "pareto_optimal"} <= set(e)
               for e in enum["equilibria"])
    assert {"profile", "welfare"} <= set(enum["optimal"])
    assert out["generic"] == []


def test_I02_cli_report_schema():
    report = _run_cli("--report", "--seeds", "5", "--timing-runs", "1")
    assert {"note", "meta", "scenario", "enumeration", "dynamics_summary", "demo"} <= set(report)
    assert set(report["dynamics_summary"]) == {"round_robin", "random"}
    assert report["meta"]["interface_version"] == g.INTERFACE_VERSION


# ---------------------------------------------------------------------------------------------- I-03
BAD_CALLS = [
    ("validate_scenario", lambda: g.validate_scenario({"students": ["a"]}), g.ScenarioError, "projects"),
    ("asymmetric", lambda: g.utilities([0, 0], dict(sd.get_tiny_scenario(), w=[[0, 1], [2, 0]])), g.ScenarioError,
     "symmetric"),
    ("profile length", lambda: g.utilities([0], sd.get_tiny_scenario()), g.ProfileError, "2 entries"),
    ("profile range", lambda: g.is_nash([0, 9], sd.get_tiny_scenario()), g.ProfileError, "out of range"),
    ("profile type", lambda: g.teams("01", sd.get_tiny_scenario()), g.ProfileError, "list"),
    ("student index", lambda: g.best_response(7, [0, 0], sd.get_tiny_scenario()), g.StratosError, "student index"),
    ("order", lambda: g.best_response_dynamics(sd.get_tiny_scenario(), [0, 0], order="x"), g.StratosError, "order"),
    ("max_rounds", lambda: g.best_response_dynamics(sd.get_tiny_scenario(), [0, 0], max_rounds=0), g.StratosError,
     "max_rounds"),
    ("enumeration limit", lambda: g.enumerate_equilibria(sd.get_tiny_scenario(), max_profiles=1), g.StratosError,
     "limit"),
]


@pytest.mark.parametrize("label,call,exc,fragment", BAD_CALLS, ids=[c[0] for c in BAD_CALLS])
def test_I03_invalid_input_raises_informative_stratos_errors(label, call, exc, fragment):
    with pytest.raises(exc, match=fragment) as info:
        call()
    assert isinstance(info.value, g.StratosError) and isinstance(info.value, ValueError)


def test_I03_ui_can_catch_one_base_class_for_everything():
    caught = 0
    for _, call, _, _ in BAD_CALLS:
        try:
            call()
        except g.StratosError:
            caught += 1
    assert caught == len(BAD_CALLS)


# ---------------------------------------------------------------------------------------------- I-04
def test_I04_pandas_tables_can_be_built_directly_from_engine_output():
    pd = pytest.importorskip("pandas")
    run = g.best_response_dynamics(SC, START)
    steps = pd.DataFrame(run["steps"])
    assert len(steps) == len(run["steps"]) and {"student", "gain", "potential", "welfare"} <= set(steps.columns)
    table = pd.DataFrame({"student": SC["students"], "project": [SC["projects"][t] for t in run["final_profile"]],
                          "utility": g.utilities(run["final_profile"], SC)})
    assert len(table) == 8 and table["utility"].sum() == g.social_welfare(run["final_profile"], SC)
    devs = pd.DataFrame(g.profitable_deviations(START, SC))
    assert len(devs) >= 2 and (devs["gain"] > 0).all()
    eqs = pd.DataFrame(g.enumerate_equilibria(SC)["equilibria"])
    assert len(eqs) >= 1 and {"profile", "welfare", "pareto_optimal"} <= set(eqs.columns)


def test_I04_app_helpers_module_if_present_imports_cleanly():
    # app_helpers.py is owned by Harsh; skipped until it exists, then it must at least import against the engine.
    pytest.importorskip("app_helpers")


def test_I04_engine_has_no_ui_or_numpy_dependency():
    code = "import sys, game_engine, sample_data; bad = {'streamlit', 'numpy', 'pandas'} & set(sys.modules); " \
           "assert not bad, bad"
    done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


# ---------------------------------------------------------------------------------------------- I-05
def _run_cli(*args):
    done = subprocess.run([sys.executable, "game_engine.py", *args], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_I05_cli_report_is_valid_json_and_equals_the_library_result():
    report = _run_cli("--report", "--seeds", "20", "--timing-runs", "1")
    assert report["enumeration"] == g.enumerate_equilibria(sd.get_default_scenario())
    assert report["scenario"] == sd.get_default_scenario()
    assert report["meta"]["timing"]["n_profiles"] == 6561 and len(report["meta"]["timing"]["runs_seconds"]) == 1
    assert report["demo"]["start_profile"] == sd.get_demo_start_profile()
    assert report["demo"]["dynamics_round_robin"] == g.best_response_dynamics(SC, START)
    for order, summary in report["dynamics_summary"].items():
        assert summary["n_runs"] == 20 and summary["all_converged"] is True
        assert summary["all_final_profiles_pass_is_nash"] is True
        assert summary["all_final_profiles_in_enumerated_set"] is True
        assert sum(e["count"] for e in summary["endpoints"]) == 20


def test_I05_cli_gamma_override_and_out_file(tmp_path):
    out = tmp_path / "report.json"
    done = subprocess.run([sys.executable, "game_engine.py", "--report", "--gamma", "0", "--seeds", "3",
                           "--timing-runs", "1", "--out", str(out)], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout == ""
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["scenario"]["gamma"] == 0
    assert report["enumeration"] == g.enumerate_equilibria(dict(sd.get_default_scenario(), gamma=0))


def test_I05_cli_bad_seeds_and_unwritable_output_fail_cleanly(tmp_path):
    for args in (["--seeds", "0"], ["--seeds", "-4"], ["--timing-runs", "0"],
                 ["--out", str(tmp_path / "no_such_dir" / "r.json")]):
        done = subprocess.run([sys.executable, "game_engine.py", "--report", "--timing-runs", "1", *args],
                              cwd=ROOT, capture_output=True, text=True)
        assert done.returncode == 2 and done.stderr.startswith("error:") and "Traceback" not in done.stderr, args


def test_I05_cli_without_flags_prints_help_and_bad_gamma_fails_cleanly():
    done = subprocess.run([sys.executable, "game_engine.py"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0 and "--report" in done.stdout
    done = subprocess.run([sys.executable, "game_engine.py", "--report", "--gamma", "-1", "--timing-runs", "1"],
                          cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 2 and "gamma" in done.stderr and "Traceback" not in done.stderr


# ---------------------------------------------------------------------------------------------- I-06
def test_I06_saved_results_are_not_stale():
    """If docs/results/engine_report.json exists it must describe the current engine and data."""
    path = os.path.join(ROOT, "docs", "results", "engine_report.json")
    if not os.path.exists(path):
        pytest.skip("docs/results/engine_report.json not generated yet")
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    assert saved["scenario"] == sd.get_default_scenario(), "regenerate: python scripts/generate_results.py"
    assert saved["enumeration"] == g.enumerate_equilibria(sd.get_default_scenario()), \
        "regenerate: python scripts/generate_results.py"
    assert saved["meta"]["interface_version"] == g.INTERFACE_VERSION
    # the seeded dynamics summary and the demo trace are deterministic, so they must reproduce exactly too
    n_seeds = saved["dynamics_summary"]["round_robin"]["n_runs"]
    fresh = g.build_report(n_seeds=n_seeds, timing_runs=1)
    assert saved["dynamics_summary"] == fresh["dynamics_summary"], "regenerate: python scripts/generate_results.py"
    assert saved["demo"] == fresh["demo"], "regenerate: python scripts/generate_results.py"
