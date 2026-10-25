"""Collect every fact the viva PDFs quote, from the repository and a fresh run of the engine (nothing typed by hand).

Environment variable STRATOS_TEST_PYTHON may point at a Python that has the application requirements installed; it is
used only to collect (not run) the pytest tests so that per-file counts are exact.
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)
import game_engine as ge  # noqa: E402
import sample_data as sd  # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def collect():
    F = {"root": ROOT}
    F["date"] = datetime.date.today().isoformat()
    F["commit"] = git("rev-parse", "HEAD")
    F["short"] = F["commit"][:7]
    F["branch"] = git("branch", "--show-current")
    dirty = [l for l in git("status", "--porcelain").splitlines()
             if l.strip() and not l[3:].replace("\\", "/").strip('"').startswith("deliverables/")]
    F["tree_clean_apart_from_pdfs"] = not dirty
    F["dirty_paths"] = dirty

    rep = json.load(open(os.path.join(ROOT, "docs", "results", "engine_report.json"), encoding="utf-8"))
    F["report"] = rep
    F["results_commit"] = rep["meta"]["git"]["commit"]
    F["results_note"] = rep["meta"]["git"]["note"]
    F["timing"] = rep["meta"]["timing"]
    pt = open(os.path.join(ROOT, "docs", "results", "pytest_output.txt"), encoding="utf-8").read()
    m = re.search(r"(\d+) passed(?:, (\d+) skipped)?(?:, (\d+) failed)? in ([\d.]+)s", pt)
    F["tests_passed"], F["tests_skipped"], F["tests_failed"], F["tests_secs"] = int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0), m.group(4)
    F["tests_commit"] = re.search(r"git commit: (\w+)", pt).group(1)
    F["tests_when"] = re.search(r"generated: (.+)", pt).group(1)
    cc = open(os.path.join(ROOT, "docs", "results", "independent_crosscheck_output.txt"), encoding="utf-8").read()
    F["crosscheck_identical"] = "comparison with game_engine: IDENTICAL" in cc
    F["crosscheck_text"] = cc

    wl = json.load(open(os.path.join(ROOT, "screenshots", "walkthrough_log.json"), encoding="utf-8"))
    F["n_shots"] = sum(1 for s in wl["steps"] if "file" in s)
    F["shots_all_matched"] = all(s["all_expected_values_found"] for s in wl["steps"] if "file" in s)
    F["shots_commit"] = wl["commit"]

    py = os.environ.get("STRATOS_TEST_PYTHON", sys.executable)
    out = subprocess.run([py, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True,
                         text=True, encoding="utf-8").stdout
    counts = collections.Counter(l.split("::")[0] for l in out.splitlines() if "::" in l)
    F["tests_per_file"] = dict(sorted(counts.items()))
    F["tests_collected"] = sum(counts.values())

    F["shortlog"] = git("shortlog", "-sne", "--all")
    F["log_by_author"] = {}
    for line in git("log", "--all", "--format=%h|%an|%ad|%s", "--date=short").splitlines():
        h, a, d, s = line.split("|", 3)
        F["log_by_author"].setdefault(a, []).append((h, d, s))

    # ---- scenario and engine facts, freshly computed -------------------------------------------------------------
    sc = sd.get_default_scenario()
    F["sc"] = sc
    S, Pn = sc["students"], sc["projects"]
    F["n"], F["m"] = len(S), len(Pn)
    enum = ge.enumerate_equilibria(sc)
    F["enum"] = enum
    F["eq_sorted"] = sorted(enum["equilibria"], key=lambda e: (-e["welfare"], e["profile"]))
    F["demo_start"] = sd.get_demo_start_profile()
    F["demo_check"] = ge.is_nash(F["demo_start"], sc)
    F["demo_rr"] = ge.best_response_dynamics(sc, F["demo_start"])
    F["demo_rand7"] = ge.best_response_dynamics(sc, F["demo_start"], order="random", seed=7)
    F["worst_eq"] = min(enum["equilibria"], key=lambda e: (e["welfare"], e["profile"]))
    F["opt_profiles"] = enum["optimal_profiles"]
    F["opt_is_eq"] = [any(e["profile"] == p for e in enum["equilibria"]) for p in F["opt_profiles"]]
    F["n_pareto_eq"] = sum(1 for e in enum["equilibria"] if e["pareto_optimal"])
    F["reset_all0"] = {"profile": [0] * F["n"], "welfare": ge.social_welfare([0] * F["n"], sc), "potential": ge.potential([0] * F["n"], sc),
                       "check": ge.is_nash([0] * F["n"], sc)}
    tiny = sd.get_tiny_scenario()
    F["tiny"] = tiny
    F["tiny_table"] = {tuple(p): (ge.utilities(list(p), tiny), ge.social_welfare(list(p), tiny), ge.potential(list(p), tiny),
                                  ge.is_nash(list(p), tiny)["is_nash"]) for p in [(0, 0), (0, 1), (1, 0), (1, 1)]}
    F["gamma3"] = ge.enumerate_equilibria(dict(sc, gamma=3))
    return F


def utility_breakdown(sc, profile, i):
    """Explain u_i step by step using the scenario data only: returns dict of components."""
    t = profile[i]
    mates = [j for j in range(len(profile)) if j != i and profile[j] == t]
    size = len(mates) + 1
    compat = [(sc["students"][j], sc["w"][i][j]) for j in mates]
    crowd = sc["gamma"] * (size - 1) ** 2
    total = sc["pref"][i][t] + sum(w for _, w in compat) - crowd
    assert total == ge.utility(i, profile, sc)  # tie the hand arithmetic to the engine
    return {"pref": sc["pref"][i][t], "compat": compat, "size": size, "crowd": crowd, "total": total, "project": sc["projects"][t]}


if __name__ == "__main__":
    F = collect()
    for k in ("date", "commit", "branch", "tree_clean_apart_from_pdfs", "results_commit", "tests_passed", "tests_commit", "tests_per_file",
              "tests_collected", "n_pareto_eq", "crosscheck_identical"):
        print(k, "=", F[k])
