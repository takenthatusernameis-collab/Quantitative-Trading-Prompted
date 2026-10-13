#!/usr/bin/env python3
"""Dependency-free source contract check for the corrected C4 runner.

This is intentionally static: the full data-backed validation belongs to
research/run_cycle15_c4_corrected.py and requires the frozen local parquet cache.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "research" / "run_cycle15_c4_corrected.py"
EXPECTED_UNIVERSE = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
EXPECTED_CORE7 = ["SPY", "QQQ", "IWM", "TLT", "GLD", "EFA", "EEM"]
EXPECTED_FOLD_ENDPOINTS = (
    {
        "train_start": "1998-12-22",
        "train_end": "2008-08-18",
        "test_start": "2008-09-17",
        "test_end": "2009-09-03",
    },
    {
        "train_start": "2015-11-17",
        "train_end": "2025-07-14",
        "test_start": "2025-08-13",
        "test_end": "2026-07-30",
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"C4 source contract FAILED: {message}")


def get_assignment(module: ast.Module, name: str):
    for node in module.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                value = node.value
                try:
                    return ast.literal_eval(value)
                except (ValueError, TypeError):
                    return None
    return None


def get_function(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise SystemExit(f"C4 source contract FAILED: function {name} is missing")


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def main() -> None:
    require(RUNNER.is_file(), "corrected runner file is missing")
    source = RUNNER.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(RUNNER))

    require(get_assignment(tree, "UNIVERSE") == EXPECTED_UNIVERSE,
            "candidate universe is not exactly the nine frozen sector ETFs")
    require(get_assignment(tree, "CORE7") == EXPECTED_CORE7,
            "incumbent benchmark universe changed unexpectedly")
    require(get_assignment(tree, "START_DATE") == "1998-12-22",
            "candidate start date must be 1998-12-22")
    require(get_assignment(tree, "END_DATE") == "2026-10-09",
            "frozen requested end date must remain 2026-10-09")
    require(get_assignment(tree, "CORE7_START_DATE") == "1993-01-01",
            "incumbent warm-up history must remain separate and start in 1993")
    require(get_assignment(tree, "N_PREREGISTERED_TRIALS") == 18,
            "frozen multiple-testing trial count must be 18")

    lookbacks = get_assignment(tree, "LOOKBACKS")
    skips = get_assignment(tree, "SKIPS")
    fractions = get_assignment(tree, "TOP_FRACTIONS")
    require(lookbacks is not None and skips is not None and fractions is not None,
            "parameter grid assignments must remain literal and inspectable")
    require(len(lookbacks) * len(skips) * len(fractions) == 18,
            "3 x 2 x 3 grid must equal exactly 18 configurations")

    fold_endpoints = get_assignment(tree, "EXPECTED_FOLD_ENDPOINTS")
    require(fold_endpoints == EXPECTED_FOLD_ENDPOINTS,
            "first/last frozen walk-forward endpoints changed unexpectedly")

    hash_body = ast.get_source_segment(source, get_function(tree, "_config_hash")) or ""
    require("sectorrotation_candidate_001.yaml" in hash_body,
            "configuration hash must reference the frozen C4 config")
    require("csmomentum_candidate_001.yaml" not in hash_body,
            "configuration hash still references C3")

    for function_name in (
        "_validate_preregistered_contract",
        "_require_cached_inputs",
        "_validate_sector_close",
        "_validate_core_benchmark_close",
        "_validate_generated_outputs",
    ):
        get_function(tree, function_name)

    main_function = get_function(tree, "main")
    call_lines: dict[str, list[int]] = {}
    for node in ast.walk(main_function):
        if isinstance(node, ast.Call):
            name = call_name(node)
            if name:
                call_lines.setdefault(name, []).append(node.lineno)

    contract_line = min(call_lines.get("_validate_preregistered_contract", [10**9]))
    cache_line = min(call_lines.get("_require_cached_inputs", [10**9]))
    fetch_lines = call_lines.get("fetch_close_prices", [])
    output_line = min(call_lines.get("_validate_generated_outputs", [10**9]))
    require(contract_line < cache_line < min(fetch_lines, default=10**9) < output_line,
            "pre-registration and cache guards must run before fetches; output verification must run last")

    # Confirm the benchmark is loaded independently rather than selected from the candidate universe.
    has_separate_benchmark_load = False
    for node in ast.walk(main_function):
        if isinstance(node, ast.Call) and call_name(node) == "fetch_close_prices" and len(node.args) >= 2:
            if isinstance(node.args[0], ast.Name) and node.args[0].id == "CORE7":
                if isinstance(node.args[1], ast.Name) and node.args[1].id == "CORE7_START_DATE":
                    has_separate_benchmark_load = True
    require(has_separate_benchmark_load, "CORE7 benchmark must be loaded separately")
    require("close_core = close[CORE7]" not in source,
            "benchmark KeyError risk remains: CORE7 is not a subset of the sector universe")

    for token in (
        "EXPECTED_CLOSE_ROWS = 6991",
        "if len(splits) != 36",
        "Persisted artifact contract: PASS",
        "config/sectorrotation_candidate_001.yaml",
        "research/run_cycle15_c4_corrected.py",
    ):
        require(token in source, f"required runtime check/provenance token is missing: {token}")

    for stale_claim in (
        "csmomentum_001",
        "config/csmomentum_candidate_001.yaml",
        "18 ETF files + ^VIX",
        "constant 1/18",
        "1993-2009",
        "pre-registration mislabel",
        "Both are negative",
    ):
        require(stale_claim not in source, f"stale copied-report claim remains: {stale_claim}")

    print("C4 source contract: PASS (universe, config provenance, 18-config grid, 36-fold anchors, cache guard, separate incumbent benchmark, output verification).")


if __name__ == "__main__":
    main()
