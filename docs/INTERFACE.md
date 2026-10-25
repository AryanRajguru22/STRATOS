# STRATOS engine <-> app interface contract (v1.0)

Owner: Aryan Rajguru (engine). Consumer: Harsh's Streamlit app (`app.py`, `app_helpers.py`).
Implemented by `game_engine.py` and `sample_data.py`; verified by `tests/test_integration.py`.
The engine exposes `game_engine.INTERFACE_VERSION == "1.0"`. **Do not change a signature or return key without
all three members agreeing and bumping this document.** Additive keys (marked *additive* below) may be ignored.

Model definitions are in [`MODEL.md`](MODEL.md). All data is fictional and synthetic.

## 1. Conventions

* All indices are **0-based**: students `0..n-1`, projects `0..m-1`. The UI maps indices to names with
  `scenario["students"][i]` and `scenario["projects"][t]`.
* A **profile** is a list of `n` ints; `profile[i]` is student `i`'s project. Tuples and NumPy arrays are accepted
  as input and converted; outputs are always `list`.
* Inputs are never mutated. Nothing is printed. Outputs are plain Python `dict` / `list` / `int` / `float` / `bool` /
  `str` / `None`: no tuples, no NumPy types, no custom classes (so `json.dumps` always works).
* Numbers: `int` stays `int`, otherwise `float`. Comparisons use `EPS = 1e-9`. Integers are recommended.
* Deterministic: the same inputs and the same `seed` give identical outputs.
* The engine does not import Streamlit, NumPy or pandas.

## 2. Input schemas

```python
scenario = {
    "students": ["Asha", "Bram", ...],      # list[str], n >= 1, non-empty, unique
    "projects": ["Campus ...", ...],         # list[str], m >= 2, non-empty, unique
    "pref":     [[8, 6, 2], ...],            # n x m numbers
    "w":        [[0, 2, ...], ...],          # n x n numbers, symmetric (tolerance EPS), zero diagonal
    "gamma":    2,                           # number >= 0;  c(k) = gamma * (k - 1) ** 2
    "skills":   {"Asha": ["Analysis"], ...}  # OPTIONAL display metadata; validated but ignored by the engine
}
profile = [0, 1, 2, 0, 1, 2, 0, 1]           # list[int], len n, each 0..m-1
```

Booleans, strings, `None`, `NaN` and infinities are rejected where numbers are expected.

## 3. Errors

```
StratosError(ValueError)        base class: catch this in the UI
 |- ScenarioError               malformed scenario or violated model assumption
 |- ProfileError                malformed or out-of-range profile
```

Messages name the offending field and index, e.g. `'w' must be symmetric, but w[0][1] = 5 and w[1][0] = 2`.
Bad *other* arguments (student index, `seed`, `order`, `max_rounds`, team size `k`, `max_profiles`, generic game
arguments) raise plain `StratosError`. The UI should wrap engine calls like this:

```python
try:
    result = game_engine.is_nash(profile, scenario)
except game_engine.StratosError as exc:
    st.error(str(exc))
```

## 4. Functions (module `game_engine`)

| Function | Returns | Notes |
|---|---|---|
| `validate_scenario(scenario)` | `None` | raises `ScenarioError` |
| `validate_profile(profile, scenario)` | `None` | raises `ProfileError` |
| `crowding_cost(k, scenario)` | number | `gamma * (k-1)**2`; `k` int `>= 1` |
| `utility(i, profile, scenario)` | number | `u_i(s)` |
| `utilities(profile, scenario)` | `list[number]` | `u_i(s)` for all `i` |
| `social_welfare(profile, scenario)` | number | sum of utilities |
| `potential(profile, scenario)` | number | exact potential `Phi(s)` |
| `teams(profile, scenario)` | `list[list[int]]` | `teams[t]` = ascending student indices on project `t`; may be `[]` |
| `best_response(i, profile, scenario)` | dict | see 4.1 |
| `profitable_deviations(profile, scenario)` | `list[dict]` | see 4.2 |
| `is_nash(profile, scenario)` | dict | see 4.3 |
| `random_profile(scenario, seed=None)` | `list[int]` | seeded random assignment |
| `best_response_dynamics(scenario, start, order="round_robin", seed=None, max_rounds=100)` | dict | see 4.4 |
| `enumerate_equilibria(scenario, with_analysis=True, max_profiles=100000)` | dict | see 4.5 |
| `pure_nash_equilibria(strategy_counts, payoff_fn)` | `list[list[int]]` | generic finite game; see 4.6 |
| `build_report(scenario=None, n_seeds=200, timing_runs=5)` | dict | what the CLI prints; see 6. The `demo` section is `None` unless the scenario has the default size (the fixed demo start is 8 students) |

`sample_data`: `get_default_scenario()` (8 students, 3 projects, `gamma = 2`; fresh dict each call),
`get_tiny_scenario()` (2 x 2 hand example), `get_demo_start_profile()` (fixed unstable start for the live demo; *additive*),
constants `SYNTHETIC_DATA_NOTICE`, `DEFAULT_GAMMA`.

### 4.1 `best_response`

```python
{"student": 1, "current": 0, "best": 1, "improves": True,
 "options": [{"project": 0, "utility": 2}, {"project": 1, "utility": 5}]}
```

`options` has one entry per project, in project order. `best` is the current project when it is already a best
response; otherwise the lowest-index maximiser. `improves` is `True` exactly when moving to `best` is a strictly
profitable deviation.

### 4.2 `profitable_deviations`

A list (empty at an equilibrium) of every strictly profitable single-student switch, sorted by `student` then
`to_project`:

```python
{"student": 1, "from_project": 0, "to_project": 1, "current_utility": 2, "new_utility": 5, "gain": 3}
```

### 4.3 `is_nash`

```python
{"is_nash": False, "utilities": [6, 2], "deviations": [<4.2 items>]}
```

`is_nash` is `True` iff `deviations` is empty. This is the function to use for any "stable" claim.

### 4.4 `best_response_dynamics`

`order` is `"round_robin"` (ascending index each sweep) or `"random"` (seeded permutation each sweep). A student moves
only for a strictly positive gain, to the lowest-index maximiser.

```python
{"converged": True,            # a full sweep produced no move
 "rounds": 2,                  # sweeps performed, including the final no-move sweep (== max_rounds if not converged)
 "start_profile": [0, 0],
 "final_profile": [0, 1],
 "is_nash_final": True,        # FRESH equilibrium check of final_profile; use this, not "converged", to claim stability
 "steps": [                    # one entry per move, in order; [] if the start was already an equilibrium
   {"step": 1, "round": 1, "student": 1, "from_project": 0, "to_project": 1, "gain": 3,
    "profile": [0, 1],         # profile AFTER the move
    "utilities": [5, 5],       # additive: utilities after the move
    "potential": 10, "welfare": 10}]}
```

If `max_rounds` is exhausted, `converged` is `False` even if the profile happens to be stable; `is_nash_final`
still tells the truth. For this model the dynamics always terminates, but the UI must still show "not converged"
if it ever reports `False`.

### 4.5 `enumerate_equilibria`

Evaluates all `m**n` profiles; raises `StratosError` if `m**n > max_profiles` (limit: 100,000, i.e. up to about 10
students with 3 projects).

```python
{"n_profiles": 4,
 "equilibria": [                                   # every pure Nash equilibrium, in lexicographic profile order; may be []
   {"profile": [0, 1], "utilities": [5, 5], "welfare": 10, "potential": 10,
    "pareto_optimal": True}],                      # None when with_analysis=False
 "optimal": {"profile": [0, 1], "welfare": 10,     # welfare maximiser (lexicographically first if tied)
             "utilities": [5, 5]},                 # utilities: additive
 "welfare_gap_best_equilibrium": 0,                # W_opt - max equilibrium welfare; None if there is no equilibrium
 "welfare_gap_worst_equilibrium": 0,               # W_opt - min equilibrium welfare; None if there is no equilibrium
 "price_of_anarchy": 1.0,                          # W_opt / min equilibrium welfare; None unless all welfare > 0
 "price_of_stability": 1.0,                        # W_opt / max equilibrium welfare; None unless all welfare > 0
 # additive keys:
 "n_equilibria": 1,
 "optimal_profiles": [[0, 1]],                     # every welfare maximiser (ties)
 "potential_maximizers": {"potential": 10, "profiles": [[0, 1]], "all_are_equilibria": True}}
```

`with_analysis=False` skips the Pareto flags (`None`) and both ratios (`None`); everything else is still computed.
**The ratios can legitimately be `None`** (for the default data this happens at larger `gamma`, for example 3, where
equilibrium welfare is no longer positive): display "undefined (welfare not positive)" and show the gaps instead.
Calling this takes about a tenth of a second for the default scenario on the development machine; cache it with
`st.cache_data` keyed on the scenario anyway.

### 4.6 `pure_nash_equilibria`

`strategy_counts[p]` = number of strategies of player `p`; `payoff_fn(profile_tuple)` returns the payoff of every
player (a sequence of length `len(strategy_counts)`). Returns every pure equilibrium as a list of lists; `[]` means
**no pure equilibrium exists** (for example matching pennies). Not needed by the UI.

## 5. Worked example (hand-derived, then confirmed by running the engine)

`get_tiny_scenario()`: `pref = [[5, 1], [1, 5]]`, `w01 = 2`, `gamma = 1` (so `c(1) = 0`, `c(2) = 1`).

| profile | utilities | welfare | potential | pure Nash? |
|---|---|---|---|---|
| `[0, 0]` | `[6, 2]` | 8 | 7 | no: student 1 gains 3 by moving to project 1 |
| `[0, 1]` | `[5, 5]` | 10 | 10 | **yes** (unique; also the welfare optimum) |
| `[1, 0]` | `[1, 1]` | 2 | 2 | no: both students gain 5 by moving |
| `[1, 1]` | `[2, 6]` | 8 | 7 | no: student 0 gains 3 by moving to project 0 |

```python
from sample_data import get_tiny_scenario
from game_engine import is_nash, best_response_dynamics, enumerate_equilibria

sc = get_tiny_scenario()
is_nash([0, 0], sc)
# {'is_nash': False, 'utilities': [6, 2], 'deviations': [{'student': 1, 'from_project': 0, 'to_project': 1,
#   'current_utility': 2, 'new_utility': 5, 'gain': 3}]}
best_response_dynamics(sc, [0, 0])["final_profile"]       # [0, 1]
enumerate_equilibria(sc)["equilibria"][0]["profile"]       # [0, 1]
```

## 6. Command line

```
python game_engine.py --report [--gamma G] [--seeds N] [--timing-runs N] [--out PATH]
```

Prints (or writes with `--out`, UTF-8) one JSON object for the default scenario:

| key | content |
|---|---|
| `note` | synthetic-data disclaimer |
| `meta` | interface version, Python version, platform, and `timing` (`runs_seconds`, `min_seconds`, `median_seconds`) of `enumerate_equilibria` |
| `scenario` | the exact scenario used (with `--gamma` applied) |
| `enumeration` | exactly the dict from `enumerate_equilibria(scenario)` |
| `dynamics_summary` | for `round_robin` and `random`: runs over seeds `0..N-1`, whether all converged / passed `is_nash` / landed in the enumerated set, steps and rounds statistics, endpoint counts |
| `demo` | the demo start profile, its `is_nash` report and its round-robin dynamics trace |

`--gamma` lets the UI's gamma slider be cross-checked against the CLI. Without `--report` the help text is printed.
Errors exit with status 2 and a one-line message on stderr.

Reproduce all saved evidence (writes `docs/results/engine_report.json`, `pytest_output.txt`, `timing.txt`):

```
python scripts/generate_results.py
```

## 7. Integration guide for Harsh

**Setup.** Python 3.11, then from the repository root:

```
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt   # streamlit, pandas, pytest
python -m pytest -q               # engine and integration tests (pytest.ini puts the repo root on the path)
```

**Import.** `import game_engine as ge` and `import sample_data` from `app.py` (same folder). `pytest.ini` already sets
`pythonpath = .`, so `tests/test_ui_smoke.py` can import them too.

**Suggested mapping.**

| Tab | Calls |
|---|---|
| Scenario | `sample_data.get_default_scenario()`; show `students`, `skills`, `projects`, `pref`, `w`; the gamma slider copies the scenario and sets `sc["gamma"]` (never mutate a cached object) |
| Assignment | build `profile` from one selectbox per student; `ge.random_profile(sc, seed)`; `ge.utilities`, `ge.teams`, `ge.social_welfare`, `ge.potential` |
| Equilibrium | `ge.is_nash(profile, sc)`; table from `["deviations"]` |
| Simulation | `ge.best_response_dynamics(sc, profile, order, seed, max_rounds)`; trace from `["steps"]`; **final badge from a fresh `ge.is_nash(run["final_profile"], sc)`** (equivalent to `run["is_nash_final"]`) |
| Analysis (P1) | `ge.enumerate_equilibria(sc)` under `st.cache_data`; handle `None` ratios; demo start: `sample_data.get_demo_start_profile()` |

**Common mistakes to avoid.**

1. Off-by-one: the engine is 0-based; convert selectbox names to indices (`projects.index(name)`).
2. Passing a changed scenario copy to some calls and the original to others; always pass the same `sc`.
3. Claiming "optimal" for an equilibrium. Say "stable against unilateral deviations". Show `optimal` and the gaps separately.
4. Treating `converged` as proof of stability; use `is_nash_final` / a fresh `is_nash`.
5. Formatting `None` ratios or gaps (`None` when there is no equilibrium) as numbers.
6. Indexing `profile` with a student *name*; use the index.
7. Letting `StratosError` escape: wrap engine calls as in section 3.
8. Mutating returned dicts that are shared through `st.session_state`; copy first.

Values from a `st.data_editor` (pandas/NumPy ints and floats) are accepted by the engine and never leak back out. NumPy arrays and pandas `DataFrame` / `Series` objects are accepted for `pref`, `w`, `students`, `projects` and for profiles (they are converted with `.to_numpy().tolist()`), so the frame returned by `st.data_editor` can be passed directly.

**Saved results and `sample_data.py`.** `tests/test_integration.py::test_I06_saved_results_are_not_stale` deliberately fails if anyone edits `sample_data.py` (or the engine's results) without regenerating `docs/results/` with `python scripts/generate_results.py`. That failure is the check working, not a bug in the app.

## 8. Known ambiguities and decisions

* **Ties.** A tie never counts as a profitable deviation; a tied profile can be an equilibrium (weak definition).
  `best` stays on the current project when it is already a best response.
* **Welfare ties.** `optimal` is the lexicographically first maximiser; `optimal_profiles` lists all of them.
* **Contract additions beyond the plan's Section 8** (all additive; ignoring them is safe): `max_profiles` argument and
  `random_profile` default `seed=None`; keys `n_equilibria`, `optimal.utilities`, `optimal_profiles`,
  `potential_maximizers`, `steps[].utilities`; function `build_report`; `sample_data.get_demo_start_profile()`.
* **Not resolved by the engine:** the exact assigned project title and any faculty requirements (unverified, Ayush's Q1).
