"""STRATOS independent oracle: a second implementation written from docs/MODEL.md only.

    python tests/oracle/independent_check.py            # oracle self-checks + hand-derived tables (no engine import)
    python tests/oracle/independent_check.py --compare  # ... and compare against game_engine on every scenario
    python tests/oracle/independent_check.py --compare --full --report docs/results/oracle_report.txt  # exhaustive

What "independent" means here, honestly:
  * The oracle never imports game_engine, sample_data or scenario_io for any of its own numbers. Scenarios are
    re-typed below (the default one is rebuilt from its skill sets with the MODEL.md formula).
  * It uses a different code path: explicit teammate lists, deviations built by constructing the deviated profile,
    exact rational arithmetic (fractions.Fraction, so no tolerance is needed), brute-force Pareto dominance over all
    profiles, and its own best-response loops.
  * It does NOT have a different author or a different specification from the engine (both follow MODEL.md and were
    produced in the same project), so it catches implementation bugs, not a mistake in the model itself. The model's
    correctness rests on the proof in MODEL.md Section 4, which the oracle also checks numerically (see
    `potential_identity`), and on the hand-derived tables below.
  * The one engine behaviour the oracle must copy rather than derive is the random update order: INTERFACE.md says
    "seeded random permutation per sweep", realised with `random.Random(seed).shuffle`. The oracle reproduces that
    with the standard library; this is stated in the report.

Scenarios are chosen to cover: the 2-student tiny example, a hand-solved 3-student game, the 8-student default
scenario, and seeded random scenarios with negative weights, zero and half-integer gamma, and 2..4 projects.
"""
from __future__ import annotations

import itertools
import os
import random
import sys
from fractions import Fraction

F = Fraction


# ---------------------------------------------------------------------------------------------- run size
FULL = False  # --full: exhaustive for the 6,561-profile default scenario (minutes); default: fixed-seed samples


def pick(profiles, k, seed):
    """All profiles when the list is small or FULL is on, else a fixed-seed sample of k of them."""
    if FULL or len(profiles) <= 800:
        return list(profiles)
    return random.Random(seed).sample(list(profiles), k)


# ---------------------------------------------------------------------------------------------- scenarios
def make(pref, w, gamma, students=None, projects=None):
    n, m = len(pref), len(pref[0])
    return {"students": students or [f"S{i}" for i in range(n)], "projects": projects or [f"P{t}" for t in range(m)],
            "pref": pref, "w": w, "gamma": gamma}


TINY = make([[5, 1], [1, 5]], [[0, 2], [2, 0]], 1)
TRIO = make([[4, 0], [3, 1], [0, 4]], [[0, 2, -1], [2, 0, 1], [-1, 1, 0]], 1)

_SKILLS = {"Asha": {"Programming", "Analysis"}, "Bram": {"Programming"}, "Chen": {"Analysis", "Communication"},
           "Dara": {"Design", "Communication"}, "Eli": {"Programming", "Design"}, "Farah": {"Analysis"},
           "Goran": {"Communication"}, "Hana": {"Design", "Analysis"}}
_NAMES = list(_SKILLS)
_PREF = [[8, 6, 2], [9, 1, 5], [3, 9, 4], [7, 3, 8], [9, 2, 6], [4, 8, 3], [2, 5, 9], [6, 7, 5]]
DEFAULT = make(_PREF, [[0 if i == j else 1 * len(_SKILLS[_NAMES[i]] ^ _SKILLS[_NAMES[j]]) - 1 for j in range(8)]
                       for i in range(8)], 2, students=_NAMES,
               projects=["Campus Navigation App", "Wellbeing Survey Analysis", "Event Management Portal"])


def random_scenario(seed):
    rng = random.Random(seed)
    n, m = rng.randint(2, 6), rng.randint(2, 4)
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            w[i][j] = w[j][i] = rng.randint(-3, 4)
    return make([[rng.randint(-2, 10) for _ in range(m)] for _ in range(n)], w, rng.choice([0, 0.5, 1, 1.5, 2, 3]))


SCENARIOS = {"tiny": TINY, "trio": TRIO, "default": DEFAULT, **{f"random-{s}": random_scenario(s) for s in range(20)}}

# Hand-derived expectations (arithmetic written out literally, NOT computed by the model code below).
# profile -> (utilities, welfare, potential, is_nash)
TINY_HAND = {
    (0, 0): ([5 + 2 - 1, 1 + 2 - 1], (5 + 2 - 1) + (1 + 2 - 1), 5 + 1 + 2 - (0 + 1), False),
    (0, 1): ([5, 5], 5 + 5, 5 + 5, True),
    (1, 0): ([1, 1], 1 + 1, 1 + 1, False),
    (1, 1): ([1 + 2 - 1, 5 + 2 - 1], (1 + 2 - 1) + (5 + 2 - 1), 1 + 5 + 2 - (0 + 1), False),
}
TRIO_HAND = {  # gamma = 1: c(1)=0, c(2)=1, c(3)=4
    (0, 0, 1): ([4 + 2 - 1, 3 + 2 - 1, 4], (4 + 2 - 1) + (3 + 2 - 1) + 4, 4 + 3 + 4 + 2 - (0 + 1) - 0),
    (0, 0, 0): ([4 + 2 - 1 - 4, 3 + 2 + 1 - 4, 0 - 1 + 1 - 4], (4 + 2 - 1 - 4) + (3 + 2 + 1 - 4) + (0 - 1 + 1 - 4),
                4 + 3 + 0 + (2 - 1 + 1) - (0 + 1 + 4)),
    (1, 0, 1): ([0 - 1 - 1, 3, 4 - 1 - 1], (0 - 1 - 1) + 3 + (4 - 1 - 1), 0 + 3 + 4 - 1 - (0 + 0 + 1)),
}


# ---------------------------------------------------------------------------------------------- the model
def q(x):
    """Exact rational from an int / float (floats used here are binary-exact: halves and integers)."""
    return F(x)


def crowd(g, k):
    return q(g["gamma"]) * (k - 1) ** 2


def teammates(s, i):
    return [j for j in range(len(s)) if j != i and s[j] == s[i]]


def team_sizes(g, s):
    return [sum(1 for x in s if x == t) for t in range(len(g["projects"]))]


def utility(g, s, i):
    mates = teammates(s, i)
    return q(g["pref"][i][s[i]]) + sum((q(g["w"][i][j]) for j in mates), F(0)) - crowd(g, len(mates) + 1)


def utilities(g, s):
    return [utility(g, s, i) for i in range(len(s))]


def welfare(g, s):
    return sum(utilities(g, s), F(0))


def potential(g, s):
    n = len(s)
    pref = sum((q(g["pref"][i][s[i]]) for i in range(n)), F(0))
    pairs = sum((q(g["w"][i][j]) for i in range(n) for j in range(i + 1, n) if s[i] == s[j]), F(0))
    cost = sum((crowd(g, k) for size in team_sizes(g, s) for k in range(1, size + 1)), F(0))
    return pref + pairs - cost


def moved(s, i, t):
    return s[:i] + (t,) + s[i + 1:]


def deviations(g, s):
    """[(student, target, gain)] for every strictly profitable single-student switch."""
    base = utilities(g, s)
    out = []
    for i in range(len(s)):
        for t in range(len(g["projects"])):
            if t != s[i]:
                gain = utility(g, moved(s, i, t), i) - base[i]
                if gain > 0:
                    out.append((i, t, gain))
    return out


def is_nash(g, s):
    return not deviations(g, s)


def best_response(g, s, i):
    """(project, utility_there) following MODEL.md: stay if the current project is a maximiser, else lowest index."""
    opts = [utility(g, moved(s, i, t), i) for t in range(len(g["projects"]))]
    top = max(opts)
    return (s[i] if opts[s[i]] == top else opts.index(top)), top


def dynamics(g, start, order="round_robin", seed=None, max_rounds=100):
    """(final, moves, converged, rounds, trace[(student, from, to, gain)])"""
    s = tuple(start)
    n = len(s)
    rng = random.Random(seed)
    trace = []
    for rnd in range(1, max_rounds + 1):
        visit = list(range(n))
        if order == "random":
            rng.shuffle(visit)
        changed = False
        for i in visit:
            t, top = best_response(g, s, i)
            cur = utility(g, s, i)
            if top > cur:
                trace.append((i, s[i], t, top - cur))
                s = moved(s, i, t)
                changed = True
        if not changed:
            return s, len(trace), True, rnd, trace
    return s, len(trace), False, max_rounds, trace


def all_profiles(g):
    return list(itertools.product(range(len(g["projects"])), repeat=len(g["pref"])))


def analyse(g):
    P = all_profiles(g)
    U = {p: utilities(g, p) for p in P}
    W = {p: sum(U[p], F(0)) for p in P}
    Phi = {p: potential(g, p) for p in P}
    eq = [p for p in P if is_nash(g, p)]
    wmax = max(W.values())
    opt = [p for p in P if W[p] == wmax]

    def dominated_by(p):
        for r in P:
            if r != p and all(a >= b for a, b in zip(U[r], U[p])) and any(a > b for a, b in zip(U[r], U[p])):
                return r
        return None

    eqw = [W[p] for p in eq]
    ratios = (wmax / min(eqw), wmax / max(eqw)) if eq and min(eqw) > 0 and wmax > 0 else (None, None)
    pmax = max(Phi.values())
    return {"profiles": P, "U": U, "W": W, "Phi": Phi, "eq": eq, "wmax": wmax, "opt": opt, "poa": ratios[0],
            "pos": ratios[1], "pareto": {p: dominated_by(p) is None for p in eq}, "phi_max": pmax,
            "phi_argmax": [p for p in P if Phi[p] == pmax], "eq_welfare_levels": sorted(set(eqw))}


# ---------------------------------------------------------------------------------------------- oracle self-checks
class Report:
    def __init__(self):
        self.rows = []

    def add(self, name, scenario, cases, ok, detail=""):
        self.rows.append({"check": name, "scenario": scenario, "cases": cases, "ok": bool(ok), "detail": detail})

    @property
    def failures(self):
        return [r for r in self.rows if not r["ok"]]


def selfchecks(rep):
    """Checks that need no engine: hand tables and the model's own identities."""
    for name, g, table in (("tiny", TINY, TINY_HAND), ("trio", TRIO, TRIO_HAND)):
        bad = []
        for s, exp in table.items():
            u, w_, phi = exp[0], exp[1], exp[2]
            if utilities(g, s) != [F(x) for x in u]:
                bad.append(f"{s}: utilities {utilities(g, s)} != {u}")
            if welfare(g, s) != w_:
                bad.append(f"{s}: welfare")
            if potential(g, s) != phi:
                bad.append(f"{s}: potential")
            if len(exp) > 3 and is_nash(g, s) != exp[3]:
                bad.append(f"{s}: is_nash")
        rep.add("hand-derived table reproduced by oracle", name, len(table), not bad, "; ".join(bad))
    for name, g in SCENARIOS.items():
        P = pick(all_profiles(g), 700, 1)
        bad_pot = bad_w = bad_sizes = 0
        n_dev = 0
        for p in P:
            u = utilities(g, p)
            # welfare closed form from MODEL.md Section 3: sum pref + 2 * pair-sum - sum n_t c(n_t)
            closed = (sum((q(g["pref"][i][p[i]]) for i in range(len(p))), F(0))
                      + 2 * sum((q(g["w"][i][j]) for i in range(len(p)) for j in range(i + 1, len(p)) if p[i] == p[j]), F(0))
                      - sum((k * crowd(g, k) for k in team_sizes(g, p)), F(0)))
            bad_w += sum(u) != closed
            bad_sizes += sum(team_sizes(g, p)) != len(p)
            phi = potential(g, p)
            for i in range(len(p)):
                for t in range(len(g["projects"])):
                    if t != p[i]:
                        n_dev += 1
                        r = moved(p, i, t)
                        bad_pot += (potential(g, r) - phi) != (utility(g, r, i) - u[i])
        rep.add("exact potential: delta Phi == delta u_i for every profile x unilateral deviation", name, n_dev, bad_pot == 0)
        rep.add("welfare closed form == sum of utilities; team sizes sum to n", name, len(P), bad_w == 0 and bad_sizes == 0)
    for name, g in SCENARIOS.items():
        a = analyse(g)
        rep.add("a pure equilibrium exists (finite potential game)", name, len(a["profiles"]), len(a["eq"]) >= 1)
        rep.add("every potential maximiser is an equilibrium", name, len(a["phi_argmax"]), all(p in set(a["eq"]) for p in a["phi_argmax"]))
        ok = True
        starts = pick(a["profiles"], 300, 5)
        for p in starts:
            final, _, conv, _, trace = dynamics(g, p)
            phis = [potential(g, p)]
            s = p
            for (i, _, t, gain) in trace:
                s = moved(s, i, t)
                phis.append(potential(g, s))
            ok &= conv and is_nash(g, final) and all(b > a_ for a_, b in zip(phis, phis[1:]))
        rep.add("round-robin dynamics (every start; fixed-seed sample on the default scenario unless --full): converges, ends in equilibrium, potential strictly increases", name, len(starts), ok)
    # ties never count as profitable deviations
    tie = make([[1, 1], [1, 1]], [[0, 0], [0, 0]], 0)
    rep.add("ties are not profitable deviations (all-equal game: every profile is an equilibrium)", "tie", 4,
            all(is_nash(tie, p) for p in all_profiles(tie)))


# ---------------------------------------------------------------------------------------------- comparison with the engine
def eqf(a, b):
    return F(a) == F(b)


def compare(rep, rnd_seed=2026, names=None):
    """Diff the engine against the oracle. This is the only function that imports the engine."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import game_engine as ge

    rng = random.Random(rnd_seed)
    for name, g in SCENARIOS.items():
        if names is not None and name not in names:
            continue
        a = analyse(g)
        P = a["profiles"]
        sample = pick(P, 400, 2) if not FULL else (P if len(P) <= 2000 else rng.sample(P, 2000))
        n, m = len(g["pref"]), len(g["projects"])
        bad = {k: [] for k in ("utility", "welfare", "potential", "teams", "breakdown", "nash", "deviations",
                               "best_response", "deltaPhi")}
        for p in sample:
            u_e = ge.utilities(list(p), g)
            if [F(x) for x in u_e] != a["U"][p]:
                bad["utility"].append(p)
            if F(ge.social_welfare(list(p), g)) != a["W"][p]:
                bad["welfare"].append(p)
            if F(ge.potential(list(p), g)) != a["Phi"][p]:
                bad["potential"].append(p)
            if [len(t) for t in ge.teams(list(p), g)] != team_sizes(g, p):
                bad["teams"].append(p)
            for i in range(n):
                b = ge.utility_breakdown(i, list(p), g)
                if not (F(b["total"]) == a["U"][p][i] and F(b["preference"]) == q(g["pref"][i][p[i]])
                        and F(b["crowding"]) == crowd(g, team_sizes(g, p)[p[i]])
                        and F(b["compatibility"]) == sum((q(g["w"][i][j]) for j in teammates(p, i)), F(0))):
                    bad["breakdown"].append((p, i))
            nash = ge.is_nash(list(p), g)
            if nash["is_nash"] != is_nash(g, p):
                bad["nash"].append(p)
            mine = {(i, t, gain) for i, t, gain in deviations(g, p)}
            theirs = {(d["student"], d["to_project"], F(d["gain"])) for d in nash["deviations"]}
            if mine != theirs or {(d["student"], d["to_project"], F(d["gain"])) for d in ge.profitable_deviations(list(p), g)} != mine:
                bad["deviations"].append(p)
            for i in range(n):
                br = ge.best_response(i, list(p), g)
                t_mine, top = best_response(g, p, i)
                if br["best"] != t_mine or F(max(o["utility"] for o in br["options"])) != top or br["improves"] != (top > utility(g, p, i)):
                    bad["best_response"].append((p, i))
            i = rng.randrange(n)
            t = rng.randrange(m)
            if t != p[i]:
                r = moved(p, i, t)
                if F(ge.potential(list(r), g)) - F(ge.potential(list(p), g)) != F(ge.utility(i, list(r), g)) - F(ge.utility(i, list(p), g)):
                    bad["deltaPhi"].append((p, i, t))
        labels = {"utility": "individual utility", "welfare": "social welfare", "potential": "exact potential",
                  "teams": "team sizes", "breakdown": "utility breakdown (pref / compat / crowding / total)",
                  "nash": "Nash classification", "deviations": "profitable deviations (student, target, gain)",
                  "best_response": "best-response choice", "deltaPhi": "engine's delta Phi == delta u_i"}
        for k, lab in labels.items():
            rep.add(f"engine == oracle: {lab}", name, len(sample), not bad[k], str(bad[k][:3]))

        # exhaustive results
        e = ge.enumerate_equilibria(g)
        L = ge.analyze_landscape(g)
        eqs = {tuple(x["profile"]) for x in e["equilibria"]}
        ok = (e["n_profiles"] == len(P) and eqs == set(a["eq"]) and {tuple(x["profile"]) for x in L["equilibria"]} == eqs)
        rep.add("engine == oracle: profile count and the complete set of pure equilibria", name, len(P), ok,
                f"engine {len(eqs)} vs oracle {len(a['eq'])}")
        ok = (eqf(e["optimal"]["welfare"], a["wmax"]) and sorted(map(tuple, e["optimal_profiles"])) == sorted(a["opt"])
              and L["optimal_is_equilibrium"] == [p in set(a["eq"]) for p in map(tuple, L["optimal_profiles"])])
        rep.add("engine == oracle: maximum welfare, optimal profiles, optimum-is-equilibrium", name, len(P), ok)
        poa_ok = (e["price_of_anarchy"] is None) == (a["poa"] is None) and (a["poa"] is None or (
            abs(e["price_of_anarchy"] - float(a["poa"])) < 1e-12 and abs(e["price_of_stability"] - float(a["pos"])) < 1e-12))
        poa_ok &= (L["price_of_anarchy"] == e["price_of_anarchy"] and L["price_of_stability"] == e["price_of_stability"]
                   and (L["ratio_status"] == "defined") == (a["poa"] is not None))
        rep.add("engine == oracle: price of anarchy and price of stability (incl. undefined cases)", name, 1, poa_ok,
                f"oracle PoA={a['poa']} PoS={a['pos']} engine PoA={e['price_of_anarchy']}")
        pareto_ok = all(x["pareto_optimal"] == a["pareto"][tuple(x["profile"])] for x in e["equilibria"]) and \
            all(x["pareto_optimal"] == a["pareto"][tuple(x["profile"])] for x in L["equilibria"]) and \
            L["n_pareto_optimal_equilibria"] == sum(a["pareto"].values())
        wit_ok = True
        for x in L["equilibria"]:
            if x["dominated_by"] is not None:
                u, v = a["U"][tuple(x["profile"])], a["U"][tuple(x["dominated_by"])]
                wit_ok &= all(y >= z for y, z in zip(v, u)) and any(y > z for y, z in zip(v, u))
        rep.add("engine == oracle: Pareto-optimality of each equilibrium; dominators are genuine", name, len(a["eq"]), pareto_ok and wit_ok)
        lv = [(x["welfare"], x["count"]) for x in L["equilibrium_welfare_levels"]]
        mine_lv = sorted((w_, sum(1 for p in a["eq"] if a["W"][p] == w_)) for w_ in set(a["W"][p] for p in a["eq"]))
        dist_ok = (sum(r["n_profiles"] for r in L["welfare_distribution"]) == len(P)
                   and [(F(w_), c) for w_, c in lv] == [(w_, c) for w_, c in mine_lv]
                   and L["n_equilibrium_welfare_levels"] == len(a["eq_welfare_levels"]))
        rep.add("engine == oracle: equilibrium welfare levels and welfare distribution", name, len(P), dist_ok)
        ok = eqf(e["potential_maximizers"]["potential"], a["phi_max"]) and \
            sorted(map(tuple, e["potential_maximizers"]["profiles"])) == sorted(a["phi_argmax"])
        rep.add("engine == oracle: potential maximum and maximisers", name, len(P), ok)

        # dynamics: engine vs oracle, both update orders
        starts = P if len(P) <= 800 else rng.sample(P, 400 if FULL else 100)
        bad_dyn = []
        for p in starts:
            for order, seed in (("round_robin", None), ("random", 0), ("random", 7)):
                run = ge.best_response_dynamics(g, list(p), order=order, seed=seed)
                final, moves, conv, rounds, trace = dynamics(g, p, order, seed)
                mine_trace = [(i, f_, t_) for i, f_, t_, _ in trace]
                their_trace = [(s_["student"], s_["from_project"], s_["to_project"]) for s_ in run["steps"]]
                if not (tuple(run["final_profile"]) == final and run["converged"] == conv and run["rounds"] == rounds
                        and mine_trace == their_trace and run["is_nash_final"] == is_nash(g, final)
                        and [F(s_["gain"]) for s_ in run["steps"]] == [x[3] for x in trace]
                        and [F(s_["potential"]) for s_ in run["steps"]] == [potential(g, p_) for p_ in _replay(p, trace)]):
                    bad_dyn.append((p, order, seed))
        rep.add("engine == oracle: best-response dynamics (trace, final profile, rounds, converged), round-robin and random order",
                name, len(starts) * 3, not bad_dyn, str(bad_dyn[:2]))
        # sweep limit is reported honestly
        p0 = starts[0]
        lim = ge.best_response_dynamics(g, list(p0), max_rounds=1)
        f1, _, c1, r1, _ = dynamics(g, p0, max_rounds=1)
        rep.add("engine == oracle: sweep-limit behaviour (max_rounds=1)", name, 1,
                lim["converged"] == c1 and tuple(lim["final_profile"]) == f1 and lim["is_nash_final"] == is_nash(g, f1))


def _replay(start, trace):
    s = tuple(start)
    out = []
    for (i, _, t, _) in trace:
        s = moved(s, i, t)
        out.append(s)
    return out


def format_report(rep, compared):
    lines = ["STRATOS independent oracle report", "=" * 34,
             f"engine compared: {'yes' if compared else 'no (oracle self-checks only)'}",
             f"mode: {'full (exhaustive on the default scenario)' if FULL else 'fast (fixed-seed samples on the 6,561-profile default scenario; every other scenario exhaustive)'}",
             f"scenarios: {', '.join(SCENARIOS)}", ""]
    width = max(len(r["check"]) for r in rep.rows)
    for r in rep.rows:
        lines.append(f"{'PASS' if r['ok'] else 'FAIL'}  {r['check']:<{width}}  [{r['scenario']}, {r['cases']} cases]"
                     + (f"  -> {r['detail']}" if not r["ok"] and r["detail"] else ""))
    lines += ["", f"checks run: {len(rep.rows)}   failed: {len(rep.failures)}",
              "RESULT: " + ("ALL CHECKS PASSED" if not rep.failures else "DISCREPANCIES FOUND")]
    return "\n".join(lines)


def main(argv):
    global FULL
    FULL = "--full" in argv
    rep = Report()
    selfchecks(rep)
    compared = "--compare" in argv
    if compared:
        compare(rep)
    text = format_report(rep, compared)
    print(text)
    if "--report" in argv:
        path = argv[argv.index("--report") + 1]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
