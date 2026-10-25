"""Handbook sections 6-10: frontend and demo, testing, installation, question bank, ownership map."""
from __future__ import annotations

import os

from PIL import Image
from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak

import game_engine as ge

from viva_lib import (BL, CALL, CHECK, CODE, H1, H2, H3, NL, P, PB, QA, RAW, SHOT, SP, T)

APP_COMMIT = "c94f918"


def shot(F, name, caption, y0, y1, max_h=125):
    """Embed the main-area region y0..y1 of a screenshot (content spans x=370..1370 in every capture)."""
    path = os.path.join(F["root"], "screenshots", name)
    w, h = Image.open(path).size
    return SHOT(path, f"{caption} __(file `screenshots/{name}`, region of the page; real engine; app code of commit `{APP_COMMIT}`; automated Chrome run.)__",
                crop=(370, y0, 1370, min(h, y1)), max_w_mm=172, max_h_mm=max_h)


def section6_frontend(F):
    S = F["sc"]["students"]
    s = [H1("6. The frontend and the live demonstration")]
    s += [P("The app is a thin layer: it holds state, calls the engine and draws the results. It never implements its own model when the real engine is present. "
            "Every control below was exercised in a real Chrome session; the screenshots are from that run.")]
    s += [H2("6.1 Every control, what it changes, what it shows")]
    s += T([["Control (exact label)", "Where", "What it changes", "What to look at"],
            ["Scenario preset", "sidebar", "Switches between *Tiny hand-verified example* (2x2), *Default scenario* (8 students, 3 projects, γ = 2) and *Custom mock scenario*. The assignment resets to everyone on project 0.", "Scenario tab changes; header still says \"Real engine detected\"."],
            ["Number of students / projects, Crowding parameter (gamma), Random seed", "sidebar, Custom preset only", "Builds a random scenario in the same format (frontend-generated, not the team's dataset).", "Useful to show the model at other sizes; still validated by the real engine."],
            ["Regenerate scenario", "sidebar", "Rebuilds the current preset and resets the assignment.", "Back to a known state during a demo."],
            ["Student order each sweep: round_robin / random", "sidebar", "Update order used by *Run dynamics*.", "Different orders can reach different equilibria (section 3.9)."],
            ["Dynamics seed (default 7), Max sweeps (default 50)", "sidebar", "Seed used by the random order; sweep limit.", "If the limit is hit the status says *Not converged*."],
            ["Per-student selectboxes", "Assignment tab", "Set one project per student (always a valid profile).", "Teams, utilities, welfare and Φ update at once."],
            ["Seed box, Random, ↺ Reset", "Assignment tab", "Random = seeded random assignment (`random_profile`); Reset = everyone on project 0.", "Reset on the default scenario gives welfare −670 and many deviations; Random with seed 1 gives [0,2,0,1,0,1,1,1]."],
            ["▶️ Run dynamics", "Simulation tab", "Runs best-response dynamics from the Assignment tab's assignment (it does not change that assignment).", "Sweeps run, Moves made, Status, trace, step slider, welfare/Φ chart."],
            ["Inspect profile after move #", "Simulation tab", "Replays the first k moves.", "Teams after k moves; useful for narrating the trace."]],
           [0.22, 0.13, 0.35, 0.30], size=7.8)
    s += [H2("6.2 The four tabs, with real screenshots")]
    s += [H3("Scenario tab: the players, the projects and the parameters")]
    s += [P("Shows the student table with skills, the project list, the crowding parameter and two heatmaps: preferences (0–10) and teammate compatibility w (blue = synergy, red = friction). "
            "It is where you say that the data is synthetic (the header carries the engine's synthetic-data notice).")]
    s += [shot(F, "S1b_scenario_default_preset.png", "Figure 4. Scenario tab, Default scenario (tables and the start of the preference heatmap).", 570, 1330)]
    s += [H3("Assignment tab: build an assignment and read its numbers")]
    s += [P(f"The demo start assignment ({', '.join(S[i] + '→' + 'CWE'[x] for i, x in enumerate(F['demo_start']))}) has welfare {sum(F['demo_check']['utilities'])} and potential {ge.potential(F['demo_start'], F['sc'])}. "
            "Per-student utilities appear in the table and bar chart.")]
    s += [shot(F, "S2b_assignment_demo_start.png", "Figure 5a. Assignment tab controls: Random, Reset and one selectbox per student (demo start).", 690, 960),
          shot(F, "S2b_assignment_demo_start.png", "Figure 5b. Evaluation panel at the demo start: welfare 15, potential 35, teams and per-student utilities.", 1030, 1545)]
    s += [H3("Equilibrium tab: is this assignment stable?")]
    s += [P("If not stable, it states how many **distinct students** have a profitable move, gives an example, and lists every profitable deviation with current utility, new utility and gain. "
            "(An earlier version counted deviation entries, so all-on-one-project showed \"16 student(s)\" for 8 students; this was fixed in commit `c94f918` with a regression test.)")]
    s += [shot(F, "S3_equilibrium_demo_start_unstable.png", "Figure 6. Equilibrium tab at the demo start: 2 students have a profitable move (Dara gains 3, Eli gains 4).", 570, 1010)]
    s += [H3("Simulation tab: best-response dynamics")]
    s += [P("Shows sweeps, moves and status, the move-by-move trace, a slider to inspect any intermediate assignment, and a welfare/potential chart. The final status is **re-verified with a fresh equilibrium check**.")]
    s += [shot(F, "S4_simulation_round_robin.png", "Figure 7. Simulation tab, round_robin from the demo start: 3 sweeps, 4 moves, Stable, ending at welfare 29.", 690, 1440)]
    s += [shot(F, "S5_simulation_random_order_seed7.png", "Figure 8. Same start, update order random (seed 7): 4 sweeps, 4 moves, Stable, but a different equilibrium with welfare 23.", 690, 1440)]
    s += [H2("6.3 How to demonstrate stability versus maximum welfare")]
    s += NL([f"On the Assignment tab set the **worst equilibrium** [0, 2, 1, 2, 2, 1, 0, 0] (Asha→C, Bram→E, Chen→W, Dara→E, Eli→E, Farah→W, Goran→C, Hana→C). Welfare **{F['worst_eq']['welfare']}**, potential {F['worst_eq']['potential']}.",
             "Open the Equilibrium tab: it says the assignment is **stable**. Nobody can gain by moving alone, yet 16 is far below the best attainable welfare of 29.",
             "Now set [0, 0, 1, 0, 1, 1, 2, 2] (welfare **29**, the maximum). The Equilibrium tab says it is **not stable**: Eli gains 2 by moving. So the best welfare is not even guaranteed to be an equilibrium.",
             "Finish by running the dynamics from the demo start with round_robin (ends at the stable welfare-29 assignment) and random (ends at a stable welfare-23 assignment): stable outcomes differ in quality."])
    s += [shot(F, "S6_assignment_worst_equilibrium_welfare16.png", "Figure 9. The worst equilibrium on the Assignment tab: welfare 16, potential 38.", 1030, 1545),
          shot(F, "S7_equilibrium_worst_equilibrium_stable.png", "Figure 10. The same assignment on the Equilibrium tab: stable.", 570, 900),
          shot(F, "S8b_equilibrium_welfare_optimum_not_stable.png", "Figure 11. The welfare-29 assignment [0,0,1,0,1,1,2,2]: not stable, Eli gains 2.", 570, 1010)]
    s += [CALL("warn", "Honest status of the browser evidence",
               "These screenshots come from an **automated** Chrome run (Playwright) in which every on-screen metric and message was compared with the engine. "
               "A **manual** walkthrough by a team member on the presentation machine has **not** yet been done. Dataframe contents are drawn on a canvas and were checked by eye. "
               "Two cosmetic defects were observed and not fixed: an empty rounded bar above the title, and the Simulation chart's legend overlapping its title.")]
    return s


def section7_testing(F):
    s = [H1("7. Testing and validation")]
    s += [CALL("ok", "Latest recorded run",
               f"`python -m pytest -q` → **{F['tests_passed']} passed, {F['tests_failed']} failed, {F['tests_skipped']} skipped** in {F['tests_secs']} s, on commit `{F['tests_commit'][:7]}`, "
               f"clean working tree, fresh virtual environment, {F['tests_when']}. Source: `docs/results/pytest_output.txt`. "
               f"(Collection on the final commit `{F['short']}` finds {F['tests_collected']} tests; only evidence/PDF files changed after the recorded run.)")]
    pf = F["tests_per_file"]
    s += [H2("7.1 What each test group establishes, and what it does not")]
    s += T([["Test file", "Tests", "What it establishes", "What it does NOT establish"],
            ["`tests/test_game_engine.py`", str(pf.get("tests/test_game_engine.py", "?")),
             "Hand-solved fixtures (TINY, TRIO, COORD, REPEL), the exact-potential and welfare identities as property tests, tie handling, input validation, immutability, determinism, enumeration on small games, matching pennies has no pure equilibrium, dynamics endpoints lie in the enumerated set.",
             "That the model is a good model of real teams; correctness of any code outside the engine."],
            ["`tests/test_integration.py`", str(pf.get("tests/test_integration.py", "?")),
             "The documented UI contract: return keys and types, JSON-serialisability, pandas/NumPy inputs, error behaviour, the CLI report, and that saved results in `docs/results/` are not stale (test I06).",
             "That the UI uses the contract correctly (that is the UI tests' job)."],
            ["`tests/test_ui_smoke.py`", str(pf.get("tests/test_ui_smoke.py", "?")),
             "The Streamlit app boots with four tabs and no exception, the Run dynamics button works, the real engine is used (not the mock), a broken-but-present engine is not misreported as missing, strict mode raises, the distinct-student count (8, not 16).",
             "Table contents or chart pixels; it uses Streamlit's AppTest, not a real browser. Some tests check the **mock** engine against the tiny example, which proves the mock is faithful, not that the real engine is."],
            ["`tests/test_independent_crosscheck.py`", str(pf.get("tests/test_independent_crosscheck.py", "?")),
             "A separate computation from `docs/MODEL.md` reproduces 6,561 / 23 / 29 / PoS 1 / PoA 29/16, the potential identity on every profile and deviation, and agrees with the engine, including dynamics from all 6,561 starts.",
             "Independence of authorship (same author as the engine); not a substitute for a second person's oracle."]],
           [0.20, 0.07, 0.43, 0.30], size=7.8)
    s += [H2("7.2 Real engine versus mock engine")]
    s += [P("The mock in `app_helpers.py` was written so the frontend could be built before the engine existed. With the engine present it is never selected. "
            "`test_real_engine_loads_successfully_when_available` asserts `using_mock is False` and that `INTERFACE_VERSION == \"1.0\"`; the header of every screenshot shows \"Real engine detected\". "
            "A mock figure would carry a visible mock badge.")]
    s += [H2("7.3 Known limitations and defects (stated honestly)")]
    s += BL(["**Pending verification:** the formal independent re-implementation and Excel oracle (tasks Q4, Q5, O-01..O-04) are not in the repository; the cross-check here is prepared by the engine's owner.",
             "**Pending:** a manual walkthrough on the presentation machine; the official title and faculty rules.",
             "**Cosmetic UI defects (open):** empty rounded bar above the page title (the header-card `<div>` cannot wrap Streamlit elements); legend overlaps the title of the Simulation chart.",
             "**Browser testing was automated:** Streamlit's canvas tables are not readable as text, so team compositions were checked by eye against the engine, not by script.",
             "**Streamlit floor:** `streamlit>=1.51` was determined by inspecting the 1.50.0 and 1.51.0 wheels (width parameter on `st.plotly_chart`); the full suite was run on 1.66.1 only.",
             "**Timings** are measured on one machine and are indicative only.",
             "**Synthetic data:** results illustrate the model, not real student behaviour."])
    return s


def section8_install(F):
    s = [H1("8. Dependencies, installation and execution (Windows, verified)")]
    s += [P("These commands were run in a fresh virtual environment for this document. Use PowerShell from the repository root.")]
    s += CODE("git clone https://github.com/AryanRajguru22/STRATOS.git\ncd STRATOS\npython -m venv .venv\n.venv\\Scripts\\activate\n"
              "python -m pip install -r requirements.txt\nstreamlit run app.py          # opens http://localhost:8501\npython -m pytest -q          # full test suite")
    s += T([["Purpose", "Command", "Expected result"],
            ["Run the app", "`streamlit run app.py`", "Browser opens; header shows green \"Real engine detected: game_engine.py and sample_data.py loaded.\""],
            ["Run all tests", "`python -m pytest -q`", f"`{F['tests_collected']} passed` (about 20 s)"],
            ["Engine report (default scenario)", "`python game_engine.py --report`", "JSON: 6,561 profiles, 23 equilibria, optimum welfare 29, PoS 1.0, PoA 1.8125"],
            ["Independent cross-check", "`python scripts/independent_crosscheck.py --compare`", "Ends with `comparison with game_engine: IDENTICAL` (about 4 s)"],
            ["Regenerate saved evidence", "`python scripts/generate_results.py`", "Rewrites `docs/results/*`; run it only on a clean, committed tree so the provenance is true"],
            ["Strict engine mode", "`$env:STRATOS_REQUIRE_REAL_ENGINE=\"1\"; streamlit run app.py`", "Any engine problem becomes a hard error instead of a mock"],
            ["Different port", "`streamlit run app.py --server.port 8765`", "Use if 8501 is busy"],
            ["Health check", "`curl http://localhost:8501/_stcore/health`", "`ok`"]], [0.22, 0.43, 0.35], size=8)
    s += [H2("Roles of the four packages")]
    s += BL(["**Streamlit** runs the web app and provides tabs, widgets, session state and the `AppTest` harness used in tests.",
             "**pandas** holds the tables that the UI displays (students, teams, utilities, deviations, the dynamics trace).",
             "**Plotly** draws the two heatmaps, the utility bar chart and the welfare/potential line chart. It was missing from `requirements.txt` until commit `859a798`; a fresh install without it fails with `ModuleNotFoundError: No module named 'plotly'`.",
             "**pytest** discovers and runs the tests (`pytest.ini` sets `pythonpath = .` and `testpaths = tests`)."])
    s += [H2("If something goes wrong")]
    s += T([["Symptom", "Likely cause", "Fix"],
            ["`ModuleNotFoundError: plotly` (or streamlit)", "Dependencies not installed in the active environment", "Activate `.venv`, then `python -m pip install -r requirements.txt`"],
            ["`.venv\\Scripts\\activate` is blocked", "PowerShell execution policy", "`Set-ExecutionPolicy -Scope Process Bypass`, then activate again"],
            ["`TypeError` mentioning `width` on a button/chart", "Streamlit older than 1.51", "`python -m pip install -U \"streamlit>=1.51\"`"],
            ["Red box \"found but failed to import\"", "`game_engine.py` / `sample_data.py` has a bug or was damaged", "Run `python game_engine.py --report` to see the real error; restore the file from git"],
            ["Page does not load", "Port busy or server stopped", "Close the other server or use `--server.port`"],
            ["A number differs from this handbook", "Different preset, gamma, assignment, seed or update order in the sidebar", "Compare with `python game_engine.py --report`; use the Default scenario, dynamics seed 7, max sweeps 50"]],
           [0.30, 0.33, 0.37], size=8)
    return s


def bank(F):
    sc = F["sc"]
    e = F["enum"]
    rr, rd = F["demo_rr"], F["demo_rand7"]
    out = []

    def group(title, qs):
        out.append(CondPageBreak(55 * mm))
        out.append(H2(title))
        for q in qs:
            out.extend(QA(*q))

    group("9.1 Project motivation and scope", [
        ("What problem does STRATOS address?", "Forming project teams when students have preferences over projects, differ in how well they work together, and dislike crowded teams. "
         "Because each student's outcome depends on others' choices, we treat it as a game and ask which assignments are stable, how they compare with the best assignment, and whether repeated switching settles down.", "basic"),
        ("Why not just choose the assignment with the highest total welfare?", f"Because it might not be stable. In our default scenario the maximum welfare is {e['optimal']['welfare']}, attained by two assignments, and one of them is not an equilibrium: Eli gains 2 by moving. "
         "A planner can propose it, but a student with a profitable move has a reason to defect. Game Theory lets us ask about stability, not only about total welfare.", "basic"),
        ("Is this real student data?", "No. Every student, preference and weight is fictional and synthetic, chosen so strategic behaviour is visible in a small demonstration. The app and README say so. "
         "The results illustrate how the model behaves, not what real students would do.", "basic"),
        ("Is STRATOS a system a university could deploy to assign teams?", "No. It is a demonstration and analysis tool for a course project. It has no capacity limits, no real data and no authentication, and it analyses only unilateral deviations.", "scope"),
        ("What is deliberately out of scope?", "Coalition-proof equilibria, hard team-size capacities, incomplete information, mixed strategies, real data and large-scale heuristics. Exhaustive enumeration is capped at 100,000 assignments.", "scope"),
        ("What is the official title of your project?", RAW("<b>[PENDING]</b> Do not guess. Say: \"Our topic is strategic behaviour in university course / project team formation; we are confirming the exact title and group row against the official sheet.\" "
                                                       "Ayush owns this check (task Q1). Update this answer once it is done.")),
        ("Why did you build the interface in Streamlit?", "It lets us write the UI in the same language as the engine, gives interactive widgets and charts with little code, and starts with a single command (`streamlit run app.py`). "
         "The engine is independent of it, so the UI could be replaced without touching the mathematics.", "arch"),
    ])
    group("9.2 Game Theory fundamentals", [
        ("What are the three ingredients of a game, and what are they here?", "Players: the 8 students. Strategies: each student's choice of one of 3 projects. Payoffs: the utility function u_i(s) = preference + compatibility with teammates − crowding cost.", "GT"),
        ("Is this a simultaneous or sequential game?", "Static and simultaneous with complete information: everyone chooses at once and knows all parameters. Best-response dynamics is an adjustment process we simulate to see where students might settle; it is not a sequential game.", "GT"),
        ("What is a best response?", "The project that maximises a student's utility given everyone else's current choices. Ours keeps the current project if it is already a maximiser, otherwise takes the lowest-index maximiser.", "GT"),
        ("Define a Nash equilibrium. Is yours strict or weak?", "A profile where nobody can gain by deviating alone. Ours is the weak form: ties do not count as profitable deviations (gain must exceed 10⁻⁹), so an equilibrium may leave a student indifferent between projects.", "GT"),
        ("Does every game have a pure Nash equilibrium?", "No. Matching pennies has none (our generic checker confirms it returns an empty list). Every finite game has a mixed equilibrium (Nash's theorem), but for our model the potential-game argument guarantees a **pure** one, so we do not need mixed strategies.", "GT"),
        ("Is there a dominant strategy for a student?", "Not in general. A student's best project depends on who else is where and how crowded each team is, so the best choice changes with the others' choices. That is why equilibrium, not dominance, is the right concept.", "GT"),
        ("What is the difference between Pareto optimality and welfare maximisation?", "Welfare maximisation picks the assignment with the largest sum of utilities. Pareto optimality only says no other assignment makes everyone at least as well off and someone strictly better off. "
         f"A welfare maximiser is always Pareto-optimal, but a Pareto-optimal assignment need not maximise welfare. {F['n_pareto_eq']} of our {e['n_equilibria']} equilibria are Pareto-optimal.", "GT"),
        ("Give an everyday analogy for 'stable but not optimal'.", "The prisoner's dilemma: each player's best reply is to defect, so (defect, defect) is an equilibrium, yet both would be better off cooperating. In our game the worst equilibrium has welfare 16 while the optimum is 29.", "GT"),
    ])
    group("9.3 Mathematical model and equations", [
        ("Write the utility function and explain each term.", "u_i(s) = p(i, s_i) + Σ over teammates j of w(i,j) − γ(k_i − 1)². The first term is how much i likes their project, the second is the summed compatibility with the students who share it (positive = synergy, negative = friction), "
         "and the third is a crowding cost that grows quadratically with team size k_i (counting i).", "model"),
        ("Compute the crowding cost for a team of 5 when γ = 2.", "c(5) = 2·(5−1)² = 2·16 = 32 for each member, so the team pays 5·32 = 160 in total.", "numeric"),
        ("Three students share a project. Each has preference 4 for it, every pair has w = 1, and γ = 1. What is each utility and the welfare?", "k = 3, so c(3) = 1·2² = 4. Each has two teammates: u = 4 + (1 + 1) − 4 = 2. Welfare = 3·2 = 6.", "numeric"),
        ("Why must w be symmetric?", "Each pair's compatibility enters the potential once, and enters both members' utilities. If w(i,j) ≠ w(j,i), a move by i would change the potential by something different from i's utility change, and the exact-potential property fails. The engine rejects asymmetric w.", "model"),
        ("What does a negative w mean? What does w = 0 mean?", "Negative: two students work badly together, so sharing a project reduces utility. Zero: no effect. With our skill-based data, two students with identical skill sets get w = 0 − 1 = −1.", "model"),
        ("Why is welfare W(s) = Σp + 2Σw − Σ n·c(n), with a factor 2?", "Summing every student's utility counts each compatible pair twice (once for each member), so the pair term is doubled, while the potential counts it once. The crowding terms add up to n(t)·c(n(t)) per project.", "model"),
        ("What is γ and what happens at γ = 0?", "γ scales the crowding cost. At γ = 0 crowding disappears, so compatibility and preference alone decide, and large teams are not penalised. Larger γ pushes teams to be smaller and more balanced.", "model"),
        ("Do utilities have units? Is adding them up meaningful?", "They are on an arbitrary common scale (preferences are 0–10). Adding them assumes utilities are comparable across students, which is a modelling assumption, not a fact; we flag this as a limitation of welfare as a measure.", "model"),
        ("What does \"ties\" mean for the equilibrium definition?", "If a student is exactly indifferent, moving is not a profitable deviation, so the profile can still be an equilibrium. We use the weak definition because it is the standard one and keeps the best-response rule deterministic.", "model"),
    ])
    group("9.4 Nash equilibrium and potential games", [
        ("What is a potential game?", "A game with a function Φ over strategy profiles such that any player's change in payoff from a unilateral deviation equals the change in Φ. If it exists, local maxima of Φ are pure equilibria.", "potential"),
        ("State your potential function and prove the key property.", "Φ(s) = Σ p(i,s_i) + Σ_{same-team pairs} w(i,j) − Σ_t Σ_{k=1}^{n(t)} c(k). When i moves from team a to team t, only the terms involving i and these two teams change, and the change equals "
         "[p(i,t) + Σ w on t − c(n(t)+1)] − [p(i,a) + Σ w on a − c(n(a))], which is exactly i's utility change.", "potential"),
        ("Why does the potential guarantee that an equilibrium exists?", "There are finitely many assignments, so Φ has a maximum. From a maximiser no deviation can raise Φ, hence none can raise the deviator's utility, so it is a pure equilibrium.", "potential"),
        ("Why does best-response dynamics converge?", "Every strictly profitable move raises Φ by exactly the mover's gain, so Φ strictly increases, assignments cannot repeat, and there are finitely many. With integer data each move raises Φ by at least 1, bounding the number of moves by Φ_max − Φ_min.", "potential"),
        ("Does converging mean reaching the best equilibrium?", f"No. From the same start, round-robin ended at welfare {ge.social_welfare(rr['final_profile'], sc)} and random order (seed 7) at {ge.social_welfare(rd['final_profile'], sc)}; both are equilibria. The dynamics finds an equilibrium, not the best one.", "potential"),
        ("Is every equilibrium a maximiser of Φ?", f"No. Φ's maximum is {e['potential_maximizers']['potential']}, but equilibria have other Φ values (the table of 23 equilibria shows several). Φ-maximisers are equilibria; the converse fails.", "potential"),
        ("Could your proof fail for some data?", "It requires symmetric w and a crowding cost depending only on team size. Asymmetric compatibility or a non-pairwise team bonus breaks it. That is why the engine validates symmetry and why the code never relies on the theorem: it checks the equilibrium condition directly.", "potential"),
    ])
    group("9.5 Algorithms and implementation", [
        ("How do you check whether an assignment is a Nash equilibrium?", "For every student and every other project, build the deviated assignment, compute that student's utility, and compare it with the current one. If any gain exceeds ε = 10⁻⁹ the assignment is not stable. Cost n(m−1) = 16 utility evaluations for the default scenario.", "algo"),
        ("How does exhaustive enumeration work and what does it cost?", f"It generates all m^n assignments, computes utilities, welfare and potential for each, keeps those with no profitable deviation, and finds the welfare and potential maximisers; Pareto-optimality compares each equilibrium with every other assignment. It is exponential in n; the default takes about {F['timing']['median_seconds']} s, and it refuses more than 100,000 assignments.", "algo"),
        ("Why is the result deterministic?", "Visiting order is fixed (round_robin) or a seeded permutation (random); ties are broken by the lowest project index; there is no hidden randomness. The same inputs and seed give identical output.", "algo"),
        ("What does the engine do with invalid input?", "Every public function validates its input and raises `StratosError` (or `ScenarioError`/`ProfileError`) with a message naming the offending field and index, e.g. an asymmetric w. Booleans, strings, NaN and infinities are rejected. The UI catches the error and shows it instead of crashing.", "algo"),
        ("Does the engine modify its inputs?", "No. It compiles the scenario into an internal copy; tests check that inputs are unchanged. Outputs are plain lists, dicts and numbers so `json.dumps` always works.", "algo"),
        ("Why does `best_response_dynamics` return `is_nash_final` and the UI re-checks anyway?", "`converged` only says one sweep had no move. Stability is a separate claim, so the engine recomputes it from scratch and the UI does a fresh `is_nash` call as well. It is cheap and removes any trust in a flag.", "algo"),
        ("What is `rounds` in the dynamics result?", "The number of sweeps performed, including the final sweep in which nobody moved. For the demo start under round-robin: 3 sweeps and 4 moves.", "algo"),
        ("How would the method scale to 100 students?", "Dynamics scales fine: a sweep costs O(n²m). Enumeration does not (m^n); you would drop it and rely on dynamics from many starts, or on integer programming/heuristics to look for the welfare optimum.", "algo"),
    ])
    group("9.6 Architecture and frontend", [
        ("Why is the engine separate from the UI?", "So it can be tested and run without a browser, reused by the CLI report, and verified independently. The engine imports neither Streamlit, NumPy nor pandas, and the interface between them is a documented contract (`docs/INTERFACE.md`).", "arch"),
        ("How does a click on a selectbox end up as a number on screen?", "The selection is stored in `st.session_state.profile` (a list of project indices). On rerun the app validates it, calls `utilities`, `teams`, `social_welfare` and `potential`, converts the results into DataFrames and Plotly figures through `app_helpers`, and Streamlit redraws.", "arch"),
        ("What is the mock engine and why does it exist?", "A contract-mirroring stand-in in `app_helpers.py`, written so the frontend could be developed before the engine existed. With the real engine present it is never used; if the engine is missing the app labels everything as mock, and if it is present but broken the app shows a red error. `STRATOS_REQUIRE_REAL_ENGINE=1` makes any fallback an error.", "arch"),
        ("How do you know the screen shows the engine's numbers?", "Tests assert that the real engine is loaded, and the Chrome walkthrough compared the on-screen metrics (welfare, potential, sweeps, moves, status, messages) with values computed by the engine for " + str(F["n_shots"]) + " states.", "arch"),
        ("What happens if a user supplies bad input?", "The UI only offers valid choices, and any `StratosError` from the engine is shown with `st.error`. The app does not crash. The Custom preset's sliders are bounded.", "arch"),
        ("Why does the Simulation tab not change the Assignment tab's assignment?", "Dynamics starts from the current assignment and keeps its own result in `last_dynamics_result`. This lets you run different update orders from the same start, which is exactly what the demo does.", "arch"),
        ("Why did you replace `use_container_width` and what did that require?", "Streamlit deprecated it in favour of `width=\"stretch\"`. That parameter exists on `st.plotly_chart` only from Streamlit 1.51, so the declared minimum was raised from 1.30 to 1.51 (checked in the 1.50.0 and 1.51.0 packages).", "arch"),
    ])
    group("9.7 Testing and independent validation", [
        ("How do you know your engine is correct?", f"Several layers: hand-solved fixtures, property tests (potential and welfare identities on random games), tie and validation tests, enumeration checked against dynamics endpoints, matching pennies through a generic checker, a CLI report, and an independent recomputation that agrees exactly. Latest recorded run: {F['tests_passed']} passed.", "test"),
        ("What does the independent cross-check do and what are its limits?", "It re-derives utilities, welfare, potential, equilibria, optimum, Pareto flags, PoA/PoS and dynamics from MODEL.md with different code and exact fractions, without importing the engine for its own numbers, then diffs against the engine. "
         "Limit: it shares an author and a specification with the engine. A second person's re-implementation and an Excel oracle are planned and not yet in the repository.", "test"),
        ("What does test I06 do?", "It fails if `sample_data.py` or the engine changes without regenerating `docs/results/`, so saved evidence can never silently go stale. A failure there means the check is working.", "test"),
        ("What does `AppTest` check, and what doesn't it?", "It runs the Streamlit script headlessly and lets tests click widgets and inspect elements: no exceptions, four tabs, the dynamics button works, messages appear. It does not render pixels or canvas tables, so we added an automated Chrome run for screenshots. A manual walkthrough on the demo machine is still pending.", "test"),
        ("Which test would catch a wrong crowding formula?", "The hand-solved fixtures (for example the tiny example's utilities [6, 2] at [0, 0], which depend on c(2) = 1) and the independent cross-check, which recomputes every utility with its own implementation of c(k).", "test"),
        ("Did the tests ever find a real defect?", "Yes, in the course of the project: Plotly was imported but missing from `requirements.txt`, which broke a fresh install; and the Equilibrium tab counted deviation entries instead of students (showed 16 for 8 students). Both were fixed, the second with a regression test.", "test"),
        ("What could still be wrong that your tests would not catch?", "A mistaken modelling assumption (the tests verify the code against the model, not the model against reality), synthetic data being unrepresentative, and any visual defect not covered by an assertion, such as the two cosmetic issues we know about.", "test"),
    ])
    group("9.8 Results and interpretation", [
        ("Summarise your main numerical results.", f"For the default scenario: {e['n_profiles']:,} assignments, {e['n_equilibria']} pure Nash equilibria, maximum welfare {e['optimal']['welfare']} (two optimal assignments, only one stable), price of stability {e['price_of_stability']}, price of anarchy {e['price_of_anarchy']} (= 29/16), and {F['n_pareto_eq']} of the 23 equilibria Pareto-optimal.", "results"),
        ("What does a price of stability of 1.0 mean?", "The best equilibrium achieves the maximum possible welfare (29), so stability does not cost anything in the best case. Our enumeration found that the welfare-29 assignment [0,0,1,0,2,1,2,2] is itself an equilibrium.", "results"),
        ("What does the price of anarchy of 1.8125 mean?", "The worst equilibrium has welfare 16 and 29/16 = 1.8125: selfish stable behaviour can leave the class with about 55% of the achievable welfare. It is a worst-case measure over equilibria.", "results"),
        ("Why are there 23 equilibria and not 1?", "Many different assignments are mutually consistent: moving one student alone does not pay in any of them. Because the game has many local optima of Φ (and equilibria that are not Φ-maximisers), there is no unique stable outcome.", "results"),
        ("Why can the two update orders end differently?", "Each order is a different path through the assignments; each path climbs Φ to some local maximum in the sense of unilateral moves, and there are 23 such endpoints. All 6,561 starts under round-robin end in one of them.", "results"),
        ("Why did the ratios become None at γ = 3?", "Higher crowding makes some equilibria have non-positive welfare, so dividing the optimum by that welfare is meaningless. The engine returns null and reports the gaps instead (here " + str(F['gamma3']['welfare_gap_best_equilibrium']) + " and " + str(F['gamma3']['welfare_gap_worst_equilibrium']) + ").", "results"),
        ("If students are rational, why would they end at the worst equilibrium?", "Rationality only gives local improvements. From a bad starting assignment, a sequence of individually sensible moves can end in a stable but poor assignment, because nobody can coordinate a joint move. That is exactly the cost of lacking coordination.", "results"),
        ("What would you recommend a planner do, based on the model?", "Use the equilibrium analysis to find an assignment that is both high-welfare and stable (here [0,0,1,0,2,1,2,2], welfare 29), rather than only maximising welfare or letting students settle on their own. With synthetic data this is an illustration, not advice about real classes.", "results"),
    ])
    group("9.9 Limitations, trade-offs and future improvements", [
        ("What are the main limitations?", "Synthetic data and assumed weights; complete information; only unilateral deviations; additive pairwise compatibility; no hard capacities; exhaustive search is exponential; the UI does not display PoA/PoS.", "limits"),
        ("What would you add with more time?", "An Analysis tab showing equilibria and efficiency in the UI; coalition-proof analysis; hard capacities; real preference data; a heuristic search for large classes; and the independent oracle.", "limits"),
        ("Why unilateral deviations only?", "It is the standard Nash notion and keeps the potential structure. Groups moving together require coalition concepts (strong equilibrium, coalition-proof equilibrium), which are harder to compute and may not exist.", "limits"),
        ("What is the trade-off between soft crowding and a hard cap?", "Soft crowding keeps every deviation feasible and preserves the potential property, but cannot enforce a maximum size. A hard cap is more realistic but makes the feasible set depend on others' choices and can break existence results.", "limits"),
        ("How sensitive are results to the data?", "Considerably: the number of equilibria and the PoA depend on preferences, compatibility and γ (at γ = 3 the ratios are undefined). We deliberately chose data to make strategic behaviour visible, and say so.", "limits"),
    ])
    group("9.10 Individual contribution and teamwork", [
        ("Who did what?", "See section 10: the ownership map is built from the repository's git history and the team plan, and lists what is evidenced and what is pending. Each member must describe only their own part and say \"I understand and can explain\" for the rest.", "team"),
        ("Tell me about a problem you found and fixed.", "Examples from the record: the missing Plotly dependency (found by a fresh-install test), the deviation count that showed 16 for 8 students (found in review, fixed with a regression test), the silent mock fallback (now a loud error), and a stale Streamlit minimum version.", "team"),
        ("How did you make sure the pieces fit together?", "A written interface contract (`docs/INTERFACE.md`), integration tests against it, a results generator with git provenance, and fresh-environment installs.", "team"),
        ("How much of the work did the tools do?", RAW("<b>Answer honestly.</b> Parts of the code, tests, documentation and these PDFs were prepared with AI assistance (Claude) under the team's direction and were then run and checked. "
                                                      "Each member should be able to explain the part they present without notes. If asked, say so plainly.")),
        ("What did you personally not do, and who did?", "Be ready to say, for example: the engine and model are Aryan's, the app is Harsh's, verification and documentation tasks are Ayush's; whoever presents the rest explains it but does not claim to have built it.", "team"),
    ])
    return out


def section9_questions(F):
    s = [PB(), H1("9. Likely viva questions and model answers")]
    s += [P("Answers are written to be **spoken**: lead with the one-sentence answer, then add the supporting detail only if asked. Tags show the topic. "
            "Items marked **[PENDING]** or **Answer honestly** need a decision from the team before the viva.")]
    s += bank(F)
    return s


def section10_ownership(F):
    s = [H1("10. Four-member contribution and ownership map")]
    s += [P("This map is built only from what the repository and the team plan show. **Do not claim anything that is not supported here or that you did not do yourself.** "
            "Commits are listed by the author name recorded in git.")]
    rows = [["Member", "Role in the team plan", "Evidence in the repository", "Be prepared to defend"]]
    ar = F["log_by_author"].get("AryanRajguru22", [])
    ha = F["log_by_author"].get("Harsh Kumar Singh", []) + F["log_by_author"].get("Harsh", [])
    ay = [a for a in F["log_by_author"] if "ayush" in a.lower()]
    def fmt(commits):
        return "<br/>".join(f"<font name='Mono' size='7'>{h}</font> {d} {sub if len(sub) <= 62 else sub[:60].rsplit(' ', 1)[0] + '…'}" for h, d, sub in commits[:9])
    rows.append(["**Aryan Rajguru**", "Game theory engine, mathematical model, technical integration and sign-off; owns `game_engine.py`, `sample_data.py`, `docs/MODEL.md`, `docs/INTERFACE.md`, engine and integration tests, `docs/results/`, `requirements.txt`",
                 RAW(fmt(ar)), "The whole model: utility, potential proof, equilibrium and dynamics, enumeration and PoA, test strategy, the results and their limits"])
    rows.append(["**Harsh Kumar Singh**", "Frontend: Streamlit app, UI integration, UI smoke tests; frontend README draft",
                 RAW(fmt(ha)), "The four tabs, every control, session state, engine loading and the mock fallback, UI tests, the live demonstration"])
    if ay:
        rows.append(["**Ayush**", "Independent verification, README, report, slides, test log, demo script (plan section 6)", RAW(fmt([c for a in ay for c in F["log_by_author"][a]])), "Whatever the evidence above supports"])
    else:
        rows.append(["**Ayush**", "Per the team plan: independent verification (Q4, Q5, O-01..O-04), README, test plan/log, report, slides, demo script, viva file, screenshots",
                     RAW("<b>No commits by Ayush were found in the repository</b> when this document was built, and none of the plan's Ayush deliverables (<font name='Mono' size='7.4'>tests/oracle/</font>, report, slides, <font name='Mono' size='7.4'>docs/TEST_LOG.md</font>) are present. "
                         "This is not a judgement of the work done off-repository; it is what can be evidenced."),
                     "Whatever he has actually done. He should explain the testing and verification evidence in this handbook, and **claim only his own work**"])
    rows.append(["**Kashish**", "Fourth team member. Presents and explains selected parts of the completed product (problem, concepts, results, limitations).",
                 "No implementation, testing or documentation is attributed to Kashish, and none should be claimed.", "Problem and motivation, what each tab is for, utility / Nash equilibrium / best-response dynamics in plain words, the meaning of the results, limitations and future work. Must also understand the whole system."])
    s += T(rows, [0.14, 0.26, 0.34, 0.26], size=7.6, valign="TOP")
    s += [CALL("note", "Work prepared for the final release (not attributable to a single team member)",
               "Prepared by Aryan with AI assistance and committed on branch `release/final-product`: the independent cross-check and its tests, `README.md`, `requirements-docs.txt`, the "
               "Streamlit minimum-version fix, the real-browser screenshots with their index, the regenerated `docs/results/`, and these two PDFs. Ayush should review the README and the "
               "verification text because they fall in his areas.")]
    s += [H2("Who can be asked about what")]
    s += T([["Topic", "Primary", "Everyone must still be able to say"],
            ["Utility, potential, equilibrium, dynamics, enumeration, results", "Aryan", "The utility equation, what Nash equilibrium means, why stable ≠ optimal, the headline numbers"],
            ["Tabs, controls, state, demo, UI tests", "Harsh", "What each tab shows and how to read it"],
            ["Testing strategy, verification evidence, documentation, conclusions", "Ayush (to confirm what he did)", "What the tests establish and what is still pending"],
            ["Motivation, concepts in plain language, interpretation, limitations", "Kashish", "How the pieces fit together (architecture)"]], [0.40, 0.20, 0.40], size=8)
    return s
