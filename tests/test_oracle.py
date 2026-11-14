"""Run the independent oracle (tests/oracle/independent_check.py) inside the suite.

The oracle recomputes the model from docs/MODEL.md with exact rational arithmetic and its own code paths, then diffs the
engine against it. These tests (1) require every oracle check to pass, (2) prove the oracle does not import the engine
unless asked to compare, and (3) prove the comparison is not vacuous by injecting engine bugs and requiring detection.
"""
import importlib.util
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORACLE = os.path.join(ROOT, "tests", "oracle", "independent_check.py")


@pytest.fixture(scope="module")
def oracle():
    spec = importlib.util.spec_from_file_location("independent_check", ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def full_report(oracle):
    rep = oracle.Report()
    oracle.selfchecks(rep)
    oracle.compare(rep)
    return rep


def test_O01_every_oracle_check_passes(full_report):
    assert full_report.failures == [], full_report.failures[:3]
    assert len(full_report.rows) > 400


def test_O02_hand_derived_tables_are_reproduced(full_report):
    rows = [r for r in full_report.rows if r["check"].startswith("hand-derived")]
    assert {r["scenario"] for r in rows} == {"tiny", "trio"} and all(r["ok"] for r in rows)


def test_O03_oracle_self_checks_run_without_importing_the_engine():
    code = ("import importlib.util,sys;"
            f"s=importlib.util.spec_from_file_location('o',r'{ORACLE}');m=importlib.util.module_from_spec(s);"
            "s.loader.exec_module(m);r=m.Report();m.selfchecks(r);"
            "assert not r.failures;"
            "assert not any(x in sys.modules for x in ('game_engine','sample_data','scenario_io')), 'engine imported'")
    done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=os.path.dirname(ORACLE))
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize("target,label", [
    ("social_welfare", "social welfare"),
    ("potential", "exact potential"),
    ("is_nash", "Nash classification"),
])
def test_O04_oracle_detects_injected_engine_bugs(oracle, monkeypatch, target, label):
    import game_engine as ge
    original = getattr(ge, target)

    def broken(*args, **kwargs):
        out = original(*args, **kwargs)
        if isinstance(out, dict):
            return dict(out, is_nash=not out["is_nash"])
        return out + 1

    monkeypatch.setattr(ge, target, broken)
    rep = oracle.Report()
    oracle.compare(rep, names={"tiny", "trio", "random-1"})
    assert rep.failures, f"oracle failed to notice a broken {label}"


def test_O04_oracle_detects_a_wrong_best_response_tiebreak(oracle, monkeypatch):
    import game_engine as ge
    original = ge.best_response_dynamics

    def broken(scenario, start, order="round_robin", seed=None, max_rounds=100):
        run = original(scenario, start, order, seed, max_rounds)
        run = dict(run, rounds=run["rounds"] + 1)
        return run

    monkeypatch.setattr(ge, "best_response_dynamics", broken)
    rep = oracle.Report()
    oracle.compare(rep, names={"tiny", "trio"})
    assert rep.failures
