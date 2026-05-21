import json

import pytest

from onecite.benchmark import format_benchmark_text, load_benchmark_suite, run_benchmark


def _valid_case(**overrides):
    case = {
        "id": "case-1",
        "description": "valid case",
        "input": "10.1038/nature14236",
        "input_type": "txt",
        "template": "journal_article_full",
        "output_format": "bibtex",
        "expect": {"min_total": 1, "min_succeeded": 1},
    }
    case.update(overrides)
    return case


def _write_suite(tmp_path, *cases):
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(
        json.dumps({"suite": "local-suite", "version": "1.0", "cases": list(cases)}),
        encoding="utf-8",
    )
    return suite_path


def test_load_bundled_benchmark_suite():
    suite = load_benchmark_suite()

    assert suite["suite"] == "onecite-golden"
    assert suite["version"]
    assert len(suite["cases"]) >= 7
    assert {case["id"] for case in suite["cases"]} >= {
        "doi_crossref_nature_dqn",
        "arxiv_transformer_identifier",
        "mixed_batch_valid_and_invalid",
    }


def test_load_benchmark_suite_rejects_missing_required_keys(tmp_path):
    suite_path = tmp_path / "bad-suite.json"
    suite_path.write_text(json.dumps({"suite": "bad", "cases": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required keys"):
        load_benchmark_suite(str(suite_path))


def test_load_benchmark_suite_rejects_duplicate_case_ids(tmp_path):
    suite_path = _write_suite(tmp_path, _valid_case(id="dup"), _valid_case(id="dup"))

    with pytest.raises(ValueError, match="must be unique"):
        load_benchmark_suite(str(suite_path))


def test_load_benchmark_suite_rejects_invalid_expectation_key(tmp_path):
    suite_path = _write_suite(
        tmp_path,
        _valid_case(expect={"min_total": 1, "unsupported": True}),
    )

    with pytest.raises(ValueError, match="unsupported expectation keys"):
        load_benchmark_suite(str(suite_path))


def test_run_benchmark_json_report_contract(tmp_path):
    suite_path = _write_suite(
        tmp_path,
        _valid_case(
            id="contract",
            expect={
                "min_total": 1,
                "min_succeeded": 1,
                "required_substrings": ["Contract Title"],
            },
        ),
    )

    def fake_process_fn(**_kwargs):
        return {
            "results": ["@article{Contract, title={Contract Title}}"],
            "report": {"total": 1, "succeeded": 1, "failed_entries": []},
        }

    report = run_benchmark(cases_path=str(suite_path), process_fn=fake_process_fn)

    assert set(report) == {
        "schema_version",
        "suite",
        "suite_version",
        "source_mode",
        "status",
        "summary",
        "cases",
    }
    assert set(report["summary"]) == {
        "total_cases",
        "passed",
        "failed",
        "success_rate",
        "min_success_rate",
    }
    assert set(report["cases"][0]) == {
        "id",
        "description",
        "status",
        "failures",
        "observed",
    }
    assert set(report["cases"][0]["observed"]) == {"total", "succeeded", "failed"}


def test_run_benchmark_gate_uses_unrounded_success_ratio(tmp_path):
    suite_path = _write_suite(
        tmp_path,
        _valid_case(id="pass-1", input="pass one", expect={"min_total": 1}),
        _valid_case(id="pass-2", input="pass two", expect={"min_total": 1}),
        _valid_case(
            id="fail-3",
            input="fail three",
            expect={"min_total": 1, "required_substrings": ["missing sentinel"]},
        ),
    )

    def fake_process_fn(**_kwargs):
        return {
            "results": ["@article{Observed, title={Observed Title}}"],
            "report": {"total": 1, "succeeded": 1, "failed_entries": []},
        }

    report = run_benchmark(
        cases_path=str(suite_path),
        min_success_rate=0.6667,
        process_fn=fake_process_fn,
    )

    assert report["summary"]["passed"] == 2
    assert report["summary"]["total_cases"] == 3
    assert report["summary"]["success_rate"] == 0.6667
    assert report["status"] == "failed"


def test_run_benchmark_uses_noninteractive_candidate_policy(tmp_path):
    suite_path = _write_suite(tmp_path, _valid_case(id="candidate-policy"))
    observed_choices = []

    def fake_process_fn(*, interactive_callback, **_kwargs):
        observed_choices.append(interactive_callback([{"title": "Candidate"}]))
        return {
            "results": ["@article{Candidate}"],
            "report": {"total": 1, "succeeded": 1, "failed_entries": []},
        }

    report = run_benchmark(cases_path=str(suite_path), process_fn=fake_process_fn)

    assert report["status"] == "passed"
    assert observed_choices == [-1]


def test_run_bundled_benchmark_with_mocked_sources():
    report = run_benchmark()

    assert report["status"] == "passed"
    assert report["summary"]["passed"] == report["summary"]["total_cases"]
    assert report["source_mode"] == "offline"


def test_run_bundled_benchmark_offline_overrides_live_network_get(monkeypatch):
    import onecite.pipeline as pipeline

    def fail_if_live_network_is_used(*_args, **_kwargs):
        raise AssertionError("live network was used during offline benchmark")

    monkeypatch.setattr(pipeline.requests, "get", fail_if_live_network_is_used)

    report = run_benchmark()

    assert report["status"] == "passed"
    assert report["source_mode"] == "offline"


def test_run_benchmark_requires_expected_failed_entries(tmp_path):
    suite_path = _write_suite(
        tmp_path,
        _valid_case(id="mixed", expect={"min_total": 2, "min_succeeded": 1, "min_failed": 1}),
    )

    def fake_process_fn(**_kwargs):
        return {
            "results": ["@article{Observed}"],
            "report": {"total": 2, "succeeded": 1, "failed_entries": []},
        }

    report = run_benchmark(cases_path=str(suite_path), process_fn=fake_process_fn)

    assert report["status"] == "failed"
    assert "Expected at least 1 failed entries" in report["cases"][0]["failures"][0]


def test_format_benchmark_text_includes_failures():
    report = {
        "suite": "local",
        "suite_version": "1.0",
        "status": "failed",
        "summary": {"passed": 0, "total_cases": 1, "success_rate": 0.0, "min_success_rate": 1.0},
        "cases": [{"id": "case-1", "status": "failed", "failures": ["missing title"]}],
    }

    text = format_benchmark_text(report)

    assert "Benchmark suite: local 1.0" in text
    assert "case-1: failed" in text
    assert "missing title" in text
