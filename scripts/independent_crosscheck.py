"""Independent re-computation of the STRATOS results, written from docs/MODEL.md only.

    python scripts/independent_crosscheck.py            # recompute and print the figures
    python scripts/independent_crosscheck.py --compare  # ... and compare them with game_engine

The computation itself does NOT import game_engine or sample_data: the default data (preferences, skill sets,
LAMBDA, BETA, gamma) is re-typed below from sample_data.py / MODEL.md, and every quantity is re-derived with a
deliberately different code path (explicit teammate lists, deviation by constructing the deviated profile, exact
rational arithmetic via fractions.Fraction, brute-force Pareto dominance, own best-response loop).
Only `--compare` imports game_engine, and only to diff its output against the numbers computed here.

Status of this file: a cross-check prepared for Aryan with Claude's help. It is independent of the engine's CODE, but it
shares an author and a specification with the engine, so it is not the team's formal independent verification
(Ayush's tests/oracle/independent_check.py and Excel oracle, tasks Q4/Q5/O-01..O-04, are separate and are not
replaced by this file).
"""
from __future__ import annotations

import itertools
import os
import sys
from fractions import Fraction

# ---- data re-typed from docs/MODEL.md and sample_data.py (default scenario) ---------------------------------
STUDENTS = ["Asha", "Bram", "Chen", "Dara", "Eli", "Farah", "Goran", "Hana"]
SKILLS = {
    "Asha": {"Programming", "Analysis"},
    "Bram": {"Programming"},
    "Chen": {"Analysis", "Communication"},
    "Dara": {"Design", "Communication"},
    "Eli": {"Programming", "Design"},
    "Farah": {"Analysis"},
    "Goran": {"Communication"},
    "Hana": {"Design", "Analysis"},
}
PREF = [[8, 6, 2], [9, 1, 5], [3, 9, 4], [7, 3, 8], [9, 2, 6], [4, 8, 3], [2, 5, 9], [6, 7, 5]]
LAMBDA, BETA, GAMMA = 1, 1, 2
DEMO_START = (0, 0, 0, 1, 1, 1, 2, 2)

# Hand-derived tiny example (docs/INTERFACE.md section 5): profile -> (utilities, welfare, potential, is_nash)
TINY = {"pref": [[5, 1], [1, 5]], "w": [[0, 2], [2, 0]], "gamma": 1}
TINY_EXPECTED = {
    (0, 0): ([6, 2], 8, 7, False),
    (0, 1): ([5, 5], 10, 10, True),
    (1, 0): ([1, 1], 2, 2, False),
    (1, 1): ([2, 6], 8, 7, False),
}


def default_game() -> dict:
    n = len(STUDENTS)
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                w[i][j] = LAMBDA * len(SKILLS[STUDENTS[i]] ^ SKILLS[STUDENTS[j]]) - BETA
    return {"pref": PREF, "w": w, "gamma": GAMMA}


# ---- independent model implementation --------------------------------------------------------------------
def utility(g: dict, s: tuple, i: int) -> int:
    mates = [j for j in range(len(s)) if j != i and s[j] == s[i]]
    size = len(mates) + 1
    return g["pref"][i][s[i]] + sum(g["w"][i][j] for j in mates) - g["gamma"] * (size - 1) ** 2


def utilities(g: dict, s: tuple) -> list:
    return [utility(g, s, i) for i in range(len(s))]


def welfare_closed_form(g: dict, s: tuple) -> int:
    """W = sum pref + 2 * sum_{pairs on same team} w - sum_t n_t * c(n_t)   (MODEL.md section 3)."""
    n = len(s)
    pref = sum(g["pref"][i][s[i]] for i in range(n))
    pairs = sum(g["w"][i][j] for i in range(n) for j in range(i + 1, n) if s[i] == s[j])
    sizes = [sum(1 for x in s if x == t) for t in range(len(g["pref"][0]))]
    return pref + 2 * pairs - sum(k * g["gamma"] * (k - 1) ** 2 for k in sizes)


def potential(g: dict, s: tuple) -> int:
    """Phi = sum pref + sum_{pairs on same team} w - sum_t sum_{k=1..n_t} c(k)   (MODEL.md section 4)."""
    n = len(s)
    pref = sum(g["pref"][i][s[i]] for i in range(n))
    pairs = sum(g["w"][i][j] for i in range(n) for j in range(i + 1, n) if s[i] == s[j])
    sizes = [sum(1 for x in s if x == t) for t in range(len(g["pref"][0]))]
    return pref + pairs - sum(g["gamma"] * (k - 1) ** 2 for size in sizes for k in range(1, size + 1))


def deviations(g: dict, s: tuple) -> list:
    """All (student, to_project, gain) with gain > 0, found by building the deviated profile explicitly."""
    m = len(g["pref"][0])
    base = utilities(g, s)
    out = []
    for i in range(len(s)):
        for t in range(m):
            if t != s[i]:
                moved = s[:i] + (t,) + s[i + 1:]
                gain = utility(g, moved, i) - base[i]
                if gain > 0:
                    out.append((i, t, gain))
    return out


def best_response_dynamics_round_robin(g: dict, start: tuple, max_rounds: int = 1000) -> tuple:
    """MODEL.md section 5: ascending sweeps; a student moves only for a strictly positive gain, to the lowest-index
    maximiser. Returns (final_profile, number_of_moves, converged)."""
    s = list(start)
    m = len(g["pref"][0])
    moves = 0
    for _ in range(max_rounds):
        changed = False
        for i in range(len(s)):
            options = []
            for t in range(m):
                trial = tuple(s[:i] + [t] + s[i + 1:])
                options.append(utility(g, trial, i))
            top = max(options)
            if top > options[s[i]]:
                s[i] = options.index(top)  # lowest-index maximiser
                moves += 1
                changed = True
        if not changed:
            return tuple(s), moves, True
    return tuple(s), moves, False


def analyse(g: dict) -> dict:
    n, m = len(g["pref"]), len(g["pref"][0])
    profiles = list(itertools.product(range(m), repeat=n))
    util = {p: utilities(g, p) for p in profiles}
    welfare = {p: sum(util[p]) for p in profiles}

    # identity checks over EVERY profile and EVERY unilateral deviation (exact potential property)
    welfare_identity_ok = all(welfare[p] == welfare_closed_form(g, p) for p in profiles)
    potential_identity_ok = True
    for p in profiles:
        phi = potential(g, p)
        for i in range(n):
            for t in range(m):
                if t != p[i]:
                    q = p[:i] + (t,) + p[i + 1:]
                    if potential(g, q) - phi != util[q][i] - util[p][i]:
                        potential_identity_ok = False

    equilibria = [p for p in profiles if not deviations(g, p)]
    w_opt = max(welfare.values())
    optimal = [p for p in profiles if welfare[p] == w_opt]

    def pareto(p) -> bool:
        up = util[p]
        return not any(
            q != p and all(util[q][i] >= up[i] for i in range(n)) and any(util[q][i] > up[i] for i in range(n))
            for q in profiles
        )

    eq_w = [welfare[p] for p in equilibria]
    poa = pos = None
    if eq_w and min(eq_w) > 0 and w_opt > 0:
        poa, pos = Fraction(w_opt, min(eq_w)), Fraction(w_opt, max(eq_w))

    # best-response dynamics (round robin) from EVERY start profile
    terminal_ok, max_moves, terminals = True, 0, set()
    for p in profiles:
        final, moves, converged = best_response_dynamics_round_robin(g, p)
        terminal_ok &= converged and not deviations(g, final)
        max_moves = max(max_moves, moves)
        terminals.add(final)

    phi_max = max(potential(g, p) for p in profiles)
    return {
        "n_profiles": len(profiles),
        "equilibria": equilibria,
        "n_equilibria": len(equilibria),
        "equilibrium_welfares": sorted(set(eq_w)),
        "w_opt": w_opt,
        "optimal_profiles": optimal,
        "optimal_is_equilibrium": [p in set(equilibria) for p in optimal],
        "pareto_optimal_equilibria": sum(1 for p in equilibria if pareto(p)),
        "welfare_gap_best": (w_opt - max(eq_w)) if eq_w else None,
        "welfare_gap_worst": (w_opt - min(eq_w)) if eq_w else None,
        "price_of_anarchy": poa,
        "price_of_stability": pos,
        "potential_max": phi_max,
        "potential_maximisers": [p for p in profiles if potential(g, p) == phi_max],
        "welfare_identity_ok": welfare_identity_ok,
        "potential_identity_ok": potential_identity_ok,
        "round_robin_from_every_start": {"all_converge_to_nash": terminal_ok, "max_moves": max_moves,
                                         "distinct_terminal_profiles": len(terminals),
                                         "terminals_subset_of_equilibria": terminals <= set(equilibria)},
        "demo_start": {"profile": DEMO_START, "deviations": deviations(g, DEMO_START),
                       "round_robin": best_response_dynamics_round_robin(g, DEMO_START)},
    }


def check_tiny() -> list:
    """Compare the independent model against the hand-derived table. Returns a list of mismatch messages."""
    bad = []
    for s, (u, w, phi, nash) in TINY_EXPECTED.items():
        if utilities(TINY, s) != u:
            bad.append(f"{s}: utilities {utilities(TINY, s)} != {u}")
        if sum(utilities(TINY, s)) != w:
            bad.append(f"{s}: welfare != {w}")
        if potential(TINY, s) != phi:
            bad.append(f"{s}: potential != {phi}")
        if (not deviations(TINY, s)) != nash:
            bad.append(f"{s}: is_nash != {nash}")
    return bad


def compare_with_engine(result: dict) -> list:
    """Diff the independent numbers with a fresh run of game_engine. Returns a list of discrepancy messages."""
    import game_engine as ge
    import sample_data as sd

    sc = sd.get_default_scenario()
    bad = []
    if sc["w"] != default_game()["w"] or sc["pref"] != PREF or sc["gamma"] != GAMMA:
        bad.append("sample_data default scenario differs from the data re-typed in this file")
    e = ge.enumerate_equilibria(sc)
    mine = {tuple(p) for p in result["equilibria"]}
    theirs = {tuple(x["profile"]) for x in e["equilibria"]}
    if mine != theirs:
        bad.append(f"equilibrium sets differ: only-mine={sorted(mine - theirs)} only-engine={sorted(theirs - mine)}")
    if e["n_profiles"] != result["n_profiles"]:
        bad.append("n_profiles differs")
    if e["optimal"]["welfare"] != result["w_opt"]:
        bad.append(f"w_opt differs: {e['optimal']['welfare']} vs {result['w_opt']}")
    if sorted(map(tuple, e["optimal_profiles"])) != sorted(result["optimal_profiles"]):
        bad.append("optimal_profiles differ")
    if e["price_of_anarchy"] != float(result["price_of_anarchy"]) or e["price_of_stability"] != float(result["price_of_stability"]):
        bad.append("PoA/PoS differ")
    if (e["welfare_gap_best_equilibrium"], e["welfare_gap_worst_equilibrium"]) != (result["welfare_gap_best"], result["welfare_gap_worst"]):
        bad.append("welfare gaps differ")
    if sum(1 for x in e["equilibria"] if x["pareto_optimal"]) != result["pareto_optimal_equilibria"]:
        bad.append("number of Pareto-optimal equilibria differs")
    for x in e["equilibria"]:
        if x["utilities"] != utilities(default_game(), tuple(x["profile"])):
            bad.append(f"utilities differ at equilibrium {x['profile']}")
    # engine dynamics from every start profile must end where the independent loop ends
    g = default_game()
    for p in itertools.product(range(3), repeat=len(STUDENTS)):
        run = ge.best_response_dynamics(sc, list(p))
        final, moves, _ = best_response_dynamics_round_robin(g, p)
        if tuple(run["final_profile"]) != final or len(run["steps"]) != moves:
            bad.append(f"dynamics from {p}: engine {run['final_profile']}/{len(run['steps'])} vs mine {final}/{moves}")
            break
    return bad


def main(argv: list) -> int:
    g = default_game()
    r = analyse(g)
    tiny_bad = check_tiny()
    print("STRATOS independent cross-check (computed without game_engine)")
    print(f"tiny hand-derived table reproduced: {not tiny_bad} {tiny_bad or ''}")
    print(f"profiles enumerated: {r['n_profiles']} (= 3^8)")
    print(f"pure Nash equilibria: {r['n_equilibria']}   distinct equilibrium welfares: {r['equilibrium_welfares']}")
    print(f"welfare optimum: {r['w_opt']} at {r['optimal_profiles']}  (optimum is an equilibrium: {r['optimal_is_equilibrium']})")
    print(f"welfare gaps (best/worst equilibrium): {r['welfare_gap_best']} / {r['welfare_gap_worst']}")
    print(f"price of stability: {r['price_of_stability']} = {float(r['price_of_stability'])}")
    print(f"price of anarchy:   {r['price_of_anarchy']} = {float(r['price_of_anarchy'])}")
    print(f"Pareto-optimal equilibria: {r['pareto_optimal_equilibria']} of {r['n_equilibria']}")
    print(f"potential maximum: {r['potential_max']} at {r['potential_maximisers']}")
    print(f"welfare closed form == sum of utilities on all profiles: {r['welfare_identity_ok']}")
    print(f"exact-potential identity on every profile x deviation: {r['potential_identity_ok']}")
    print(f"round-robin dynamics from all {r['n_profiles']} starts: {r['round_robin_from_every_start']}")
    print(f"demo start {r['demo_start']['profile']}: {len(r['demo_start']['deviations'])} profitable deviations; "
          f"round-robin ends at {r['demo_start']['round_robin']}")
    status = 0 if not tiny_bad and r["welfare_identity_ok"] and r["potential_identity_ok"] else 1
    if "--compare" in argv:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        bad = compare_with_engine(r)
        print("comparison with game_engine:", "IDENTICAL" if not bad else "DISCREPANCIES")
        for b in bad:
            print("  -", b)
        status |= 1 if bad else 0
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
