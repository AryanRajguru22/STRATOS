# STRATOS: formal model (v1.0)

Owner: Aryan Rajguru. This document is the single specification that `game_engine.py` implements and that Ayush's
independent checker (`tests/oracle/independent_check.py`) must be written from. If code and this file ever disagree,
that is a bug to report, not something to patch silently.

> **All student data and all model weights are fictional and synthetic.** They were fixed so that strategic
> behaviour is visible in a small demonstration. They are modelling assumptions, not measurements of real students.

## 1. The game

**Players.** Students `N = {0, ..., n-1}`. The default scenario has `n = 8`.

**Strategies.** Each student chooses exactly one project from `M = {0, ..., m-1}`. The default scenario has `m = 3`.
Student `i`'s strategy is `s_i`.

**Profile (assignment).** `s = (s_0, ..., s_{n-1})`, a list of `n` integers in `0..m-1`. There are `m^n` profiles
(`3^8 = 6561` by default). Indices are 0-based everywhere in the code and the interface; the UI maps them to names.

**Teams.** `T_t(s) = { i : s_i = t }` and `n_t(s) = |T_t(s)|`. Empty teams are allowed. There is no hard size limit.

**Information and timing.** The game is *static*: students choose simultaneously and every student knows all
parameters (complete information). Best-response dynamics (Section 5) is an *adjustment process* we simulate; it is
not a sequential or repeated game.

## 2. Parameters

| Symbol | Code | Meaning | Constraint |
|---|---|---|---|
| `p[i][t]` | `pref` (n x m) | how much student `i` likes project `t` | finite number (integers recommended; 0..10 suggested) |
| `w[i][j]` | `w` (n x n) | benefit (or cost, if negative) to `i` of having `j` on the same team | **symmetric** (`w[i][j] = w[j][i]`), zero diagonal |
| `gamma` | `gamma` | crowding strength | number `>= 0` |
| `c(k)` | `crowding_cost(k)` | crowding cost of a team of size `k` | `c(k) = gamma * (k - 1)^2`, so `c(1) = 0`, convex, non-decreasing |

Symmetry is checked with tolerance `EPS = 1e-9`. Booleans, strings, `NaN` and infinities are rejected.

**Skill-derived compatibility (default data only).** Each student has a skill set `S_i` drawn from
{Programming, Analysis, Design, Communication}. The default `w` is
`w[i][j] = LAMBDA * |S_i symmetric-difference S_j| - BETA` with `LAMBDA = 1`, `BETA = 1` (see `sample_data.py`).
This is symmetric by construction: complementary skills help, near-identical students help less. The engine itself
does not know about skills; it only reads `w`.

**Soft crowding instead of a hard cap.** A hard cap would make some deviations infeasible and complicate the
equilibrium definition. A convex cost keeps every deviation feasible and keeps the potential structure of Section 4.

## 3. Payoffs

```
u_i(s) = p[i][s_i]  +  sum over j != i with s_j = s_i of w[i][j]  -  c( n_{s_i}(s) )
          preference     compatibility with teammates                crowding cost
```

Note `n_{s_i}(s)` includes student `i` themself, so a student alone on a project pays `c(1) = 0`.

**Social welfare.** `W(s) = sum_i u_i(s) = sum_i p[i][s_i] + 2 * sum over pairs i<j on the same team of w[i][j]
- sum_t n_t(s) * c(n_t(s))`. (The factor 2 appears because each pair benefits both members.)

## 4. Equilibrium, best response and the potential

**Unilateral deviation.** Student `i` switches to project `t` while everyone else keeps their choice:
profile `(t, s_-i)`. Its **gain** is `u_i(t, s_-i) - u_i(s)`. It is *profitable* if the gain exceeds `EPS`.

**Best response.** `BR_i(s_-i)` is the set of projects maximising `u_i(t, s_-i)`. The engine's `best` project is
the *current* project if it is already a maximiser (within `EPS`); otherwise the **lowest-index** maximiser.
A student moves only for a strictly positive gain.

**Pure Nash equilibrium (weak form).** `s*` is a pure Nash equilibrium iff, for every student `i` and every
project `t`, `u_i(s*) >= u_i(t, s*_-i)`. Equivalently, no student has a profitable unilateral deviation. Checking
costs `n (m - 1)` utility evaluations (16 for the default scenario). Ties do not break an equilibrium.

**Exact potential.**

```
Phi(s) = sum_i p[i][s_i]  +  sum over pairs i<j on the same team of w[i][j]  -  sum_t sum_{k=1..n_t(s)} c(k)
```

**Claim.** For any profile `s` and any unilateral deviation of student `i` to `s'`:
`u_i(s') - u_i(s) = Phi(s') - Phi(s)`.

**Proof.** Let `i` move from project `a` to project `t != a`. Only terms involving `i`, team `a` and team `t`
change in `Phi`. The preference term changes by `p[i][t] - p[i][a]`. The pair terms lose `sum_{j on a, j != i} w[i][j]`
and gain `sum_{j on t} w[i][j]`. In the crowding sum, team `a` shrinks from `n_a` to `n_a - 1`, removing the term
`c(n_a)` from what is subtracted, and team `t` grows from `n_t` to `n_t + 1`, adding `c(n_t + 1)` to it. Hence
`Phi(s') - Phi(s) = [p[i][t] + sum_{j on t} w[i][j] - c(n_t + 1)] - [p[i][a] + sum_{j on a, j != i} w[i][j] - c(n_a)]`,
which is exactly `u_i(s') - u_i(s)`. QED.

**Consequences (for THIS model).**

1. A maximiser of `Phi` over the finite set of profiles exists, and no unilateral deviation from it can be
   profitable (it would raise `Phi`). Therefore **a pure Nash equilibrium always exists.**
2. Every strictly profitable move raises `Phi` by exactly the mover's gain, so **best-response dynamics cannot
   revisit a profile and terminates.** With integer data each move raises `Phi` by at least 1, so there are at most
   `Phi_max - Phi_min` moves.
3. The guarantee needs **symmetric `w`** and a crowding cost that depends **only on team size**. An asymmetric `w`,
   or a non-pairwise "team covers a skill" bonus, can destroy it. The code never relies on the proof: it checks the
   equilibrium condition directly and reports honestly if no equilibrium is found.

**What is NOT implied.**

* `Phi` is not social welfare. A maximiser of `Phi` is an equilibrium, but an equilibrium need not maximise `Phi`
  (see the `COORD` fixture in `tests/test_game_engine.py`, where `[0, 0]` is an equilibrium with smaller potential).
* An equilibrium is *stable against unilateral deviations*; it is **not** necessarily welfare-optimal, Pareto-optimal,
  unique, or reached from every start. Coalitions of students moving together are not considered.
* The welfare-maximising profile may or may not be an equilibrium. The engine reports both separately.

## 5. Algorithms

**Best-response dynamics** (`best_response_dynamics`).

```
s = start
repeat sweeps r = 1 .. max_rounds:
    visit order = ascending index ("round_robin") or a seeded random permutation per sweep ("random")
    changed = False
    for i in visit order:
        t* = best response of i given s_-i          (stay if the current project is already a maximiser)
        if u_i(t*, s_-i) > u_i(s) + EPS:  s_i = t*;  record step;  changed = True
    if not changed: converged = True; stop
return converged, rounds r, trace, final s, and a FRESH is_nash(final s)
```

* `rounds` counts sweeps, including the final sweep in which nobody moves.
* `converged` means a full sweep produced no move. If `max_rounds` runs out first, `converged` is `False` and the
  result says so. `is_nash_final` is always recomputed independently, so no caller needs to trust `converged`.

**Exhaustive enumeration** (`enumerate_equilibria`). Evaluates all `m^n` profiles; keeps those with no profitable
deviation (all pure Nash equilibria); finds the welfare maximiser(s) and the potential maximiser(s); computes, for
each equilibrium, whether it is Pareto-optimal among *all* profiles (no other profile makes every student at least
as well off and someone strictly better off, up to `EPS`). Guarded by `MAX_ENUMERATION_PROFILES = 100000`.

**Efficiency measures.**

* Welfare optimum `W_opt = max_s W(s)` (ties: all optimal profiles are listed; the lexicographically first is `optimal`).
* Welfare gap of an equilibrium `s*`: `W_opt - W(s*)`. Reported for the best and the worst equilibrium.
* Price of anarchy `W_opt / min_{equilibria} W` and price of stability `W_opt / max_{equilibria} W`, **only when every
  equilibrium welfare (and `W_opt`) is strictly positive**; otherwise `null`. The gaps are always reported.

**Generic checker** (`pure_nash_equilibria`). Exhaustive pure-Nash search for any finite normal-form game, used
to confirm that a game with no pure equilibrium (matching pennies) returns an empty list, and to cross-check the
team game through an independent code path.

## 6. Complexity

| Operation | Cost | Note |
|---|---|---|
| one utility | `O(n)` | recount teammates |
| best response of one student | `O(n m)` | |
| one sweep of the dynamics | `O(n^2 m)` | number of sweeps is finite; the *measured* counts are in `docs/results/engine_report.json` |
| `is_nash` on one profile | `O(n^2 m)` | |
| enumeration | `O(m^n n^2 m)` | exponential in `n`; measured wall-clock time is in `docs/results/timing.txt` |

## 7. Verification strategy (what the evidence will consist of)

1. `is_nash` is a separate function from the dynamics and checks every unilateral deviation.
2. Hand-computed fixtures (2-student `TINY`, 3-student `TRIO`, `COORD`, `REPEL`) and property tests (exact
   potential identity, welfare identity, determinism, immutability) in `tests/test_game_engine.py`.
3. Matching pennies through the generic checker returns no pure equilibrium.
4. Every dynamics endpoint from 200 seeded starts per update order is in the enumerated equilibrium set.
5. Independent re-implementation by Ayush from this document, and an Excel oracle, must reproduce the
   equilibrium set, welfare optimum and utilities.
6. UI numbers must equal engine numbers and the CLI report on at least three assignments.

## 8. Symbol-to-code map

| Math | Code |
|---|---|
| `n`, `m` | `len(students)`, `len(projects)` |
| `p[i][t]` | `scenario["pref"][i][t]` |
| `w[i][j]` | `scenario["w"][i][j]` |
| `gamma`, `c(k)` | `scenario["gamma"]`, `crowding_cost(k, scenario)` |
| `u_i(s)` | `utility(i, profile, scenario)` / `utilities(profile, scenario)[i]` |
| `W(s)` | `social_welfare(profile, scenario)` |
| `Phi(s)` | `potential(profile, scenario)` |
| `T_t(s)` | `teams(profile, scenario)[t]` |
| profitable deviations / Nash test | `profitable_deviations`, `is_nash` |
| best response / dynamics | `best_response`, `best_response_dynamics` |
| all equilibria, optimum, efficiency | `enumerate_equilibria` |
| any finite game | `pure_nash_equilibria` |

## 9. Assumptions and limitations

* Synthetic data and assumed weights; additive pairwise compatibility; no capacity limits (soft crowding only).
* Complete information; only unilateral deviations (coalition-proof analysis is not performed).
* Small `n`: exhaustive enumeration is exponential in `n`; the dynamics scales much further.
* Hand-assigned preferences, `DEFAULT_GAMMA = 2` and the skill sets were fixed before analysis. The demo start
  profile was chosen *after* inspecting the model's behaviour, to give a short readable trace.
* The exact assigned project title and any faculty-specific rules have **not** been verified against
  `Groups.xlsx` or the course handout (Ayush's task Q1).
