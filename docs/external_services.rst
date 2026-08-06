Privacy and External Services
=============================

OneCite performs local parsing and formatting, but ordinary ``process`` and
``suggest`` runs can make outbound requests to different services according to
the input. OneCite does **not** send every reference to every service.

Before processing confidential, embargoed, or personally identifying text,
decide whether it is appropriate to disclose the relevant identifier, query,
or URL to the services listed below. Redact unrelated text and never place
credentials or private tokens in an input URL. The project does not claim that
using OneCite makes a workflow compliant with any privacy or regulatory
framework. Each provider, network proxy, and execution environment may log or
retain requests under its own policy.

When accepting untrusted input in a server or agent, validate or allow-list
URLs before invoking ``process``. The non-GitHub/non-arXiv URL route fetches the
user-supplied host to inspect DOI metadata; OneCite does not itself provide a
deployment network sandbox or URL allow-list.

``process`` routes
------------------

``process`` does not run a general title search for an ordinary ambiguous
reference. Its live routes are input-dependent:

.. list-table:: Outbound requests made by ``process``
   :header-rows: 1
   :widths: 20 23 32 25

   * - Input or trigger
     - Service
     - Data sent
     - Boundary
   * - DOI
     - Crossref; DataCite after a Crossref ``404``; an exact Zenodo DOI may
       additionally fall back to Zenodo
     - The DOI in the request path. Crossref also receives OneCite's package
       contact in the ``User-Agent`` and ``mailto`` parameter.
     - A successful registry response is checked against the requested DOI.
       Returned metadata can still be incomplete or wrong upstream.
   * - DOI record with no abstract
     - Semantic Scholar, then NCBI E-utilities if needed
     - Semantic Scholar receives the DOI. NCBI receives a DOI search term and,
       when found, the resulting PMID.
     - This fallback runs only when the original input carried a DOI and the
       resolved record still lacks an abstract. It does not title-search for an
       abstract.
   * - PMID
     - NCBI E-utilities; Crossref may then receive a DOI returned by PubMed
     - The PMID, followed by the returned DOI when one is available.
     - A PMID lookup is identifier-based. Failure does not fall through to a
       fuzzy title match.
   * - arXiv identifier or arXiv URL
     - arXiv
     - The arXiv identifier.
     - Metadata comes from the matching arXiv feed entry.
   * - ISBN-bearing reference
     - Google Books
     - A derived book query made from the input, which can include ISBN, title,
       or author text.
     - The current route uses a search result rather than an exact ISBN
       identity assertion. Review the resulting book metadata.
   * - GitHub repository URL
     - GitHub REST API
     - Repository owner/name, followed by a tags request for that repository.
     - Requests are unauthenticated and therefore subject to GitHub's
       unauthenticated limits.
   * - Other URL
     - The host named by the supplied URL, then a DOI registry if a DOI is
       found
     - The complete URL path and query string, plus OneCite's ``User-Agent``.
     - The request follows redirects and reads at most 5 MiB. Only a
       publisher-declared DOI meta tag or schema.org identifier is accepted;
       body-text DOI scraping is not used.
   * - Explicit thesis or dissertation citation
     - OpenAIRE, then BASE when OpenAIRE returns no result
     - OpenAIRE receives the parsed thesis title and fixed publication-type
       filters. The BASE fallback receives a derived thesis query plus the year
       when one was parsed.
     - If neither provider returns a record, OneCite can format explicit
       author/title/year/school fields parsed from the input and marks the
       internal source as ``manual``. That fallback is input-derived, not
       independently source-resolved.
   * - Ordinary title or author text with no supported route
     - None
     - Nothing is sent by ``process`` for candidate search.
     - The entry remains unresolved with ``no_strong_identifier``. Use
       ``suggest`` for candidates.

Some DOI, dataset, and software inputs can take more than one route as a
fallback. A route being labelled "source-resolved" means a service returned a
record for the identifier; it does not prove that the work is authentic,
unretracted, or correctly described by the provider.

``suggest`` routes
------------------

``suggest`` is deliberately broader because its output is a candidate list for
review, not resolved bibliography output.

.. list-table:: Outbound requests made by ``suggest``
   :header-rows: 1
   :widths: 24 26 50

   * - When used
     - Service
     - Data sent
   * - Every non-empty query
     - Crossref
     - The normalized citation query. Crossref search may try bibliographic,
       general, and title/author query strategies.
   * - Every non-empty query
     - Semantic Scholar
     - The normalized citation query and requested result fields.
   * - Every non-empty query with usable title terms
     - arXiv
     - Title terms derived from the text before the first comma.
   * - PMID-shaped input or strong medical cues
     - NCBI E-utilities
     - The PMID or the full normalized medical query, followed by PMIDs returned
       from search.
   * - ISBN, edition, or configured publisher cues
     - Google Books
     - A derived query containing relevant book/title/author text.
   * - ``thesis`` or ``dissertation`` cue
     - OpenAIRE, then BASE as a fallback
     - The normalized citation query and a derived thesis query.
   * - Explicit ``--google-scholar`` opt-in, when both Crossref and Semantic
       Scholar return no candidates
     - Google Scholar through the optional ``scholarly`` package
     - The normalized citation query.

Candidate scores are similarity and ranking signals, not verification. Review
the candidate, then pass a trusted identifier (normally its DOI) back through
``process``. A candidate list can be incomplete even when some sources
succeeded.

Google Scholar is off by default
--------------------------------

The Google Scholar fallback is available only after installing
``onecite[scholar]`` and opting in with ``suggest --google-scholar`` (or
``suggest_references(..., use_google_scholar=True)``). It automates Scholar
through ``scholarly`` rather than using a documented API route in OneCite.
Automated requests can be throttled, blocked, or challenged by a CAPTCHA, can
take substantially longer than the API-backed routes, and are not a
reproducible dependency. It is never used by ``process``.

Source health and rate limits
-----------------------------

For each query, ``suggest --json`` reports a ``sources`` list for the three
always-consulted indexes: ``crossref``, ``semantic_scholar``, and ``arxiv``.
Each item contains a status and candidate count. Persistent throttling is
reported as ``rate_limited`` where the route distinguishes it; other failures
are reported as ``error``. A source that failed terminally on consecutive
earlier entries of the same run is short-circuited for a cooldown period and
reported as ``skipped_unhealthy`` instead of being re-queried — the skip is
always disclosed, and one probe request is allowed after the cooldown so a
recovered source rejoins automatically. Applicable sources are queried
concurrently with bounded retry waits, so one degraded provider slows only
its own entry in the ``sources`` list rather than the whole batch. If any
reported source is degraded, the suggestion status ends in ``_incomplete``.
Human-readable output prints a warning for each degraded reported source.

This is not a complete network trace. Conditional sources such as PubMed,
Google Books, OpenAIRE, BASE, and Google Scholar do not currently have the same
per-source health entries. ``process`` also has no equivalent source-health
list; inspect failure reason codes and logs instead. Those reasons are also
coarse: the current DataCite, PMID, and ISBN helpers collapse some caught
provider errors into the same unresolved outcome as a lookup miss. Retry and
backoff behavior varies by route, so do not assume that every service is
retried, that every ``429`` is surfaced the same way, or that a fixed runtime
applies. Provider limits can change independently of OneCite. The reported
``suggest`` status is not a per-request trace either; for example, Crossref can
remain ``ok`` when one search strategy failed but another produced usable
candidates. See the current `Crossref access
guidance <https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/>`_
and `NCBI E-utilities usage guidance
<https://eutilities.github.io/site/API_Key/usageandkey/>`_ when operating large
jobs.

Offline checks are not live-service checks
-------------------------------------------

- ``onecite benchmark`` uses bundled fixtures by default and patches the HTTP
  source calls. It does not contact the services above. ``--live`` opts into
  live external requests.
- ``onecite doctor`` checks the installed package, templates, bundled
  resources, Skill file, and the offline benchmark gate. It does not test live
  provider reachability or current metadata.
- ``onecite templates`` and ``onecite --version`` are local commands after the
  package is installed.

Passing an offline benchmark proves only that the bundled cases passed against
their fixed fixtures. It does not establish current service availability,
current metadata quality, or general citation accuracy.

Caching, snapshots, and local traces
------------------------------------

Ordinary live lookups do not have a persistent OneCite HTTP-response cache or
source snapshot. Therefore, a later run can change when a provider changes its
metadata, ranking, availability, or limits. The bundled benchmark fixtures are
test data, not a cache of a user's previous lookups.

This boundary is not a promise that no data is stored anywhere. In particular:

- ``-o`` intentionally writes the selected output; JSON reports can include
  original input text, queries, failures, and candidates;
- terminal capture, application logs, proxies, and provider logs may retain
  request or response details; and
- OneCite does not control retention by external services.

For a reproducible audit, preserve the input you are allowed to retain, the
OneCite version, command options, output/report, and run time. Treat live
metadata as time-varying evidence rather than a pinned snapshot.
