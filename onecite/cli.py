#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command-line interface for OneCite.
"""

import argparse
import json
import os
import platform
import sys
from contextlib import nullcontext
from importlib import resources
from pathlib import Path
from typing import Any, List, Dict
from unittest.mock import patch

from .benchmark import format_benchmark_text, load_benchmark_suite, run_benchmark
from .benchmarks.offline import offline_requests_get
from .core import process_references, suggest_references, TemplateLoader
from .exceptions import OneCiteError
from . import __version__


def main() -> int:
    """CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.command == "process":
            return process_command(args)
        elif args.command in ("suggest", "sugget"):
            return suggest_command(args)
        elif args.command == "benchmark":
            return benchmark_command(args)
        elif args.command == "doctor":
            return doctor_command(args)
        elif args.command == "templates":
            return templates_command(args)
        elif args.command == "version":
            print(f"OneCite version {__version__}")
            return 0
        else:
            parser.print_help()
            return 1

    except OneCiteError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Processing failed: {e}", file=sys.stderr)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="onecite",
        description="Citation management and academic reference toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  onecite process references.txt --output-format bibtex
  onecite process references.bib --input-type bib --template conference_paper
  onecite process references.txt --output results.bib
  onecite process "10.1038/nature14539"
  onecite process "attention is all you need, Vaswani et al., NIPS 2017"
  onecite suggest "attention is all you need, Vaswani et al., NIPS 2017" --json
  onecite benchmark --json
  onecite doctor --json
  onecite templates
  echo "10.1038/nature14539" | onecite process -
        """,
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("version", help="Display the installed OneCite version")

    # Main processing command
    process_parser = subparsers.add_parser(
        "process", help="Process references through the OneCite pipeline"
    )
    process_parser.add_argument(
        "input_file", help='Input file, "-" for stdin, or a reference string (e.g. a DOI or title)'
    )
    process_parser.add_argument(
        "--input-type", choices=["txt", "bib"], default="txt", help="Input type (default: txt)"
    )
    process_parser.add_argument(
        "--template",
        default="journal_article_full",
        help=(
            "Fallback BibTeX entry-type preset when auto-detection is "
            "inconclusive (default: journal_article_full)"
        ),
    )
    process_parser.add_argument(
        "--output-format",
        choices=["bibtex"],
        default="bibtex",
        help="Output format (default: bibtex)",
    )
    process_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    process_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress verbose logging output"
    )
    output_mode_group = process_parser.add_mutually_exclusive_group()
    output_mode_group.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print a stable machine-readable JSON envelope instead of BibTeX text",
    )
    output_mode_group.add_argument(
        "--ndjson",
        action="store_true",
        dest="as_ndjson",
        help="Print newline-delimited JSON events for streaming automation workflows",
    )
    process_parser.add_argument(
        "--fail-on-unresolved",
        action="store_true",
        help="Return exit code 2 when one or more entries could not be resolved",
    )

    suggest_parser = subparsers.add_parser(
        "suggest",
        aliases=["sugget"],
        help="Suggest candidate matches without resolving them to BibTeX",
    )
    suggest_parser.add_argument(
        "input_file", help='Input file, "-" for stdin, or a reference string to search'
    )
    suggest_parser.add_argument(
        "--input-type", choices=["txt", "bib"], default="txt", help="Input type (default: txt)"
    )
    suggest_parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum candidates per entry (default: 5)",
    )
    suggest_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    suggest_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress saved-file status output"
    )
    suggest_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print a stable machine-readable JSON envelope",
    )
    suggest_parser.add_argument(
        "--google-scholar",
        action="store_true",
        default=False,
        help="Enable Google Scholar as an additional suggestion source",
    )

    benchmark_parser = subparsers.add_parser(
        "benchmark", help="Run deterministic golden-case benchmarks"
    )
    benchmark_parser.add_argument(
        "--cases", help="Path to a benchmark suite JSON file (default: bundled golden cases)"
    )
    benchmark_parser.add_argument(
        "--min-success-rate",
        type=float,
        default=1.0,
        help="Minimum case pass rate required for a successful exit (default: 1.0)",
    )
    benchmark_parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Print the benchmark report as JSON"
    )
    benchmark_parser.add_argument(
        "--live",
        action="store_true",
        help="Use live external APIs instead of bundled offline fixtures",
    )

    doctor_parser = subparsers.add_parser(
        "doctor", help="Check local OneCite installation health for automation and CI"
    )
    doctor_parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Print the doctor report as JSON"
    )

    templates_parser = subparsers.add_parser(
        "templates", help="List bundled fallback BibTeX templates"
    )
    templates_parser.add_argument(
        "--json", action="store_true", dest="as_json", help="Print template metadata as JSON"
    )

    return parser


def _read_input_content(args: "argparse.Namespace") -> str:
    """Read CLI input from stdin, a file, or an inline reference string."""
    if args.input_file == "-":
        return sys.stdin.read()
    if os.path.exists(args.input_file):
        with open(args.input_file, "r", encoding="utf-8") as f:
            input_content = f.read()
        if args.input_type == "txt" and args.input_file.lower().endswith(".bib"):
            args.input_type = "bib"
        return input_content
    return args.input_file


def _build_process_report(args: "argparse.Namespace", result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the stable process report used by JSON and NDJSON modes."""
    report = result.get("report", {})
    failed_entries = list(report.get("failed_entries", []))
    total = int(report.get("total", 0))
    succeeded = int(report.get("succeeded", 0))
    failed = len(failed_entries)
    success_rate = round(succeeded / total, 4) if total else 0.0

    return {
        "schema_version": "1.0",
        "tool": "onecite",
        "command": "process",
        "status": "passed" if failed == 0 else "failed",
        "summary": {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "success_rate": success_rate,
        },
        "options": {
            "input_type": args.input_type,
            "template": args.template,
            "output_format": args.output_format,
            "fail_on_unresolved": bool(args.fail_on_unresolved),
        },
        "failed_entries": failed_entries,
        "results": list(result.get("results", [])),
    }


def _build_process_error_report(args: "argparse.Namespace", error: Exception) -> Dict[str, Any]:
    """Build a machine-readable process report for catastrophic failures."""
    return {
        "schema_version": "1.0",
        "tool": "onecite",
        "command": "process",
        "status": "failed",
        "summary": {
            "total": 1,
            "succeeded": 0,
            "failed": 1,
            "success_rate": 0.0,
        },
        "options": {
            "input_type": args.input_type,
            "template": args.template,
            "output_format": args.output_format,
            "fail_on_unresolved": bool(args.fail_on_unresolved),
        },
        "failed_entries": [{"id": None, "error": str(error)}],
        "results": [],
    }


def _build_suggest_report(args: "argparse.Namespace", result: Dict[str, Any]) -> Dict[str, Any]:
    """Build the stable suggest report used by JSON mode."""
    report = result.get("report", {})
    return {
        "schema_version": "1.0",
        "tool": "onecite",
        "command": "suggest",
        "status": "completed",
        "summary": {
            "total": int(report.get("total", 0)),
            "with_candidates": int(report.get("with_candidates", 0)),
            "without_candidates": int(report.get("without_candidates", 0)),
        },
        "options": {
            "input_type": args.input_type,
            "limit": int(args.limit),
            "google_scholar": bool(args.google_scholar),
        },
        "suggestions": list(result.get("suggestions", [])),
    }


def _build_suggest_error_report(args: "argparse.Namespace", error: Exception) -> Dict[str, Any]:
    """Build a machine-readable suggest report for hard failures."""
    return {
        "schema_version": "1.0",
        "tool": "onecite",
        "command": "suggest",
        "status": "failed",
        "summary": {
            "total": 1,
            "with_candidates": 0,
            "without_candidates": 1,
        },
        "options": {
            "input_type": args.input_type,
            "limit": int(args.limit),
            "google_scholar": bool(args.google_scholar),
        },
        "suggestions": [
            {
                "id": None,
                "raw_text": "",
                "query_string": "",
                "status": "error",
                "error": str(error),
                "candidates": [],
            }
        ],
    }


def _format_suggest_text(report: Dict[str, Any]) -> str:
    """Format a suggest report for humans."""
    lines = []
    for suggestion in report["suggestions"]:
        heading = suggestion.get("query_string") or suggestion.get("raw_text") or "<empty>"
        lines.append(f"Entry {suggestion.get('id')}: {heading}")
        candidates = suggestion.get("candidates", [])
        if not candidates:
            lines.append("  No candidates found.")
            continue
        for index, candidate in enumerate(candidates, start=1):
            score = candidate.get("match_score", "n/a")
            source = candidate.get("source", "unknown")
            title = candidate.get("title", "Untitled")
            identifier = (
                candidate.get("doi") or candidate.get("arxiv_id") or candidate.get("url") or ""
            )
            suffix = f" [{identifier}]" if identifier else ""
            lines.append(f"  {index}. {title}{suffix}")
            lines.append(f"     source={source} score={score}")
    return "\n".join(lines)


def _format_process_ndjson(report: Dict[str, Any]) -> str:
    """Format a process report as newline-delimited JSON events."""
    events = [
        {
            "type": "summary",
            "schema_version": report["schema_version"],
            "tool": report["tool"],
            "command": report["command"],
            "status": report["status"],
            "summary": report["summary"],
            "options": report["options"],
        }
    ]
    events.extend(
        {"type": "result", "index": index, "content": content}
        for index, content in enumerate(report["results"])
    )
    events.extend(
        {"type": "failure", "entry": failed_entry} for failed_entry in report["failed_entries"]
    )
    return "\n".join(json.dumps(event) for event in events)


def _offline_source_context():
    """Use bundled source fixtures when subprocess tests request offline mode."""
    if os.environ.get("ONECITE_OFFLINE_FIXTURES") != "1":
        return nullcontext()
    return patch.multiple("onecite.pipeline.requests", get=offline_requests_get)


def benchmark_command(args: "argparse.Namespace") -> int:
    """Run the ``onecite benchmark`` subcommand."""
    report = run_benchmark(
        cases_path=args.cases,
        min_success_rate=args.min_success_rate,
        live=args.live,
    )
    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        print(format_benchmark_text(report))
    return 0 if report["status"] == "passed" else 1


def doctor_command(args: "argparse.Namespace") -> int:
    """Run installation and quality-gate health checks."""
    report = _build_doctor_report()
    if args.as_json:
        print(json.dumps(report, indent=2))
    else:
        print(_format_doctor_text(report))
    return 0 if report["status"] == "passed" else 1


def _build_doctor_report() -> Dict[str, Any]:
    checks = [
        _check_package_version(),
        _check_templates(),
        _check_benchmark_resources(),
        _check_skill_package(),
        _check_offline_benchmark_gate(),
    ]
    passed = sum(1 for check in checks if check["status"] == "passed")
    total = len(checks)
    return {
        "schema_version": "1.0",
        "tool": "onecite",
        "command": "doctor",
        "status": "passed" if passed == total else "failed",
        "environment": {
            "python": platform.python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
            "package_version": __version__,
        },
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
        "checks": checks,
    }


def _doctor_check(
    name: str,
    passed: bool,
    message: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "status": "passed" if passed else "failed",
        "message": message,
        "details": details or {},
    }


def _check_package_version() -> Dict[str, Any]:
    return _doctor_check(
        "package_version",
        bool(__version__),
        f"OneCite {__version__} is importable.",
        {"version": __version__},
    )


def _check_templates() -> Dict[str, Any]:
    try:
        templates = TemplateLoader().list_templates()
    except Exception as exc:
        return _doctor_check("templates", False, f"Template discovery failed: {exc}")
    names = [template["name"] for template in templates]
    return _doctor_check(
        "templates",
        bool(names),
        f"Discovered {len(names)} bundled templates.",
        {"count": len(names), "templates": names},
    )


def _check_benchmark_resources() -> Dict[str, Any]:
    try:
        suite_path = resources.files("onecite.benchmarks").joinpath("golden_cases.json")
        suite_exists = suite_path.is_file()
        suite = load_benchmark_suite()
    except Exception as exc:
        return _doctor_check("benchmark_resources", False, f"Benchmark resources failed: {exc}")
    return _doctor_check(
        "benchmark_resources",
        suite_exists,
        f"Loaded benchmark suite {suite['suite']} {suite['version']}.",
        {"suite": suite["suite"], "version": suite["version"], "cases": len(suite["cases"])},
    )


def _check_skill_package() -> Dict[str, Any]:
    candidates = [
        Path(__file__).resolve().parents[1] / "skills" / "onecite" / "SKILL.md",
        Path.cwd() / "skills" / "onecite" / "SKILL.md",
        Path(sys.prefix) / "share" / "onecite" / "skills" / "onecite" / "SKILL.md",
        Path(sys.base_prefix) / "share" / "onecite" / "skills" / "onecite" / "SKILL.md",
    ]
    found = next((candidate for candidate in candidates if candidate.is_file()), None)
    return _doctor_check(
        "skill_package",
        found is not None,
        (
            "Bundled OneCite Skill file is present."
            if found
            else "Bundled OneCite Skill file was not found."
        ),
        {"path": str(found) if found else "", "checked": [str(path) for path in candidates]},
    )


def _check_offline_benchmark_gate() -> Dict[str, Any]:
    try:
        report = run_benchmark()
    except Exception as exc:
        return _doctor_check("offline_benchmark_gate", False, f"Offline benchmark failed: {exc}")
    summary = report["summary"]
    return _doctor_check(
        "offline_benchmark_gate",
        report["status"] == "passed",
        (
            f"Offline benchmark {report['suite']} {report['suite_version']} "
            f"passed {summary['passed']}/{summary['total_cases']} cases."
        ),
        {
            "suite": report["suite"],
            "suite_version": report["suite_version"],
            "source_mode": report["source_mode"],
            "summary": summary,
        },
    )


def _format_doctor_text(report: Dict[str, Any]) -> str:
    lines = [
        f"OneCite doctor: {report['status']}",
        f"Version: {report['environment']['package_version']}",
        ("Checks: " f"{report['summary']['passed']}/{report['summary']['total']} passed"),
    ]
    for check in report["checks"]:
        lines.append(f"- {check['name']}: {check['status']} - {check['message']}")
    return "\n".join(lines)


def templates_command(args: "argparse.Namespace") -> int:
    """Run the ``onecite templates`` subcommand.

    Args:
        args: Parsed command-line arguments from :func:`create_parser`.

    Returns:
        Exit code — ``0`` on success.
    """
    templates = TemplateLoader().list_templates()

    if args.as_json:
        print(json.dumps(templates, indent=2))
        return 0

    print("Available templates:")
    for template in templates:
        required = ", ".join(template["required_fields"]) or "-"
        optional = ", ".join(template["optional_fields"]) or "-"
        print(f"- {template['name']} ({template['entry_type']})")
        print(f"  required: {required}")
        print(f"  optional: {optional}")

    return 0


def suggest_command(args: "argparse.Namespace") -> int:
    """Run the ``onecite suggest`` subcommand."""
    try:
        input_content = _read_input_content(args)

        if args.quiet or args.as_json:
            import logging

            logging.basicConfig(level=logging.CRITICAL)
            for logger_name in ["onecite", "scholarly", "httpx", "fake_useragent"]:
                logging.getLogger(logger_name).setLevel(logging.CRITICAL)

        with _offline_source_context():
            result = suggest_references(
                input_content=input_content,
                input_type=args.input_type,
                limit=args.limit,
                use_google_scholar=args.google_scholar,
            )

        suggest_report = _build_suggest_report(args, result)
        output_content = (
            json.dumps(suggest_report, indent=2)
            if args.as_json
            else _format_suggest_text(suggest_report)
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_content)
                if args.as_json:
                    f.write("\n")
            if not args.quiet:
                status_stream = sys.stderr if args.as_json else sys.stdout
                print(f"Suggestions saved to: {args.output}", file=status_stream)
        else:
            print(output_content)

        return 0

    except Exception as e:
        if args.as_json:
            print(json.dumps(_build_suggest_error_report(args, e), indent=2))
        else:
            print(f"Suggestion failed: {e}", file=sys.stderr)
        return 1


def process_command(args: "argparse.Namespace") -> int:
    """Run the ``onecite process`` subcommand.

    Args:
        args: Parsed command-line arguments from
            :func:`create_parser`.

    Returns:
        Exit code — ``0`` on success, ``1`` on failure.
    """
    try:
        input_content = _read_input_content(args)

        # The process pipeline is non-interactive: plain-text candidate
        # selection lives in `onecite suggest`. This callback is retained only
        # to satisfy the process_references signature and always skips.
        def interactive_callback(candidates: List[Dict]) -> int:
            return -1

        if args.quiet or args.as_json or args.as_ndjson:
            import logging

            logging.basicConfig(level=logging.CRITICAL)
            for logger_name in ["onecite", "scholarly", "httpx", "fake_useragent"]:
                logging.getLogger(logger_name).setLevel(logging.CRITICAL)

        with _offline_source_context():
            result = process_references(
                input_content=input_content,
                input_type=args.input_type,
                template_name=args.template,
                output_format=args.output_format,
                interactive_callback=interactive_callback,
            )

        process_report = _build_process_report(args, result)
        if args.as_json:
            output_content = json.dumps(process_report, indent=2)
        elif args.as_ndjson:
            output_content = _format_process_ndjson(process_report)
        else:
            output_content = "\n\n".join(result["results"])

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_content)
                if args.as_json or args.as_ndjson:
                    f.write("\n")
            if not args.quiet:
                status_stream = sys.stderr if args.as_json or args.as_ndjson else sys.stdout
                print(f"Results saved to: {args.output}", file=status_stream)
        else:
            print(output_content)

        if not args.quiet and not args.as_json and not args.as_ndjson:
            report = result["report"]
            print("\nProcessing Report:")
            print(f"  Total entries: {report['total']}")
            print(f"  Successfully processed: {report['succeeded']}")
            print(f"  Failed entries: {len(report['failed_entries'])}")

            if report["failed_entries"]:
                print("\nFailed entries:")
                for failed in report["failed_entries"]:
                    print(f"  - Entry {failed['id']}: {failed.get('error', 'Unknown error')}")

        if args.fail_on_unresolved and process_report["summary"]["failed"] > 0:
            return 2
        return 0

    except Exception as e:
        if args.as_json:
            print(json.dumps(_build_process_error_report(args, e), indent=2))
        elif args.as_ndjson:
            print(_format_process_ndjson(_build_process_error_report(args, e)))
        else:
            print(f"Processing failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
