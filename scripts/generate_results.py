"""Regenerate the evidence files in docs/results/ from real commands (nothing is typed by hand).

    python scripts/generate_results.py

Writes:
  docs/results/engine_report.json   output of  python game_engine.py --report --out ...  plus git provenance
  docs/results/pytest_output.txt    full output of  python -m pytest -q
  docs/results/timing.txt           enumeration timing read from the report (5 timed runs)

Provenance records the commit hash AND whether uncommitted changes existed, because results generated before a
commit describe the working tree, not the hash. The exit status is non-zero if the tests fail.
"""
import datetime
import json
import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "results")
PY = sys.executable


def run(*cmd):
    return subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def git_info():
    head = run("git", "rev-parse", "HEAD")
    if head.returncode != 0:
        return {"commit": None, "branch": None, "uncommitted_paths": None, "note": "not a git repository"}
    status = run("git", "status", "--porcelain")
    paths = [line for line in status.stdout.splitlines() if line.strip() and "docs/results/" not in line]
    return {"commit": head.stdout.strip(), "branch": run("git", "branch", "--show-current").stdout.strip(),
            "uncommitted_paths": len(paths),
            "note": ("working tree has uncommitted changes: results describe the working tree on top of this commit"
                     if paths else "working tree clean: results describe exactly this commit")}


def main():
    os.makedirs(OUT, exist_ok=True)
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    info = git_info()
    report_path = os.path.join(OUT, "engine_report.json")

    # 1. engine report (before pytest, so the timing is not disturbed and I-06 checks the fresh file)
    rep = run(PY, "game_engine.py", "--report", "--out", report_path)
    if rep.returncode != 0:
        sys.stderr.write(rep.stderr)
        return rep.returncode
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)
    report["meta"]["generated_at"] = now
    report["meta"]["git"] = info
    with open(report_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    # 2. tests
    tests = run(PY, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    with open(os.path.join(OUT, "pytest_output.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(f"command: python -m pytest -q -p no:cacheprovider\n")
        f.write(f"generated: {now}\npython: {platform.python_version()}  platform: {platform.platform()}\n")
        f.write(f"git commit: {info['commit']}  branch: {info['branch']}\n")
        f.write(f"git note: {info['note']}\n")
        f.write(f"exit code: {tests.returncode}\n--- output ---\n{tests.stdout}")
        if tests.stderr.strip():
            f.write(f"--- stderr ---\n{tests.stderr}")

    # 3. timing (read from the report that the engine itself produced)
    t = report["meta"]["timing"]
    with open(os.path.join(OUT, "timing.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("STRATOS exhaustive enumeration timing (measured, not estimated)\n")
        f.write(f"command: python scripts/generate_results.py  (runs: python game_engine.py --report)\n")
        f.write(f"generated: {now}\npython: {platform.python_version()}  platform: {platform.platform()}\n")
        f.write(f"git commit: {info['commit']}  ({info['note']})\n")
        f.write(f"what: {t['what']}\nprofiles enumerated per run: {t['n_profiles']}\n")
        f.write(f"runs (seconds): {t['runs_seconds']}\nmin: {t['min_seconds']} s   median: {t['median_seconds']} s\n")
        f.write("Timings vary between machines and runs; treat them as indicative of this machine only.\n")

    print(f"engine report, pytest output (exit code {tests.returncode}) and timing written to docs/results/")
    print(tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else "(no pytest output)")
    return tests.returncode


if __name__ == "__main__":
    sys.exit(main())
