"""
Evals Runner - Shared logic for CLI.
"""

import json
from pathlib import Path
from typing import Optional

from llm import generate_sql
from validator import validate_sql


def load_cases(path: Optional[str] = None) -> dict:
    """Load eval cases from JSON."""
    cases_path = Path(path) if path else Path(__file__).parent.parent / "evals" / "cases.json"
    with open(cases_path) as f:
        return json.load(f)


def run_schema_correctness(cases: list[dict], verbose: bool = False) -> dict:
    """
    Eval 1: Schema Correctness
    Generated SQL should reference only valid table + columns.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("EVAL 1: Schema Correctness")
        print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for case in cases:
        if verbose:
            print(f"\n[{case['id']}] {case['query']}")

        gen_result = generate_sql(case["query"])
        if not gen_result["success"]:
            if verbose:
                print(f"  FAIL: Generation failed - {gen_result['error']}")
            results.append({"id": case["id"], "passed": False, "error": gen_result["error"]})
            failed += 1
            continue

        sql = gen_result["sql"]
        if verbose:
            print(f"  SQL: {sql}")

        is_valid, errors = validate_sql(sql)
        if is_valid:
            if verbose:
                print("  PASS")
            results.append({"id": case["id"], "passed": True, "sql": sql})
            passed += 1
        else:
            if verbose:
                print(f"  FAIL: {errors}")
            results.append({"id": case["id"], "passed": False, "sql": sql, "errors": errors})
            failed += 1

    if verbose:
        print(f"\n--- Schema Correctness: {passed}/{len(cases)} passed ---")
    return {"name": "schema_correctness", "passed": passed, "failed": failed, "results": results}


def run_intent_checks(cases: list[dict], verbose: bool = False) -> dict:
    """
    Eval 2: Intent/Shape Checks
    SQL should contain expected structural patterns.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("EVAL 2: Intent Checks")
        print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for case in cases:
        if verbose:
            print(f"\n[{case['id']}] {case['query']}")
            print(f"  Expected: {case['expected_patterns']}")

        gen_result = generate_sql(case["query"])
        if not gen_result["success"]:
            if verbose:
                print(f"  FAIL: Generation failed - {gen_result['error']}")
            results.append({"id": case["id"], "passed": False, "error": gen_result["error"]})
            failed += 1
            continue

        sql = gen_result["sql"]
        sql_upper = sql.upper()
        if verbose:
            print(f"  SQL: {sql}")

        missing = []
        for pattern in case["expected_patterns"]:
            if pattern.upper() not in sql_upper:
                missing.append(pattern)

        if not missing:
            if verbose:
                print("  PASS")
            results.append({"id": case["id"], "passed": True, "sql": sql})
            passed += 1
        else:
            if verbose:
                print(f"  FAIL: Missing patterns: {missing}")
            results.append({"id": case["id"], "passed": False, "sql": sql, "missing": missing})
            failed += 1

    if verbose:
        print(f"\n--- Intent Checks: {passed}/{len(cases)} passed ---")
    return {"name": "intent_checks", "passed": passed, "failed": failed, "results": results}


def run_determinism(cases: list[dict], verbose: bool = False) -> dict:
    """
    Eval 3: Determinism/Stability
    Same query should produce valid SQL across multiple samples.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("EVAL 3: Determinism")
        print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for case in cases:
        samples = case.get("samples", 5)
        if verbose:
            print(f"\n[{case['id']}] {case['query']} (x{samples})")

        valid_count = 0
        sqls = []

        for i in range(samples):
            gen_result = generate_sql(case["query"])
            if gen_result["success"]:
                sql = gen_result["sql"]
                sqls.append(sql)
                is_valid, _ = validate_sql(sql)
                if is_valid:
                    valid_count += 1
                    if verbose:
                        print(f"  Sample {i+1}: VALID")
                else:
                    if verbose:
                        print(f"  Sample {i+1}: INVALID")
            else:
                if verbose:
                    print(f"  Sample {i+1}: GENERATION FAILED")
                sqls.append(None)

        validity_rate = valid_count / samples
        case_passed = validity_rate >= 0.8

        if verbose:
            if case_passed:
                print(f"  PASS ({valid_count}/{samples} = {validity_rate:.0%})")
            else:
                print(f"  FAIL ({valid_count}/{samples} = {validity_rate:.0%})")

        results.append({
            "id": case["id"],
            "passed": case_passed,
            "valid_count": valid_count,
            "total": samples,
            "validity_rate": validity_rate,
            "sqls": sqls
        })

        if case_passed:
            passed += 1
        else:
            failed += 1

    if verbose:
        print(f"\n--- Determinism: {passed}/{len(cases)} passed ---")
    return {"name": "determinism", "passed": passed, "failed": failed, "results": results}


def run_evals(eval_name: str = "all", cases: Optional[dict] = None, verbose: bool = False) -> dict:
    if cases is None:
        cases = load_cases()

    all_results = []
    total_passed = 0
    total_failed = 0

    if eval_name in ["schema", "all"]:
        result = run_schema_correctness(cases["schema_correctness"], verbose=verbose)
        all_results.append(result)
        total_passed += result["passed"]
        total_failed += result["failed"]

    if eval_name in ["intent", "all"]:
        result = run_intent_checks(cases["intent_checks"], verbose=verbose)
        all_results.append(result)
        total_passed += result["passed"]
        total_failed += result["failed"]

    if eval_name in ["determinism", "all"]:
        result = run_determinism(cases["determinism"], verbose=verbose)
        all_results.append(result)
        total_passed += result["passed"]
        total_failed += result["failed"]

    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for r in all_results:
            print(f"  {r['name']}: {r['passed']}/{r['passed'] + r['failed']} passed")
        print(f"\n  TOTAL: {total_passed}/{total_passed + total_failed} passed")

    return {
        "results": all_results,
        "summary": {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total": total_passed + total_failed
        }
    }
