#!/usr/bin/env python3
"""
Evals Runner - Test the NL→SQL pipeline.

Evals:
1. Schema Correctness: Generated SQL uses only valid table/columns
2. Intent Checks: SQL contains expected patterns for given queries
3. Determinism: Same query produces valid SQL across multiple samples

Usage:
    python run.py                    # Run all evals
    python run.py --eval schema      # Run specific eval
    python run.py --eval intent
    python run.py --eval determinism
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from llm import generate_sql
from validator import validate_sql


def load_cases() -> dict:
    """Load eval cases from JSON."""
    cases_path = Path(__file__).parent / "cases.json"
    with open(cases_path) as f:
        return json.load(f)


def run_schema_correctness(cases: list[dict]) -> dict:
    """
    Eval 1: Schema Correctness
    Generated SQL should reference only valid table + columns.
    """
    print("\n" + "=" * 60)
    print("EVAL 1: Schema Correctness")
    print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for case in cases:
        print(f"\n[{case['id']}] {case['query']}")

        # Generate SQL
        gen_result = generate_sql(case["query"])
        if not gen_result["success"]:
            print(f"  FAIL: Generation failed - {gen_result['error']}")
            results.append({"id": case["id"], "passed": False, "error": gen_result["error"]})
            failed += 1
            continue

        sql = gen_result["sql"]
        print(f"  SQL: {sql}")

        # Validate
        is_valid, errors = validate_sql(sql)
        if is_valid:
            print("  PASS")
            results.append({"id": case["id"], "passed": True, "sql": sql})
            passed += 1
        else:
            print(f"  FAIL: {errors}")
            results.append({"id": case["id"], "passed": False, "sql": sql, "errors": errors})
            failed += 1

    print(f"\n--- Schema Correctness: {passed}/{len(cases)} passed ---")
    return {"name": "schema_correctness", "passed": passed, "failed": failed, "results": results}


def run_intent_checks(cases: list[dict]) -> dict:
    """
    Eval 2: Intent/Shape Checks
    SQL should contain expected structural patterns.
    """
    print("\n" + "=" * 60)
    print("EVAL 2: Intent Checks")
    print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for case in cases:
        print(f"\n[{case['id']}] {case['query']}")
        print(f"  Expected: {case['expected_patterns']}")

        # Generate SQL
        gen_result = generate_sql(case["query"])
        if not gen_result["success"]:
            print(f"  FAIL: Generation failed - {gen_result['error']}")
            results.append({"id": case["id"], "passed": False, "error": gen_result["error"]})
            failed += 1
            continue

        sql = gen_result["sql"].upper()
        print(f"  SQL: {gen_result['sql']}")

        # Check patterns
        missing = []
        for pattern in case["expected_patterns"]:
            if pattern.upper() not in sql:
                missing.append(pattern)

        if not missing:
            print("  PASS")
            results.append({"id": case["id"], "passed": True, "sql": gen_result["sql"]})
            passed += 1
        else:
            print(f"  FAIL: Missing patterns: {missing}")
            results.append({"id": case["id"], "passed": False, "sql": gen_result["sql"], "missing": missing})
            failed += 1

    print(f"\n--- Intent Checks: {passed}/{len(cases)} passed ---")
    return {"name": "intent_checks", "passed": passed, "failed": failed, "results": results}


def run_determinism(cases: list[dict]) -> dict:
    """
    Eval 3: Determinism/Stability
    Same query should produce valid SQL across multiple samples.
    """
    print("\n" + "=" * 60)
    print("EVAL 3: Determinism")
    print("=" * 60)

    results = []
    passed = 0
    failed = 0

    for case in cases:
        samples = case.get("samples", 5)
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
                    print(f"  Sample {i+1}: VALID")
                else:
                    print(f"  Sample {i+1}: INVALID")
            else:
                print(f"  Sample {i+1}: GENERATION FAILED")
                sqls.append(None)

        validity_rate = valid_count / samples
        case_passed = validity_rate >= 0.8  # 80% threshold

        if case_passed:
            print(f"  PASS ({valid_count}/{samples} = {validity_rate:.0%})")
            passed += 1
        else:
            print(f"  FAIL ({valid_count}/{samples} = {validity_rate:.0%})")
            failed += 1

        results.append({
            "id": case["id"],
            "passed": case_passed,
            "valid_count": valid_count,
            "total": samples,
            "validity_rate": validity_rate,
            "sqls": sqls
        })

    print(f"\n--- Determinism: {passed}/{len(cases)} passed ---")
    return {"name": "determinism", "passed": passed, "failed": failed, "results": results}


def main():
    parser = argparse.ArgumentParser(description="Run NL→SQL evals")
    parser.add_argument("--eval", choices=["schema", "intent", "determinism", "all"], default="all")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()

    cases = load_cases()
    all_results = []
    total_passed = 0
    total_failed = 0

    if args.eval in ["schema", "all"]:
        result = run_schema_correctness(cases["schema_correctness"])
        all_results.append(result)
        total_passed += result["passed"]
        total_failed += result["failed"]

    if args.eval in ["intent", "all"]:
        result = run_intent_checks(cases["intent_checks"])
        all_results.append(result)
        total_passed += result["passed"]
        total_failed += result["failed"]

    if args.eval in ["determinism", "all"]:
        result = run_determinism(cases["determinism"])
        all_results.append(result)
        total_passed += result["passed"]
        total_failed += result["failed"]

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in all_results:
        print(f"  {r['name']}: {r['passed']}/{r['passed'] + r['failed']} passed")
    print(f"\n  TOTAL: {total_passed}/{total_passed + total_failed} passed")

    # Save results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    # Exit code
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
