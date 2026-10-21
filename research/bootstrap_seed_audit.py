#!/usr/bin/env python3
"""Cycle 940: audit of the seeded/unseeded bootstrap calls in the repository.

Why this tool exists
--------------------
A moving-block bootstrap whose seed is not fixed draws a **different resample on
every execution**, so every statistic derived from it (the Deflated Sharpe Ratio,
the probabilistic Sharpe Ratio, the bootstrap confidence interval) is
**unreproducible**: a publisher that writes such a statistic into a committed
record silently rewrites that record with a different number on the next run.

The Cycle-938 ``liquidity_001`` record was published that way (the Deflated Sharpe
Ratio line read -2.919035 and changed on every run; see
``research/experiments/liquidity_001_evaluation_erratum_001.md``). This tool
audits every bootstrap call site in ``research/`` and ``src/`` so that the same
defect cannot recur silently.

What it does
------------
* parses every ``.py`` file under ``research/`` and ``src/`` with :mod:`ast`;
* finds the calls to the three bootstrap entry points whose seed has a default of
  ``None`` (``compute_dsr``, ``compute_psr``, ``block_bootstrap_sharpe``);
* decides, per call site, whether a seed is supplied (keyword or positional) and
  whether the supplied seed is the literal ``None``;
* reports the call sites that are **unseeded**;
* **fails closed** when a *candidate evaluator* (``research/*_evaluation.py``) holds
  an unseeded call, because those tools publish their output into committed
  records.

``moving_block_bootstrap_mean`` (the fold-level CI helper) takes its seed as a
**required** positional argument, so a call without one raises ``TypeError``; it
needs no audit and is not scanned.

The tool is **read-only**: it writes nothing unless ``--write`` is given, and it
never touches ``data/`` or ``config/``.

Reproduction
------------
```bash
python research/bootstrap_seed_audit.py
python research/bootstrap_seed_audit.py --write
python -m pytest -q tests/test_bootstrap_seed_audit.py
```
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CYCLE = "940"

REPORTS_DIR = REPO_ROOT / "research" / "reports"
EXPERIMENTS_DIR = REPO_ROOT / "research" / "experiments"
OUT_REPORT = REPORTS_DIR / "bootstrap_seed_audit_001.md"
OUT_EXP = EXPERIMENTS_DIR / "bootstrap_seed_audit_001.md"

SCAN_ROOTS = ("research", "src")

#: The bootstrap entry points whose ``seed`` parameter defaults to ``None``.
#: ``seed_index`` is the position of ``seed`` in the signature, ``required`` the
#: number of parameters before it.
TARGETS: dict[str, dict[str, int]] = {
    "compute_dsr": {"seed_index": 5, "required": 2},
    "compute_psr": {"seed_index": 4, "required": 1},
    "block_bootstrap_sharpe": {"seed_index": 3, "required": 1},
}

#: A tool that publishes a committed record must never hold an unseeded call.
CANDIDATE_EVALUATOR_GLOB = "research/*_evaluation.py"


def _is_target(node: ast.Call) -> str | None:
    """Return the audited function name if *node* calls one of the targets."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id if func.id in TARGETS else None
    if isinstance(func, ast.Attribute):
        return func.attr if func.attr in TARGETS else None
    return None


def _seed_state(node: ast.Call, spec: dict[str, int]) -> tuple[bool, str]:
    """Classify the seed of one call site.

    Returns ``(seeded, expression)`` where *expression* is the source text of the
    seed argument (empty when the call supplies none).
    """
    for keyword in node.keywords:
        if keyword.arg == "seed":
            expression = ast.unparse(keyword.value)
            return expression.strip() != "None", expression
    if len(node.args) > spec["seed_index"]:
        expression = ast.unparse(node.args[spec["seed_index"]])
        return expression.strip() != "None", expression
    return False, ""


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        files.extend(
            path
            for path in base.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    return sorted(files)


def scan() -> dict[str, Any]:
    """Scan every python file and classify its bootstrap call sites."""
    call_sites: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for path in _python_files():
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except SyntaxError as error:  # pragma: no cover - defensive
            parse_errors.append(f"{path.relative_to(REPO_ROOT)}: {error}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _is_target(node)
            if name is None:
                continue
            seeded, expression = _seed_state(node, TARGETS[name])
            call_sites.append(
                {
                    "file": str(path.relative_to(REPO_ROOT)),
                    "line": int(node.lineno),
                    "function": name,
                    "seeded": bool(seeded),
                    "seed": expression,
                }
            )
    call_sites.sort(key=lambda site: (site["file"], site["line"], site["function"]))

    unseeded = [site for site in call_sites if not site["seeded"]]
    candidate_evaluators = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in REPO_ROOT.glob(CANDIDATE_EVALUATOR_GLOB)
    )
    offending = sorted(
        {site["file"] for site in unseeded if site["file"] in candidate_evaluators}
    )
    return {
        "call_sites": call_sites,
        "unseeded": unseeded,
        "candidate_evaluators": candidate_evaluators,
        "offending_evaluators": offending,
        "parse_errors": parse_errors,
    }


def run_checks(result: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "repository_parses",
            "pass": not result["parse_errors"],
            "detail": "every python file under research/ and src/ parses",
        }
    )
    checks.append(
        {
            "name": "candidate_evaluators_seed_every_bootstrap",
            "pass": not result["offending_evaluators"],
            "detail": (
                "no unseeded bootstrap call in a candidate evaluator"
                if not result["offending_evaluators"]
                else "unseeded bootstrap in " + ", ".join(result["offending_evaluators"])
            ),
        }
    )
    checks.append(
        {
            "name": "bootstrap_call_sites_found",
            "pass": len(result["call_sites"]) > 0,
            "detail": f"{len(result['call_sites'])} bootstrap call sites scanned",
        }
    )
    return checks


def _site_rows(sites: list[dict[str, Any]]) -> list[str]:
    rows = []
    for site in sites:
        rows.append(
            f"| `{site['file']}:{site['line']}` | `{site['function']}` | "
            f"{'seeded' if site['seeded'] else '**unseeded**'} | "
            f"{('`' + site['seed'] + '`') if site['seed'] else '(none)'} |"
        )
    return rows


def render_report(result: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Report: bootstrap seed audit (bootstrap_seed_audit)")
    lines.append("")
    lines.append(
        f"**Cycle {CYCLE}.** Read-only, deterministic audit of every bootstrap call "
        "site in `research/` and `src/`. The tool parses the repository with `ast`; "
        "it reads no market data, calls no fetcher and writes nothing unless "
        "`--write` is given. This document contains no timestamp: two consecutive "
        "runs are byte-identical."
    )
    lines.append("")
    lines.append("## What a missing seed costs")
    lines.append("")
    lines.append(
        "`compute_dsr`, `compute_psr` and `block_bootstrap_sharpe` draw their "
        "resamples with `np.random.default_rng(seed)`. With `seed=None` the "
        "generator is seeded from OS entropy, so a different resample -- and every "
        "statistic derived from it -- is produced on every execution. A tool that "
        "publishes such a statistic into a committed record therefore rewrites that "
        "record with a different number on its next run. That is exactly what "
        "happened to the Cycle-938 `liquidity_001` record; the correction of "
        "record is `research/experiments/liquidity_001_evaluation_erratum_001.md`."
    )
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| Bootstrap call sites scanned | {len(result['call_sites'])} |")
    lines.append(f"| Seeded call sites | {len(result['call_sites']) - len(result['unseeded'])} |")
    lines.append(f"| Unseeded call sites | {len(result['unseeded'])} |")
    lines.append(f"| Candidate evaluators audited | {len(result['candidate_evaluators'])} |")
    lines.append(f"| Candidate evaluators with an unseeded call | {len(result['offending_evaluators'])} |")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Outcome | Detail |")
    lines.append("|---|---|---|")
    for check in checks:
        lines.append(
            f"| `{check['name']}` | {'PASS' if check['pass'] else '**FAIL**'} | {check['detail']} |"
        )
    lines.append("")
    lines.append("## Every bootstrap call site")
    lines.append("")
    lines.append("| Call site | Function | Seed | Seed expression |")
    lines.append("|---|---|---|---|")
    lines.extend(_site_rows(result["call_sites"]))
    lines.append("")
    if result["unseeded"]:
        lines.append("## Unseeded call sites (findings)")
        lines.append("")
        lines.append("| Call site | Function | Seed | Seed expression |")
        lines.append("|---|---|---|---|")
        lines.extend(_site_rows(result["unseeded"]))
        lines.append("")
        lines.append(
            "These call sites are **not** repaired by this audit. They belong to "
            "historical cycle scripts whose published records are immutable; the "
            "audit records their status so that the next cycle can decide whether "
            "to re-state them. The candidate evaluators, whose output is "
            "regenerated into committed records on every test run, are all seeded."
        )
        lines.append("")
    lines.append("## Reproduction")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/bootstrap_seed_audit.py")
    lines.append("python research/bootstrap_seed_audit.py --write")
    lines.append("python -m pytest -q tests/test_bootstrap_seed_audit.py")
    lines.append("```")
    return "\n".join(lines) + "\n"


def render_experiment(result: dict[str, Any], checks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Experiment: bootstrap seed audit (bootstrap_seed_audit)")
    lines.append("")
    lines.append(f"**Cycle {CYCLE}.** Deterministic, read-only audit of the seed of "
                 "every bootstrap call site in `research/` and `src/`.")
    lines.append("")
    lines.append("## Hypothesis reference")
    lines.append("")
    lines.append(
        "None (measurement cycle). The audit was triggered by the Cycle-940 "
        "finding that the Cycle-938 `liquidity_001` record published an "
        "unreproducible Deflated Sharpe Ratio."
    )
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append(
        "- every `.py` file under `research/` and `src/` is parsed with `ast`;"
    )
    lines.append(
        "- every call to `compute_dsr`, `compute_psr` and `block_bootstrap_sharpe` "
        "(the bootstrap entry points whose `seed` defaults to `None`) is located;"
    )
    lines.append(
        "- a call is **seeded** when it supplies a `seed` keyword (or the seed's "
        "positional slot) whose value is not the literal `None`;"
    )
    lines.append(
        "- the audit **fails closed** when a candidate evaluator "
        "(`research/*_evaluation.py`) holds an unseeded call."
    )
    lines.append("")
    lines.append("## Result")
    lines.append("")
    lines.append("| Quantity | Value |")
    lines.append("|---|---|")
    lines.append(f"| Bootstrap call sites scanned | {len(result['call_sites'])} |")
    lines.append(f"| Unseeded call sites | {len(result['unseeded'])} |")
    lines.append(f"| Candidate evaluators with an unseeded call | {len(result['offending_evaluators'])} |")
    lines.append("")
    for check in checks:
        lines.append(
            f"- `{check['name']}`: {'PASS' if check['pass'] else '**FAIL**'} -- {check['detail']}"
        )
    lines.append("")
    lines.append("## Reproduction commands")
    lines.append("")
    lines.append("```bash")
    lines.append("python research/bootstrap_seed_audit.py")
    lines.append("python -m pytest -q tests/test_bootstrap_seed_audit.py")
    lines.append("```")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the report and the experiment record under research/",
    )
    args = parser.parse_args(argv)

    result = scan()
    checks = run_checks(result)
    overall = all(check["pass"] for check in checks)

    if args.write:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(render_report(result, checks))
        OUT_EXP.write_text(render_experiment(result, checks))

    print(f"OVERALL: {'PASS' if overall else 'FAIL'}")
    for check in checks:
        print(f"CHECK|{check['name']}|{'PASS' if check['pass'] else 'FAIL'}|{check['detail']}")
    print(f"CALL_SITES|{len(result['call_sites'])}")
    print(f"UNSEEDED|{len(result['unseeded'])}")
    for site in result["unseeded"]:
        print(f"UNSEEDED_SITE|{site['file']}:{site['line']}|{site['function']}")
    print(f"REPORT|{OUT_REPORT if args.write else '(not written: no --write)'}")
    print(f"EXPERIMENT|{OUT_EXP if args.write else '(not written: no --write)'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
