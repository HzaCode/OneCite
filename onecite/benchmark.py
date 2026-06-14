#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Benchmark runner for deterministic OneCite golden cases."""

import json
import logging
from contextlib import contextmanager, nullcontext
from importlib import resources
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import patch

from .benchmarks.offline import offline_requests_get
from .core import process_references

BenchmarkProcess = Callable[..., Dict[str, Any]]
_ALLOWED_INPUT_TYPES = {"txt", "bib"}
_ALLOWED_OUTPUT_FORMATS = {"bibtex"}
_ALLOWED_EXPECT_KEYS = {
    "min_total",
    "min_succeeded",
    "min_failed",
    "required_substrings",
}


def load_benchmark_suite(cases_path: Optional[str] = None) -> Dict[str, Any]:
    """Load a benchmark suite from disk or from the bundled golden cases."""
    if cases_path:
        with open(cases_path, "r", encoding="utf-8") as f:
            suite = json.load(f)
    else:
        suite_resource = resources.files("onecite.benchmarks").joinpath("golden_cases.json")
        suite = json.loads(suite_resource.read_text(encoding="utf-8"))

    _validate_suite(suite)
    return suite


def run_benchmark(
    cases_path: Optional[str] = None,
    min_success_rate: float = 1.0,
    live: bool = False,
    process_fn: BenchmarkProcess = process_references,
) -> Dict[str, Any]:
    """Run the benchmark suite and return a JSON-serializable report."""
    if not 0 <= min_success_rate <= 1:
        raise ValueError("min_success_rate must be between 0 and 1.")

    suite = load_benchmark_suite(cases_path)
    with _source_context(live=live), _silence_pipeline_logs():
        case_reports = [_run_case(case=case, process_fn=process_fn) for case in suite["cases"]]
    passed = sum(1 for case_report in case_reports if case_report["status"] == "passed")
    total = len(case_reports)
    raw_success_rate = passed / total if total else 0.0
    success_rate = round(raw_success_rate, 4)
    gate_passed = raw_success_rate >= min_success_rate

    return {
        "schema_version": "1.0",
        "suite": suite["suite"],
        "suite_version": suite["version"],
        "source_mode": "live" if live else "offline",
        "status": "passed" if gate_passed else "failed",
        "summary": {
            "total_cases": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": success_rate,
            "min_success_rate": min_success_rate,
        },
        "cases": case_reports,
    }


def _source_context(live: bool):
    if live:
        return nullcontext()
    return patch.multiple(
        "onecite.pipeline.requests",
        get=offline_requests_get,
    )


@contextmanager
def _silence_pipeline_logs():
    previous_disable_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous_disable_level)


def _validate_suite(suite: Dict[str, Any]) -> None:
    if not isinstance(suite, dict):
        raise ValueError("Benchmark suite must be a JSON object.")

    required_top_level = {"suite", "version", "cases"}
    missing = sorted(required_top_level.difference(suite))
    if missing:
        raise ValueError(f"Benchmark suite missing required keys: {', '.join(missing)}")
    if not isinstance(suite["suite"], str) or not suite["suite"].strip():
        raise ValueError("Benchmark suite 'suite' must be a non-empty string.")
    if not isinstance(suite["version"], str) or not suite["version"].strip():
        raise ValueError("Benchmark suite 'version' must be a non-empty string.")
    if not isinstance(suite["cases"], list) or not suite["cases"]:
        raise ValueError("Benchmark suite must contain at least one case.")

    seen_case_ids = set()
    for index, case in enumerate(suite["cases"]):
        if not isinstance(case, dict):
            raise ValueError(f"Benchmark case {index} must be a JSON object.")

        missing_case_keys = [
            key
            for key in ("id", "input", "input_type", "template", "output_format", "expect")
            if key not in case
        ]
        if missing_case_keys:
            raise ValueError(
                f"Benchmark case {index} missing required keys: {', '.join(missing_case_keys)}"
            )

        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"Benchmark case {index} id must be a non-empty string.")
        if case_id in seen_case_ids:
            raise ValueError(f"Benchmark case id must be unique: {case_id}")
        seen_case_ids.add(case_id)

        if not isinstance(case["input"], str) or not case["input"].strip():
            raise ValueError(f"Benchmark case {case_id} input must be a non-empty string.")
        if case["input_type"] not in _ALLOWED_INPUT_TYPES:
            allowed = ", ".join(sorted(_ALLOWED_INPUT_TYPES))
            raise ValueError(
                f"Benchmark case {case_id} has invalid input_type; expected {allowed}."
            )
        if not isinstance(case["template"], str) or not case["template"].strip():
            raise ValueError(f"Benchmark case {case_id} template must be a non-empty string.")
        if case["output_format"] not in _ALLOWED_OUTPUT_FORMATS:
            allowed = ", ".join(sorted(_ALLOWED_OUTPUT_FORMATS))
            raise ValueError(
                f"Benchmark case {case_id} has invalid output_format; expected {allowed}."
            )
        _validate_expectation(case_id, case["expect"])


def _validate_expectation(case_id: str, expect: Dict[str, Any]) -> None:
    if not isinstance(expect, dict):
        raise ValueError(f"Benchmark case {case_id} expect must be a JSON object.")

    unknown = sorted(set(expect).difference(_ALLOWED_EXPECT_KEYS))
    if unknown:
        raise ValueError(
            f"Benchmark case {case_id} has unsupported expectation keys: {', '.join(unknown)}"
        )

    for key in ("min_total", "min_succeeded", "min_failed"):
        value = expect.get(key, 0)
        if not _is_non_negative_int(value):
            raise ValueError(
                f"Benchmark case {case_id} expectation {key} must be a non-negative integer."
            )

    min_total = expect.get("min_total", 1)
    min_succeeded = expect.get("min_succeeded", min_total)
    min_failed = expect.get("min_failed", 0)
    if min_succeeded > min_total:
        raise ValueError(
            f"Benchmark case {case_id} expectation min_succeeded cannot exceed min_total."
        )
    if min_failed > min_total:
        raise ValueError(
            f"Benchmark case {case_id} expectation min_failed cannot exceed min_total."
        )

    required_substrings = expect.get("required_substrings", [])
    if not isinstance(required_substrings, list) or not all(
        isinstance(item, str) and item for item in required_substrings
    ):
        raise ValueError(
            f"Benchmark case {case_id} expectation required_substrings must be a list "
            "of non-empty strings."
        )


def _is_non_negative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _run_case(case: Dict[str, Any], process_fn: BenchmarkProcess) -> Dict[str, Any]:
    failures: List[str] = []
    try:
        result = process_fn(
            input_content=case["input"],
            input_type=case["input_type"],
            template_name=case["template"],
            output_format=case["output_format"],
            interactive_callback=lambda _candidates: -1,
        )
        output = "\n\n".join(result.get("results", []))
        _check_report_expectations(case, result.get("report", {}), failures)
        _check_required_substrings(case, output, failures)
        return {
            "id": case["id"],
            "description": case.get("description", ""),
            "status": "passed" if not failures else "failed",
            "failures": failures,
            "observed": {
                "total": int(result.get("report", {}).get("total", 0)),
                "succeeded": int(result.get("report", {}).get("succeeded", 0)),
                "failed": len(result.get("report", {}).get("failed_entries", [])),
            },
        }
    except Exception as exc:
        return {
            "id": case["id"],
            "description": case.get("description", ""),
            "status": "failed",
            "failures": [str(exc)],
            "observed": {"total": 0, "succeeded": 0, "failed": 0},
        }


def _check_report_expectations(
    case: Dict[str, Any],
    report: Dict[str, Any],
    failures: List[str],
) -> None:
    expect = case["expect"]
    total = int(report.get("total", 0))
    succeeded = int(report.get("succeeded", 0))
    failed = len(report.get("failed_entries", []))

    min_total = int(expect.get("min_total", 1))
    if total < min_total:
        failures.append(f"Expected at least {min_total} total entries, observed {total}.")

    min_succeeded = int(expect.get("min_succeeded", min_total))
    if succeeded < min_succeeded:
        failures.append(f"Expected at least {min_succeeded} successes, observed {succeeded}.")

    min_failed = int(expect.get("min_failed", 0))
    if failed < min_failed:
        failures.append(f"Expected at least {min_failed} failed entries, observed {failed}.")


def _check_required_substrings(
    case: Dict[str, Any],
    output: str,
    failures: List[str],
) -> None:
    for required in case["expect"].get("required_substrings", []):
        if required not in output:
            failures.append(f"Missing required output substring: {required!r}.")


def format_benchmark_text(report: Dict[str, Any]) -> str:
    """Format a compact human-readable benchmark report."""
    summary = report["summary"]
    lines = [
        f"Benchmark suite: {report['suite']} {report['suite_version']}",
        f"Status: {report['status']}",
        (
            "Cases: "
            f"{summary['passed']}/{summary['total_cases']} passed "
            f"(success rate {summary['success_rate']:.2%}, gate {summary['min_success_rate']:.2%})"
        ),
    ]
    for case in report["cases"]:
        lines.append(f"- {case['id']}: {case['status']}")
        for failure in case["failures"]:
            lines.append(f"  - {failure}")
    return "\n".join(lines)


__all__ = [
    "format_benchmark_text",
    "load_benchmark_suite",
    "run_benchmark",
]
