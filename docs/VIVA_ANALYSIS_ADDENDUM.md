# Viva addendum: current facts and answers

The printable handbook and speaking plan in `deliverables/viva/` were produced before the Analysis and Guide tabs, the
oracle and the full-coverage verification existed. Where they say "four tabs" or "158 tests", this page is current. All figures
below come from `docs/results/` and `docs/VERIFICATION.md` and can be reproduced with the commands in `README.md`.
(All data are fictional and synthetic.)

**Current state:** six tabs (Scenario, Assignment, Equilibrium, Simulation, Analysis, Guide); the full test suite is run with
`python -m pytest -q` (the exact count and result of the latest run is in `docs/results/pytest_output.txt`).

| Question | Short answer (with the number to quote) |
|---|---|
| What is the game? | 8 students each choose 1 of 3 projects. `u_i = pref + sum of teammate compatibilities - gamma (k-1)^2`, where `k` is the full team size including `i`. One global `gamma = 2`. |
| How big is the strategy space and did you check all of it? | `3^8 = 6561` profiles; the engine, an exact-arithmetic oracle and an integer cross-check all evaluate all 6561 and agree on utilities, welfare, potential and every profitable deviation. Enumeration takes about 0.12 s. |
| How do you detect a Nash equilibrium? | For every student and every other project, compare utility after the switch with the current utility (others fixed). No gain above `1e-9` means equilibrium; ties do not break it. 16 evaluations per profile. There are **23** pure equilibria. |
| Is the checker really independent? | It never imports the engine for its own numbers, uses exact fractions and different code paths, and detects injected bugs. But it was written from the same spec, so it would not catch a modelling error. Say this plainly. |
| Can best-response dynamics cycle? | Not in this model: the potential `Phi` is exact, so each move raises `Phi` by the mover's gain and no profile repeats. Measured: all 6561 starts converge, longest run 13 moves, at most 5 sweeps (round robin) or 7 (random order). The code still checks, and would report, any non-convergence. |
| Does best-response reach the best equilibrium? | No. All 23 equilibria are reached from some start; only 558 of 6561 round-robin starts end at a welfare-29 equilibrium, while the largest basin (1033 starts) ends at welfare 22. |
| Equilibrium vs social optimum? | `W_opt = 29` at two profiles; one is stable, the other is not (Eli gains 2 by moving). So price of stability = 1, but the worst equilibrium has welfare 16: price of anarchy = 29/16 = 1.8125, and 3 of the 23 equilibria are Pareto-dominated. These facts are specific to this synthetic data. |
| Why is there a crowding penalty? | Without it everyone would join their favourite or most compatible team with no downside; a convex cost makes large teams unattractive, keeps every deviation feasible (no hard cap) and keeps the potential structure. |
| What does the sensitivity analysis show, and does it change your results? | It re-solves the game on a *copy* with a different `gamma` (or scaled compatibility / preferences). The baseline is never modified (tested). For `gamma = 0` there are 6 equilibria and the optimum puts all 8 students on one team (welfare 114); at `gamma = 0.5` there are 4; at `gamma = 1`, 19; from `gamma = 1.5` upward, 23. |
| Why do the ratios disappear at large gamma? | Price of anarchy/stability need all equilibrium welfare strictly positive; at `gamma >= 3` it is not, so the app shows absolute welfare gaps instead. |
| Limitations? | Synthetic data; additive pairwise compatibility; only unilateral deviations (no coalitions); complete information; exhaustive analysis capped at 100,000 profiles; checker shares the engine's specification. |
