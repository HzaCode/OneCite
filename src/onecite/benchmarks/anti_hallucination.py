#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Reproducible anti-hallucination (non-fabrication) evaluation for OneCite.

This small regression evaluation exercises OneCite's covered safety contract:
``onecite process`` emits a source-resolved citation when a fixture-backed
strong identifier resolves, and does not emit an entry for the bundled
ambiguous or non-existent inputs.

The bundled dataset (``anti_hallucination_cases.json``) is labelled into four
classes:

* ``A_strong_identifier`` — a real DOI / PMID / arXiv id / repository URL;
  expected RESOLVED into a source-resolved entry.
* ``B_ambiguous_text`` — a plain-text title or snippet; expected UNRESOLVED.
  Such inputs are the domain of ``onecite suggest``, which returns ranked
  candidates for human review rather than source-resolved output.
* ``C_fabricated_identifier`` — a syntactically valid but non-existent DOI of
  the kind a language model may hallucinate; expected UNRESOLVED (rejected).
* ``D_mismatched_pairing`` — a real DOI paired with a *different* work's
  title (the most common hallucinated-citation shape); expected RESOLVED
  from the supplied DOI **with** a ``text_metadata_mismatch`` warning,
  not silently emitted as clean source-resolved output.

It runs fully offline against the bundled deterministic fixtures, so the
reported metrics are reproducible without network access.
"""

import json
import logging
from contextlib import contextmanager, nullcontext
from importlib import resources
from typing import Any, Callable, Dict
from unittest.mock import patch

from .offline import offline_requests_get
from ..core import process_references

EvalProcess = Callable[..., Dict[str, Any]]

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
ERROR = "error"
_VALID_CLASSES = {
    "A_strong_identifier",
    "B_ambiguous_text",
    "C_fabricated_identifier",
    "D_mismatched_pairing",
}


def load_eval_cases() -> Dict[str, Any]:
    """Load and validate the bundled anti-hallucination evaluation dataset."""
    resource = resources.files("onecite.benchmarks").joinpath("anti_hallucination_cases.json")
    suite = json.loads(resource.read_text(encoding="utf-8"))
    _validate(suite)
    return dict(suite)


def run_anti_hallucination_eval(
    process_fn: EvalProcess = process_references,
    live: bool = False,
) -> Dict[str, Any]:
    """Run the anti-hallucination evaluation and return a JSON-serializable report.

    The headline metric is ``non_fabrication_rate``: the fraction of ambiguous
    (class B) and fabricated (class C) inputs that OneCite correctly left
    unresolved instead of emitting a necessarily-wrong source-resolved
    citation. A value of ``1.0`` means no covered B/C fixture emitted a result;
    it is not a population estimate.

    Args:
        process_fn: The processing entry point to evaluate (defaults to the
            public :func:`onecite.process_references`).
        live: When ``True``, hit live external APIs instead of the bundled
            offline fixtures. Defaults to ``False`` for deterministic results.

    Returns:
        A report dict with ``metrics`` (resolution_rate, non_fabrication_rate,
        mismatch_detection_rate, and counts), a per-case breakdown, and an
        overall ``status``.
    """
    suite = load_eval_cases()
    with _source_context(live=live), _silence_pipeline_logs():
        case_reports = [_run_one(case, process_fn) for case in suite["cases"]]

    resolution = [c for c in case_reports if c["class"] == "A_strong_identifier"]
    non_fabrication = [
        c for c in case_reports if c["class"] in ("B_ambiguous_text", "C_fabricated_identifier")
    ]
    mismatch = [c for c in case_reports if c["class"] == "D_mismatched_pairing"]

    resolved_correct = sum(1 for c in resolution if c["correct"])
    non_fabrication_correct = sum(1 for c in non_fabrication if c["correct"])
    mismatch_correct = sum(1 for c in mismatch if c["correct"])

    resolution_rate = round(resolved_correct / len(resolution), 4) if resolution else 0.0
    non_fabrication_rate = (
        round(non_fabrication_correct / len(non_fabrication), 4) if non_fabrication else 0.0
    )
    mismatch_detection_rate = round(mismatch_correct / len(mismatch), 4) if mismatch else 0.0
    gate_passed = all(c["correct"] for c in case_reports)

    return {
        "schema_version": "1.1",
        "suite": suite["suite"],
        "suite_version": suite["version"],
        "source_mode": "live" if live else "offline",
        "status": "passed" if gate_passed else "failed",
        "metrics": {
            "resolution_rate": resolution_rate,
            "non_fabrication_rate": non_fabrication_rate,
            "mismatch_detection_rate": mismatch_detection_rate,
            "resolved_correct": resolved_correct,
            "resolution_total": len(resolution),
            "non_fabrication_correct": non_fabrication_correct,
            "non_fabrication_total": len(non_fabrication),
            "mismatch_correct": mismatch_correct,
            "mismatch_total": len(mismatch),
        },
        "cases": case_reports,
    }


def _run_one(case: Dict[str, Any], process_fn: EvalProcess) -> Dict[str, Any]:
    error = None
    observed_warnings: list = []
    try:
        result = process_fn(
            input_content=case["input"],
            input_type=case.get("input_type", "txt"),
            template_name="journal_article_full",
            output_format="bibtex",
        )
        report = result.get("report", {})
        succeeded = int(report.get("succeeded", 0))
        observed = RESOLVED if succeeded >= 1 else UNRESOLVED
        observed_warnings = sorted(
            {w.get("type", "") for w in report.get("warnings", []) if w.get("type")}
        )
    except Exception as exc:
        # A crash produces no citation, but it is not a clean rejection:
        # counting it as "unresolved" would let an infrastructure bug
        # inflate the non-fabrication rate. Errors are their own outcome
        # and never count as correct.
        observed = ERROR
        error = str(exc)

    expected = case["expect_resolution"]
    expected_warning = case.get("expect_warning")
    correct = observed == expected
    if correct and expected_warning:
        correct = expected_warning in observed_warnings

    return {
        "id": case["id"],
        "class": case["class"],
        "input": case["input"],
        "expected": expected,
        "observed": observed,
        "expected_warning": expected_warning,
        "observed_warnings": observed_warnings,
        "correct": correct,
        "note": case.get("note", ""),
        "error": error,
    }


def _source_context(live: bool):
    if live:
        return nullcontext()
    return patch.multiple("onecite.pipeline.requests", get=offline_requests_get)


@contextmanager
def _silence_pipeline_logs():
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(previous)


def _validate(suite: Dict[str, Any]) -> None:
    if not isinstance(suite, dict) or "cases" not in suite:
        raise ValueError("Anti-hallucination suite must be a JSON object with 'cases'.")
    for key in ("suite", "version"):
        if not isinstance(suite.get(key), str) or not suite[key].strip():
            raise ValueError(f"Anti-hallucination suite '{key}' must be a non-empty string.")
    if not isinstance(suite["cases"], list) or not suite["cases"]:
        raise ValueError("Anti-hallucination suite must contain at least one case.")

    seen = set()
    for index, case in enumerate(suite["cases"]):
        for key in ("id", "class", "input", "expect_resolution"):
            if key not in case:
                raise ValueError(f"Anti-hallucination case {index} missing required key: {key}")
        if case["id"] in seen:
            raise ValueError(f"Duplicate anti-hallucination case id: {case['id']}")
        seen.add(case["id"])
        if case["class"] not in _VALID_CLASSES:
            raise ValueError(f"Case {case['id']} has invalid class: {case['class']}")
        if case["expect_resolution"] not in (RESOLVED, UNRESOLVED):
            raise ValueError(
                f"Case {case['id']} expect_resolution must be '{RESOLVED}' or '{UNRESOLVED}'."
            )


def format_anti_hallucination_text(report: Dict[str, Any]) -> str:
    """Format a compact human-readable anti-hallucination report."""
    metrics = report["metrics"]
    lines = [
        f"Anti-hallucination eval: {report['suite']} {report['suite_version']}",
        f"Status: {report['status']} (source: {report['source_mode']})",
        (
            "Resolution rate (class A):        "
            f"{metrics['resolution_rate']:.2%} "
            f"({metrics['resolved_correct']}/{metrics['resolution_total']})"
        ),
        (
            "Non-fabrication rate (class B+C): "
            f"{metrics['non_fabrication_rate']:.2%} "
            f"({metrics['non_fabrication_correct']}/{metrics['non_fabrication_total']})"
        ),
    ]
    if metrics.get("mismatch_total"):
        lines.append(
            "Mismatch detection (class D):     "
            f"{metrics['mismatch_detection_rate']:.2%} "
            f"({metrics['mismatch_correct']}/{metrics['mismatch_total']})"
        )
    for case in report["cases"]:
        mark = "ok " if case["correct"] else "MISS"
        line = (
            f"- [{mark}] {case['id']} ({case['class']}): "
            f"expected {case['expected']}, observed {case['observed']}"
        )
        if case.get("expected_warning"):
            observed = ", ".join(case.get("observed_warnings") or []) or "none"
            line += f"; expected warning {case['expected_warning']}, observed {observed}"
        lines.append(line)
    return "\n".join(lines)


__all__ = [
    "load_eval_cases",
    "run_anti_hallucination_eval",
    "format_anti_hallucination_text",
]
