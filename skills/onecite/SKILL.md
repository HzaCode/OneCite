---
name: onecite
description: Validate, clean, and audit academic references with OneCite from a local repository checkout. Use when a workflow needs deterministic citation verification, BibTeX cleanup, benchmark gating, or template discovery.
---

# OneCite

Use this skill to turn raw references, DOI lists, arXiv IDs, PMID/ISBN-like
identifiers, GitHub URLs, Zenodo/DataCite DOIs, or existing BibTeX into
verified BibTeX output through the OneCite pipeline.

## When To Use

- A manuscript, README, paper, package, or dataset has references that need
  canonical metadata lookup.
- A citation list has been generated or edited and needs a deterministic
  API-layer check before being trusted.
- A repository needs reproducible citation regression checks.
- A user asks for a clean `.bib` file, reference audit, or template discovery.

## Ground Rules

- Do not fabricate bibliographic fields. Missing metadata should stay missing
  or be reported as a failure.
- Treat formatting success as different from truth. OneCite checks metadata
  against academic APIs; it does not prove that a citation supports a claim.
- Keep raw references separated by blank lines when using plain text input.
- Run `onecite benchmark --json` first for deterministic offline regression
  checks; it uses bundled fixtures and does not require network access.
- Use `onecite process ...` for citation metadata lookup; unless test fixtures
  or mocks are explicitly configured, process mode may contact upstream APIs.
- Use `onecite benchmark --live --json` only when the user explicitly wants
  current upstream source behavior.
- OneCite performs deterministic source lookups and formatting at runtime.

## Setup

From the repository root:

```bash
python -m pip install -e ".[dev]"
```

Use the repository's virtual environment when one exists:

```bash
.venv/bin/python -m onecite.cli --help
```

## Common Commands

Process a plain-text reference file:

```bash
onecite process references.txt -o references.bib --quiet
```

Process an existing BibTeX file:

```bash
onecite process references.bib -o cleaned.bib --quiet
```

Process a direct identifier:

```bash
onecite process "10.1038/nature14539"
```

List available fallback templates:

```bash
onecite templates --json
```

Run the deterministic benchmark regression check:

```bash
onecite benchmark --json
```

Check the local install, bundled resources, skill package, and offline
benchmark gate:

```bash
onecite doctor --json
```

Produce an automation-friendly validation envelope:

```bash
onecite process references.txt --json --fail-on-unresolved
```

Stream newline-delimited events:

```bash
onecite process references.txt --ndjson
```

Use live APIs for an upstream spot check:

```bash
onecite benchmark --live --json
```

## Automation Workflow

1. Read the user's source reference material and preserve original text for
   traceability.
2. Put one reference per blank-separated block in `references.txt`, or use the
   user's existing `.bib` file directly.
3. Run `onecite process ... --quiet` to generate BibTeX.
4. Run `onecite process ... --json --fail-on-unresolved` when a script needs
   a strict machine-readable gate.
5. Run `onecite benchmark --json` before reporting regression-check results.
6. Run `onecite doctor --json` before reporting that the local installation
   has the expected automation or CI resources.
7. Inspect `failed_entries`, `warnings`, and `duplicates` in the process
   report, benchmark case failures, and doctor failed checks.
8. Report unresolved entries explicitly instead of inventing replacements.

## Interpreting Process Reports

- `warnings` with type `text_metadata_mismatch`: the entry resolved from its
  DOI, but the surrounding input text appears to describe a **different**
  work — the classic hallucinated title+DOI pairing. Surface this to the
  user for review; do not silently accept the entry.
- `duplicates`: the same work appeared more than once in the batch (bare
  DOI, PMID, formatted citation). It was emitted once; cite the listed
  `bib_key`.
- `failed_entries[].reason` tells you the correct follow-up:
  - `doi_not_found` — the DOI does not exist in CrossRef or DataCite;
    likely fabricated or mistyped. Do not retry unchanged; flag it.
  - `no_strong_identifier` — ambiguous plain text; run `onecite suggest`
    and have the result reviewed. Never promote a candidate to verified
    output yourself.
  - `source_error` — a source errored; retrying later may succeed.
  - `pmid_unresolved` / `isbn_unresolved` — the lookup found no record
    (nonexistent identifier or source unavailable/rate-limited).

## Using Suggest Safely

- `onecite suggest` returns **candidates for review, not verified
  citations**. Check each suggestion's `sources` list: a status other than
  `ok` (and an entry status ending in `_incomplete`) means a scholarly
  index was rate-limited or errored and the correct match may be missing
  from the list entirely.
- Treat a low `match_score` as no-confidence: do not present a top
  candidate as "the match" just because it ranks first. A `year_conflict`
  flag in `score_breakdown` means the candidate's year contradicts the year
  the query cites.
- To turn a reviewed candidate into verified BibTeX, take its DOI and run
  `onecite process "<doi>"` — never hand-assemble an entry from candidate
  fields.

## Anti-Hallucination Evaluation

Run the labelled non-fabrication evaluation (offline, deterministic):

```bash
onecite benchmark --anti-hallucination --json
```

It reports the resolution rate on real identifiers, the non-fabrication
rate on ambiguous/fabricated inputs, and the mismatch detection rate on
real DOIs paired with a different paper's title.

## Repository Validation Checks

1. Start from the Roadmap section in `README.md`; choose one scoped Roadmap
   item or one explicit maintenance follow-up.
2. Implement the change locally and keep unrelated edits out of the diff.
3. Run local validation before release or handoff:

   ```bash
   python -m pytest
   flake8 src/onecite tests --statistics --count
   onecite benchmark --json
   onecite doctor --json
   python -m build --wheel
   ```

4. Summarize the changed files, exact commands, pass/fail status, and any
   generated archive or wheel hashes.
5. Do not report local verification evidence until the local checks pass and
   references or failed checks are reported explicitly.

## Output Expectations

For automation handoff, include:

- the command used,
- the output `.bib` path when one was written,
- the benchmark status from `onecite benchmark --json`,
- the doctor status from `onecite doctor --json`,
- the `onecite process --json` status when strict validation was used,
- unresolved entry IDs and error messages,
- whether live APIs were used.

## Release and Review Checks

For repository changes to OneCite itself, do not mark the Roadmap done
unless these checks pass from the repository root:

```bash
python -m pytest
flake8 src/onecite tests
onecite benchmark --json
onecite doctor --json
python -m build --wheel
```

For handoff, include the exact commands run, the pass/fail summary, the commit
or diff reference, and any ZIP/wheel hash. Do not use live APIs for the default
gate unless the user explicitly requests upstream-current behavior.

## Troubleshooting

- If a `.bib` file is being treated as text, pass `--input-type bib`.
- If plain text merges separate references, add blank lines between entries.
- If Google Scholar is needed, install the optional dependency and pass
  `--google-scholar`; otherwise leave it off for deterministic runs.
- If a benchmark must be reproducible in CI, do not pass `--live`.
- If `onecite doctor --json` fails, fix the missing resource or failing
  benchmark before relying on package-level results.
