"""Scenario export / import for STRATOS (standard library only, independent of Streamlit).

A scenario file is plain JSON::

    {"format": "stratos-scenario", "version": 1, "synthetic": true,
     "students": [...], "projects": [...], "pref": [[...]], "w": [[...]], "gamma": 2, "skills": {...}}

Import is strict: the text is size-limited, parsed with a JSON parser that rejects NaN/Infinity, checked for unknown
or missing keys, limited to the same player/project counts the UI offers, and finally passed through the engine's own
``validate_scenario`` (symmetry, zero diagonal, numeric types, unique names). Anything invalid raises
``ScenarioFileError`` with a message the UI can show verbatim; nothing invalid is ever returned.

Every file carries ``"synthetic": true``: STRATOS scenarios are experimental inputs, never real student records.
"""
from __future__ import annotations

import json
from typing import Any

import game_engine

FORMAT = "stratos-scenario"
VERSION = 1
MAX_FILE_BYTES = 200_000
MAX_STUDENTS = 12
MAX_PROJECTS = 5
_ALLOWED = {"format", "version", "synthetic", "students", "projects", "pref", "w", "gamma", "skills", "title"}
_REQUIRED = {"students", "projects", "pref", "w", "gamma"}


class ScenarioFileError(game_engine.StratosError):
    """The scenario file is not valid STRATOS scenario JSON (the message says why)."""


def scenario_to_json(scenario: dict, title: str | None = None) -> str:
    """Serialise a (valid) scenario to the STRATOS JSON format. Raises ScenarioError if it is not valid."""
    game_engine.validate_scenario(scenario)
    doc: dict = {"format": FORMAT, "version": VERSION, "synthetic": True}
    if title:
        doc["title"] = str(title)
    for key in ("students", "projects", "pref", "w"):
        doc[key] = game_engine._as_list(scenario[key])
    doc["gamma"] = scenario["gamma"]
    if scenario.get("skills"):
        doc["skills"] = scenario["skills"]
    return json.dumps(doc, indent=2, ensure_ascii=False)


def _reject_constant(name: str) -> Any:
    raise ScenarioFileError(f"JSON constant {name} is not allowed (numbers must be finite)")


def scenario_from_json(text: str | bytes, max_students: int = MAX_STUDENTS, max_projects: int = MAX_PROJECTS) -> dict:
    """Parse and fully validate scenario JSON; return a plain scenario dict or raise ScenarioFileError."""
    if isinstance(text, (bytes, bytearray)):
        if len(text) > MAX_FILE_BYTES:
            raise ScenarioFileError(f"file is too large ({len(text)} bytes; limit {MAX_FILE_BYTES})")
        try:
            text = bytes(text).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ScenarioFileError(f"file is not valid UTF-8 text: {exc}") from exc
    if not isinstance(text, str):
        raise ScenarioFileError(f"expected JSON text, got {type(text).__name__}")
    if len(text.encode("utf-8")) > MAX_FILE_BYTES:
        raise ScenarioFileError(f"file is too large (limit {MAX_FILE_BYTES} bytes)")
    try:
        doc = json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise ScenarioFileError(f"not valid JSON: {exc}") from exc
    if not isinstance(doc, dict):
        raise ScenarioFileError("the top level of the file must be a JSON object")
    if "format" in doc and doc["format"] != FORMAT:
        raise ScenarioFileError(f"unsupported format {doc['format']!r} (expected {FORMAT!r})")
    if "version" in doc and doc["version"] != VERSION:
        raise ScenarioFileError(f"unsupported version {doc['version']!r} (this build reads version {VERSION})")
    unknown = sorted(set(doc) - _ALLOWED)
    if unknown:
        raise ScenarioFileError(f"unknown key(s): {', '.join(unknown)}")
    missing = sorted(_REQUIRED - set(doc))
    if missing:
        raise ScenarioFileError(f"missing required key(s): {', '.join(missing)}")
    scenario = {k: doc[k] for k in ("students", "projects", "pref", "w", "gamma", "skills") if k in doc}
    try:
        game_engine.validate_scenario(scenario)
    except game_engine.ScenarioError as exc:
        raise ScenarioFileError(str(exc)) from exc
    n, m = len(scenario["students"]), len(scenario["projects"])
    if n > max_students:
        raise ScenarioFileError(f"{n} students exceeds the limit of {max_students}")
    if m > max_projects:
        raise ScenarioFileError(f"{m} projects exceeds the limit of {max_projects}")
    return scenario
