CLI Contracts
=============

OneCite exposes stable command-line envelopes for automation and CI
workflows. Human-readable output is still available, but automation
should prefer the JSON or NDJSON modes below.

Process JSON
------------

``onecite process INPUT --json`` writes one JSON object to stdout unless
``--output`` is used. The envelope contains:

- ``schema_version``: currently ``"1.0"``.
- ``tool`` and ``command``: ``"onecite"`` and ``"process"``.
- ``status``: ``"passed"`` when all entries resolved, otherwise
  ``"failed"``.
- ``summary``: total, succeeded, failed, and success rate.
- ``options``: the effective CLI options that affect processing.
- ``failed_entries``: unresolved entries with their error payloads.
- ``results``: formatted BibTeX strings.

The current top-level contract is exactly ``schema_version``, ``tool``,
``command``, ``status``, ``summary``, ``options``, ``failed_entries``,
and ``results``. Additive fields should be treated as a contract change
and covered by tests.

Use ``--fail-on-unresolved`` when unresolved entries should make the
process exit with code ``2``.

If a hard processing error happens before per-entry results can be built,
``--json`` still writes the same top-level envelope with ``status:
"failed"``, a single ``failed_entries`` error payload, and exit code
``1``.

Process NDJSON
--------------

``onecite process INPUT --ndjson`` emits newline-delimited JSON events:

- ``summary``: one event containing status, summary, and options.
- ``result``: one event per formatted BibTeX result.
- ``failure``: one event per unresolved entry.

This mode is intended for streaming automation workflows that want partial
results without parsing human text.

Hard processing errors in ``--ndjson`` mode emit a ``summary`` event with
``status: "failed"`` followed by one ``failure`` event, then exit with
code ``1``.

Benchmark JSON
--------------

``onecite benchmark --json`` emits a deterministic regression report for the
configured benchmark suite:

- ``schema_version``: currently ``"1.0"``.
- ``suite`` and ``suite_version``.
- ``source_mode``: ``"offline"`` by default, ``"live"`` with
  ``--live``.
- ``status`` and ``summary``.
- ``cases`` with per-case status, failures, and observed counts.

The default offline mode uses bundled fixtures and patches OneCite's HTTP
source calls, so the deterministic benchmark does not require network
access. Passing ``--live`` removes that isolation and should be reserved
for explicit upstream-source spot checks.

The default command exits ``0`` only when every bundled case passes. Custom
suites can lower the gate with ``--min-success-rate``. Reports should include
the suite name, suite version, source mode, total case count, and pass counts
so the result is not mistaken for a general citation-accuracy score. Passing
the bundled suite means the covered cases passed. The displayed
``success_rate`` is rounded to four decimals for readability; the exit gate
uses the unrounded ``passed / total_cases`` ratio, so a displayed ``0.6667``
does not satisfy ``--min-success-rate 0.6667`` when the actual ratio is
``2/3``.

Doctor JSON
-----------

``onecite doctor --json`` emits an installation-health report:

- ``schema_version``: currently ``"1.0"``.
- ``tool`` and ``command``: ``"onecite"`` and ``"doctor"``.
- ``status``: ``"passed"`` only when every check passed.
- ``environment``: Python executable, Python version, platform, and
  package version.
- ``summary``: total, passed, and failed check counts.
- ``checks``: package version, templates, benchmark resources,
  skill package, and offline benchmark gate.

The current doctor top-level contract is exactly ``schema_version``,
``tool``, ``command``, ``status``, ``environment``, ``summary``, and
``checks``. Each check contains ``name``, ``status``, ``message``, and
``details``.

Exit Codes
----------

- ``0``: command completed and its quality gate passed.
- ``1``: command failed, benchmark/doctor gate failed, or processing
  raised an error.
- ``2``: ``onecite process --fail-on-unresolved`` found unresolved
  entries.

Stdout and Stderr
-----------------

Machine-readable JSON and NDJSON are written to stdout. Interactive
prompts and saved-file status messages are routed to stderr in those
modes so stdout stays parseable.
