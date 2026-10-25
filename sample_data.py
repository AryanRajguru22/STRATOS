"""Synthetic scenarios for STRATOS.

EVERYTHING HERE IS FICTIONAL. The students do not exist, and the preference numbers and model weights are
modelling assumptions chosen so that strategic behaviour (profitable deviations, several equilibria, a gap
between stable and welfare-maximising outcomes) is visible in a small demonstration. They are not measurements.

Compatibility is derived from skill sets: w[i][j] = LAMBDA * |S_i symmetric-difference S_j| - BETA, which is
symmetric by construction (complementary skills help, near-identical students help less).
"""
from __future__ import annotations

import copy

SYNTHETIC_DATA_NOTICE = ("All student data and model weights are fictional and synthetic, chosen to make "
                         "strategic behaviour visible; they are not measurements of real students.")

LAMBDA = 1
BETA = 1
DEFAULT_GAMMA = 2

_STUDENTS = ["Asha", "Bram", "Chen", "Dara", "Eli", "Farah", "Goran", "Hana"]
_SKILLS = {
    "Asha": ["Programming", "Analysis"],
    "Bram": ["Programming"],
    "Chen": ["Analysis", "Communication"],
    "Dara": ["Design", "Communication"],
    "Eli": ["Programming", "Design"],
    "Farah": ["Analysis"],
    "Goran": ["Communication"],
    "Hana": ["Design", "Analysis"],
}
_PROJECTS = ["Campus Navigation App", "Wellbeing Survey Analysis", "Event Management Portal"]
_PREF = [
    [8, 6, 2],   # Asha
    [9, 1, 5],   # Bram
    [3, 9, 4],   # Chen
    [7, 3, 8],   # Dara
    [9, 2, 6],   # Eli
    [4, 8, 3],   # Farah
    [2, 5, 9],   # Goran
    [6, 7, 5],   # Hana
]
# Chosen after inspecting the model's behaviour (it has 2 profitable deviations and a readable 4-move trace);
# the preferences, skills and DEFAULT_GAMMA above were fixed beforehand.
_DEMO_START = [0, 0, 0, 1, 1, 1, 2, 2]


def _compatibility(students: list, skills: dict) -> list:
    n = len(students)
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            diff = len(set(skills[students[i]]) ^ set(skills[students[j]]))
            w[i][j] = w[j][i] = LAMBDA * diff - BETA
    return w


def get_default_scenario() -> dict:
    """Eight fictional students, three projects. Returns a fresh dict every call."""
    return {
        "students": list(_STUDENTS),
        "projects": list(_PROJECTS),
        "pref": copy.deepcopy(_PREF),
        "w": _compatibility(_STUDENTS, _SKILLS),
        "gamma": DEFAULT_GAMMA,
        "skills": copy.deepcopy(_SKILLS),
    }


def get_demo_start_profile() -> list:
    """Fixed, deliberately unstable start assignment used by the live demo (see docs/DEMO_SCRIPT.md)."""
    return list(_DEMO_START)


def get_tiny_scenario() -> dict:
    """Two students, two projects, gamma = 1: the hand-derived example in Section 8 of the plan.

    pref = [[5, 1], [1, 5]], w = [[0, 2], [2, 0]]. Unique pure equilibrium [0, 1], which is also welfare-optimal.
    """
    return {
        "students": ["S0", "S1"],
        "projects": ["P0", "P1"],
        "pref": [[5, 1], [1, 5]],
        "w": [[0, 2], [2, 0]],
        "gamma": 1,
    }
