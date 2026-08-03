"""Tests for the reproducible anti-hallucination (non-fabrication) evaluation.

These verify OneCite's headline safety property for AI-assisted workflows:
``process`` resolves real strong identifiers but never fabricates a citation
for an ambiguous or non-existent reference. The evaluation runs fully offline,
so the assertions are deterministic.
"""

import argparse
import json

from onecite import cli
from onecite.benchmarks.anti_hallucination import (
    format_anti_hallucination_text,
    load_eval_cases,
    run_anti_hallucination_eval,
)


def test_dataset_loads_and_is_labelled():
    suite = load_eval_cases()
    assert suite["suite"] == "onecite-anti-hallucination"
    classes = {case["class"] for case in suite["cases"]}
    assert classes == {
        "A_strong_identifier",
        "B_ambiguous_text",
        "C_fabricated_identifier",
        "D_mismatched_pairing",
    }
    assert all(case["expect_resolution"] in ("resolved", "unresolved") for case in suite["cases"])


def test_eval_passes_offline_with_perfect_non_fabrication():
    report = run_anti_hallucination_eval()
    assert report["status"] == "passed"
    assert report["source_mode"] == "offline"
    metrics = report["metrics"]
    # Every real identifier resolves ...
    assert metrics["resolution_rate"] == 1.0
    # ... and nothing is fabricated for ambiguous or non-existent references.
    assert metrics["non_fabrication_rate"] == 1.0
    assert metrics["non_fabrication_total"] >= 1


def test_every_case_matches_expectation():
    report = run_anti_hallucination_eval()
    for case in report["cases"]:
        assert case[
            "correct"
        ], f"{case['id']}: expected {case['expected']}, observed {case['observed']}"


def test_fabricated_dois_are_rejected_not_fabricated():
    report = run_anti_hallucination_eval()
    fabricated = [c for c in report["cases"] if c["class"] == "C_fabricated_identifier"]
    assert fabricated
    for case in fabricated:
        assert case["observed"] == "unresolved"


def test_ambiguous_text_is_not_auto_resolved():
    report = run_anti_hallucination_eval()
    ambiguous = [c for c in report["cases"] if c["class"] == "B_ambiguous_text"]
    assert ambiguous
    for case in ambiguous:
        assert case["observed"] == "unresolved"


def test_format_text_includes_metrics():
    text = format_anti_hallucination_text(run_anti_hallucination_eval())
    assert "Resolution rate" in text
    assert "Non-fabrication rate" in text


def test_mismatched_pairing_resolves_with_warning():
    # Class D: a real DOI paired with a different paper's title must resolve
    # from the authoritative DOI *and* carry a text_metadata_mismatch warning
    # — silently clean output would launder a hallucinated pairing.
    report = run_anti_hallucination_eval()
    mismatched = [c for c in report["cases"] if c["class"] == "D_mismatched_pairing"]
    assert mismatched
    for case in mismatched:
        assert case["observed"] == "resolved"
        assert "text_metadata_mismatch" in case["observed_warnings"]
        assert case["correct"]
    assert report["metrics"]["mismatch_detection_rate"] == 1.0


def test_crash_is_not_counted_as_safe_rejection():
    # An evaluation harness that counted crashes as "unresolved" would report
    # a perfect non-fabrication rate for a completely broken pipeline. A
    # crash must be its own outcome and never count as correct.
    def broken_process(**_kwargs):
        raise RuntimeError("pipeline exploded")

    report = run_anti_hallucination_eval(process_fn=broken_process)
    assert report["status"] == "failed"
    assert report["metrics"]["non_fabrication_rate"] == 0.0
    assert report["metrics"]["resolution_rate"] == 0.0
    for case in report["cases"]:
        assert case["observed"] == "error"
        assert case["correct"] is False
        assert "pipeline exploded" in case["error"]


def test_cli_benchmark_anti_hallucination_json(capsys):
    namespace = argparse.Namespace(
        command="benchmark",
        cases=None,
        min_success_rate=None,
        as_json=True,
        live=False,
        anti_hallucination=True,
    )
    code = cli.benchmark_command(namespace)
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["suite"] == "onecite-anti-hallucination"
    assert payload["metrics"]["non_fabrication_rate"] == 1.0


def test_cli_anti_hallucination_rejects_conflicting_options(capsys):
    # Silently ignoring --cases/--min-success-rate would misrepresent what
    # was evaluated; the combination must be refused, not glossed over.
    namespace = argparse.Namespace(
        command="benchmark",
        cases="my_cases.json",
        min_success_rate=0.9,
        as_json=False,
        live=False,
        anti_hallucination=True,
    )
    code = cli.benchmark_command(namespace)
    captured = capsys.readouterr()
    assert code == 1
    assert "--cases and --min-success-rate" in captured.err
    assert "cannot be combined" in captured.err
