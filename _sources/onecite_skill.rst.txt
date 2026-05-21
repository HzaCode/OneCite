OneCite Skill
=============

The repository includes a local skill package for automated citation
workflows:

``skills/onecite/SKILL.md``

The skill documents when to use OneCite, the citation-verification
boundaries, deterministic benchmark commands, and the expected handoff
format for automated workflows.

This skill is repository-contained. It is not installed into a user's
local tool memory automatically; workflows can read or package it from
the repository when they need OneCite-specific operating instructions.

Core commands from the skill::

    onecite process references.txt -o references.bib --quiet
    onecite process references.txt --json --fail-on-unresolved
    onecite templates --json
    onecite benchmark --json
    onecite doctor --json

Use ``onecite benchmark --json`` first for deterministic offline regression
checks; it uses bundled source fixtures and does not require network access.
``onecite process ...`` is the metadata lookup workflow and may contact
upstream APIs unless a test fixture or mock source is explicitly configured.
Use ``onecite benchmark --live --json`` only when checking live upstream
source behavior.

Before a workflow reports OneCite local verification results, it should run
both ``onecite benchmark --json`` and ``onecite doctor --json``. The benchmark
exercises covered source-routing behavior through deterministic fixtures; the
doctor command checks that the local installation has the expected resources,
skill package, templates, and benchmark resources.

For Roadmap work, the skill anchors scope on the Roadmap section in
``README.md`` and defines a local quality loop: implement one scoped
change, run the pytest/flake8/benchmark/doctor/wheel checks, and report
the exact test output plus archive hashes as local verification evidence.
