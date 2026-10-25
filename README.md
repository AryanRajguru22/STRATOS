# STRATOS

**Strategic Behavior in University Course / Project Team Formation** — a Game Theory course project.

> Title note: this is the topic as stated in the task brief. The exact title and group row in `Groups.xlsx` and the
> course handout have **not** been verified against the official files (they were not available to the team's
> engineer); see [Status and limitations](#7-status-and-limitations).

STRATOS models project-team formation as a **potential game**. Each student (a *player*) chooses exactly one project.
A student's utility combines their own preference for the project, how well they work with the teammates who end up on
the same project, and a crowding cost that grows with team size. The software checks whether an assignment is
**stable against unilateral deviations** (a pure Nash equilibrium), simulates best-response dynamics, and enumerates
every assignment of the default scenario to compare stable outcomes with the welfare-maximising one.

> **All student data and all model weights are fictional and synthetic.** They were chosen so that strategic behaviour is
> visible in a small demonstration; they are not measurements of real students.

## 1. Quick start (Windows, Python 3.11)

```powershell
git clone https://github.com/AryanRajguru22/STRATOS.git
cd STRATOS
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

The app opens at <http://localhost:8501>. To check the server without a browser: `/_stcore/health` returns `ok`.

| Package | Declared in `requirements.txt` | Used for |
|---|---|---|
| Streamlit | `streamlit>=1.51` | the web UI (`width="stretch"` on buttons, tables and charts needs 1.51) |
| Pandas | `pandas>=2.0` | tables shown in the UI |
| Plotly | `plotly>=5.0` | heatmaps and line/bar charts |
| Pytest | `pytest>=7.0` | the test suite |

The game engine itself (`game_engine.py`, `sample_data.py`) uses only the Python standard library.
PDF/document tooling (`reportlab`) is **not** needed to run or test the product; see `requirements-docs.txt`.

## 2. The four tabs

| Tab | What you do | What it shows | Engine calls |
|---|---|---|---|
| **Scenario** | Pick a preset in the sidebar (*Tiny hand-verified example*, *Default scenario*, or an adjustable *Custom mock scenario*). | Students and skills, projects, the crowding parameter `gamma`, a preference heatmap and a teammate-compatibility heatmap. | the scenario dict from `sample_data` |
| **Assignment** | Choose a project for every student, or press **Random** / **Reset**. | Teams per project, utility per student, social welfare `W(s)`, potential `Φ(s)`, and a utility bar chart. | `random_profile`, `validate_profile`, `teams`, `utilities`, `social_welfare`, `potential` |
| **Equilibrium** | None (it reads the current assignment). | Whether the assignment is stable; if not, every profitable unilateral move and how many distinct students have one. | `is_nash` |
| **Simulation** | Choose the update order (`round_robin` or `random`), the seed and the sweep limit in the sidebar, then press **Run dynamics**. | Sweeps, moves, a move-by-move trace, a slider to inspect any intermediate assignment, a welfare/potential chart, and a final status that is re-verified with a fresh `is_nash` call (never taken from the `converged` flag alone). | `best_response_dynamics`, `is_nash`, `teams` |

The header states whether the **real engine** is loaded. If `game_engine.py` or `sample_data.py` is missing, the app
falls back to a clearly labelled mock; if they are present but fail to import, it shows the import error loudly. To make
any fallback a hard failure (useful for demos and CI) set `STRATOS_REQUIRE_REAL_ENGINE=1` before launching:

```powershell
$env:STRATOS_REQUIRE_REAL_ENGINE = "1"; streamlit run app.py
```

## 3. Running the tests

```powershell
python -m pytest -q
```

The suite covers the engine (`tests/test_game_engine.py`), the engine/UI contract (`tests/test_integration.py`), the
Streamlit app and its helpers (`tests/test_ui_smoke.py`, using Streamlit's `AppTest`), and an independent recomputation
of the results (`tests/test_independent_crosscheck.py`). The most recent recorded run, with its commit hash and whether
the working tree was clean, is in `docs/results/pytest_output.txt`.

## 4. The model in brief

Full definitions and the potential-game proof are in [`docs/MODEL.md`](docs/MODEL.md).

```
u_i(s) = pref[i][s_i]  +  sum over teammates j (j != i, s_j = s_i) of w[i][j]  -  c(n_{s_i}(s))
c(k)   = gamma * (k - 1)^2          (crowding cost of a team of size k; c(1) = 0)
W(s)   = sum_i u_i(s)               (social welfare)
Phi(s) = sum_i pref[i][s_i] + sum over same-team pairs i<j of w[i][j] - sum_t sum_{k=1..n_t} c(k)   (exact potential)
```

* A **profitable deviation** is a single student switching project (everyone else fixed) for a strictly higher utility.
* A **pure Nash equilibrium** is an assignment with no profitable deviation. Ties do not break an equilibrium.
* Because `w` is symmetric and the crowding cost depends only on team size, `Φ` is an *exact potential*: a unilateral
  move changes `Φ` by exactly the mover's change in utility. So a pure equilibrium always exists and best-response
  dynamics always terminates.
* A stable assignment is **not** necessarily welfare-maximising, Pareto-optimal or unique.

### Default scenario results (8 students, 3 projects, `gamma = 2`)

Regenerated and independently recomputed; evidence is in `docs/results/`.

| Quantity | Value |
|---|---|
| Possible assignments (3^8) | 6,561 |
| Pure Nash equilibria | 23 |
| Maximum social welfare | 29 (two optimal assignments; exactly one of them is an equilibrium) |
| Lowest equilibrium welfare | 16 |
| Price of stability / price of anarchy | 1.0 / 1.8125 (= 29/16) |
| Pareto-optimal equilibria | 20 of 23 |

## 5. Repository structure

```
app.py                      Streamlit entry point: the four tabs (thin UI layer)
app_helpers.py              engine loading (real vs mock), DataFrame and Plotly chart builders
game_engine.py              the engine: utility, Nash check, dynamics, enumeration, CLI report
sample_data.py              synthetic scenarios: tiny hand example and the 8-student default
requirements.txt            application + test dependencies
requirements-docs.txt       optional: tools used only to build the PDF deliverables
pytest.ini                  puts the repo root on the import path; tests live in tests/
docs/MODEL.md               formal model, potential-game proof, algorithms
docs/INTERFACE.md           the frozen engine <-> UI contract (signatures, return keys, errors)
docs/results/               reproducible evidence: engine report, test log, timing, cross-check output
docs/TEAM_WORK_ALLOCATION.md  the team plan
scripts/generate_results.py regenerates docs/results/ from real commands
scripts/independent_crosscheck.py  recomputes the results without importing the engine (see below)
tests/                      engine, integration, UI-smoke and cross-check tests
screenshots/                screenshots captured from the running app (see screenshots/INDEX.md)
deliverables/viva/          printable viva handbook and speaking plan (PDF) and their build scripts
```

## 6. Reproducing the results

```powershell
python game_engine.py --report                       # JSON report for the default scenario
python scripts/independent_crosscheck.py --compare   # independent recomputation, diffed against the engine
python scripts/generate_results.py                   # rewrites docs/results/ (engine report, test log, timing, cross-check)
```

`generate_results.py` records the git commit and whether the working tree was clean, so a results file never claims to
describe a commit it was not produced from. `tests/test_integration.py::test_I06_saved_results_are_not_stale` fails if
`sample_data.py` or the engine changes without the saved report being regenerated; that failure is the check working.

## 7. Status and limitations

* Data and weights are synthetic; no real student data was used.
* Only **unilateral** deviations are analysed; coalitions of students moving together are out of scope.
* Complete information and a static game; best-response dynamics is a simulated adjustment process, not a repeated game.
* Exhaustive enumeration is exponential in the number of students and is capped at 100,000 assignments (up to about
  10 students with 3 projects). The UI does not expose enumeration; the enumeration results come from the CLI report.
* The optional *Analysis* tab (price of anarchy/stability in the UI) was not built.
* Not yet verified by the team at the time of writing: the official project title and any faculty-specific rules
  (`Groups.xlsx` / handout), a formal independent re-implementation and Excel oracle by the verification owner
  (`tests/oracle/`), and a manual walkthrough on the presentation machine.
* The *Custom mock scenario* preset uses a frontend-generated random scenario, not the team's dataset; it exists to
  exercise the UI at other sizes.
