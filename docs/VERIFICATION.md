# STRATOS: mathematical verification report

All student data and weights are **fictional and synthetic** (see `sample_data.py`). Every number below was produced by
running the code named next to it; the evidence files are in `docs/results/`. This report separates three things:
*definitions* (the model in `docs/MODEL.md`), *implementation* (`game_engine.py`), and *observed results*.

## 1. The model that was verified (exactly as implemented)

```
u_i(s) = pref[i][s_i] + sum_{j != i, s_j = s_i} w[i][j] - c(n_{s_i}(s)),      c(k) = gamma * (k - 1)^2
W(s)   = sum_i u_i(s)
Phi(s) = sum_i pref[i][s_i] + sum_{i<j, s_i=s_j} w[i][j] - sum_t sum_{k=1..n_t} c(k)      (exact potential)
```

Answers to the questions a reviewer will ask about the formula, read from the source, not assumed:

| Question | Answer in the code |
|---|---|
| Is compatibility individual or aggregate? | Aggregate over teammates: the sum of `w[i][j]` over the *other* members of `i`'s team. `w` is symmetric with zero diagonal (validated). |
| Is the crowding penalty student-specific? | No. One global `gamma`; `c(k)` depends only on the team size `k`. (An earlier informal description of the project used a per-student `gamma_i`; the implemented and documented model uses a single `gamma`.) |
| What size does it apply to? | `k = n_{s_i}(s)` = the full team size **including** student `i`; a student alone pays `c(1) = 0`. |
| Is utility computed per student? | Yes, `u_i` for every `i`; `W` is their plain sum (not an average, not normalised). |
| Strategy space? | Each of `n = 8` students picks one of `m = 3` projects: `m^n = 3^8 = 6561` profiles. |

Default scenario: `gamma = 2`, preferences in `0..9`, `w[i][j] = |S_i symmetric-difference S_j| - 1` from skill sets.

## 2. What was independently checked, and how

There are three separate computation paths. None of the checkers imports `game_engine` to obtain its own numbers.

| Path | File | Arithmetic | Independence from the engine |
|---|---|---|---|
| Engine | `game_engine.py` | floats/ints with `EPS = 1e-9` | n/a |
| Oracle | `tests/oracle/independent_check.py` | exact `fractions.Fraction`, no tolerance | own teammate lists; deviations built by constructing the deviated profile; brute-force Pareto over all profiles; own best-response loops |
| Cross-check | `scripts/independent_crosscheck.py` | exact integers | recomputes from `MODEL.md` with its own loops; also runs best-response from every start |

**Honest limit.** The oracle and cross-check were written from the same specification (`MODEL.md`) inside the same project, so
they catch *implementation* mistakes (index errors, wrong tie-breaks, tolerance bugs), not a mistake in the model itself.
The model's soundness rests on the proof of the exact-potential identity (MODEL.md section 4), which the checkers also verify
numerically on every profile × deviation, and on the hand-derived tables (`TINY_HAND`, `TRIO_HAND`) whose arithmetic is
written out literally in the oracle.

### 2.1 Checks and results

| # | Property | How | Result |
|---|---|---|---|
| 1 | Strategy space has exactly `3^8 = 6561` distinct profiles | `test_V02`: oracle list equals `itertools.product(range(3), repeat=8)`, no duplicates; engine `analyze_landscape` and `analyze_distributions` both report 6561 | match |
| 2 | Team membership | `test_V03`: engine `teams()` sizes equal the oracle's team sizes on **all 6561** profiles | match |
| 3 | Individual utilities | `test_V03`: engine `utilities()` equal the oracle's exact `Fraction`s on all 6561 profiles | 0 discrepancies |
| 4 | Social welfare, potential | `test_V03`: all 6561 profiles, exact equality | 0 discrepancies |
| 5 | Unilateral deviations | `test_V03`: for each of the 6561 profiles the *set* of (student, target, gain) profitable deviations equals the oracle's | 0 discrepancies |
| 6 | Pure Nash equilibrium set | `test_V04`, plus `docs/results/oracle_report.txt` | engine, oracle and cross-check all give the same **23** equilibria |
| 7 | Largest profitable deviation | `test_V05`: zero at every equilibrium, positive at non-equilibria | match |
| 8 | Welfare optimum | `test_V04` | `W_opt = 29`, two optimal profiles; exactly one is an equilibrium |
| 9 | Price of stability / anarchy | `test_V04` (exact fractions) | `1` and `29/16 = 1.8125` |
| 10 | Pareto-optimal equilibria | `test_V04` brute force over all profiles | 20 of 23 |
| 11 | Exact-potential identity | oracle, 104,976 profile × deviation cases on the default scenario | holds everywhere |
| 12 | Welfare closed form `sum pref + 2 sum w - sum n c(n)` equals the sum of utilities | oracle, 6561 cases | holds |
| 13 | Best-response dynamics | `test_V07`: for **every one of the 6561 starts**, for both update orders, the oracle's own dynamics ends at the same profile with the same number of moves as the engine; basin sizes agree | match |
| 14 | Distributions (welfare stats, team-size patterns, utility histogram, per-student ranges) | `test_V06` against exact oracle values | match |
| 15 | Sensitivity analysis | `test_V09`: 7 parameter variants re-solved by the oracle on its own scaled copies; `test_V10`: baseline dict and every baseline number unchanged after sweeping | match, no mutation |
| 16 | Displayed numbers = engine numbers | `tests/test_analysis_tab_ui.py` (Streamlit `AppTest`): metrics shown equal engine output; changing `gamma` changes every analysis number (no stale results) | match |
| 17 | The checkers can fail | `tests/test_oracle.py`: injected bugs in `social_welfare`, `potential`, `is_nash` and the dynamics are each detected | detected |

Oracle run: `python tests/oracle/independent_check.py --compare --full --report docs/results/oracle_report.txt`
(509 checks, 0 failed, 23 scenarios: tiny, trio, default and 20 seeded random scenarios with negative weights,
zero and half-integer `gamma`, 2-4 projects).

### 2.2 Discrepancies

None were found between the engine and either independent computation, so no engine behaviour was changed to match
a checker. One *documentation* inconsistency was found and fixed: the Analysis tab's price-of-stability/anarchy labels used
`s*` for the welfare optimum while MODEL.md uses `s*` for an equilibrium; they now read `W_opt`.

## 3. Nash equilibrium, ties and tolerance

* A profile is a pure Nash equilibrium iff `u_i(s) >= u_i(t, s_-i)` for all `i`, `t`. The engine flags a deviation as
  profitable only if its gain exceeds `EPS = 1e-9`; **ties do not break an equilibrium**. The oracle uses exact arithmetic
  and strict `> 0`, so the tolerance cannot hide or invent a deviation on integer/half-integer data (checked on 20 random scenarios).
* Multiple equilibria: the default scenario has 23. A game with no pure equilibrium cannot arise in this model (exact potential), but the "no equilibrium" code path is still exercised:
  `pure_nash_equilibria` is verified on matching pennies, which has none, so the "no equilibrium" path is exercised.

## 4. Best-response dynamics

* Mechanism (MODEL.md section 5): sweeps over the students (ascending index, or a seeded random permutation per sweep); a
  student moves only for a strictly positive gain, to the lowest-index maximiser, staying put if the current project is a maximiser.
* **Convergence is justified, not just observed.** `Phi` is an exact potential (proof in MODEL.md), so every move raises `Phi` by the
  mover's gain: no profile can be revisited, **cycles are impossible for this model**, and every run terminates. The guarantee
  needs symmetric `w` and size-only crowding; the engine rejects asymmetric `w`. The code does not rely on it: every run reports
  `converged` and a fresh `is_nash_final`.
* Measured on all 6561 starts (`docs/results/analysis_report.json`):

| Order | Converged | Final is Nash | Longest run (moves) | Mean moves | Max sweeps | Distinct endpoints |
|---|---|---|---|---|---|---|
| round_robin | 6561 / 6561 | 6561 / 6561 | 13 | 5.40 | 5 | 23 |
| random (seed = start index) | 6561 / 6561 | 6561 / 6561 | 13 | 5.62 | 7 | 23 |

  All 23 equilibria are reached from some start. Where the dynamics ends depends on the start: under round-robin, 558 of the
  6561 starts end at a welfare-optimal profile while the largest basin (1033 starts) ends at an equilibrium with welfare 22.
  **Best-response dynamics does not select the best equilibrium.**

## 5. Equilibrium versus social optimum (observed in the default scenario)

* `W_opt = 29`, reached by two profiles. `[0,0,1,0,1,1,2,2]` is **not** stable: Eli (index 4) gains 2 by moving from project 1 to
  project 2. `[0,0,1,0,2,1,2,2]` **is** stable, so here price of stability = 1.
* The worst equilibrium has welfare 16, so price of anarchy = 29/16 = 1.8125, and 3 of the 23 equilibria are Pareto-dominated by
  some (non-equilibrium) profile. Stability against single-student deviations is therefore neither welfare maximisation nor Pareto efficiency.
* These conclusions are properties of *this synthetic scenario*, not general facts.

## 6. Sensitivity (what-if copies; baseline untouched)

`gamma` sweep, default data (`docs/results/analysis_report.json`; each row is an exhaustive re-solve of 6561 profiles):

| gamma | equilibria | max welfare | best equilibrium | worst equilibrium | largest team at optimum |
|---|---|---|---|---|---|
| 0 | 6 | 114 | 114 | 79 | 8 |
| 0.5 | 4 | 68 | 68 | 58 | 3 |
| 1 | 19 | 55 | 55 | 44 | 3 |
| 2 (baseline) | 23 | 29 | 29 | 16 | 3 |
| 3 | 23 | 3 | 3 | -10 | 3 |

For `gamma >= 3` equilibrium welfare is no longer positive, so the price ratios become *undefined* and the app reports absolute
welfare gaps instead (MODEL.md section 5).

## 7. Performance and reproducibility

* Exhaustive enumeration of 6561 profiles: about 0.12 s (`docs/results/timing.txt`); best-response from all 6561 starts: about 2 s;
  each `gamma` sweep point: about 0.07 s. Memory is a few MB (all profiles and utilities are held in lists).
* Reproduce everything:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe tests\oracle\independent_check.py --compare --full --report docs\results\oracle_report.txt
.venv\Scripts\python.exe scripts\independent_crosscheck.py --compare
.venv\Scripts\python.exe scripts\generate_results.py
```

## 8. What this verification does not establish

* That the model is a *good* description of real team formation (the data are synthetic assumptions).
* Anything about coalition deviations, mixed strategies or incomplete information (out of scope).
* Independence of authorship: see the honest limit in section 2.
