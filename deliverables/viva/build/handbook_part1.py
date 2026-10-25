"""Handbook sections 0-5: status, overview, architecture, model, worked example, enumeration and results."""
from __future__ import annotations

import game_engine as ge

from facts import utility_breakdown
from viva_lib import (BL, CALL, CODE, EQ, H1, H2, H3, NL, P, PB, QA, RAW, SP, T, KeepTogether, architecture_diagram, dataflow_diagram,
                      make_toc, potential_chart)

PN = {0: "Campus Navigation App", 1: "Wellbeing Survey Analysis", 2: "Event Management Portal"}
PS = {0: "C", 1: "W", 2: "E"}


def I(x): return f"<i>{x}</i>"
def sb(base, s): return f"<i>{base}</i><sub>{s}</sub>"
def fm(n):  # signed number with a real minus sign
    return str(n).replace("-", "−")
def prof_str(p): return " ".join(str(x) for x in p)
def prof_letters(p): return "".join(PS[x] for x in p)


def teams_text(sc, profile):
    out = []
    for t in range(3):
        members = [sc["students"][i] for i, x in enumerate(profile) if x == t]
        out.append(f"{PS[t]}: {', '.join(members) or '(empty)'}")
    return "; ".join(out)


def section0_status(F):
    s = []
    s += [H1("0. Status at a glance: what is verified, and what is still pending")]
    s += [P("This page is deliberately blunt. Everything marked **verified** was actually run on the commit named on the cover. "
            "Everything marked **pending** has not been done, or its evidence is not in the repository, and **must not be claimed** at the viva.")]
    rows = [["Item", "Status", "Evidence (where to look)"],
            [f"Automated test suite", f"**verified**: {F['tests_passed']} passed, {F['tests_failed']} failed, {F['tests_skipped']} skipped",
             f"`docs/results/pytest_output.txt` (run on commit `{F['tests_commit'][:7]}`, clean tree, {F['tests_when']})"],
            ["Engine results recomputed independently of the engine code", "**verified** (by a cross-check script, see note below)",
             "`scripts/independent_crosscheck.py --compare` → IDENTICAL; `docs/results/independent_crosscheck_output.txt`"],
            ["Application runs with the real engine in a real browser", "**verified** (automated Chrome run, not a manual one)",
             f"`screenshots/INDEX.md`, `screenshots/walkthrough_log.json`: {F['n_shots']} steps, on-screen values matched the engine, 0 console errors"],
            ["Manual walkthrough on the presentation machine", "**pending**", "Harsh (frontend owner) + whoever demos; use the checklist in the speaking plan"],
            ["Formal independent checker and Excel oracle (plan tasks Q4, Q5, O-01..O-04)", "**pending / not in repository**",
             "Expected at `tests/oracle/` (Ayush). Not present when this handbook was built."],
            ["Official project title, group row, faculty rules (`Groups.xlsx`, handout)", "**pending**", "Not available to the engineer; plan task Q1 (Ayush)"],
            ["README.md", "**prepared, needs owner review**", "`README.md` was written from the frontend draft and the engine docs; Ayush owns the final README"],
            ["Technical report, slides, test log, demo script, `docs/VIVA.md`", "**pending / not in repository**", "Plan tasks Q6-Q13 (Ayush)"],
            ["Screenshots", "**verified, genuine**", f"`screenshots/` ({F['n_shots']} PNGs, captured from the running app)"]]
    s += T(rows, [0.30, 0.27, 0.43])
    s += [CALL("warn", "Note on \"independent\"",
               "The cross-check recomputes the model from `docs/MODEL.md` with different code (it never imports the engine for its own numbers, "
               "and it uses exact fractions). But it was prepared for Aryan, the same person who owns the engine and the specification, so it is "
               "**independent of the engine's code, not independent of its author**. It supports the numbers; it does not replace the team's "
               "formal independent verification by a second person (Ayush's oracle), which is still to be done.")]
    return s


def section1_overview(F):
    n, m = F["n"], F["m"]
    s = [H1("1. Project overview")]
    s += [H2("1.1 Title and context")]
    s += [P("**Working title (from the task brief):** *Strategic Behavior in University Course / Project Team Formation*. "
            "STRATOS is our Game Theory course project. The software, the mathematics and the evidence are all in one repository: "
            "`https://github.com/AryanRajguru22/STRATOS`.".replace("*Strategic", "__Strategic").replace("Formation*", "Formation__"))]
    s += [CALL("pending", "PENDING: official title and faculty requirements",
               "The exact assigned title, the group row in `Groups.xlsx` and any faculty-specific rules have **not been verified** against the official files "
               "(they were not available to the engineer; the team plan assigns this check to Ayush as task Q1). Until Ayush confirms, say "
               "\"our topic is strategic behaviour in course/project team formation\" and do **not** quote an official title or rubric.")]
    s += [H2("1.2 Problem statement and motivation")]
    s += [P(f"A class of students must end up on project teams. Each student cares about three things: how much they like the project, how well "
            f"they work with the particular classmates who end up on the same project, and how crowded the team is. If students could choose for "
            f"themselves, what each one gets depends on what **everyone else** chooses, which is exactly the situation Game Theory studies.")]
    s += [P("A central planner could simply maximise the total satisfaction of the class. But an assignment that is best on paper is not necessarily "
            "one that people will stay in: if some student could do better by switching alone, the assignment is fragile. STRATOS therefore asks "
            "three questions:")]
    s += NL(["Which assignments are **stable**, meaning no single student gains by switching on their own?",
             "How do the stable assignments compare with the assignment that maximises total welfare?",
             "If students repeatedly switch to their best project, do they settle down, and where?"])
    s += [H2("1.3 Why Game Theory is the right tool")]
    s += BL(["**Strategic interdependence.** A student's utility depends on teammates' choices and on team size, so decisions cannot be analysed one student at a time.",
             "**A solution concept that fits the question.** A pure Nash equilibrium is exactly \"nobody wants to move alone\".",
             f"**Structure we can prove things about.** With symmetric compatibility and a crowding cost that depends only on team size, the game is an exact potential game: a pure equilibrium always exists and best-response dynamics always terminates (section 3.8).",
             "**Measures of efficiency.** Welfare gap, price of stability and price of anarchy quantify what stability costs compared with the best assignment."])
    s += [H2("1.4 What STRATOS does")]
    s += BL([f"Models {n} fictional students choosing among {m} projects, with preference, teammate compatibility and a convex crowding cost.",
             "Provides an engine (`game_engine.py`) that computes utilities, welfare and the potential, finds profitable deviations, checks Nash equilibrium, runs best-response dynamics and enumerates every assignment.",
             "Provides a Streamlit app with four tabs (Scenario, Assignment, Equilibrium, Simulation) so the model can be explored and demonstrated live.",
             "Provides reproducible evidence: a command-line report, a test suite, saved results with git provenance, and an independent cross-check."])
    s += [H2("1.5 Intended users, assumptions, scope and limitations")]
    s += [P("**Intended users:** the project team, the faculty evaluators, and anyone who wants to explore how strategic choice shapes team formation in a small class. "
            "STRATOS is a **demonstration and analysis tool, not a deployed allocation system**.")]
    s += T([["Assumption / limitation", "What it means for the claims we can make"],
            ["All student data and weights are fictional and synthetic", "Results show how the model behaves, not what real students would do. The data was chosen so that strategic behaviour is visible."],
            ["Complete information, static game", "Every student knows every parameter and chooses simultaneously. Best-response dynamics is a simulated adjustment process, not a repeated game."],
            ["Only unilateral deviations", "A stable assignment can still be improved by two or more students moving together; coalitions are not analysed."],
            ["Compatibility is additive and pairwise, and symmetric", "This is what makes the potential argument work. An asymmetric or non-pairwise bonus could break it."],
            ["Soft crowding instead of a hard capacity", "Teams can be any size; large teams are simply costly. Empty teams are allowed."],
            ["Exhaustive enumeration is exponential", "Capped at 100,000 assignments (about 10 students with 3 projects); the default 8 x 3 case takes about "
             f"{F['timing']['median_seconds']} s."],
            ["Ties", "A tie is not a profitable deviation, so a tied assignment can be an equilibrium (weak definition)."]], [0.34, 0.66])
    s += [H2("1.6 Implemented versus only proposed")]
    s += T([["Implemented and evidenced", "Not implemented (future work / out of scope)"],
            [RAW("• Formal model and proof (<font name='Mono' size='8'>docs/MODEL.md</font>)<br/>• Engine with validation, 16 public functions and a CLI report<br/>"
                 "• Four-tab Streamlit app using the real engine<br/>• Test suite and saved results with git provenance<br/>"
                 "• Independent cross-check and real-browser screenshots<br/>• README and this documentation"),
             RAW("• An <b>Analysis tab</b> showing equilibria / price of anarchy in the UI (the numbers exist in the CLI report only)<br/>"
                 "• Coalition-proof equilibria; hard team capacity; incomplete information; mixed strategies<br/>"
                 "• Real student data<br/>• Heuristics for large classes (enumeration is exponential)<br/>"
                 "• Excel oracle and formal second-person verification (pending)<br/>• Report and slides (pending, not in repo)")]],
          [0.5, 0.5], zebra=False)
    return s


def section2_architecture(F):
    s = [H1("2. Complete architecture")]
    s += [P("Everything the user sees is produced by a thin UI layer that calls a self-contained engine. The engine knows nothing about Streamlit, NumPy or pandas, "
            "which is why it can be tested and run from the command line on its own.")]
    s += [architecture_diagram(), SP(6)]
    s += [P("__Figure 1. Architecture. Green = the engine and its data (Aryan), blue/grey = UI and helpers (Harsh), amber = documentation and saved evidence, purple = tests and scripts.__", "cap")]
    s += [H2("2.1 Files and responsibilities")]
    rows = [["File", "Responsibility", "Main author (from git history / plan)"],
            ["`app.py`", "Streamlit entry point: page config, sidebar (scenario preset, update order, dynamics seed, max sweeps), session state, the four tabs", "Harsh"],
            ["`app_helpers.py`", "`load_engine_bundle()` (real engine, or a labelled mock, or a loud error), DataFrame builders, Plotly chart builders, header banner, `count_students_with_deviations`", "Harsh"],
            ["`game_engine.py`", "The engine: validation, utility, welfare, potential, teams, best response, profitable deviations, `is_nash`, dynamics, enumeration, generic Nash finder, `build_report`, CLI", "Aryan"],
            ["`sample_data.py`", "Synthetic data: 2x2 hand example, 8-student default scenario, demo start profile, synthetic-data notice", "Aryan"],
            ["`docs/MODEL.md`, `docs/INTERFACE.md`", "The formal model with proof; the frozen engine ↔ UI contract (signatures, return keys, errors)", "Aryan"],
            ["`tests/test_game_engine.py`, `test_integration.py`", "Engine unit/property tests; engine ↔ UI contract and saved-results checks", "Aryan"],
            ["`tests/test_ui_smoke.py`", "AppTest smoke tests, engine-bundle tests, deviation-count regression", "Harsh"],
            ["`scripts/generate_results.py`", "Regenerates `docs/results/` from real commands, with git provenance", "Aryan"],
            ["`scripts/independent_crosscheck.py`, `tests/test_independent_crosscheck.py`", "Independent recomputation of the results, diffed against the engine", "Aryan (prepared with Claude's help)"],
            ["`screenshots/`", "Genuine screenshots of the running app + index + machine-readable log", "Aryan's tooling; Ayush owns the screenshots folder in the plan"],
            ["`README.md`, `requirements.txt`, `requirements-docs.txt`, `pytest.ini`", "Setup and reproducibility", "Aryan (README to be reviewed by Ayush)"]]
    s += T(rows, [0.27, 0.53, 0.20], size=8)
    s += [H2("2.2 How data moves from the UI to the engine and back")]
    s += [dataflow_diagram(), SP(6)]
    s += [P("__Figure 2. Data flow for the Assignment tab. The same pattern (state → validate → engine → helpers → widgets) is used by the other tabs.__", "cap")]
    s += NL(["The user picks a project for each student in a selectbox. The choices are stored in `st.session_state.profile`, a list with one project index per student (0-based).",
             "Before anything is computed the app calls `engine.validate_profile(profile, scenario)`; a `StratosError` is shown with `st.error` instead of crashing.",
             "The Assignment tab calls `engine.teams`, `engine.utilities`, `engine.social_welfare` and `engine.potential` with the **same** scenario object.",
             "`app_helpers` turns the engine's plain lists and dicts into pandas DataFrames and Plotly figures.",
             "The Equilibrium tab calls `engine.is_nash`. The Simulation tab calls `engine.best_response_dynamics`, then **re-checks** the final profile with a fresh `is_nash` call rather than trusting the `converged` flag."])
    s += [H2("2.3 How the application starts")]
    s += CODE("streamlit run app.py\n"
              "  app.py                 st.set_page_config(...) ; helpers.apply_custom_styles()\n"
              "  app_helpers.load_engine_bundle()\n"
              "      real engine importable?  -> EngineBundle(engine=game_engine, sample_data=sample_data, using_mock=False)\n"
              "      modules missing?          -> labelled mock (or EngineUnavailableError if STRATOS_REQUIRE_REAL_ENGINE=1)\n"
              "      present but import fails? -> mock + a loud red error box with the traceback (never a silent fallback)\n"
              "  sidebar                scenario preset, regenerate, update order, dynamics seed, max sweeps\n"
              "  st.tabs([...])         Scenario | Assignment | Equilibrium | Simulation", 7.8)
    s += [H2("2.4 Dependencies and what each is for")]
    s += T([["Package", "Declared", "Role in STRATOS"],
            ["Python", "3.11 used and tested", "Language of every module"],
            ["Streamlit", "`streamlit>=1.51`", "Web UI. `width=\"stretch\"` on `st.button`, `st.dataframe` and `st.plotly_chart` requires 1.51 (checked in the 1.50.0 and 1.51.0 wheels)"],
            ["pandas", "`pandas>=2.0`", "Tables shown in the UI and the frames built by `app_helpers`"],
            ["Plotly", "`plotly>=5.0`", "Heatmaps, bar chart and the welfare/potential line chart (it was missing from `requirements.txt` until commit `859a798`)"],
            ["pytest", "`pytest>=7.0`", "Test runner; the UI tests use Streamlit's `AppTest`"],
            ["ReportLab, PyMuPDF", "`requirements-docs.txt` only", "Used to build these PDFs; **not** needed to run or test the product"]], [0.15, 0.25, 0.60])
    s += [P("The engine itself needs nothing beyond the Python standard library. Tested environment for the evidence in this handbook: Python 3.11.9, Streamlit 1.66.1, pandas 3.1.0, Plotly 7.1.0, pytest 9.1.1 on Windows 11.")]
    s += [CALL("viva", "Real engine versus mock engine", [
        "`app_helpers.py` contains a **mock engine** that mirrors the interface contract. It exists so the frontend could be built before the real engine was ready. "
        "With the real engine present it is never used; the app header says \"Real engine detected\", and the mock badge never appears. "
        "Some UI tests (`test_ui_smoke.py`) exercise the **mock** against the hand-solved tiny example, so they prove the mock is faithful, not that the real engine is correct. "
        "The real engine's correctness is established by the engine tests, the integration tests and the independent cross-check. "
        "Set `STRATOS_REQUIRE_REAL_ENGINE=1` to make any fallback a hard error."])]
    return s


def section3_model(F):
    sc = F["sc"]
    S = sc["students"]
    demo = F["demo_start"]
    s = [H1("3. The mathematical model, from first principles")]
    s += [P("Every definition below is the one in `docs/MODEL.md` and in the code. Symbols map to code as: "
            "`pref[i][t]` = p(i,t), `w[i][j]` = w(i,j), `gamma` = γ, `utility()`, `social_welfare()`, `potential()`, `is_nash()`.")]

    # 3.1
    s += [H2("3.1 Players, strategies, assignments")]
    s += [P(f"**Players:** students 0,…,n−1. The default scenario has n = {F['n']}: {', '.join(S)}. "
            f"**Strategies:** each student picks exactly one project from 0,…,m−1 (m = {F['m']}: "
            + "; ".join(f"{PS[t]} = {PN[t]}" for t in range(3)) + "). "
            "**Assignment (profile):** s = (s<sub>0</sub>,…,s<sub>n−1</sub>), one project per student. Indices are 0-based everywhere in the code.")]
    s += [EQ(f"number of assignments = <i>m</i><super><i>n</i></super> = 3<super>8</super> = {F['enum']['n_profiles']:,}")]
    s += [P(f"__Example.__ The demo start assignment is {prof_str(demo)}, i.e. " + teams_text(sc, demo) + ".")]
    s += QA("Why are there exactly 6,561 assignments?", "Each of the 8 students independently has 3 choices, and choices are independent, so the count is 3 × 3 × … × 3 (eight times) = 3⁸ = 6,561. "
            "Empty teams are allowed and there is no capacity limit, so every one of these is a legal assignment.", "model")

    # 3.2
    s += [H2("3.2 Parameters: preference, compatibility, crowding strength")]
    rows = [["Student", "Skills"] + [f"p(·,{PS[t]})" for t in range(3)]]
    for i, name in enumerate(S):
        rows.append([name, ", ".join(sc["skills"][name]), *[str(sc["pref"][i][t]) for t in range(3)]])
    s += T(rows, [0.15, 0.45, 0.13, 0.13, 0.13], size=8)
    s += [P(f"__Table 1. Default preferences p(i,t) on a 0–10 scale (C = {PN[0]}, W = {PN[1]}, E = {PN[2]}). Fictional data.__", "cap")]
    s += [EQ("w(<i>i</i>,<i>j</i>) = λ · | <i>S<sub>i</sub></i> Δ <i>S<sub>j</sub></i> | − β,   with λ = 1, β = 1",
             "S<sub>i</sub> is student i's skill set; Δ is the symmetric difference (skills held by exactly one of the two). Used only to generate the default w; the engine just reads the matrix w.")]
    s += [P("Complementary skills help (large symmetric difference); near-identical students help less, and two students with identical skill sets have w = 0 − 1 = −1. "
            "w is **symmetric by construction** (w(i,j) = w(j,i)) and has a zero diagonal.")]
    bd_e = utility_breakdown(sc, demo, 4)
    s += [P(f"__Example.__ Eli = {{Programming, Design}} and Dara = {{Design, Communication}}: the symmetric difference is {{Programming, Communication}}, size 2, "
            f"so w(Eli, Dara) = 2 − 1 = 1. Eli and Farah = {{Analysis}}: symmetric difference has size 3, so w(Eli, Farah) = 3 − 1 = 2. "
            f"(Both values are what the engine's matrix contains: {sc['w'][4][3]} and {sc['w'][4][5]}.)")]

    # 3.3
    s += [H2("3.3 Crowding cost")]
    s += [EQ("<i>c</i>(<i>k</i>) = γ · (<i>k</i> − 1)<super>2</super>",
             "k = number of students on a project, counting the student themself. γ ≥ 0 is the crowding strength (default γ = 2).")]
    s += [P("A student alone on a project pays nothing, c(1) = 0. The cost is **convex**: each extra teammate costs more than the last, which is what stops everyone piling onto their favourite project.")]
    g = sc["gamma"]
    s += T([["team size k", "1", "2", "3", "4", "5", "6", "7", "8"], [f"c(k), γ = {g}"] + [str(g * (k - 1) ** 2) for k in range(1, 9)]],
           [0.2] + [0.1] * 8, size=8.4)
    s += [P(f"__Example.__ At the demo start, Eli's team (Dara, Eli, Farah) has k = 3, so each member pays c(3) = {g}·(3−1)² = {bd_e['crowd']}. "
            f"If all 8 students were on one project, each would pay c(8) = {g}·7² = {g*49}, which is why the Reset button gives welfare {fm(F['reset_all0']['welfare'])}.")]
    s += QA("Why a quadratic crowding cost rather than a hard limit on team size?",
            "A hard cap makes some moves infeasible, which complicates the definition of a deviation and can destroy the potential structure. A convex cost keeps every move feasible, "
            "still discourages crowding, and the cost depends only on team size, which is exactly what the potential-game proof needs.", "model")

    # 3.4
    s += [H2("3.4 Utility")]
    s += [EQ("<i>u<sub>i</sub></i>(<i>s</i>) = <i>p</i>(<i>i</i>, <i>s<sub>i</sub></i>) + Σ<sub><i>j</i> ∈ mates(<i>i</i>)</sub> <i>w</i>(<i>i</i>,<i>j</i>) − <i>c</i>(<i>k<sub>i</sub></i>)",
             "mates(i) = the other students on i's project; k<sub>i</sub> = number of students on i's project including i. preference + compatibility with teammates − crowding cost.")]
    comp = " + ".join(str(w) for _, w in bd_e["compat"])
    s += [P(f"__Worked example (default scenario, demo start).__ Eli is on {bd_e['project']} with " + " and ".join(n for n, _ in bd_e["compat"]) +
            f". u = preference {bd_e['pref']} + compatibility ({comp}) − crowding {bd_e['crowd']} = **{fm(bd_e['total'])}**.")]
    alt = list(demo); alt[4] = 2
    bd_alt = utility_breakdown(sc, alt, 4)
    comp2 = " + ".join(str(w) for _, w in bd_alt["compat"])
    s += [P(f"If Eli alone moved to {bd_alt['project']} (everyone else unchanged) he would join " + " and ".join(n for n, _ in bd_alt["compat"]) +
            f": u = {bd_alt['pref']} + ({comp2}) − {bd_alt['crowd']} = **{fm(bd_alt['total'])}**, a gain of {bd_alt['total'] - bd_e['total']}.")]
    s += QA("Does a student's utility depend on other students' choices?",
            "Yes, in two ways. Who else is on my project changes the compatibility term, and how many are on it changes the crowding cost. My preference term depends only on my own choice. "
            "That dependence is what makes this a game rather than 8 separate optimisation problems.", "model")
    s += QA("Why does the crowding term count the student themself?",
            "k includes me, so a student alone has k = 1 and pays c(1) = γ·0 = 0. A team of two pays c(2) = γ each. Counting only the others would charge a lone student c(0), which is not defined by the model.", "model")

    # 3.5
    s += [H2("3.5 Social welfare")]
    s += [EQ("<i>W</i>(<i>s</i>) = Σ<sub><i>i</i></sub> <i>u<sub>i</sub></i>(<i>s</i>) = Σ<sub><i>i</i></sub> <i>p</i>(<i>i</i>,<i>s<sub>i</sub></i>) + 2 Σ<sub>same-team pairs <i>i</i>&lt;<i>j</i></sub> <i>w</i>(<i>i</i>,<i>j</i>) − Σ<sub><i>t</i></sub> <i>n</i>(<i>t</i>)·<i>c</i>(<i>n</i>(<i>t</i>))",
             "n(t) = number of students on project t. The factor 2 appears because each compatible pair benefits both members.", small=True)]
    ut = F["demo_check"]["utilities"]
    s += [P(f"__Example.__ At the demo start the utilities are [{', '.join(fm(u) for u in ut)}], so W = {fm(sum(ut))}. "
            "Welfare adds up everyone's utility; it is **not** the same as the potential Φ below, and not the same as stability.")]

    # 3.6
    s += [H2("3.6 Unilateral deviation and best response")]
    s += [P("A **unilateral deviation** is one student i switching to project t while everyone else keeps their choice. Its **gain** is "
            "u<sub>i</sub>(t, s<sub>−i</sub>) − u<sub>i</sub>(s). It is **profitable** if the gain exceeds ε = 10⁻⁹. "
            "A student's **best response** is a project that maximises their utility given the others; the engine keeps the current project if it is already a maximiser, "
            "otherwise it takes the **lowest-index** maximiser. A student moves only for a strictly positive gain.")]
    br = ge.best_response(4, demo, sc)
    s += T([["Eli's options at the demo start", *[f"{PS[o['project']]}" for o in br["options"]]],
            ["u<sub>Eli</sub> if he chooses it", *[fm(o["utility"]) for o in br["options"]]]],
           [0.4, 0.2, 0.2, 0.2], size=8.4)
    s += [P(f"Eli's current project is W with utility {fm(br['options'][1]['utility'])}; his best response is {PS[br['best']]} with utility {fm(br['options'][br['best']]['utility'])}, so he has a profitable deviation.")]
    s += QA("What happens when two projects give a student exactly the same utility?",
            "A tie is not a profitable deviation (the gain is not strictly positive), so the student stays. If the current project is already a maximiser the best response is to stay; "
            "if not, the engine picks the lowest-index maximiser so the result is deterministic. Consequently a tied assignment can still be a (weak) equilibrium.", "model")

    # 3.7
    s += [H2("3.7 Pure Nash equilibrium")]
    s += [EQ("<i>s</i>* is a pure Nash equilibrium  ⇔  for every student <i>i</i> and every project <i>t</i>:  <i>u<sub>i</sub></i>(<i>s</i>*) ≥ <i>u<sub>i</sub></i>(<i>t</i>, <i>s</i>*<sub>−<i>i</i></sub>)",
             "Equivalently: no student has a profitable unilateral deviation. The test costs n(m−1) utility evaluations, 16 for the default scenario.", small=True)]
    dev = F["demo_check"]["deviations"]
    s += [P(f"__Example (not an equilibrium).__ The demo start has {len(dev)} profitable deviations: " +
            "; ".join(f"{S[d['student']]} {PS[d['from_project']]}→{PS[d['to_project']]} gains {d['gain']} ({fm(d['current_utility'])}→{fm(d['new_utility'])})" for d in dev) +
            ". So it is **not** stable.")]
    s += [P("__Example (equilibrium).__ In the tiny example (section 4), [0, 1] is stable: each student would lose by moving alone.")]
    s += [CALL("viva", "Say it this way", "A Nash equilibrium is **stable against unilateral deviations**. Never call it \"optimal\", \"best\" or \"fair\": it may not maximise welfare, "
                       "may not be Pareto-optimal, need not be unique, and says nothing about two students moving together.")]
    s += QA("Define a pure Nash equilibrium in this game in one sentence.",
            "An assignment in which no single student can raise their own utility by switching to a different project while everyone else stays where they are.", "NE")

    # 3.8
    s += [H2("3.8 The potential function and why the game always has an equilibrium")]
    s += [EQ("Φ(<i>s</i>) = Σ<sub><i>i</i></sub> <i>p</i>(<i>i</i>,<i>s<sub>i</sub></i>) + Σ<sub>same-team pairs <i>i</i>&lt;<i>j</i></sub> <i>w</i>(<i>i</i>,<i>j</i>) − Σ<sub><i>t</i></sub> Σ<sub><i>k</i>=1</sub><super><i>n</i>(<i>t</i>)</super> <i>c</i>(<i>k</i>)")]
    s += [EQ("<i>u<sub>i</sub></i>(<i>s</i>′) − <i>u<sub>i</sub></i>(<i>s</i>) = Φ(<i>s</i>′) − Φ(<i>s</i>)    for every unilateral deviation of any student <i>i</i> from <i>s</i> to <i>s</i>′",
             "Exact potential property: a student's gain equals the change in Φ.", small=True)]
    s += [P("**Proof idea.** Let i move from project a to project t. Only terms involving i and the two teams change. The preference part changes by p(i,t) − p(i,a). "
            "The pair part loses i's compatibility with the old teammates and gains it with the new ones. In the crowding sum, team a shrinks from n(a) to n(a)−1, removing c(n(a)) from what is subtracted, "
            "and team t grows to n(t)+1, adding c(n(t)+1). The total change is exactly [p(i,t) + Σ w on t − c(n(t)+1)] − [p(i,a) + Σ w on a − c(n(a))], which is u<sub>i</sub> after minus u<sub>i</sub> before.")]
    steps = F["demo_rr"]["steps"]
    s += [P(f"__Numerical check.__ At the demo start Φ = {ge.potential(demo, sc)}. Dara's first move gains {steps[0]['gain']}, and Φ becomes {steps[0]['potential']}: "
            f"{ge.potential(demo, sc)} + {steps[0]['gain']} = {steps[0]['potential']}. ✓")]
    s += [P("**Consequences for this model.**")]
    s += NL(["Φ takes finitely many values, so some assignment maximises it, and no unilateral move from it can be profitable (it would raise Φ). **A pure equilibrium always exists.**",
             "Every profitable move raises Φ by exactly the mover's gain, so Φ strictly increases along best-response dynamics and an assignment can never repeat: **dynamics always terminates.** With integer data each move raises Φ by at least 1, so the number of moves is at most Φ<sub>max</sub> − Φ<sub>min</sub>.",
             "The argument needs **symmetric w** and a crowding cost that depends **only on team size**. The code never relies on the proof: it checks the equilibrium condition directly."])
    s += [CALL("warn", "What the potential does NOT mean", "Φ is **not** social welfare. A maximiser of Φ is an equilibrium, but an equilibrium need not maximise Φ, and the welfare-maximising assignment need not be an equilibrium. "
               f"In the default scenario the two welfare-optimal assignments are {prof_str(F['opt_profiles'][0])} and {prof_str(F['opt_profiles'][1])}; only the second is an equilibrium.")]
    s += QA("Why does best-response dynamics have to stop?",
            "Each strictly profitable move increases the potential Φ by exactly the mover's gain. Φ is bounded because there are only 3⁸ assignments, so it cannot increase forever, and an assignment cannot repeat "
            "(Φ would have to return to an earlier, lower value). Therefore a sweep with no move must eventually occur, and that assignment is an equilibrium.", "potential")
    s += QA("What would break the potential-game guarantee?",
            "An asymmetric compatibility matrix (w(i,j) ≠ w(j,i)), or a team bonus that is not a sum over pairs (for example \"the team covers every skill\"), or a crowding cost that depends on who is on the team rather than how many. "
            "In those cases there may be no exact potential and dynamics could cycle. The engine rejects asymmetric w at validation.", "potential")

    # 3.9
    s += [H2("3.9 Best-response dynamics and its stopping conditions")]
    s += CODE("s = start\nfor sweep r = 1 .. max_rounds:\n    visit order = ascending index (round_robin)  or  a seeded random permutation each sweep (random)\n"
              "    changed = False\n    for i in visit order:\n        t* = best response of i given the others      (stay if current project already maximises)\n"
              "        if u_i(t*, s_-i) > u_i(s) + EPS:  s_i = t*; record the step; changed = True\n"
              "    if not changed: converged = True; stop\nreturn converged, rounds, steps, final profile, and a FRESH is_nash(final)", 7.8)
    s += BL(["**Stops** when a full sweep produces no move (`converged = True`) or when `max_rounds` is used up (`converged = False`, shown in the UI as \"Not converged\").",
             "`rounds` counts sweeps **including the last sweep in which nobody moved**.",
             "`is_nash_final` is recomputed from scratch, so stability is never inferred from `converged` alone."])
    rr, rd = F["demo_rr"], F["demo_rand7"]
    s += [P(f"__Observed on the demo start.__ Round-robin: {rr['rounds']} sweeps, {len(rr['steps'])} moves, ends at {prof_str(rr['final_profile'])} with welfare {ge.social_welfare(rr['final_profile'], sc)}. "
            f"Random order with seed 7: {rd['rounds']} sweeps, {len(rd['steps'])} moves, ends at {prof_str(rd['final_profile'])} with welfare {ge.social_welfare(rd['final_profile'], sc)}. "
            "Both ends are Nash equilibria, but they are **different** equilibria with different welfare: the outcome depends on the update order.")]
    s += QA("Does the order in which students update change the answer?",
            f"It can. From the same start, round-robin ends at welfare {ge.social_welfare(rr['final_profile'], sc)} and random order (seed 7) at welfare {ge.social_welfare(rd['final_profile'], sc)}; both are stable. "
            "That is why we enumerate all equilibria rather than trusting one run, and why we say dynamics finds __an__ equilibrium, not __the best__ one.", "dynamics")

    # 3.10
    s += [H2("3.10 Pareto optimality, welfare gap, price of stability and price of anarchy")]
    s += [EQ("PoS = <i>W</i><sub>opt</sub> / max<sub>equilibria</sub> <i>W</i>,      PoA = <i>W</i><sub>opt</sub> / min<sub>equilibria</sub> <i>W</i>,      gap = <i>W</i><sub>opt</sub> − <i>W</i>(<i>s</i>*)",
             "W<sub>opt</sub> = max over all assignments of W. The ratios are reported only when W<sub>opt</sub> and every equilibrium welfare are strictly positive; otherwise they are null (None) and the gaps are shown instead.")]
    s += BL(["**Pareto-optimal** assignment: no other assignment makes every student at least as well off and someone strictly better off.",
             "**Welfare gap** of an equilibrium: how much total welfare is lost compared with the best assignment (always defined).",
             "**Price of stability:** how close the *best* equilibrium is to the optimum. **Price of anarchy:** how far the *worst* equilibrium is."])
    e = F["enum"]
    s += [P(f"__Default scenario.__ W<sub>opt</sub> = {e['optimal']['welfare']}; best equilibrium welfare {e['optimal']['welfare'] - e['welfare_gap_best_equilibrium']} (gap {e['welfare_gap_best_equilibrium']}), "
            f"worst equilibrium welfare {e['optimal']['welfare'] - e['welfare_gap_worst_equilibrium']} (gap {e['welfare_gap_worst_equilibrium']}). PoS = {e['price_of_stability']}, PoA = 29/16 = {e['price_of_anarchy']}. "
            f"{F['n_pareto_eq']} of the {e['n_equilibria']} equilibria are Pareto-optimal.")]
    g3 = F["gamma3"]
    s += [P(f"__Why the ratios can be undefined.__ With γ = 3 the enumeration still finds {g3['n_equilibria']} equilibria, but some equilibrium welfare is no longer positive, so PoA and PoS are "
            f"{g3['price_of_anarchy']} (None) while the gaps are {g3['welfare_gap_best_equilibrium']} and {g3['welfare_gap_worst_equilibrium']}. The engine returns null rather than a meaningless or negative ratio.")]
    s += QA("Price of anarchy is 1.8125. What does that number mean?",
            "The best possible total welfare is 29, and the worst stable assignment achieves only 16, and 29 / 16 = 1.8125. So selfish, stable behaviour can cost up to about 45% of the achievable welfare in the worst case "
            "(16 is 55% of 29). The price of stability is 1.0 because the best equilibrium reaches the optimum.", "efficiency")
    return s


def section4_worked(F):
    tiny = F["tiny"]
    s = [H1("4. Worked example by hand (and confirmed by the engine)")]
    s += [P("The tiny example is small enough to compute everything on paper. Two students, two projects, "
            "p = [[5, 1], [1, 5]], w(0,1) = 2, γ = 1, so c(1) = 0 and c(2) = 1. Student 0 likes project 0; student 1 likes project 1; together they are compatible (+2) but a team of two pays a crowding cost of 1 each.")]
    s += [H3("Step 1. Profile [0, 0]: both choose project 0")]
    s += NL(["Team sizes: project 0 has k = 2, project 1 is empty. Crowding cost c(2) = 1·(2−1)² = 1 for each of them.",
             "u₀ = p(0,0) + w(0,1) − c(2) = 5 + 2 − 1 = **6**.",
             "u₁ = p(1,0) + w(1,0) − c(2) = 1 + 2 − 1 = **2**.",
             "Welfare W = 6 + 2 = **8**.  Potential Φ = (5 + 1) + 2 − [c(1) + c(2)] = 6 + 2 − (0 + 1) = **7**."])
    s += [H3("Step 2. Is [0, 0] an equilibrium?")]
    s += NL(["Student 0 moving to project 1 would be alone there: u₀ = p(0,1) + 0 − c(1) = 1 − 0 = 1 < 6, no gain.",
             "Student 1 moving to project 1 would be alone: u₁ = p(1,1) + 0 − c(1) = 5 − 0 = **5** > 2. Gain = 5 − 2 = **3**. A profitable deviation exists, so [0, 0] is **not** a Nash equilibrium."])
    s += [H3("Step 3. One best-response move")]
    s += NL(["Student 1 moves: profile becomes [0, 1].",
             "Now each is alone on a project: u₀ = 5 + 0 − 0 = 5, u₁ = 5 + 0 − 0 = 5. W = **10**.",
             "Φ(0,1) = (5 + 5) + 0 − [c(1) + c(1)] = **10**. Check the potential identity: Φ rose from 7 to 10, i.e. by 3, which is exactly student 1's gain. ✓"])
    s += [H3("Step 4. Is [0, 1] an equilibrium?")]
    s += NL(["Student 0 moving to project 1 would share it with student 1: u₀ = 1 + 2 − c(2) = 1 + 2 − 1 = 2 < 5.",
             "Student 1 moving to project 0 would share it with student 0: u₁ = 1 + 2 − 1 = 2 < 5.",
             "Nobody gains, so [0, 1] **is** a Nash equilibrium. It also has the highest welfare (10), so here stability and optimality coincide."])
    rows = [["profile", "utilities", "W", "Φ", "pure Nash?"]]
    for p, (u, w_, phi, nash) in F["tiny_table"].items():
        rows.append([str(list(p)), str(u), str(w_), str(phi), "yes" if nash else "no"])
    s += T(rows, [0.2, 0.25, 0.15, 0.15, 0.25], size=8.6)
    s += [P("__Table 2. All four profiles of the tiny example, computed by the engine; they match the hand arithmetic above and the table in `docs/INTERFACE.md`. "
            "The app's *Tiny hand-verified example* preset reproduces this.__", "cap")]
    s += [H3("The same ideas on the default scenario: the round-robin trace")]
    steps = F["demo_rr"]["steps"]
    sc = F["sc"]
    rows = [["move", "sweep", "student", "from → to", "gain", "welfare after", "Φ after"]]
    rows.append(["0 (start)", "–", "–", prof_letters(F["demo_start"]), "–", str(ge.social_welfare(F["demo_start"], sc)), str(ge.potential(F["demo_start"], sc))])
    for st in steps:
        rows.append([str(st["step"]), str(st["round"]), sc["students"][st["student"]], f"{PS[st['from_project']]} → {PS[st['to_project']]}", str(st["gain"]), str(st["welfare"]), str(st["potential"])])
    s += T(rows, [0.12, 0.09, 0.16, 0.2, 0.1, 0.17, 0.16], size=8.4)
    pts = [(0, ge.social_welfare(F["demo_start"], sc), ge.potential(F["demo_start"], sc))] + [(st["step"], st["welfare"], st["potential"]) for st in steps]
    s += [potential_chart(pts), SP(4)]
    s += [P(f"__Figure 3. Welfare and potential along the round-robin run from the demo start. Φ rises at every move by exactly the mover's gain (35 → 38 → 44 → 47 → 49); welfare is not guaranteed to rise at every move, though here it does. "
            f"The run ends at {prof_str(F['demo_rr']['final_profile'])}, an equilibrium with welfare {ge.social_welfare(F['demo_rr']['final_profile'], sc)}.__", "cap")]
    return s


def section5_results(F):
    sc, e = F["sc"], F["enum"]
    rep = F["report"]
    s = [H1("5. Exhaustive enumeration and results")]
    s += [H2("5.1 How the enumeration works")]
    s += NL([f"Generate all 3⁸ = {e['n_profiles']:,} assignments with `itertools.product(range(3), repeat=8)`.",
             "For each assignment compute every student's utility, the welfare and the potential.",
             "Keep an assignment as an **equilibrium** if no student has a profitable deviation (`_has_deviation`, the same test as `is_nash`).",
             "Find the welfare maximiser(s) and the potential maximiser(s).",
             "For each equilibrium decide Pareto-optimality by comparing it with **every** other assignment.",
             "Guard: if m^n exceeds 100,000 the function raises `StratosError` instead of running for minutes."])
    s += [P(f"Measured on this machine: median {F['timing']['median_seconds']} s, minimum {F['timing']['min_seconds']} s for the whole enumeration (5 timed runs, `docs/results/timing.txt`). Timings vary between machines.")]
    s += [H2("5.2 Results for the default scenario")]
    s += [CALL("ok", "Re-validated, not copied", f"These five figures were reported earlier. They were **recomputed from scratch** for this document by a fresh engine run and by the independent cross-check "
               f"(`{F['crosscheck_identical'] and 'comparison with game_engine: IDENTICAL' or 'DISCREPANCY'}`), and agree with the saved report generated on commit `{F['results_commit'][:7]}`.")]
    s += T([["Quantity", "Value", "Meaning"],
            ["Assignments enumerated", f"{e['n_profiles']:,}", "3⁸"],
            ["Pure Nash equilibria", str(e["n_equilibria"]), "assignments with no profitable unilateral deviation"],
            ["Maximum welfare W<sub>opt</sub>", str(e["optimal"]["welfare"]), f"attained by {len(F['opt_profiles'])} assignments: {prof_str(F['opt_profiles'][0])} and {prof_str(F['opt_profiles'][1])}"],
            ["Is each welfare optimum an equilibrium?", " / ".join("yes" if x else "no" for x in F["opt_is_eq"]), "only one of the two optima is stable (Eli would gain 2 by moving in the first)"],
            ["Price of stability", str(e["price_of_stability"]), "best equilibrium reaches the optimum"],
            ["Price of anarchy", f"{e['price_of_anarchy']}  (= 29/16)", f"worst equilibrium welfare = {e['optimal']['welfare'] - e['welfare_gap_worst_equilibrium']}"],
            ["Welfare gap, best / worst equilibrium", f"{e['welfare_gap_best_equilibrium']} / {e['welfare_gap_worst_equilibrium']}", "W<sub>opt</sub> minus equilibrium welfare"],
            ["Pareto-optimal equilibria", f"{F['n_pareto_eq']} of {e['n_equilibria']}", "the other 3 are dominated by some assignment"],
            ["Potential maximisers", f"Φ = {e['potential_maximizers']['potential']}", f"{len(e['potential_maximizers']['profiles'])} assignments; all are equilibria (as the theory says)"]],
           [0.30, 0.22, 0.48], size=8.4)
    s += [H2("5.3 The 23 equilibria, ordered by welfare")]
    rows = [["#", "assignment", "teams (C / W / E)", "welfare", "Φ", "Pareto?"]]
    for k, q in enumerate(F["eq_sorted"], 1):
        pr = q["profile"]
        tm = " / ".join(",".join(sc["students"][i][:2] for i, x in enumerate(pr) if x == t) or "–" for t in range(3))
        rows.append([str(k), prof_str(pr), tm, str(q["welfare"]), str(q["potential"]), "yes" if q["pareto_optimal"] else "no"])
    s += T(rows, [0.06, 0.2, 0.40, 0.1, 0.1, 0.14], size=7.6)
    s += [P("__Table 3. Every pure Nash equilibrium of the default scenario (student names abbreviated to two letters). Source: `enumerate_equilibria`, identical to `docs/results/engine_report.json`.__", "cap")]
    s += [H2("5.4 Where best-response dynamics ends")]
    dr = rep["dynamics_summary"]
    s += T([["Update order", "runs", "all converged", "all end in Nash", "all in enumerated set", "moves min / mean / max", "max sweeps", "distinct endpoints"],
            *[[o, str(dr[o]["n_runs"]), str(dr[o]["all_converged"]), str(dr[o]["all_final_profiles_pass_is_nash"]), str(dr[o]["all_final_profiles_in_enumerated_set"]),
               f"{dr[o]['steps_min']} / {dr[o]['steps_mean']} / {dr[o]['steps_max']}", str(dr[o]["rounds_max"]), str(len(dr[o]["endpoints"]))] for o in ("round_robin", "random")]],
           [0.14, 0.07, 0.11, 0.12, 0.14, 0.18, 0.09, 0.15], size=7.8)
    mm = None
    import re as _re
    mt = _re.search(r"'max_moves': (\d+)", F["crosscheck_text"])
    s += [P(f"__From the saved report:__ 200 seeded random starts per update order (seeds 0–199). Every run converged to a verified equilibrium that is in the enumerated set. "
            f"The independent cross-check ran round-robin dynamics from **all {e['n_profiles']:,}** starting assignments: all converged to an equilibrium"
            + (f", using at most {mt.group(1)} moves" if mt else "") + ".")]
    s += [H2("5.5 How the results were independently checked, and what is still missing")]
    s += T([["Check", "Who / what", "Result", "Limitation"],
            ["Hand-derived tiny table (4 profiles)", "Computed by hand in `docs/INTERFACE.md` section 5; reproduced by engine tests and by the cross-check", "match", "Tiny scenario only"],
            ["Recompute everything for the default scenario without engine code", "`scripts/independent_crosscheck.py` (exact fractions, own enumeration, own Pareto test, own dynamics)", "23 equilibria, W<sub>opt</sub> 29, PoS 1, PoA 29/16, 20 Pareto: identical to engine", "Same author and specification as the engine"],
            ["Identities on all 6,561 profiles × all deviations", "Cross-check: welfare closed form = Σu; exact-potential identity", "hold everywhere", "Confirms the model is internally consistent, not that the model is right"],
            ["Generic checker", "`pure_nash_equilibria` (engine test: matching pennies returns no pure equilibrium)", "pass", "Same codebase"],
            ["Independent second-person re-implementation and Excel oracle", "Plan tasks Q4, Q5, O-01..O-04 (Ayush)", RAW("<b>PENDING</b>: not in the repository"), "Must be done before it can be cited"]],
           [0.25, 0.30, 0.25, 0.20], size=7.8)
    return s
