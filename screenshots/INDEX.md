# Screenshot index

Real screenshots of the running STRATOS app, captured automatically by `Playwright` driving headless Google Chrome
155.0.8059.86 against `streamlit run app.py` on 2026-10-26. Nothing here is edited or mocked, and the header of every
screenshot shows **"Real engine detected"** (the mock fallback was not active).

* **Application code captured:** `app.py` and `app_helpers.py` exactly as in commit `c94f918` (full hash
  `c94f918764f8f95133ed03ca3b19118d05e62b73` was HEAD when the walkthrough ran; later commits on this branch change documentation, tests,
  requirements and evidence files only, not the app).
* **Environment:** fresh virtualenv from `requirements.txt` on Windows 11, Python 3.11.9, Streamlit 1.66.1, Plotly 7.1.0,
  pandas 3.1.0.
* **Tabs found in the page:** Scenario, Assignment, Equilibrium, Simulation.
* **Browser console errors recorded during the run:** 0.
* **What the "values matched" column means:** for each screenshot the script read the on-screen metrics and alert
  boxes and compared them with numbers computed by `game_engine` (which the independent cross-check reproduces) (for example welfare 15 / potential 35 for
  the demo start). Table contents (teams, traces) are drawn on a canvas by Streamlit and were checked by eye against the
  engine's output instead.
* **What this is not:** it is an automated walkthrough, not a manual one by a team member on the presentation machine.
  That manual walkthrough is still pending.

| File | Tab | State shown | On-screen values matched engine |
|---|---|---|---|
| `S1a_scenario_tiny_preset.png` | Scenario | Tiny hand-verified example (default on load) | yes |\n| `S1b_scenario_default_preset.png` | Scenario | Default scenario: 8 students, 3 projects, gamma = 2 | yes |\n| `S2a_assignment_reset_all_project0.png` | Assignment | after Reset: all 8 students on project 0 | yes |\n| `S2b_assignment_demo_start.png` | Assignment | demo start [0,0,0,1,1,1,2,2] | yes |\n| `S3_equilibrium_demo_start_unstable.png` | Equilibrium | demo start: 2 students have a profitable move | yes |\n| `S4_simulation_round_robin.png` | Simulation | round_robin from demo start (sidebar default) | yes |\n| `S5_simulation_random_order_seed7.png` | Simulation | random order, dynamics seed 7, same demo start | yes |\n| `S6_assignment_worst_equilibrium_welfare16.png` | Assignment | worst equilibrium [0,2,1,2,2,1,0,0]: welfare 16, potential 38 | yes |\n| `S7_equilibrium_worst_equilibrium_stable.png` | Equilibrium | worst equilibrium is stable although welfare 16 < 29 | yes |\n| `S8a_assignment_welfare_optimum_not_stable.png` | Assignment | welfare-maximising [0,0,1,0,1,1,2,2]: welfare 29, potential 47 | yes |\n| `S8b_equilibrium_welfare_optimum_not_stable.png` | Equilibrium | that optimum is NOT stable: Eli gains 2 by moving | yes |\n| `S9_assignment_random_seed1.png` | Assignment | Random button, seed 1 -> [0,2,0,1,0,1,1,1] | yes |\n| `S10_simulation_tiny_example.png` | Simulation | Tiny example from [0,0]: one move to [0,1] | yes |

## Reproducing the states

Default scenario, demo start `[0,0,0,1,1,1,2,2]` is `sample_data.get_demo_start_profile()`. Sidebar defaults: dynamics seed 7,
max sweeps 50. Worst equilibrium is `[0,2,1,2,2,1,0,0]` (welfare 16). The welfare-29 profile `[0,0,1,0,1,1,2,2]` is *not*
an equilibrium: Eli gains 2 by moving to Event Management Portal.

Observed cosmetic issues (not fixed, not affecting results): an empty rounded bar above the title (header-card markup),
and the chart legend overlapping the chart title on the Simulation tab.

Full machine-readable record: `walkthrough_log.json`.
