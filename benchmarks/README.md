# OneCite Benchmarks

This directory is the repository-facing benchmark area. The packaged
golden cases live in `src/onecite/benchmarks/golden_cases.json`; the baseline
run record lives in `benchmarks/leaderboard.json`.

The bundled suite is a small deterministic golden-case regression suite. It
covers DOI/Crossref, arXiv, PMID/PubMed, GitHub software URLs, Zenodo/DataCite
dataset DOIs, and mixed valid/invalid input handling through deterministic
offline fixtures. Passing it means the covered cases passed; it is not a
general citation-accuracy score, performance score, or claim about all
upstream source behavior.

Run the reproducible offline benchmark:

```bash
onecite benchmark --json
```

Run a live upstream-source spot check:

```bash
onecite benchmark --live --json
```

Run the labelled anti-hallucination (non-fabrication) evaluation; its
baseline record lives in `benchmarks/anti_hallucination_baseline.json`:

```bash
onecite benchmark --anti-hallucination --json
```

Baseline entries should include the suite name, suite version, source mode,
Python version, platform, total case count, pass counts, success rate, and the
command used to reproduce the result. Treat the baseline as a reproducibility
record for this suite, not as a competitive ranking across citation tools.
