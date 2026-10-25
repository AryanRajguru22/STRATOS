# STRATOS -- README draft (handoff from Harsh, frontend)

> **This is a DRAFT handoff, not the finished team deliverable.** `README.md` is Ayush's file per
> the team plan (`docs/TEAM_WORK_ALLOCATION.md`, Section 6); this document only covers what I can
> verify from the frontend side (`app.py`, `app_helpers.py`, `tests/test_ui_smoke.py`) and from
> reading Aryan's `docs/INTERFACE.md` / `docs/MODEL.md`. Please fold whatever is useful into the
> real `README.md` and drop or correct anything that doesn't match the engine/report/docs sections
> you own. Nothing below is a claim about screenshots, report results, or anything I haven't
> personally run and verified in this session.

## 1. Project overview

STRATOS models university course/project team formation as a game: each student is a player who
picks one project; utility combines the student's own preference, teammate compatibility with
whoever else lands on the same project, and a crowding cost that grows with team size. The project
asks whether an assignment is **stable against unilateral deviations** (a pure Nash equilibrium) --
not whether it is the best possible assignment. All shipped student data and model weights are
**synthetic**, chosen to make strategic behaviour visible (see `sample_data.SYNTHETIC_DATA_NOTICE`,
also shown in the running app).

## 2. Installation and dependencies

```powershell
cd C:\Users\harsh\Downloads\STRATOS
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Plotly is now declared in `requirements.txt` (`plotly>=5.0`, added in commit 859a798), so this single install command is all that is needed -- no separate `pip install plotly` step.

## 3. Running the app

```powershell
streamlit run app.py
```

Opens at `http://localhost:8501`. Health endpoint (used in automated checks): `/_stcore/health` -> `ok`.

## 4. Running tests

```powershell
pytest -q
```

Runs all three suites (`tests/test_ui_smoke.py`, `tests/test_game_engine.py`,
`tests/test_integration.py`) via `pytest.ini`'s `testpaths`. As of this draft: **146 passed, 0
skipped**, run by me just now on this machine.

## 5. Repository structure and ownership

```
app.py                    Harsh   Streamlit entry point (thin UI layer, 4 tabs)
app_helpers.py             Harsh   data/engine-bundle loading, chart builders, mock fallback
tests/test_ui_smoke.py     Harsh   frontend smoke tests (AppTest-based)
game_engine.py             Aryan   the game engine (utility, Nash, dynamics, enumeration, CLI)
sample_data.py              Aryan   synthetic scenarios (tiny hand example + 8-student default)
tests/test_game_engine.py  Aryan   engine unit tests
tests/test_integration.py  Aryan   engine/UI contract tests
requirements.txt, .gitignore, pytest.ini   Aryan
docs/MODEL.md, docs/INTERFACE.md, docs/results/   Aryan
docs/TEAM_WORK_ALLOCATION.md                       Aryan (planning doc)
README.md, test plan/log, oracle checks, report, slides, screenshots   Ayush (not yet created)
```

## 6. The four tabs

| Tab | What it shows | Engine calls used |
|---|---|---|
| **Scenario** | Student list + skills, project list, preference heatmap, teammate-compatibility heatmap, the crowding parameter `gamma` | reads the `scenario` dict (`students`, `projects`, `pref`, `w`, `gamma`, `skills`) from `sample_data` |
| **Assignment** | Build a profile (one project per student via selectboxes), "Random"/"Reset" buttons, then teams-by-project, per-student utility, social welfare, and potential | `random_profile`, `validate_profile`, `teams`, `utilities`, `social_welfare`, `potential` |
| **Equilibrium** | Whether the current assignment is stable against unilateral deviations; if not, the exact list of profitable moves and a plain-language example | `is_nash` |
| **Simulation** | Runs best-response dynamics from the current assignment, a move-by-move trace, a step slider to inspect intermediate team states, and a welfare/potential chart | `best_response_dynamics`, plus a **fresh** `is_nash` call on the final profile (never trusts the `converged` flag alone) |

The optional "Analysis" tab described as P1 in the team plan (exhaustive equilibrium enumeration,
price of anarchy/stability) was **not built** -- it's explicitly optional, and that data is already
available via `python game_engine.py --report` and `docs/results/engine_report.json`.

## 7. Utility formula and assumptions

```
u_i(s) = pref[i][s_i] + sum_{j != i, s_j = s_i} w[i][j] - crowding_cost(team_size(s_i))
crowding_cost(k) = gamma * (k - 1)^2
```

Full derivation and proof of the potential-game guarantee: `docs/MODEL.md`. Key assumptions worth
repeating in the report: data is synthetic; compatibility `w` is symmetric with a zero diagonal;
only **unilateral** deviations are checked (no coalitions); the model is static/complete-information,
and best-response dynamics is a simulated adjustment process, not a repeated game.

## 8. Nash equilibrium vs. welfare-maximizing -- the distinction the app insists on

A **pure Nash equilibrium** here means no single student can raise their own utility by moving alone
while everyone else stays put. It is **not** the same as the welfare-maximizing (highest total
utility) assignment, and the app never calls a stable assignment "optimal" (I grepped both `app.py`
and `app_helpers.py` for the word "optimal" -- the only two occurrences explicitly state that stable
does *not* mean optimal). Both the welfare-optimal profile and the welfare gap of an equilibrium are
computed by `enumerate_equilibria` in the engine, but are only surfaced via the CLI/report JSON, not
in the current 4 tabs (see Section 6).

## 9. Real-engine loading and mock fallback

`app_helpers.load_engine_bundle()` tries `import game_engine` and `import sample_data`. If both
import cleanly, the app uses them directly -- verified this session: the header shows "Real engine
detected: `game_engine.py` and `sample_data.py` loaded.", and I compared UI-displayed utilities,
welfare, potential, and Nash status against direct `game_engine` calls on four assignments (tiny
scenario profiles `[0,0]` and `[0,1]`, and the default-scenario demo-start profile); all matched
exactly. If either module is missing or fails to import, the app falls back to a local mock that
mirrors the same documented contract -- every figure from the mock carries a visible "mock" badge,
and that badge is confirmed absent when the real engine is active.

## 10. Demo walkthrough (steps only -- no invented numbers)

1. **Scenario tab**: pick a preset (tiny hand-verified example, or the real default scenario once
   the engine is present) and point out the preference/compatibility heatmaps and `gamma`.
2. **Assignment tab**: click "Random" to build a profile, then walk through the resulting teams,
   per-student utilities, welfare, and potential.
3. **Equilibrium tab**: show a non-equilibrium assignment's deviation table, then click "Reset" or
   pick a known-stable profile and show the "stable against unilateral deviations" message.
4. **Simulation tab**: click "Run dynamics" from an unstable start, step through the trace slider,
   and point out the final badge is re-verified by a fresh `is_nash` call, not the `converged` flag.

## 11. Known limitations (for the report's limitations section)

- Synthetic data only; no real course/student data was used or claimed.
- Only unilateral deviations are checked; coalition-proofness is out of scope.
- Exhaustive equilibrium enumeration is exponential in student count and capped at 100,000 profiles
  in the engine; the UI doesn't expose it (see Section 6).
- `README.md`, the test plan/log, oracle checks, report, slides, and screenshots are not yet created
  (Ayush's deliverables per the team plan).
