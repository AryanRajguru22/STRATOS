"""STRATOS game engine: a strategic team-formation game with exact pure-equilibrium analysis.

Model (see docs/MODEL.md): n students each choose one of m projects. Student i's utility in profile s is

    u_i(s) = pref[i][s_i] + sum_{j != i, s_j = s_i} w[i][j] - c(n_{s_i}(s)),      c(k) = gamma * (k - 1) ** 2

with symmetric compatibility w. The game is an exact potential game, so a pure Nash equilibrium exists and
best-response dynamics terminates; the code nevertheless checks the equilibrium condition directly and never
relies on that argument. All student data and weights shipped with the project are synthetic.

Interface contract: docs/INTERFACE.md. Every public function validates its inputs, never mutates them, never
prints, and returns plain JSON-serialisable values (dict, list, int, float, bool, str, None). The engine is
independent of Streamlit and of NumPy.

Command line:  python game_engine.py --report [--gamma G] [--seeds N] [--timing-runs N] [--out PATH]
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import numbers
import platform
import random
import statistics
import sys
import time
from typing import Any, Callable, Sequence

INTERFACE_VERSION = "1.0"
EPS = 1e-9
MAX_ENUMERATION_PROFILES = 100_000
VALID_ORDERS = ("round_robin", "random")


# ----------------------------------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------------------------------
class StratosError(ValueError):
    """Base class for every error the engine raises on bad input."""


class ScenarioError(StratosError):
    """The scenario dictionary is malformed or violates a model assumption."""


class ProfileError(StratosError):
    """The assignment (profile) is malformed or out of range."""


# ----------------------------------------------------------------------------------------------
# Validation and compilation
# ----------------------------------------------------------------------------------------------
def _num(x: Any, what: str, exc: type = ScenarioError):
    """Return x as a plain Python int/float; reject bool, strings, NaN and infinity."""
    if isinstance(x, bool) or not isinstance(x, numbers.Real):
        raise exc(f"{what} must be a number, got {x!r}")
    if isinstance(x, numbers.Integral):
        return int(x)
    f = float(x)
    if not math.isfinite(f):
        raise exc(f"{what} must be finite, got {x!r}")
    return f


def _as_list(value: Any) -> Any:
    """Convert NumPy arrays and pandas objects to nested lists, without importing NumPy or pandas."""
    if isinstance(value, (list, tuple)):
        return value
    if hasattr(value, "to_numpy"):  # pandas DataFrame / Series (e.g. from st.data_editor)
        value = value.to_numpy()
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def _names(value: Any, key: str, minimum: int) -> list:
    value = _as_list(value)
    if not isinstance(value, (list, tuple)):
        raise ScenarioError(f"'{key}' must be a list of names")
    if len(value) < minimum:
        raise ScenarioError(f"'{key}' needs at least {minimum} entries, got {len(value)}")
    out = []
    for idx, name in enumerate(value):
        if not isinstance(name, str) or not name.strip():
            raise ScenarioError(f"'{key}'[{idx}] must be a non-empty string, got {name!r}")
        out.append(name)
    if len(set(out)) != len(out):
        raise ScenarioError(f"'{key}' contains duplicate names")
    return out


def _matrix(value: Any, key: str, rows: int, cols: int) -> list:
    value = _as_list(value)
    if not isinstance(value, (list, tuple)) or len(value) != rows:
        got = len(value) if isinstance(value, (list, tuple)) else type(value).__name__
        raise ScenarioError(f"'{key}' must have {rows} rows, got {got}")
    out = []
    for i, row in enumerate(value):
        if not isinstance(row, (list, tuple)) or len(row) != cols:
            got = len(row) if isinstance(row, (list, tuple)) else type(row).__name__
            raise ScenarioError(f"'{key}'[{i}] must have {cols} entries, got {got}")
        out.append([_num(v, f"'{key}'[{i}][{j}]") for j, v in enumerate(row)])
    return out


class _Model:
    """Validated, normalised scenario used internally (plain Python numbers, precomputed crowding costs)."""

    __slots__ = ("n", "m", "students", "projects", "pref", "w", "gamma", "crowd")

    def __init__(self, students, projects, pref, w, gamma):
        self.n = len(students)
        self.m = len(projects)
        self.students = students
        self.projects = projects
        self.pref = pref
        self.w = w
        self.gamma = gamma
        # crowd[k] = c(k) for k = 1..n; index 0 is unused
        self.crowd = [0] + [gamma * (k - 1) ** 2 for k in range(1, self.n + 1)]


def _compile(scenario: Any) -> _Model:
    if not isinstance(scenario, dict):
        raise ScenarioError(f"scenario must be a dict, got {type(scenario).__name__}")
    for key in ("students", "projects", "pref", "w", "gamma"):
        if key not in scenario:
            raise ScenarioError(f"scenario is missing required key '{key}'")
    students = _names(scenario["students"], "students", 1)
    projects = _names(scenario["projects"], "projects", 2)
    n, m = len(students), len(projects)
    pref = _matrix(scenario["pref"], "pref", n, m)
    w = _matrix(scenario["w"], "w", n, n)
    for i in range(n):
        if abs(w[i][i]) > EPS:
            raise ScenarioError(f"'w' must have a zero diagonal, but w[{i}][{i}] = {w[i][i]}")
        for j in range(i + 1, n):
            if abs(w[i][j] - w[j][i]) > EPS:
                raise ScenarioError(f"'w' must be symmetric, but w[{i}][{j}] = {w[i][j]} and w[{j}][{i}] = {w[j][i]}")
    gamma = _num(scenario["gamma"], "'gamma'")
    if gamma < 0:
        raise ScenarioError(f"'gamma' must be >= 0, got {gamma}")
    skills = scenario.get("skills")
    if skills is not None:
        if not isinstance(skills, dict):
            raise ScenarioError("'skills' must be a dict mapping student name to a list of skill names")
        for name, lst in skills.items():
            if name not in students:
                raise ScenarioError(f"'skills' names unknown student {name!r}")
            if not isinstance(lst, (list, tuple)) or not all(isinstance(x, str) for x in lst):
                raise ScenarioError(f"'skills'[{name!r}] must be a list of strings")
    return _Model(students, projects, pref, w, gamma)


def _profile(profile: Any, M: _Model) -> list:
    profile = _as_list(profile)
    if not isinstance(profile, (list, tuple)):
        raise ProfileError(f"profile must be a list of project indices, got {type(profile).__name__}")
    if len(profile) != M.n:
        raise ProfileError(f"profile must have {M.n} entries (one per student), got {len(profile)}")
    out = []
    for i, t in enumerate(profile):
        if isinstance(t, bool) or not isinstance(t, numbers.Integral):
            raise ProfileError(f"profile[{i}] must be an integer project index, got {t!r}")
        t = int(t)
        if not 0 <= t < M.m:
            raise ProfileError(f"profile[{i}] = {t} is out of range 0..{M.m - 1}")
        out.append(t)
    return out


def _student(i: Any, M: _Model) -> int:
    if isinstance(i, bool) or not isinstance(i, numbers.Integral) or not 0 <= int(i) < M.n:
        raise StratosError(f"student index must be an integer in 0..{M.n - 1}, got {i!r}")
    return int(i)


def _seed(seed: Any) -> None:
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, numbers.Integral)):
        raise StratosError(f"seed must be an integer or None, got {seed!r}")


def validate_scenario(scenario: Any) -> None:
    """Raise ScenarioError unless the scenario satisfies every model assumption; return None otherwise."""
    _compile(scenario)


def validate_profile(profile: Any, scenario: Any) -> None:
    """Raise ProfileError unless profile is a valid assignment for the scenario; return None otherwise."""
    _profile(profile, _compile(scenario))


# ----------------------------------------------------------------------------------------------
# Core payoff functions (internal, no validation; take a compiled model and a clean profile)
# ----------------------------------------------------------------------------------------------
def _u_with(M: _Model, s: Sequence[int], i: int, t: int):
    """Utility of student i if i chose project t while all others keep their choices in s."""
    wi = M.w[i]
    others = 0
    compat = 0
    for j in range(M.n):
        if j != i and s[j] == t:
            others += 1
            compat += wi[j]
    return M.pref[i][t] + compat - M.crowd[others + 1]


def _utilities(M: _Model, s: Sequence[int]) -> list:
    return [_u_with(M, s, i, s[i]) for i in range(M.n)]


def _potential(M: _Model, s: Sequence[int]):
    total = sum(M.pref[i][s[i]] for i in range(M.n))
    counts = [0] * M.m
    for i in range(M.n):
        counts[s[i]] += 1
        for j in range(i + 1, M.n):
            if s[i] == s[j]:
                total += M.w[i][j]
    for size in counts:
        for k in range(1, size + 1):
            total -= M.crowd[k]
    return total


def _deviations(M: _Model, s: Sequence[int], utils: Sequence) -> list:
    out = []
    for i in range(M.n):
        for t in range(M.m):
            if t == s[i]:
                continue
            new = _u_with(M, s, i, t)
            if new > utils[i] + EPS:
                out.append({"student": i, "from_project": s[i], "to_project": t,
                            "current_utility": utils[i], "new_utility": new, "gain": new - utils[i]})
    return out


def _has_deviation(M: _Model, s: Sequence[int], utils: Sequence) -> bool:
    for i in range(M.n):
        for t in range(M.m):
            if t != s[i] and _u_with(M, s, i, t) > utils[i] + EPS:
                return True
    return False


def _best_move(M: _Model, s: Sequence[int], i: int):
    """Return (best_project, best_utility, current_utility). Stay if the current project is already a best response;
    otherwise the lowest-index maximiser."""
    opts = [_u_with(M, s, i, t) for t in range(M.m)]
    top = max(opts)
    cur = opts[s[i]]
    if cur >= top - EPS:
        return s[i], cur, cur
    best = next(t for t in range(M.m) if opts[t] >= top - EPS)
    return best, opts[best], cur


# ----------------------------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------------------------
def crowding_cost(k: int, scenario: Any):
    """c(k) = gamma * (k - 1) ** 2 for a team of size k >= 1."""
    M = _compile(scenario)
    if isinstance(k, bool) or not isinstance(k, numbers.Integral) or int(k) < 1:
        raise StratosError(f"team size k must be an integer >= 1, got {k!r}")
    return M.gamma * (int(k) - 1) ** 2


def utility(i: int, profile: Sequence[int], scenario: Any):
    """u_i(s): preference + compatibility with teammates on the same project - crowding cost."""
    M = _compile(scenario)
    s = _profile(profile, M)
    i = _student(i, M)
    return _u_with(M, s, i, s[i])


def utilities(profile: Sequence[int], scenario: Any) -> list:
    """List of u_i(s) for every student."""
    M = _compile(scenario)
    return _utilities(M, _profile(profile, M))


def social_welfare(profile: Sequence[int], scenario: Any):
    """W(s) = sum of all students' utilities."""
    M = _compile(scenario)
    return sum(_utilities(M, _profile(profile, M)))


def potential(profile: Sequence[int], scenario: Any):
    """Exact potential Phi(s). A unilateral deviation changes Phi by exactly the deviator's utility change."""
    M = _compile(scenario)
    return _potential(M, _profile(profile, M))


def teams(profile: Sequence[int], scenario: Any) -> list:
    """teams[t] = ascending student indices currently on project t (empty list for an empty team)."""
    M = _compile(scenario)
    s = _profile(profile, M)
    return [[i for i in range(M.n) if s[i] == t] for t in range(M.m)]


def best_response(i: int, profile: Sequence[int], scenario: Any) -> dict:
    """Student i's utility for every project, holding the others fixed.

    'best' is the current project if it already maximises utility (within EPS); otherwise the lowest-index
    maximiser. 'improves' is True exactly when moving to 'best' is a strictly profitable deviation.
    """
    M = _compile(scenario)
    s = _profile(profile, M)
    i = _student(i, M)
    best, best_u, cur = _best_move(M, s, i)
    return {"student": i, "current": s[i], "best": best, "improves": best_u > cur + EPS,
            "options": [{"project": t, "utility": _u_with(M, s, i, t)} for t in range(M.m)]}


def profitable_deviations(profile: Sequence[int], scenario: Any) -> list:
    """Every strictly profitable unilateral deviation, sorted by student then target project."""
    M = _compile(scenario)
    s = _profile(profile, M)
    return _deviations(M, s, _utilities(M, s))


def is_nash(profile: Sequence[int], scenario: Any) -> dict:
    """Check the pure Nash condition by testing every unilateral deviation of every student."""
    M = _compile(scenario)
    s = _profile(profile, M)
    utils = _utilities(M, s)
    devs = _deviations(M, s, utils)
    return {"is_nash": not devs, "utilities": utils, "deviations": devs}


def random_profile(scenario: Any, seed: int | None = None) -> list:
    """Seeded uniformly random assignment."""
    M = _compile(scenario)
    _seed(seed)
    rng = random.Random(seed)
    return [rng.randrange(M.m) for _ in range(M.n)]


def best_response_dynamics(scenario: Any, start: Sequence[int], order: str = "round_robin",
                           seed: int | None = None, max_rounds: int = 100) -> dict:
    """Sequential best-response dynamics from 'start'.

    Each sweep visits every student once (ascending index for 'round_robin'; a seeded random permutation per
    sweep for 'random'). A student moves only for a strictly positive gain, to the lowest-index maximiser.
    'converged' means a full sweep produced no move; 'is_nash_final' is a fresh, independent equilibrium check
    of the final profile. 'rounds' counts sweeps including the final no-change sweep.
    """
    M = _compile(scenario)
    s = _profile(start, M)
    _seed(seed)
    if order not in VALID_ORDERS:
        raise StratosError(f"order must be one of {VALID_ORDERS}, got {order!r}")
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, numbers.Integral) or int(max_rounds) < 1:
        raise StratosError(f"max_rounds must be an integer >= 1, got {max_rounds!r}")
    rng = random.Random(seed)
    start_profile = list(s)
    steps: list = []
    converged = False
    rounds = 0
    for rnd in range(1, int(max_rounds) + 1):
        rounds = rnd
        visit = list(range(M.n))
        if order == "random":
            rng.shuffle(visit)
        changed = False
        for i in visit:
            best, best_u, cur = _best_move(M, s, i)
            if best_u > cur + EPS:
                origin = s[i]
                s[i] = best
                changed = True
                utils_now = _utilities(M, s)
                steps.append({"step": len(steps) + 1, "round": rnd, "student": i, "from_project": origin,
                              "to_project": best, "gain": best_u - cur, "profile": list(s),
                              "utilities": utils_now, "potential": _potential(M, s), "welfare": sum(utils_now)})
        if not changed:
            converged = True
            break
    final_utils = _utilities(M, s)
    return {"converged": converged, "rounds": rounds, "start_profile": start_profile, "final_profile": list(s),
            "steps": steps, "is_nash_final": not _has_deviation(M, s, final_utils)}


def pure_nash_equilibria(strategy_counts: Sequence[int], payoff_fn: Callable[[tuple], Sequence]) -> list:
    """Generic exhaustive pure-Nash finder for any finite normal-form game.

    strategy_counts[p] is the number of strategies of player p; payoff_fn(profile_tuple) returns the payoff of
    every player. Returns every profile (as a list) from which no player gains by deviating; [] if none exists.
    """
    if not isinstance(strategy_counts, (list, tuple)) or not strategy_counts:
        raise StratosError("strategy_counts must be a non-empty list of positive integers")
    for p, c in enumerate(strategy_counts):
        if isinstance(c, bool) or not isinstance(c, numbers.Integral) or int(c) < 1:
            raise StratosError(f"strategy_counts[{p}] must be an integer >= 1, got {c!r}")
    counts = [int(c) for c in strategy_counts]
    players = len(counts)

    def pay(profile):
        out = payoff_fn(tuple(profile))
        if len(out) != players:
            raise StratosError(f"payoff_fn must return {players} payoffs, got {len(out)}")
        return out

    found = []
    for prof in itertools.product(*[range(c) for c in counts]):
        base = pay(prof)
        stable = True
        for p in range(players):
            for alt in range(counts[p]):
                if alt == prof[p]:
                    continue
                dev = list(prof)
                dev[p] = alt
                if pay(dev)[p] > base[p] + EPS:
                    stable = False
                    break
            if not stable:
                break
        if stable:
            found.append(list(prof))
    return found


def enumerate_equilibria(scenario: Any, with_analysis: bool = True,
                         max_profiles: int = MAX_ENUMERATION_PROFILES) -> dict:
    """Exhaustively enumerate all m**n profiles.

    Returns every pure Nash equilibrium, the welfare-maximising profile, welfare gaps, price of anarchy / stability
    (only when every equilibrium welfare is strictly positive), and, if with_analysis, a Pareto flag per equilibrium.
    With with_analysis=False the Pareto flags and both ratios are null; everything else is still computed.
    Also reports the potential maximisers and whether each really passes the equilibrium check.
    """
    M = _compile(scenario)
    total = M.m ** M.n
    if total > max_profiles:
        raise StratosError(f"{M.m}^{M.n} = {total} profiles exceeds the enumeration limit of {max_profiles}")
    profiles = list(itertools.product(range(M.m), repeat=M.n))
    utils_all = [_utilities(M, p) for p in profiles]
    welfare_all = [sum(u) for u in utils_all]
    pot_all = [_potential(M, p) for p in profiles]
    eq_idx = [k for k, p in enumerate(profiles) if not _has_deviation(M, p, utils_all[k])]
    eq_lookup = set(eq_idx)

    w_max = max(welfare_all)
    opt_idx = [k for k, v in enumerate(welfare_all) if v >= w_max - EPS]
    phi_max = max(pot_all)
    phi_idx = [k for k, v in enumerate(pot_all) if v >= phi_max - EPS]

    def pareto_optimal(k: int) -> bool:
        u = utils_all[k]
        for q, v in enumerate(utils_all):
            if q != k and all(v[i] >= u[i] - EPS for i in range(M.n)) and any(v[i] > u[i] + EPS for i in range(M.n)):
                return False
        return True

    equilibria = [{"profile": list(profiles[k]), "utilities": utils_all[k], "welfare": welfare_all[k],
                   "potential": pot_all[k], "pareto_optimal": pareto_optimal(k) if with_analysis else None}
                  for k in eq_idx]
    eq_w = [welfare_all[k] for k in eq_idx]
    gap_best = gap_worst = poa = pos = None
    if eq_w:
        gap_best = w_max - max(eq_w)
        gap_worst = w_max - min(eq_w)
        if with_analysis and min(eq_w) > EPS and w_max > EPS:
            poa = w_max / min(eq_w)
            pos = w_max / max(eq_w)
    return {
        "n_profiles": total,
        "n_equilibria": len(equilibria),
        "equilibria": equilibria,
        "optimal": {"profile": list(profiles[opt_idx[0]]), "welfare": welfare_all[opt_idx[0]],
                    "utilities": utils_all[opt_idx[0]]},
        "optimal_profiles": [list(profiles[k]) for k in opt_idx],
        "welfare_gap_best_equilibrium": gap_best,
        "welfare_gap_worst_equilibrium": gap_worst,
        "price_of_anarchy": poa,
        "price_of_stability": pos,
        "potential_maximizers": {
            "potential": pot_all[phi_idx[0]],
            "profiles": [list(profiles[k]) for k in phi_idx],
            "all_are_equilibria": all(k in eq_lookup for k in phi_idx),
        },
    }


# ----------------------------------------------------------------------------------------------
# Command-line report
# ----------------------------------------------------------------------------------------------
def build_report(scenario: dict | None = None, n_seeds: int = 200, timing_runs: int = 5) -> dict:
    """Compute the full evidence report for a scenario (default: sample_data.get_default_scenario())."""
    import sample_data  # local import keeps the engine itself independent of the data module

    for name, val in (("n_seeds", n_seeds), ("timing_runs", timing_runs)):
        if isinstance(val, bool) or not isinstance(val, numbers.Integral) or int(val) < 1:
            raise StratosError(f"{name} must be an integer >= 1, got {val!r}")
    if scenario is None:
        scenario = sample_data.get_default_scenario()
    M = _compile(scenario)
    runs = []
    result = None
    for _ in range(int(timing_runs)):
        t0 = time.perf_counter()
        result = enumerate_equilibria(scenario)
        runs.append(time.perf_counter() - t0)
    eq_set = {tuple(e["profile"]) for e in result["equilibria"]}

    dynamics = {}
    for order in VALID_ORDERS:
        endpoints: dict = {}
        steps_n, rounds_n, all_conv, all_nash, all_in_set = [], [], True, True, True
        for seed in range(n_seeds):
            run = best_response_dynamics(scenario, random_profile(scenario, seed), order=order, seed=seed)
            key = tuple(run["final_profile"])
            endpoints[key] = endpoints.get(key, 0) + 1
            steps_n.append(len(run["steps"]))
            rounds_n.append(run["rounds"])
            all_conv &= run["converged"]
            all_nash &= run["is_nash_final"]
            all_in_set &= key in eq_set
        dynamics[order] = {
            "n_runs": n_seeds, "seeds": f"0..{n_seeds - 1}", "all_converged": all_conv,
            "all_final_profiles_pass_is_nash": all_nash, "all_final_profiles_in_enumerated_set": all_in_set,
            "steps_min": min(steps_n), "steps_mean": round(statistics.fmean(steps_n), 4), "steps_max": max(steps_n),
            "rounds_max": max(rounds_n),
            "endpoints": [{"profile": list(k), "count": v} for k, v in sorted(endpoints.items())],
        }

    demo = None
    demo_start = sample_data.get_demo_start_profile()
    if len(demo_start) == M.n and all(0 <= t < M.m for t in demo_start):  # the fixed demo start fits the default size only
        demo = {"start_profile": demo_start, "equilibrium_check": is_nash(demo_start, scenario),
                "dynamics_round_robin": best_response_dynamics(scenario, demo_start)}
    return {
        "note": "All student data and model weights are fictional and synthetic; chosen to make strategic behaviour visible.",
        "meta": {"interface_version": INTERFACE_VERSION, "command": "python game_engine.py --report",
                 "python": platform.python_version(), "platform": platform.platform(),
                 "timing": {"what": "enumerate_equilibria(default scenario, with_analysis=True), wall clock, perf_counter",
                            "n_profiles": M.m ** M.n, "runs_seconds": [round(r, 4) for r in runs],
                            "min_seconds": round(min(runs), 4), "median_seconds": round(statistics.median(runs), 4)}},
        "scenario": scenario,
        "enumeration": result,
        "dynamics_summary": dynamics,
        "demo": demo,
    }


def _main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="STRATOS game engine command-line report.")
    ap.add_argument("--report", action="store_true", help="print the JSON evidence report for the default scenario")
    ap.add_argument("--gamma", type=float, default=None, help="override the crowding parameter gamma")
    ap.add_argument("--seeds", type=int, default=200, help="number of seeded random starts per update order")
    ap.add_argument("--timing-runs", type=int, default=5, help="repetitions of the timed enumeration")
    ap.add_argument("--out", default=None, help="write the JSON to this UTF-8 file instead of stdout")
    args = ap.parse_args(argv)
    if not args.report:
        ap.print_help()
        return 0
    import sample_data

    scenario = sample_data.get_default_scenario()
    if args.gamma is not None:
        scenario["gamma"] = int(args.gamma) if float(args.gamma).is_integer() else args.gamma
    try:
        report = build_report(scenario, n_seeds=args.seeds, timing_runs=args.timing_runs)
    except StratosError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2)
    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write(text + "\n")
        except OSError as exc:
            print(f"error: cannot write {args.out}: {exc}", file=sys.stderr)
            return 2
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
