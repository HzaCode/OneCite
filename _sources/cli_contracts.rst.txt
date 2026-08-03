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
- ``summary``: total, succeeded, failed, duplicates, and success rate
  (duplicates count as resolved for the success rate).
- ``options``: the effective CLI options that affect processing.
- ``failed_entries``: unresolved entries with their error payloads; each
  carries the original input excerpt (``raw_text``) and a ``reason`` code
  (e.g. ``doi_not_found``, ``no_strong_identifier``, ``source_error``).
  Reasons distinguish several important paths, but are not a complete provider
  trace: some DataCite, PMID, and ISBN provider errors currently collapse into
  the same unresolved reason as a lookup miss. See :doc:`external_services`.
- ``warnings``: non-blocking review warnings attached to resolved entries,
  e.g. ``text_metadata_mismatch`` when the input text appears to describe
  a different work than the resolved DOI.
- ``duplicates``: entries whose DOI already resolved earlier in the batch;
  each points at the emitted entry (``duplicate_of``, ``bib_key``).
- ``results``: formatted citation strings, one per unique resolved work (BibTeX entries, or CSL-JSON item objects when ``--output-format csl-json`` is used; the plain-text CLI output then assembles them into one valid JSON array).

The current top-level contract is exactly ``schema_version``, ``tool``,
``command``, ``status``, ``summary``, ``options``, ``failed_entries``,
``warnings``, ``duplicates``, and ``results``. Additive fields should be
treated as a contract change and covered by tests.

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
- ``result``: one event per formatted BibTeX or CSL-JSON result.
- ``warning``: one event per non-blocking review warning.
- ``duplicate``: one event per repeated-DOI entry.
- ``failure``: one event per unresolved entry.

This mode is intended for streaming automation workflows that want partial
results without parsing human text.

Hard processing errors in ``--ndjson`` mode emit a ``summary`` event with
``status: "failed"`` followed by one ``failure`` event, then exit with
code ``1``.

Suggest JSON
------------

``onecite suggest INPUT --json`` writes one JSON object to stdout unless
``--output`` is used. This command searches candidate metadata sources but
does not resolve candidates into BibTeX. Its successful status is
``"completed"``, not ``"passed"``, so suggestion output is not confused with
validated citation output.

The envelope contains:

- ``schema_version``: currently ``"1.0"``.
- ``tool`` and ``command``: ``"onecite"`` and ``"suggest"``.
- ``status``: ``"completed"`` when candidate search ran, ``"failed"`` on a
  hard command error.
- ``summary``: total entries, entries with candidates, and entries without
  candidates.
- ``options``: input type, per-entry limit, and whether Google Scholar was
  enabled.
- ``suggestions``: one item per input entry with raw text, query string,
  status, a candidate list, and a ``sources`` list disclosing the health of
  the always-consulted scholarly indexes (``crossref``,
  ``semantic_scholar``, ``arxiv``) with per-source candidate counts. When a source was
  rate-limited or errored, the entry status becomes
  ``candidates_found_incomplete`` / ``no_candidates_incomplete`` — the
  candidate list may be missing the correct match and must not be treated
  as exhaustive.

The current top-level contract is exactly ``schema_version``, ``tool``,
``command``, ``status``, ``summary``, ``options``, and ``suggestions``.

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
