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
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from evals_runner import run_evals


def main():
    if load_dotenv:
        load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

    parser = argparse.ArgumentParser(description="Run NL→SQL evals")
    parser.add_argument("--eval", choices=["schema", "intent", "determinism", "all"], default="all")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()

    payload = run_evals(eval_name=args.eval, verbose=True)
    all_results = payload["results"]
    total_failed = payload["summary"]["total_failed"]

    # Save results
    if args.output:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    # Exit code
    sys.exit(0 if total_failed == 0 else 1)


if __name__ == "__main__":
    main()
