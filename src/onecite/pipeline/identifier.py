# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Stage 2 — identify entries and standardise them into ``IdentifiedEntry``."""

import re
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Dict, Optional, Callable
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup
from thefuzz import fuzz

try:
    from scholarly import scholarly
except ImportError:
    scholarly = None

from .. import __email__, __version__
from ..core import RawEntry, IdentifiedEntry
from ._utils import _safe_year

RETRYABLE_HTTP_STATUSES = (429, 500, 502, 503, 504)
MAX_RETRY_WAIT_SECONDS = 600.0
SUGGESTION_MAX_ATTEMPTS = 4
SUGGESTION_FALLBACK_BACKOFF_SECONDS = (10.0, 60.0, 300.0)

_SOURCE_STATUS_PRIORITY = {"ok": 0, "rate_limited": 1, "error": 2}

# Zenodo minted nine incorrect DOI numeric IDs during a short 2013 legacy
# interval. Its current official implementation still maps these record IDs
# before generating a DOI:
# https://github.com/zenodo/zenodo/blob/2d0bd3527dcb851613a00391d674be1d004c9459/zenodo/modules/records/config.py#L115-L130
_ZENODO_RECORD_ID_TO_LEGACY_DOI_ID = {
    7468: 7448,
    7458: 7457,
    7467: 7447,
    7466: 7446,
    7465: 7464,
    7469: 7449,
    7487: 7486,
    7482: 7481,
    7484: 7483,
}
_ZENODO_LEGACY_DOI_ID_TO_RECORD_ID = {
    doi_id: record_id for record_id, doi_id in _ZENODO_RECORD_ID_TO_LEGACY_DOI_ID.items()
}


def _retry_after_delay(response: Any, fallback_seconds: float) -> tuple[float, str | None, bool]:
    """Prefer a valid Retry-After delay, with a bounded deterministic fallback."""
    headers = getattr(response, "headers", None)
    raw: str | None = None
    if headers:
        for key, value in headers.items():
            if str(key).lower() == "retry-after":
                raw = str(value).strip()
                break

    parsed: float | None = None
    if raw:
        try:
            parsed = float(int(raw))
            if parsed < 0:
                parsed = None
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(raw)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                parsed = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                parsed = None

    used_retry_after = parsed is not None
    delay: float = parsed if parsed is not None else float(fallback_seconds)
    return min(max(0.0, delay), MAX_RETRY_WAIT_SECONDS), raw, used_retry_after


class IdentifierModule:
    """Stage 2: Identification and Standardization Module."""

    def __init__(self, use_google_scholar: bool = False):
        """Initialize the identifier module.

        Args:
            use_google_scholar: Enable Google Scholar lookups when
                ``True``.  Defaults to ``False``.
        """
        self.logger = logging.getLogger(__name__)
        self.crossref_base_url = "https://api.crossref.org/works"
        self.use_google_scholar = use_google_scholar
        self.github_api_base = "https://api.github.com"
        self.zenodo_api_base = "https://zenodo.org/api/records"
        self.base_search_url = "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
        self.openaire_api_base = "https://api.openaire.eu/search/publications"
        self.semantic_scholar_base = "https://api.semanticscholar.org/graph/v1"
        self.pubmed_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.datacite_base = "https://api.datacite.org"
        # Per-suggest-call health of every source actually consulted, reset by
        # suggest(). A rate-limited or errored source must be disclosed in the
        # output — silently returning fewer candidates misrepresents how
        # complete the suggestion list is.
        self._source_status: Dict[str, str] = {}
        self._user_agent = (
            f"OneCite/{__version__} " f"(https://github.com/HzaCode/OneCite; mailto:{__email__})"
        )
        self._crossref_headers = {
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        self._crossref_mailto = __email__

    def _record_source_status(self, source_name: str, status: str) -> None:
        """Record the least healthy terminal state observed for one source.

        A source can require several HTTP requests (for example, PubMed's
        search-then-summary flow).  A later successful request must not hide
        an earlier terminal failure that made the returned candidate set
        incomplete.  Transient failures recovered inside ``_get_with_retry``
        never reach this method and therefore correctly finish as ``ok``.
        """
        if status not in _SOURCE_STATUS_PRIORITY:
            raise ValueError(f"Unsupported source status: {status}")
        current = self._source_status.get(source_name)
        if current is None or _SOURCE_STATUS_PRIORITY[status] > _SOURCE_STATUS_PRIORITY[current]:
            self._source_status[source_name] = status

    def _get_with_retry(
        self,
        url: str,
        *,
        source_name: str,
        max_attempts: int,
        fallback_backoff_seconds: tuple[float, ...],
        **request_kwargs: Any,
    ) -> Any:
        """Issue a GET with a frozen, source-specific transient-error policy."""
        response = None
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                response = requests.get(url, **request_kwargs)
                last_error = None
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                last_error = exc
                if attempt >= max_attempts - 1:
                    raise
                wait_seconds = fallback_backoff_seconds[
                    min(attempt, len(fallback_backoff_seconds) - 1)
                ]
                self.logger.warning(
                    f"{source_name} raised {type(exc).__name__}; retrying in "
                    f"{wait_seconds:g}s using frozen fallback"
                )
                time.sleep(wait_seconds)
                continue
            if response.status_code not in RETRYABLE_HTTP_STATUSES or attempt >= max_attempts - 1:
                break
            fallback = fallback_backoff_seconds[min(attempt, len(fallback_backoff_seconds) - 1)]
            wait_seconds, retry_after, used_retry_after = _retry_after_delay(response, fallback)
            source = "Retry-After" if used_retry_after else "frozen fallback"
            detail = f" ({retry_after!r})" if retry_after is not None else ""
            self.logger.warning(
                f"{source_name} returned {response.status_code}; retrying in "
                f"{wait_seconds:g}s using {source}{detail}"
            )
            time.sleep(wait_seconds)
        if response is None and last_error is not None:
            raise last_error
        return response

    def identify(
        self,
        raw_entries: List[RawEntry],
        interactive_callback: Optional[Callable[[List[Dict]], int]] = None,
    ) -> List[IdentifiedEntry]:
        """Identify and standardize entries, finding a DOI for each.

        Args:
            raw_entries: List of raw entries produced by
                :meth:`ParserModule.parse`.
            interactive_callback: Accepted for backward compatibility and
                never invoked — identification is strictly identifier-based
                and fail-closed; candidate search lives in :meth:`suggest`.

        Returns:
            A list of :class:`IdentifiedEntry` dictionaries.
        """
        self.logger.info(f"Starting to identify {len(raw_entries)} entries")
        identified_entries = []

        for entry in raw_entries:
            identified_entry = self._identify_single_entry(entry, interactive_callback)
            identified_entries.append(identified_entry)

        successful_count = sum(1 for e in identified_entries if e["status"] == "identified")
        self.logger.info(
            f"Identification completed: {successful_count}/{len(identified_entries)} entries successfully identified"
        )

        return identified_entries

    def _identify_single_entry(
        self,
        raw_entry: RawEntry,
        interactive_callback: Optional[Callable[[List[Dict]], int]] = None,
    ) -> IdentifiedEntry:
        """Identify a single entry"""
        identified_entry: IdentifiedEntry = {
            "id": raw_entry["id"],
            "raw_text": raw_entry["raw_text"],
            "doi": None,
            "arxiv_id": None,
            "url": None,
            "metadata": {},
            "status": "identification_failed",
        }

        # If valid DOI already exists, verify it against Crossref / DataCite
        raw_doi = raw_entry.get("doi")
        if raw_doi:
            if self._validate_doi(raw_doi):
                real_metadata, verify_failure = self._verify_doi_and_get_metadata(raw_doi)
                if real_metadata:
                    # The supplied DOI remains the resolved identifier: resolution is never blocked
                    # by how the surrounding text reads, and no fuzzy score
                    # replaces identifier-based verification. But when that
                    # text clearly describes a *different* work (the classic
                    # hallucinated title+DOI pairing), staying silent would
                    # present a wrong citation as clean source-resolved output, so the
                    # mismatch is surfaced as a review warning on the entry.
                    identified_entry["doi"] = raw_doi
                    identified_entry["metadata"] = real_metadata
                    identified_entry["status"] = "identified"
                    mismatch = self._check_text_metadata_mismatch(
                        raw_entry["raw_text"], raw_doi, real_metadata
                    )
                    if mismatch:
                        identified_entry["warnings"] = [mismatch]
                    return identified_entry
                else:
                    identified_entry["failure_reason"] = verify_failure or "doi_not_found"
                    self.logger.warning(
                        f"Entry {raw_entry['id']} has valid DOI format but DOI does not exist: {raw_entry['doi']}"
                    )
                    # Zenodo is an explicit provider route and is also used by
                    # the deterministic offline suite.  Accept it only when
                    # the *entire* claimed DOI has the exact Zenodo record
                    # shape and the Zenodo API returns that same DOI.  A
                    # prefix match is unsafe because a fabricated suffix could
                    # otherwise be truncated back to a real parent record.
                    if re.fullmatch(r"10\.5281/zenodo\.\d+", raw_doi, re.IGNORECASE):
                        zenodo_info = self._extract_zenodo_info(raw_doi)
                        returned_doi = (zenodo_info or {}).get("doi", "")
                        if returned_doi.lower() == raw_doi.lower():
                            identified_entry["doi"] = raw_doi
                            identified_entry["metadata"] = zenodo_info or {}
                            identified_entry["status"] = "identified"
                            identified_entry.pop("failure_reason", None)
                            mismatch = self._check_text_metadata_mismatch(
                                raw_entry["raw_text"], raw_doi, zenodo_info or {}
                            )
                            if mismatch:
                                identified_entry["warnings"] = [mismatch]
                            return identified_entry
                    # An explicit DOI is an identifier claim, not ambiguous
                    # text. If that exact identifier cannot be source-resolved, fail
                    # closed.  Falling through lets DOI suffixes that resemble
                    # other identifiers (for example ``2001.01084`` as an
                    # arXiv-shaped substring) resolve to an unrelated work.
                    return identified_entry

        github_info = self._extract_github_info(raw_entry["raw_text"])
        if github_info:
            identified_entry["metadata"] = github_info
            identified_entry["url"] = github_info.get("url")
            identified_entry["status"] = "identified"
            self.logger.info(
                f"Entry {raw_entry['id']} identified as GitHub repository: {github_info.get('repo')}"
            )
            return identified_entry

        zenodo_info = self._extract_zenodo_info(raw_entry["raw_text"])
        if zenodo_info:
            identified_entry["doi"] = zenodo_info.get("doi")
            identified_entry["metadata"] = zenodo_info
            identified_entry["status"] = "identified"
            self.logger.info(f"Entry {raw_entry['id']} identified as Zenodo dataset")
            return identified_entry

        thesis_info = self._detect_thesis(raw_entry["raw_text"])
        if thesis_info:
            identified_entry["metadata"] = thesis_info
            identified_entry["status"] = "identified"
            self.logger.info(f"Entry {raw_entry['id']} identified as thesis")
            return identified_entry

        arxiv_id = self._extract_arxiv_id(raw_entry["raw_text"])
        if arxiv_id:
            identified_entry["arxiv_id"] = arxiv_id
            identified_entry["status"] = "identified"
            self.logger.info(f"Entry {raw_entry['id']} has arXiv ID: {arxiv_id}")
            return identified_entry

        # Try to extract DOI or arXiv ID from URL
        raw_url = raw_entry.get("url")
        if raw_url:
            if "github.com" in raw_url:
                github_info = self._extract_github_info(raw_url)
                if github_info:
                    identified_entry["metadata"] = github_info
                    identified_entry["url"] = raw_url
                    identified_entry["status"] = "identified"
                    self.logger.info(
                        f"Entry {raw_entry['id']} identified as GitHub repository from URL: {github_info.get('repo')}"
                    )
                    return identified_entry

            if "arxiv.org" in raw_url:
                arxiv_id = self._extract_arxiv_id_from_url(raw_url)
                if arxiv_id:
                    identified_entry["arxiv_id"] = arxiv_id
                    identified_entry["url"] = raw_url
                    identified_entry["status"] = "identified"
                    self.logger.info(
                        f"Entry {raw_entry['id']} extracted arXiv ID from URL: {arxiv_id}"
                    )
                    return identified_entry

            # For other URLs
            if "github.com" not in raw_url and "arxiv.org" not in raw_url:
                # Try to extract DOI
                extracted_doi = self._extract_doi_from_url(raw_url)
                if extracted_doi:
                    identified_entry["doi"] = extracted_doi
                    identified_entry["status"] = "identified"
                    self.logger.info(
                        f"Entry {raw_entry['id']} extracted DOI from URL: {extracted_doi}"
                    )
                    return identified_entry

                identified_entry["url"] = raw_url

        # Fuzzy search
        raw_query = raw_entry.get("query_string")
        if raw_query:
            query_string = raw_query.strip()

            # A bare 7-8 digit block is treated as a PMID; an explicitly
            # labelled "PMID:12345678" is also honoured when embedded in
            # citation text — the label makes it as unambiguous as a DOI
            # embedded in text, which has always been extracted.
            pmid = None
            bare_match = re.match(r"^(?:PMID:?\s*)?(\d{7,8})$", query_string, re.IGNORECASE)
            if bare_match:
                pmid = bare_match.group(1)
            else:
                labelled_match = re.search(r"\bPMID:?\s*(\d{7,8})\b", query_string, re.IGNORECASE)
                if labelled_match:
                    pmid = labelled_match.group(1)
            if pmid:
                pubmed_result = self._search_pubmed_by_id(pmid)
                if pubmed_result:
                    return {
                        "id": raw_entry["id"],
                        "raw_text": raw_entry["raw_text"],
                        "doi": pubmed_result.get("doi"),
                        "arxiv_id": None,
                        "url": pubmed_result.get("url"),
                        "metadata": pubmed_result,
                        "status": "identified",
                    }
                # A PMID is an identifier claim, not ambiguous text: the
                # lookup returning nothing means a nonexistent PMID or an
                # unavailable source, not a case for `onecite suggest`.
                identified_entry["failure_reason"] = "pmid_unresolved"
                self.logger.warning(f"Entry {raw_entry['id']}: PMID {pmid} lookup found nothing")
                return identified_entry

            if re.search(r"isbn[:\s]*[\d\-xX]{10,17}", query_string, re.IGNORECASE):
                books_results = self._search_google_books(query_string)
                if books_results:
                    book_result = books_results[0]
                    return {
                        "id": raw_entry["id"],
                        "raw_text": raw_entry["raw_text"],
                        "doi": book_result.get("doi"),
                        "arxiv_id": None,
                        "url": book_result.get("url"),
                        "metadata": book_result,
                        "status": "identified",
                    }
                identified_entry["failure_reason"] = "isbn_unresolved"
                self.logger.warning(f"Entry {raw_entry['id']}: ISBN lookup found nothing")
                return identified_entry

            identified_entry.setdefault("failure_reason", "no_strong_identifier")
            self.logger.info(
                "Entry %s has no strong identifier; use `onecite suggest` for candidates.",
                raw_entry["id"],
            )
            return identified_entry

        identified_entry.setdefault(
            "failure_reason",
            "url_unresolved" if identified_entry.get("url") else "no_strong_identifier",
        )
        self.logger.warning(f"Entry {raw_entry['id']} identification failed")
        return identified_entry

    def _validate_doi(self, doi: str) -> bool:
        """Validate DOI format"""
        doi_pattern = r"^10\.\d{4,}/.+"
        return bool(re.match(doi_pattern, doi))

    @staticmethod
    def _normalize_doi_identity(value: Any) -> Optional[str]:
        """Return a DOI identity suitable for exact registry-response checks.

        DOI names are case-insensitive.  Registry metadata may also express
        the same name with the conventional ``doi:`` label or DOI resolver
        URL, so those presentation wrappers are removed before comparison.
        """
        if not isinstance(value, str):
            return None

        normalized = unquote(value.strip())
        previous = None
        while normalized and normalized != previous:
            previous = normalized
            normalized = re.sub(r"^doi\s*:\s*", "", normalized, count=1, flags=re.I)
            normalized = re.sub(
                r"^https?://(?:dx\.)?doi\.org/", "", normalized, count=1, flags=re.I
            )
            normalized = normalized.strip()

        return normalized.casefold() or None

    @classmethod
    def _doi_response_matches(cls, requested: Any, *returned: Any) -> bool:
        """Whether every DOI identity present in a response matches the request."""
        requested_identity = cls._normalize_doi_identity(requested)
        returned_identities = [
            identity
            for identity in (cls._normalize_doi_identity(value) for value in returned)
            if identity is not None
        ]
        return bool(
            requested_identity
            and returned_identities
            and all(identity == requested_identity for identity in returned_identities)
        )

    def _validated_zenodo_response_identity(
        self,
        requested_doi: str,
        requested_record_id: str,
        data: Any,
    ) -> Optional[tuple[str, str, Optional[str], str, Optional[str]]]:
        """Validate the allowed Zenodo version/concept DOI relationship.

        A published-record response is accepted only when its version ``doi``
        suffix equals the official DOI ID derived from its numeric ``id``,
        including Zenodo's pinned nine-record 2013 legacy map.  When concept
        identity is present, ``conceptdoi`` and ``conceptrecid`` must both be
        present and obey the same rule.  The requested DOI must then match
        exactly one of those two response-derived identities.  Missing,
        malformed, mismatched, or ambiguous identities fail closed.

        The returned tuple keeps the matched DOI, version DOI, concept DOI,
        version-record ID, and concept-record ID separate.
        """
        if not isinstance(data, dict):
            self.logger.warning("Zenodo returned a non-object record response; rejecting response")
            return None

        returned_record_id = data.get("id")
        if (
            isinstance(returned_record_id, bool)
            or not isinstance(returned_record_id, (int, str))
            or not re.fullmatch(r"\d+", str(returned_record_id).strip())
        ):
            self.logger.warning(
                "Zenodo returned invalid record ID %r for requested DOI record ID %r; "
                "rejecting response",
                returned_record_id,
                requested_record_id,
            )
            return None
        returned_record_identity = str(int(str(returned_record_id).strip()))
        expected_version_doi_id = _ZENODO_RECORD_ID_TO_LEGACY_DOI_ID.get(
            int(returned_record_identity),
            int(returned_record_identity),
        )

        requested_identity = self._normalize_doi_identity(requested_doi)
        version_doi = self._normalize_doi_identity(data.get("doi"))
        concept_raw = data.get("conceptdoi")
        concept_doi = self._normalize_doi_identity(concept_raw)
        concept_record_raw = data.get("conceptrecid")
        zenodo_doi_pattern = r"10\.5281/zenodo\.(\d+)"

        version_match = (
            re.fullmatch(zenodo_doi_pattern, version_doi, re.IGNORECASE) if version_doi else None
        )
        if not version_match or int(version_match.group(1)) != expected_version_doi_id:
            self.logger.warning(
                "Zenodo response record ID %r and version DOI %r do not identify the same "
                "record; rejecting response",
                returned_record_identity,
                version_doi,
            )
            return None
        assert version_doi is not None

        has_concept_doi = concept_raw not in (None, "")
        has_concept_record_id = concept_record_raw not in (None, "")
        if has_concept_doi != has_concept_record_id:
            self.logger.warning(
                "Zenodo response for record %s has only one of conceptdoi/conceptrecid; "
                "rejecting response",
                returned_record_identity,
            )
            return None

        concept_record_identity: Optional[str] = None
        if has_concept_doi:
            concept_match = (
                re.fullmatch(zenodo_doi_pattern, concept_doi, re.IGNORECASE)
                if concept_doi
                else None
            )
            if (
                isinstance(concept_record_raw, bool)
                or not isinstance(concept_record_raw, (int, str))
                or not re.fullmatch(r"\d+", str(concept_record_raw).strip())
            ):
                self.logger.warning(
                    "Zenodo response for record %s has invalid conceptrecid %r; "
                    "rejecting response",
                    returned_record_identity,
                    concept_record_raw,
                )
                return None
            concept_record_identity = str(int(str(concept_record_raw).strip()))
            expected_concept_doi_id = _ZENODO_RECORD_ID_TO_LEGACY_DOI_ID.get(
                int(concept_record_identity),
                int(concept_record_identity),
            )
            if not concept_match or int(concept_match.group(1)) != expected_concept_doi_id:
                self.logger.warning(
                    "Zenodo response conceptrecid %r and concept DOI %r do not identify the "
                    "same concept; rejecting response",
                    concept_record_identity,
                    concept_doi,
                )
                return None
        elif concept_doi is not None:
            self.logger.warning(
                "Zenodo response for record %s has malformed concept DOI %r; rejecting response",
                returned_record_identity,
                concept_raw,
            )
            return None

        matches_version = requested_identity == version_doi
        matches_concept = requested_identity == concept_doi
        if matches_version == matches_concept:
            self.logger.warning(
                "Zenodo returned version/concept DOI identities %r/%r for requested DOI %r; "
                "rejecting response",
                version_doi,
                concept_doi,
                requested_doi,
            )
            return None

        requested_numeric_identity = str(int(requested_record_id))
        expected_doi_identity = (
            str(expected_version_doi_id)
            if matches_version
            else str(
                _ZENODO_RECORD_ID_TO_LEGACY_DOI_ID.get(
                    int(concept_record_identity or ""),
                    int(concept_record_identity or ""),
                )
            )
        )
        if expected_doi_identity != requested_numeric_identity:
            self.logger.warning(
                "Zenodo requested DOI record ID %r does not match the response-derived "
                "version/concept DOI record ID %r; rejecting response",
                requested_numeric_identity,
                expected_doi_identity,
            )
            return None

        matched_doi = version_doi if matches_version else concept_doi
        if matched_doi is None:  # Defensive: the exclusive match above proves this cannot occur.
            return None
        return (
            matched_doi,
            version_doi,
            concept_doi,
            returned_record_identity,
            concept_record_identity,
        )

    def _verify_doi_and_get_metadata(self, doi: str) -> "tuple[Optional[Dict], Optional[str]]":
        """Verify DOI exists in Crossref or DataCite and get real metadata.

        Returns:
            ``(metadata, None)`` on success, or ``(None, failure_reason)``
            where ``failure_reason`` distinguishes a DOI that both registries
            report as unknown (``"doi_not_found"`` — fabricated or mistyped)
            from a lookup that errored (``"source_error"`` — retryable).
        """
        # Try CrossRef first (covers most academic journals/papers)
        try:
            url = f"{self.crossref_base_url}/{doi}"
            params: Dict[str, Any] = {"mailto": self._crossref_mailto}
            response = requests.get(url, headers=self._crossref_headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            work = data.get("message", {})
            returned_doi = work.get("DOI")
            if not self._doi_response_matches(doi, returned_doi):
                self.logger.error(
                    "CrossRef returned DOI %r for requested DOI %r; rejecting response",
                    returned_doi,
                    doi,
                )
                return None, "source_error"

            real_metadata = {
                "source": "crossref_verification",
                "doi": self._normalize_doi_identity(returned_doi),
                "title": work.get("title", [""])[0] if work.get("title") else "",
                "authors": [
                    f"{a.get('given', '')} {a.get('family', '')}" for a in work.get("author", [])
                ],
                "year": _safe_year(work.get("published-print"))
                or _safe_year(work.get("published-online")),
                "journal": (
                    work.get("container-title", [""])[0] if work.get("container-title") else ""
                ),
                "volume": work.get("volume"),
                "number": work.get("issue"),
                "pages": work.get("page"),
                "publisher": work.get("publisher"),
                "citations": work.get("is-referenced-by-count", 0),
                "url": work.get("URL"),
                # The raw work object lets the enricher reuse this response
                # instead of fetching the same DOI from CrossRef again.
                # Underscore-prefixed fields are stripped from public output.
                "_crossref_work": work,
            }

            self.logger.info(f"DOI {doi} resolved successfully in Crossref")
            return real_metadata, None

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self.logger.warning(f"DOI {doi} not found in CrossRef (404)")
                # A CrossRef 404 only means the DOI is not registered with
                # CrossRef. Many valid DOIs (datasets, software, theses,
                # preprints) are DataCite-registered under prefixes far beyond
                # any short hardcoded list, so always fall back to DataCite
                # rather than guessing eligibility from the prefix.
                self.logger.info(f"DOI {doi} not in CrossRef, trying DataCite API...")
                datacite_result = self._query_datacite(doi)
                if datacite_result:
                    return datacite_result, None
                return None, "doi_not_found"
            else:
                self.logger.error(f"HTTP error verifying DOI {doi}: {str(e)}")
                return None, "source_error"
        except Exception as e:
            self.logger.error(f"Failed to verify DOI {doi}: {str(e)}")
            return None, "source_error"

    # Below this similarity score, the descriptive text around a resolved DOI
    # is considered to describe a different work than the DOI's metadata.
    TEXT_METADATA_MISMATCH_THRESHOLD = 45

    def _check_text_metadata_mismatch(
        self, raw_text: str, doi: str, metadata: Dict
    ) -> Optional[Dict]:
        """Detect input text that describes a different work than its DOI.

        This never blocks resolution — the DOI remains the authority. It only
        flags entries where the descriptive text accompanying a resolved DOI
        (title words, authors) clearly disagrees with the canonical metadata,
        which is the typical shape of a hallucinated citation: a real DOI
        paired with the wrong paper.

        Returns:
            A warning dict for the entry report, or ``None`` when the text is
            consistent with the metadata or carries too little descriptive
            signal to compare (e.g. a bare DOI).
        """
        title = (metadata.get("title") or "").strip()
        if not title:
            return None

        residual = raw_text.replace(doi, " ")
        residual = re.sub(r"https?://\S+", " ", residual)
        residual = re.sub(r"\b(?:doi|pmid|arxiv|isbn)\b\s*[:=]?", " ", residual, flags=re.I)
        residual = " ".join(re.sub(r"[^\w\s]", " ", residual).split())

        # A year cited far from the resolved metadata's year is independent
        # contradictory evidence.  Compute it before the short-text gate so a
        # concise author/journal/year citation cannot silently pass merely
        # because it lacks a title.
        year_conflict = False
        input_year_match = re.search(r"\b(19|20)\d{2}\b", residual)
        input_year = input_year_match.group(0) if input_year_match else None
        metadata_year = metadata.get("year")
        if input_year and metadata_year:
            try:
                year_conflict = abs(int(input_year) - int(metadata_year)) > 5
            except (ValueError, TypeError):
                pass

        # Journal names, volume/page numbers, and years carry no title signal;
        # require enough descriptive words for a meaningful comparison unless
        # the independently observed year is already contradictory.
        descriptive_words = [w for w in residual.split() if len(w) >= 3 and not w.isdigit()]
        if len(descriptive_words) < 4 and not year_conflict:
            return None

        residual_lower = residual.lower()
        authors = " ".join(metadata.get("authors") or [])
        canonical = f"{title} {authors} {metadata.get('journal') or ''}".lower()
        score = max(
            fuzz.token_set_ratio(residual_lower, title.lower()),
            fuzz.partial_ratio(residual_lower, title.lower()),
            fuzz.token_set_ratio(residual_lower, canonical),
        )

        # Character-level fuzz alone is not evidence that the text describes
        # this work — short titles ("Deep learning") let a single generic
        # word inflate the ratios. Require *positive* overlap: the text must
        # contain most of the title's words, or most of the authors' family
        # names. The independently computed year conflict raises the bar.

        residual_tokens = {token.lower() for token in residual.split()}
        title_tokens = {
            token for token in re.sub(r"[^\w\s]", " ", title.lower()).split() if len(token) >= 3
        }
        title_coverage = (
            len(title_tokens & residual_tokens) / len(title_tokens) if title_tokens else 0.0
        )
        family_names = {
            name.split()[-1].lower()
            for name in (metadata.get("authors") or [])
            if name.split() and len(name.split()[-1]) >= 3
        }
        author_coverage = (
            len(family_names & residual_tokens) / len(family_names) if family_names else 0.0
        )
        evidence = max(title_coverage, author_coverage)

        # Sparse references often omit the title and abbreviate the journal.
        # In that shape, exact bibliographic coordinates plus substantial
        # author agreement are stronger positive evidence than title fuzz.
        # Requiring year, volume, first page, and at least half of the family
        # names keeps this exception narrow enough not to mask a wrong-work
        # pairing that merely shares a publication year.
        metadata_volume = str(metadata.get("volume") or "").lower()
        metadata_pages = str(metadata.get("pages") or "")
        first_page_match = re.search(r"\d+", metadata_pages)
        first_page = first_page_match.group(0) if first_page_match else None
        coordinate_consistent = (
            bool(input_year)
            and bool(metadata_year)
            and input_year == str(metadata_year)
            and bool(metadata_volume)
            and metadata_volume in residual_tokens
            and first_page is not None
            and first_page in residual_tokens
            and author_coverage >= 0.5
        )
        if coordinate_consistent:
            return None

        required_evidence = 0.8 if year_conflict else 0.6
        consistent = score >= self.TEXT_METADATA_MISMATCH_THRESHOLD and (
            evidence >= required_evidence
        )
        if consistent:
            return None

        return {
            "type": "text_metadata_mismatch",
            "message": (
                "Input text does not appear to describe the work this DOI "
                "resolves to; the entry was resolved from the DOI, but the "
                "original text may cite a different work — review it."
            ),
            "similarity": score,
            "year_conflict": year_conflict,
            "input_text": raw_text.strip()[:200],
            "resolved_title": title,
            "resolved_doi": metadata.get("doi") or doi,
        }

    def _extract_github_info(self, text: str) -> Optional[Dict]:
        """Extract GitHub repository information"""
        try:
            # Match GitHub URLs
            github_pattern = r"github\.com/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)"
            match = re.search(github_pattern, text, re.IGNORECASE)

            if match:
                owner = match.group(1)
                repo = match.group(2)
                # Drop a trailing ".git" (clone URLs) and any trailing
                # punctuation so the API call targets the real repo
                # (e.g. ".../repo.git" -> "repo").
                repo = re.sub(r"\.git$", "", repo)
                repo = re.sub(r"[^a-zA-Z0-9_.-].*$", "", repo)

                url = f"{self.github_api_base}/repos/{owner}/{repo}"
                headers = {
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": self._user_agent,
                }

                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    version = None
                    try:
                        tags_url = f"{self.github_api_base}/repos/{owner}/{repo}/tags"
                        tags_response = requests.get(tags_url, headers=headers, timeout=5)
                        if tags_response.status_code == 200:
                            tags = tags_response.json()
                            if tags and len(tags) > 0:
                                version = tags[0].get("name", "").lstrip("v")
                    except Exception:
                        pass

                    return {
                        "source": "github",
                        "type": "software",
                        "is_software": True,
                        "repo": f"{owner}/{repo}",
                        "title": data.get("name", repo),
                        "description": data.get("description", ""),
                        "authors": [data.get("owner", {}).get("login", owner)],
                        "year": data.get("created_at", "")[:4] if data.get("created_at") else None,
                        "url": data.get("html_url", ""),
                        "version": version,
                        "publisher": "GitHub",
                        "language": data.get("language", ""),
                        "stars": data.get("stargazers_count", 0),
                    }

        except Exception as e:
            self.logger.warning(f"Failed to extract GitHub info: {str(e)}")

        return None

    def _extract_zenodo_info(self, text: str) -> Optional[Dict]:
        """Extract Zenodo/Figshare dataset information"""
        try:
            zenodo_pattern = r"10\.5281/zenodo\.(\d+)"
            match = re.search(zenodo_pattern, text, re.IGNORECASE)

            if match:
                zenodo_id = match.group(1)
                requested_doi = match.group(0)
                zenodo_record_id = _ZENODO_LEGACY_DOI_ID_TO_RECORD_ID.get(
                    int(zenodo_id),
                    int(zenodo_id),
                )

                url = f"{self.zenodo_api_base}/{zenodo_record_id}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    response_identity = self._validated_zenodo_response_identity(
                        requested_doi,
                        zenodo_id,
                        data,
                    )
                    if response_identity is None:
                        return None
                    (
                        matched_doi,
                        version_doi,
                        concept_doi,
                        returned_record_id,
                        concept_record_id,
                    ) = response_identity
                    metadata = data.get("metadata", {})
                    resource_type = metadata.get("resource_type", {}).get("type", "dataset")
                    normalized_resource_type = str(resource_type).strip().casefold()
                    is_software = normalized_resource_type == "software"
                    is_dataset = normalized_resource_type == "dataset"
                    output_type = (
                        "software"
                        if is_software
                        else "dataset" if is_dataset else normalized_resource_type or "misc"
                    )

                    return {
                        "source": "zenodo",
                        "type": output_type,
                        "is_software": is_software,
                        "is_dataset": is_dataset,
                        "doi": matched_doi,
                        "version_doi": version_doi,
                        "concept_doi": concept_doi,
                        "record_id": returned_record_id,
                        "concept_record_id": concept_record_id,
                        "title": metadata.get("title", ""),
                        "authors": [
                            creator.get("name", "") for creator in metadata.get("creators", [])
                        ],
                        "year": (
                            metadata.get("publication_date", "")[:4]
                            if metadata.get("publication_date")
                            else None
                        ),
                        "publisher": "Zenodo",
                        "url": f"https://zenodo.org/record/{returned_record_id}",
                        "version": metadata.get("version", ""),
                        "resource_type": resource_type,
                    }

            figshare_pattern = r"10\.6084/m9\.figshare\.(\d+)"
            match = re.search(figshare_pattern, text)

            if match:
                doi = match.group(0)
                return {
                    "source": "figshare",
                    "type": "dataset",
                    "is_dataset": True,
                    "doi": doi,
                    "publisher": "Figshare",
                    "url": f"https://doi.org/{doi}",
                }

            # DataCite DOIs often start with specific prefixes
            datacite_patterns = [
                r"10\.5061/",  # Dryad
                r"10\.6078/",  # DataONE
                r"10\.7910/",  # DVN/Dataverse
            ]

            for pattern in datacite_patterns:
                match = re.search(pattern + r"[^\s,}]+", text)
                if match:
                    doi = match.group(0)
                    datacite_info = self._query_datacite(doi)
                    if datacite_info:
                        return datacite_info

        except Exception as e:
            self.logger.warning(f"Failed to extract Zenodo/dataset info: {str(e)}")

        return None

    def _query_datacite(self, doi: str) -> Optional[Dict]:
        """Query DataCite API for dataset metadata"""
        try:
            url = f"{self.datacite_base}/dois/{doi}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                data_record = data.get("data", {})
                attributes = data_record.get("attributes", {})
                returned_id = data_record.get("id")
                returned_attribute_doi = attributes.get("doi")
                if not self._doi_response_matches(doi, returned_id, returned_attribute_doi):
                    self.logger.warning(
                        "DataCite returned DOI identities %r/%r for requested DOI %r; "
                        "rejecting response",
                        returned_id,
                        returned_attribute_doi,
                        doi,
                    )
                    return None

                creators = attributes.get("creators", [])
                authors = [c.get("name", "") for c in creators if c.get("name")]

                pub_year = attributes.get("publicationYear")

                return {
                    "source": "datacite",
                    "type": "dataset",
                    "is_dataset": True,
                    "doi": self._normalize_doi_identity(doi),
                    "title": (
                        attributes.get("titles", [{}])[0].get("title", "")
                        if attributes.get("titles")
                        else ""
                    ),
                    "authors": authors,
                    "year": pub_year,
                    "publisher": attributes.get("publisher", "DataCite"),
                    "url": attributes.get("url", f"https://doi.org/{doi}"),
                    "resource_type": attributes.get("types", {}).get(
                        "resourceTypeGeneral", "Dataset"
                    ),
                }

        except Exception as e:
            self.logger.warning(f"DataCite query failed for {doi}: {str(e)}")

        return None

    def _detect_thesis(self, text: str) -> Optional[Dict]:
        """Detect and search for thesis/dissertation"""
        try:
            text_lower = text.lower()

            thesis_keywords = [
                "phd thesis",
                "ph.d. thesis",
                "doctoral thesis",
                "dissertation",
                "master thesis",
                "master's thesis",
                "msc thesis",
                "m.s. thesis",
            ]

            is_thesis = any(keyword in text_lower for keyword in thesis_keywords)

            if not is_thesis:
                return None

            # Determine thesis type
            is_phd = any(kw in text_lower for kw in ["phd", "ph.d.", "doctoral", "dissertation"])
            thesis_type = "phdthesis" if is_phd else "mastersthesis"

            # Pattern: Author (Year). Title. Type. University.
            author_match = re.match(r"^([^(]+?)\s*\(", text)
            author = author_match.group(1).strip() if author_match else None

            year_match = re.search(r"\((\d{4})\)", text)
            year = int(year_match.group(1)) if year_match else None

            title = None
            title_pattern = r"\(\d{4}\)\.\s*(.+?)\.\s*(?:PhD|Ph\.D\.|Master|Doctoral|Dissertation)"
            title_match = re.search(title_pattern, text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
            else:
                # Fallback: extract text after year
                parts = text.split(")")
                if len(parts) > 1:
                    rest = parts[1].strip().lstrip(".")
                    # Take text before thesis keyword
                    for keyword in thesis_keywords:
                        if keyword in rest.lower():
                            title = rest.split(keyword)[0].strip().rstrip(".")
                            break
                    if not title:
                        title = rest.split(".")[0].strip()

            # Try to extract university/school
            university_patterns = [
                r"(?:PhD|Ph\.D\.|Master|Doctoral|Dissertation).*?([A-Z][^.]*?University[^.]*?)\.?\s*$",
                r"([A-Z][^.]*?University[^.]*?)\.?\s*$",
            ]

            school = None
            for pattern in university_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    school = match.group(1).strip().rstrip(".")
                    break

            if title and len(title) > 10:
                # Try external providerRE first (better for European theses)
                openaire_metadata = self._search_openaire_for_thesis(title, year)
                if openaire_metadata:
                    openaire_metadata["thesis_type"] = thesis_type
                    openaire_metadata["is_thesis"] = True
                    if author:
                        openaire_metadata["authors"] = [author]
                    if school:
                        openaire_metadata["school"] = school
                    return openaire_metadata

                # Fallback to BASE
                base_metadata = self._search_base_for_thesis(title, year)
                if base_metadata:
                    base_metadata["thesis_type"] = thesis_type
                    base_metadata["is_thesis"] = True
                    if author:
                        base_metadata["authors"] = [author]
                    if school:
                        base_metadata["school"] = school
                    return base_metadata

            # Fallback: create basic metadata from extraction (only if we have a title)
            if not title:
                return None
            result = {
                "source": "manual",
                "type": thesis_type,
                "is_thesis": True,
                "thesis_type": thesis_type,
                "title": title,
                "authors": [author] if author else [],
                "year": year,
            }
            if school:
                result["school"] = school
            return result

        except Exception as e:
            self.logger.warning(f"Failed to detect thesis: {str(e)}")

        return None

    def _search_base_for_thesis(self, query: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search BASE (Bielefeld Academic Search Engine) for thesis"""
        try:
            # Clean query
            query_clean = re.sub(
                r"\b(phd|ph\.d\.|thesis|dissertation)\b", "", query, flags=re.IGNORECASE
            ).strip()

            base_query = f"dccoll:ftthesis {query_clean}"
            if year:
                base_query += f" dcyear:{year}"

            params: Dict[str, Any] = {
                "func": "PerformSearch",
                "query": base_query,
                "hits": 3,
                "format": "json",
            }

            response = self._get_with_retry(
                self.base_search_url,
                source_name="BASE",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )

            if response.status_code == 429:
                self._record_source_status("base_search", "rate_limited")
                return None
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                self._record_source_status("base_search", "ok")

                if docs:
                    doc = docs[0]

                    authors = doc.get("dcauthor", [])
                    if isinstance(authors, str):
                        authors = [authors]

                    return {
                        "source": "base_search",
                        "title": (
                            doc.get("dctitle", [""])[0]
                            if isinstance(doc.get("dctitle"), list)
                            else doc.get("dctitle", "")
                        ),
                        "authors": authors,
                        "year": (
                            doc.get("dcyear", [""])[0]
                            if isinstance(doc.get("dcyear"), list)
                            else doc.get("dcyear")
                        ),
                        "school": (
                            doc.get("dccreator", [""])[0]
                            if isinstance(doc.get("dccreator"), list)
                            else doc.get("dccreator", "Unknown")
                        ),
                        "url": (
                            doc.get("dclink", [""])[0]
                            if isinstance(doc.get("dclink"), list)
                            else doc.get("dclink", "")
                        ),
                        "type": "thesis",
                    }

        except Exception as e:
            self.logger.warning(f"BASE search for thesis failed: {str(e)}")
            self._record_source_status("base_search", "error")

        return None

    def _search_openaire_for_thesis(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search external providerRE for thesis/dissertation"""
        try:
            query = f'"{title}"'
            if year:
                query += f' AND yearofacceptance exact "{year}"'

            params: Dict[str, Any] = {
                "title": title,
                "format": "json",
                "size": 3,
                "type": "publications",
                "publicationtype": "Bachelor thesis OR Master thesis OR Doctoral thesis",
            }

            response = self._get_with_retry(
                self.openaire_api_base,
                source_name="OpenAIRE",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )

            if response.status_code == 429:
                self._record_source_status("openaire", "rate_limited")
                return None
            response.raise_for_status()

            if response.status_code == 200:
                data = response.json()
                results = data.get("response", {}).get("results", {}).get("result", [])
                self._record_source_status("openaire", "ok")

                if results:
                    # Take first result
                    result = results[0] if isinstance(results, list) else results
                    metadata_elem = (
                        result.get("metadata", {}).get("oaf:entity", {}).get("oaf:result", {})
                    )

                    title_elem = metadata_elem.get("title", {})
                    if isinstance(title_elem, list):
                        title_text = title_elem[0].get("$", "") if title_elem else ""
                    else:
                        title_text = title_elem.get("$", "")

                    creators = metadata_elem.get("creator", [])
                    if not isinstance(creators, list):
                        creators = [creators]
                    authors = [
                        c.get("$", "") if isinstance(c, dict) else str(c) for c in creators if c
                    ]

                    year_elem = metadata_elem.get("dateofacceptance", {})
                    year_text = (
                        year_elem.get("$", "")[:4]
                        if isinstance(year_elem, dict) and year_elem.get("$")
                        else None
                    )

                    # Extract publisher (university)
                    publisher_elem = metadata_elem.get("publisher", {})
                    publisher = (
                        publisher_elem.get("$", "Unknown University")
                        if isinstance(publisher_elem, dict)
                        else str(publisher_elem)
                    )

                    url = None
                    children = (
                        result.get("metadata", {})
                        .get("oaf:entity", {})
                        .get("oaf:result", {})
                        .get("children", {})
                    )
                    instances = children.get("instance", [])
                    if not isinstance(instances, list):
                        instances = [instances]
                    for instance in instances:
                        if isinstance(instance, dict) and instance.get("webresource"):
                            webres = instance["webresource"]
                            if isinstance(webres, list):
                                url = webres[0].get("url", {}).get("$", "")
                            else:
                                url = webres.get("url", {}).get("$", "")
                            if url:
                                break

                    if title_text:
                        return {
                            "source": "openaire",
                            "title": title_text,
                            "authors": authors,
                            "year": year_text,
                            "school": publisher,
                            "url": url or "",
                            "type": "thesis",
                        }

        except Exception as e:
            self.logger.warning(f"external providerRE search for thesis failed: {str(e)}")
            self._record_source_status("openaire", "error")

        return None

    def _search_pubmed_by_id(self, pmid: str) -> Optional[Dict]:
        """Search PubMed by PMID"""
        try:
            url = f"{self.pubmed_base}/esummary.fcgi"
            params: Dict[str, Any] = {"db": "pubmed", "id": pmid, "retmode": "json"}

            response = self._get_with_retry(
                url,
                source_name="PubMed summary",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )
            if response.status_code == 429:
                self._record_source_status("pubmed", "rate_limited")
                return None
            response.raise_for_status()

            data = response.json()
            result = data.get("result", {}).get(pmid, {})
            self._record_source_status("pubmed", "ok")

            if result and result.get("title"):
                doi = None
                article_ids = result.get("articleids", [])
                for aid in article_ids:
                    if aid.get("idtype") == "doi":
                        doi = aid.get("value")
                        break

                authors = []
                for author in result.get("authors", []):
                    name = author.get("name", "")
                    if name:
                        authors.append(name)

                return {
                    "source": "pubmed",
                    "type": "article",
                    "pmid": pmid,
                    "doi": doi,
                    "title": result.get("title", ""),
                    "authors": authors,
                    "journal": result.get("fulljournalname", result.get("source", "")),
                    "year": result.get("pubdate", "")[:4] if result.get("pubdate") else None,
                    "volume": result.get("volume"),
                    "issue": result.get("issue"),
                    "pages": result.get("pages"),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }

        except Exception as e:
            self.logger.warning(f"PubMed ID search failed: {str(e)}")
            self._record_source_status("pubmed", "error")

        return None

    def _search_pubmed(self, query: str, limit: int = 5) -> List[Dict]:
        """Search PubMed for medical literature"""
        try:
            # First, search for PMIDs
            search_url = f"{self.pubmed_base}/esearch.fcgi"
            params: Dict[str, Any] = {
                "db": "pubmed",
                "term": query,
                "retmax": limit,
                "retmode": "json",
            }

            response = self._get_with_retry(
                search_url,
                source_name="PubMed search",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )
            if response.status_code == 429:
                self._record_source_status("pubmed", "rate_limited")
                return []
            response.raise_for_status()

            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            self._record_source_status("pubmed", "ok")

            if not pmids:
                return []

            results = []
            for pmid in pmids:
                result = self._search_pubmed_by_id(pmid)
                if result:
                    results.append(result)

            self.logger.info(f"PubMed search returned {len(results)} results")
            return results

        except Exception as e:
            self.logger.warning(f"PubMed search failed: {str(e)}")
            self._record_source_status("pubmed", "error")
            return []

    def _search_arxiv_candidates(self, query: str, limit: int = 5) -> List[Dict]:
        """Search the arXiv API for suggestion candidates.

        arXiv covers the CS/ML venues that CrossRef does not index (e.g.
        NeurIPS/ICML papers), so it fills a real coverage gap in suggest.
        """
        try:
            import feedparser

            # Citations usually lead with the title ("Title, Authors, Venue
            # Year"), so search the title field on the segment before the
            # first comma — requiring author/venue words in the full text is
            # what makes naive queries miss the paper. Years, punctuation,
            # and short noise words ("et", "al") carry no title signal.
            title_guess = query.split(",")[0]
            terms = [
                word
                for word in re.sub(r"[^\w\s]", " ", title_guess).split()
                if len(word) >= 3 and not re.fullmatch(r"(19|20)\d{2}", word)
            ]
            if not terms:
                self._record_source_status("arxiv", "ok")
                return []
            params: Dict[str, Any] = {
                "search_query": " AND ".join(f"ti:{term}" for term in terms[:6]),
                "max_results": limit,
            }
            # https directly — the http endpoint 301-redirects, wasting a
            # round-trip per query. arXiv rate-limits aggressively but the
            # 429s are short-lived, so back off briefly instead of failing
            # the source outright.
            response = self._get_with_retry(
                "https://export.arxiv.org/api/query",
                source_name="arXiv",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )
            if response is None:
                self._record_source_status("arxiv", "error")
                return []
            if response.status_code == 429:
                # Still throttled after backoff: disclose the truth — the
                # source was rate-limited, not broken.
                self.logger.warning("arXiv still rate-limited after retries")
                self._record_source_status("arxiv", "rate_limited")
                return []
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            results = []
            for entry in feed.entries:
                arxiv_url = entry.get("id", "")
                arxiv_match = re.search(r"abs/(\d{4}\.\d{4,5})", arxiv_url)
                arxiv_id = arxiv_match.group(1) if arxiv_match else None
                published = entry.get("published", "")
                year = None
                if len(published) >= 4 and published[:4].isdigit():
                    year = int(published[:4])
                authors = [
                    author.get("name", "")
                    for author in entry.get("authors", [])
                    if author.get("name")
                ]
                doi = entry.get("arxiv_doi") or None
                title = entry.get("title", "").replace("\n", " ").strip()
                if not title or not authors:
                    continue
                results.append(
                    {
                        "source": "arxiv",
                        "doi": doi,
                        "arxiv_id": arxiv_id,
                        "title": title,
                        "authors": authors,
                        "year": year,
                        "journal": "arXiv",
                        "citations": 0,
                        "type": "article",
                        "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else arxiv_url,
                    }
                )

            self.logger.info(f"arXiv search returned {len(results)} results")
            self._record_source_status("arxiv", "ok")
            return results
        except Exception as e:
            self.logger.warning(f"arXiv search failed: {str(e)}")
            self._record_source_status("arxiv", "error")
            return []

    def _search_semantic_scholar(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Semantic Scholar for academic papers"""
        try:
            url = f"{self.semantic_scholar_base}/paper/search"
            params: Dict[str, Any] = {
                "query": query,
                "limit": limit,
                "fields": "title,authors,year,venue,citationCount,publicationDate,externalIds,journal,url,abstract",
            }

            # Unauthenticated Semantic Scholar shares an aggressive global
            # rate limit; apply the frozen suggestion-source retry policy.
            response = self._get_with_retry(
                url,
                source_name="Semantic Scholar",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )

            if response.status_code == 429:
                self.logger.warning(
                    "Semantic Scholar rate-limited (429); candidates from this "
                    "source are missing for this query."
                )
                self._record_source_status("semantic_scholar", "rate_limited")
                return []

            if response.status_code == 200:
                data = response.json()
                papers = data.get("data", [])

                results = []
                for paper in papers:
                    external_ids = paper.get("externalIds") or {}
                    doi = external_ids.get("DOI") if external_ids else None
                    arxiv_id = external_ids.get("ArXiv") if external_ids else None

                    authors = []
                    author_list = paper.get("authors") or []
                    for author in author_list:
                        if author and isinstance(author, dict):
                            name = author.get("name", "")
                            if name:
                                authors.append(name)

                    venue = paper.get("venue") or ""
                    if not venue:
                        journal_obj = paper.get("journal")
                        if journal_obj and isinstance(journal_obj, dict):
                            venue = journal_obj.get("name", "")

                    paper_url = paper.get("url")
                    if not paper_url and paper.get("paperId"):
                        paper_url = f"https://www.semanticscholar.org/paper/{paper.get('paperId')}"

                    result = {
                        "source": "semantic_scholar",
                        "doi": doi,
                        "arxiv_id": arxiv_id,
                        "title": paper.get("title", ""),
                        "authors": authors,
                        "year": paper.get("year"),
                        "journal": venue,
                        "citations": paper.get("citationCount", 0),
                        "url": paper_url,
                        "abstract": paper.get("abstract"),
                        "type": "article",
                    }

                    if result["title"] and result["authors"]:
                        results.append(result)

                self.logger.info(f"Semantic Scholar search returned {len(results)} results")
                self._record_source_status("semantic_scholar", "ok")
                return results
            else:
                self.logger.warning(f"Semantic Scholar returned status code {response.status_code}")
                self._record_source_status("semantic_scholar", "error")
                return []

        except Exception as e:
            self.logger.warning(f"Semantic Scholar search failed: {str(e)}")
            self._record_source_status("semantic_scholar", "error")
            return []

    def _extract_arxiv_id(self, text: str) -> Optional[str]:
        """Extract arXiv ID from text"""
        # Match both old (e.g., 1706.03762) and new (e.g., arxiv:1706.03762) formats
        arxiv_patterns = [
            r"arxiv[:\s]*(\d{4}\.\d{4,5})",  # New format
            r"\b(\d{4}\.\d{4,5})\b",  # Standalone ID
            r"arXiv:(\d{4}\.\d{4,5})",  # With arXiv prefix
        ]

        for pattern in arxiv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_arxiv_id_from_url(self, url: str) -> Optional[str]:
        """Extract arXiv ID from arXiv URL"""
        # Match patterns like https://arxiv.org/abs/1706.03762
        match = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", url)
        if match:
            return match.group(1)
        return None

    def _extract_doi_from_url(self, url: str) -> Optional[str]:
        """Extract DOI from URL page. Prioritize meta tags and avoid extracting DOIs from reference sections."""
        try:
            response = requests.get(
                url, timeout=10, headers={"User-Agent": self._user_agent}, stream=True
            )
            content_len = response.headers.get("content-length")
            if content_len and int(content_len) > 5 * 1024 * 1024:
                self.logger.warning(f"Skipping URL {url}: response too large ({content_len} bytes)")
                return None
            content = response.raw.read(5 * 1024 * 1024)
            soup = BeautifulSoup(content, "html.parser")

            # 1. Look for DOI in meta tags (most reliable)
            doi_meta = (
                soup.find("meta", attrs={"name": "citation_doi"})
                or soup.find("meta", attrs={"name": "dc.identifier"})
                or soup.find("meta", attrs={"property": "citation_doi"})
            )

            if doi_meta and "content" in doi_meta.attrs:
                doi = str(doi_meta["content"])
                if self._validate_doi(doi):
                    self.logger.info(f"Found DOI in meta tags: {doi}")
                    return doi

            # 2. Check schema.org structured data
            script_tags = soup.find_all("script", type="application/ld+json")
            for script in script_tags:
                try:
                    import json

                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    if isinstance(data, dict) and "identifier" in data:
                        identifier = data["identifier"]
                        if isinstance(identifier, str) and self._validate_doi(identifier):
                            self.logger.info(f"Found DOI in structured data: {identifier}")
                            return identifier
                except Exception:
                    pass

            # Body-text DOI scraping was intentionally removed: grabbing the
            # first "10.x/y"-looking string from arbitrary page text is
            # unreliable and can adopt a *cited* paper's DOI. Only a
            # publisher-declared meta tag / schema.org identifier (above) is
            # treated as a strong, verifiable signal.
            self.logger.info(f"No reliable DOI found in URL: {url}")
            return None

        except Exception as e:
            self.logger.warning(f"Failed to extract DOI from URL {url}: {str(e)}")

        return None

    def suggest(self, raw_entry: RawEntry, limit: int = 5, audit_trace: bool = False) -> Dict:
        """Return candidate matches for a raw entry without resolving it.

        ``audit_trace`` is reserved for provenance-locked evaluation runs.  It
        retains private source/scorer positions without changing the ordinary
        CLI or Python response surface.
        """
        query_string = (raw_entry.get("query_string") or raw_entry.get("raw_text") or "").strip()
        suggestion: Dict[str, Any] = {
            "id": raw_entry["id"],
            "raw_text": raw_entry.get("raw_text", ""),
            "query_string": query_string,
            "status": "no_candidates",
            "candidates": [],
            "sources": [],
        }
        if audit_trace:
            suggestion["candidate_trace"] = []
            suggestion["candidate_trace_limit"] = max(limit, 0)
        if not query_string:
            return suggestion

        self._source_status = {}
        candidates = [
            {**candidate, "_collection_rank": rank}
            for rank, candidate in enumerate(
                self._collect_suggestion_candidates(query_string), start=1
            )
        ]
        scored_candidates = self._score_candidates(candidates, query_string) if candidates else []
        suggestion["candidates"] = [
            self._public_candidate(candidate) for candidate in scored_candidates[: max(limit, 0)]
        ]
        # Disclose every source actually consulted. A rate-limited or errored
        # source means the candidate list may be missing the correct match,
        # and the caller must be able to see that.
        candidate_counts: Dict[str, int] = {}
        for candidate in candidates:
            source_name = candidate.get("source", "unknown")
            candidate_counts[source_name] = candidate_counts.get(source_name, 0) + 1
        suggestion["sources"] = [
            {
                "source": source_name,
                "status": status,
                "candidates": candidate_counts.get(source_name, 0),
            }
            for source_name, status in sorted(self._source_status.items())
        ]
        if audit_trace:
            suggestion["candidate_trace"] = [
                {
                    **candidate,
                    "final_rank": rank,
                    "disposition": "selected" if rank <= max(limit, 0) else "below_limit",
                }
                for rank, candidate in enumerate(scored_candidates, start=1)
            ]
        if suggestion["candidates"]:
            suggestion["status"] = "candidates_found"
        if any(item["status"] != "ok" for item in suggestion["sources"]):
            suggestion["status"] = (
                "candidates_found_incomplete"
                if suggestion["candidates"]
                else "no_candidates_incomplete"
            )
        return suggestion

    def _public_candidate(self, candidate: Dict) -> Dict:
        """Remove private scorer fields from suggestion output."""
        return {key: value for key, value in candidate.items() if not key.startswith("_")}

    def _collect_suggestion_candidates(self, query_string: str) -> List[Dict]:
        """Collect possible matches for suggestion-only workflows."""
        query_lower = query_string.lower()
        candidates = []

        self.logger.info("Querying suggestion sources: CrossRef + Semantic Scholar + arXiv")
        crossref_results = self._search_crossref(query_string)
        candidates.extend(crossref_results)

        semantic_results = self._search_semantic_scholar(query_string)
        candidates.extend(semantic_results)

        arxiv_results = self._search_arxiv_candidates(query_string)
        candidates.extend(arxiv_results)

        pmid_match = re.match(r"^(PMID:?\s*)?(\d{7,8})$", query_string.strip(), re.IGNORECASE)
        if pmid_match:
            pubmed_result = self._search_pubmed_by_id(pmid_match.group(2))
            if pubmed_result:
                candidates.append(pubmed_result)

        strong_medical_cues = ["pubmed", "pmid", "clinical trial", "randomized controlled"]
        if any(cue in query_lower for cue in strong_medical_cues):
            candidates.extend(self._search_pubmed(query_string))

        has_isbn = bool(re.search(r"isbn[:\s]*[\d\-xX]{10,17}", query_lower, re.IGNORECASE))
        has_edition = bool(re.search(r"\b\d+(?:st|nd|rd|th)?\s+ed\.?\b", query_lower))
        has_book_publisher = any(
            pub in query_lower
            for pub in ["wiley", "o'reilly", "springer", "cambridge press", "mit press"]
        )
        if has_isbn or has_edition or has_book_publisher:
            candidates.extend(self._search_google_books(query_string))

        # Match whole words only: a bare "thesis"/"dissertation" substring
        # check also fires on "hypothesis", "synthesis", "parenthesis", etc.,
        # routing unrelated queries to thesis search.
        if re.search(r"\b(thesis|dissertation)\b", query_lower):
            thesis_results = self._search_openaire_for_thesis(
                query_string
            ) or self._search_base_for_thesis(query_string)
            if thesis_results:
                candidates.append(thesis_results)

        if self.use_google_scholar and not crossref_results and not semantic_results:
            candidates.extend(self._search_google_scholar(query_string))

        return candidates

    def _search_crossref(self, query: str, limit: int = 15) -> List[Dict]:
        """CrossRef search with query optimization."""
        try:
            # Crossref's bibliographic query is designed for complete or
            # partial citation strings.  Supplying the same unparsed citation
            # simultaneously as a generic query, title, and bibliographic
            # query degrades relevance for author-year and title-less forms.
            base_params: Dict[str, Any] = {
                "rows": limit,
                "sort": "relevance",
                "mailto": "onecite@users.noreply.github.com",
            }

            # Use the task-aligned strategy first, then broader fallbacks only
            # when it does not return enough usable records.
            search_strategies = [
                {**base_params, "query.bibliographic": query},
                {**base_params, "query": query},
                {
                    **base_params,
                    "query.title": query,
                    "query.author": query.split(".")[0] if "." in query else query,
                    "filter": "type:journal-article,proceedings-article,book-chapter,book,monograph",
                },
            ]

            all_results: List[Dict[str, Any]] = []
            seen_dois = set()

            for i, strategy_params in enumerate(search_strategies):
                try:
                    self.logger.debug(f"CrossRef search strategy {i+1}")
                    url = f"{self.crossref_base_url}"
                    response = self._get_with_retry(
                        url,
                        source_name=f"Crossref strategy {i + 1}",
                        max_attempts=SUGGESTION_MAX_ATTEMPTS,
                        fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                        headers=self._crossref_headers,
                        params=strategy_params,
                        timeout=15,
                    )
                    if response.status_code == 429:
                        self.logger.warning("CrossRef remained rate-limited after retries")
                        self._record_source_status("crossref", "rate_limited")
                        break
                    if response.status_code in RETRYABLE_HTTP_STATUSES:
                        self.logger.warning(
                            f"CrossRef remained unavailable with HTTP {response.status_code} "
                            "after retries"
                        )
                        self._record_source_status("crossref", "error")
                        break
                    response.raise_for_status()
                    data = response.json()
                    self._record_source_status("crossref", "ok")

                    for item in data.get("message", {}).get("items", []):
                        doi = item.get("DOI")
                        if not doi or doi in seen_dois:
                            continue

                        # More complete data extraction
                        result = {
                            "source": "crossref",
                            "doi": doi,
                            "title": item.get("title", [""])[0] if item.get("title") else "",
                            "authors": [],
                            "year": None,
                            "journal": "",
                            "citations": item.get("is-referenced-by-count", 0),
                            "type": item.get("type", ""),
                            "url": f"https://doi.org/{doi}",
                            "publisher": item.get("publisher", ""),
                            "volume": item.get("volume", ""),
                            "issue": item.get("issue", ""),
                            "pages": item.get("page", ""),
                            "isbn": None,
                            "edition": item.get("edition-number", ""),
                            # Preserve the upstream relevance position for the
                            # near-tie layer.  This private field is removed
                            # from the public suggestion payload.
                            "_source_rank": len(all_results) + 1,
                            "_source_score": item.get("score"),
                        }

                        # Handle ISBN (book-specific)
                        if item.get("ISBN"):
                            isbns = item.get("ISBN", [])
                            if isbns:
                                result["isbn"] = isbns[0]

                        # Process author information
                        for author in item.get("author", []):
                            if author.get("family") or author.get("given"):
                                author_name = (
                                    f"{author.get('given', '')} {author.get('family', '')}".strip()
                                )
                                if author_name:
                                    result["authors"].append(author_name)

                        # Handle publication year
                        published_dates = [
                            item.get("published-print", {}).get("date-parts"),
                            item.get("published-online", {}).get("date-parts"),
                            item.get("issued", {}).get("date-parts"),
                        ]

                        for date_parts in published_dates:
                            if date_parts and date_parts[0] and date_parts[0][0]:
                                result["year"] = date_parts[0][0]
                                break

                        # Process journal/conference names
                        container_titles = item.get("container-title", [])
                        if container_titles:
                            result["journal"] = container_titles[0]

                        # Special treatment for conference papers
                        if result["type"] == "proceedings-article":
                            event = item.get("event")
                            if event and event.get("name"):
                                result["journal"] = (
                                    event["name"][0]
                                    if isinstance(event["name"], list)
                                    else event["name"]
                                )

                        # Special handling of books
                        if result["type"] in ["book", "monograph", "edited-book", "reference-book"]:
                            result["is_book"] = True
                            # Books usually do not have a journal, but have a publisher
                            if not result.get("publisher"):
                                result["publisher"] = item.get("publisher", "")

                        # Only keep results with enough information
                        # For books, author may be empty (edited books)
                        if result["title"] and len(result["title"]) > 5:
                            if result.get("is_book") or result["authors"]:
                                all_results.append(result)
                                seen_dois.add(doi)

                        if len(all_results) >= limit:
                            break

                    if len(all_results) >= limit:
                        break

                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    self.logger.warning(
                        f"CrossRef search strategy {i + 1} failed after retries: {str(e)}"
                    )
                    self._record_source_status("crossref", "error")
                    break
                except Exception as e:
                    self.logger.warning(f"CrossRef search strategy {i+1} failed: {str(e)}")
                    self._record_source_status("crossref", "error")
                    continue

            self.logger.info(f"CrossRef search returned {len(all_results)} unique results")
            return all_results

        except Exception as e:
            self.logger.error(f"CrossRef search failed: {str(e)}")
            self._record_source_status("crossref", "error")
            return []

    def _search_google_books(self, query: str, limit: int = 5) -> List[Dict]:
        """Search Google Books API for book metadata"""
        try:
            # Strategy: Extract meaningful keywords - title and author last names
            query_clean = ""

            # Step 1: Find and extract title (after year, before edition/publisher)
            # Pattern: (YEAR). TITLE (edition). Publisher
            title_pattern = r"\(\d{4}\)\.\s*([^.(]+?)(?:\s*\([^)]*ed\.\)|\.)"
            title_match = re.search(title_pattern, query)

            if title_match:
                title_text = title_match.group(1).strip()
                # Remove italic markers
                title_text = re.sub(r"\*([^*]+)\*", r"\1", title_text)
                query_clean = title_text
            else:
                # Fallback: try to find text between periods
                parts = query.split(".")
                for part in parts:
                    part = part.strip()
                    # Skip author parts and years
                    if (
                        len(part) > 20
                        and not re.match(r"^[A-Z][a-z]+,", part)
                        and not re.search(r"^\d{4}$", part)
                    ):
                        query_clean = re.sub(r"\*([^*]+)\*", r"\1", part)
                        break

            # Step 2: Extract author last names
            # Pattern: Name, Initial.
            author_parts = re.findall(r"([A-Z][a-z]+),\s*[A-Z]\.", query)
            if author_parts:
                query_clean += " " + " ".join(author_parts[:2])  # Use up to 2 authors

            # If query_clean is still empty, use original
            if not query_clean or len(query_clean) < 5:
                query_clean = query.strip()

            self.logger.info(f"Google Books query: {query_clean}")

            base_url = "https://www.googleapis.com/books/v1/volumes"
            params: Dict[str, Any] = {
                "q": query_clean,
                "maxResults": limit,
                "printType": "books",
                "langRestrict": "en",
            }

            # Google Books rate-limits unauthenticated clients aggressively;
            # a single 429 must not fail the whole entry when a short backoff
            # would succeed.
            response = self._get_with_retry(
                base_url,
                source_name="Google Books",
                max_attempts=SUGGESTION_MAX_ATTEMPTS,
                fallback_backoff_seconds=SUGGESTION_FALLBACK_BACKOFF_SECONDS,
                params=params,
                timeout=10,
            )
            if response is None:
                self._record_source_status("google_books", "error")
                return []
            if response.status_code == 429:
                self._record_source_status("google_books", "rate_limited")
                return []
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])
            self._record_source_status("google_books", "ok")

            results = []
            for item in items:
                volume_info = item.get("volumeInfo", {})

                result = {
                    "source": "google_books",
                    "is_book": True,
                    "type": "book",
                    "title": volume_info.get("title", ""),
                    "authors": volume_info.get("authors", []),
                    "publisher": volume_info.get("publisher", ""),
                    "year": None,
                    "isbn": None,
                    "pages": volume_info.get("pageCount", ""),
                    "url": volume_info.get("infoLink", ""),
                    "citations": 0,  # Google Books doesn't provide citation counts
                }

                # Extract year from publishedDate (format: YYYY-MM-DD or YYYY)
                published_date = volume_info.get("publishedDate", "")
                if published_date:
                    year_match = re.search(r"\b(19|20)\d{2}\b", published_date)
                    if year_match:
                        result["year"] = int(year_match.group())

                industry_identifiers = volume_info.get("industryIdentifiers", [])
                for identifier in industry_identifiers:
                    if identifier.get("type") in ["ISBN_13", "ISBN_10"]:
                        result["isbn"] = identifier.get("identifier")
                        break

                # Extract edition if mentioned in title or subtitle
                subtitle = volume_info.get("subtitle", "")
                full_title = f"{result['title']} {subtitle}".lower()
                edition_match = re.search(r"(\d+)(?:st|nd|rd|th)?\s+(?:ed\.|edition)", full_title)
                if edition_match:
                    result["edition"] = edition_match.group(1)

                # Only add if has title and authors
                if result["title"] and result["authors"]:
                    results.append(result)

            self.logger.info(f"Google Books search returned {len(results)} results")
            return results

        except Exception as e:
            self.logger.warning(f"Google Books search failed: {str(e)}")
            self._record_source_status("google_books", "error")
            return []

    def _search_google_scholar(self, query: str, limit: int = 5) -> List[Dict]:
        """Search in Google Scholar (with retry and captcha handling)."""
        try:
            import threading
            import time

            # Add delay between requests to avoid rate limiting
            last_request = getattr(self, "_last_scholar_request", None)
            if last_request is not None:
                time_since_last = time.time() - last_request
                if time_since_last < 10.0:
                    time.sleep(10.0 - time_since_last)

            self._last_scholar_request = time.time()

            # Retry with fewer attempts and longer delay
            max_retries = 2
            for attempt in range(max_retries):
                if attempt > 0:
                    # Large incremental delays: 30 seconds, 60 seconds
                    retry_delay = 30 * (attempt + 1)
                    self.logger.info(
                        f"Google Scholar retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay"
                    )
                    time.sleep(retry_delay)

                results = []
                search_completed = [False]
                error_occurred: List[Optional[str]] = [None]

                def search_worker():
                    try:
                        self.logger.info(
                            f"Google Scholar search attempt {attempt + 1}: {query[:50]}..."
                        )
                        search_query = scholarly.search_pubs(query)

                        count = 0
                        for pub in search_query:
                            if count >= limit:
                                break

                            # Dynamic timeout check
                            elapsed = time.time() - self._last_scholar_request
                            if elapsed > 20:
                                self.logger.warning(
                                    "Google Scholar search taking too long, stopping"
                                )
                                break

                            try:
                                bib = pub.get("bib", {})

                                result = {
                                    "source": "google_scholar",
                                    "doi": None,
                                    "title": bib.get("title", "") or pub.get("title", ""),
                                    "authors": (
                                        bib.get("author", [])
                                        if isinstance(bib.get("author"), list)
                                        else (
                                            bib.get("author").split(" and ")
                                            if bib.get("author")
                                            else []
                                        )
                                    ),
                                    "year": bib.get("pub_year", "") or pub.get("year"),
                                    "journal": bib.get("venue", "")
                                    or pub.get("venue", "")
                                    or pub.get("journal", ""),
                                    "citations": pub.get("num_citations", 0),
                                    "url": pub.get("pub_url", "") or pub.get("url", ""),
                                    "arxiv_id": None,
                                }

                                # Try to extract arXiv ID from eprint or other fields
                                if "eprint" in pub:
                                    arxiv_match = re.search(r"(\d{4}\.\d{4,5})", pub["eprint"])
                                    if arxiv_match:
                                        result["arxiv_id"] = arxiv_match.group(1)

                                if result["url"] and "doi.org" in result["url"]:
                                    doi_match = re.search(r"doi\.org/(.+)", result["url"])
                                    if doi_match:
                                        result["doi"] = doi_match.group(1)

                                # For conference papers, venue often contains conference name
                                if result["journal"] and (
                                    "conference" in result["journal"].lower()
                                    or "proceedings" in result["journal"].lower()
                                    or "nips" in result["journal"].lower()
                                    or "neurips" in result["journal"].lower()
                                ):
                                    result["type"] = "conference"

                                # Filter out empty or incomplete results
                                if result["title"] and len(result["title"]) > 5:
                                    results.append(result)
                                    count += 1

                            except Exception as e:
                                self.logger.warning(
                                    f"Error processing Google Scholar result: {str(e)}"
                                )
                                continue

                        search_completed[0] = True
                        self.logger.info(
                            f"Google Scholar search completed, found {len(results)} valid results"
                        )

                    except Exception as e:
                        error_msg = str(e)
                        error_occurred[0] = error_msg
                        search_completed[0] = True

                        # Detect verification codes and throttling errors
                        is_captcha_error = any(
                            keyword in error_msg.lower()
                            for keyword in [
                                "captcha",
                                "blocked",
                                "rate",
                                "too many",
                                "429",
                                "forbidden",
                                "access denied",
                            ]
                        )

                        if is_captcha_error:
                            self.logger.warning(
                                f"Google Scholar captcha/rate limit detected: {error_msg}"
                            )
                        else:
                            self.logger.warning(f"Google Scholar search error: {error_msg}")

                # Start search thread
                search_thread = threading.Thread(target=search_worker)
                search_thread.daemon = True
                search_thread.start()

                # Wait for search to complete, dynamically adjust wait time - significantly increase timeout
                max_wait_iterations = 120
                for i in range(max_wait_iterations):
                    if search_completed[0]:
                        break
                    time.sleep(0.5)

                # Check search results
                if search_completed[0]:
                    if error_occurred[0]:
                        error_msg = error_occurred[0]
                        is_captcha_error = any(
                            keyword in error_msg.lower()
                            for keyword in [
                                "captcha",
                                "blocked",
                                "rate",
                                "too many",
                                "429",
                                "forbidden",
                                "access denied",
                            ]
                        )

                        if is_captcha_error and attempt < max_retries - 1:
                            # The verification code is wrong and there is still a chance to retry. Please wait longer for the verification code system to cool down.
                            self.logger.info(
                                "Captcha error detected, will retry with extended backoff..."
                            )
                            time.sleep(60)
                            continue
                        else:
                            # Other errors or the maximum number of retries has been reached
                            self.logger.warning(
                                f"Google Scholar search failed after retries: {error_msg}"
                            )
                            return []
                    else:
                        # Successfully obtained results
                        self.logger.info(
                            f"Google Scholar search succeeded with {len(results)} results"
                        )
                        return results

                else:
                    # Search timeout - possible captcha issue, adding extra delay
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            "Google Scholar search timed out, likely due to captcha. "
                            "Adding cooling period..."
                        )
                        time.sleep(120)
                        continue
                    else:
                        self.logger.warning(
                            f"Google Scholar search failed after {max_retries} attempts (timeout)"
                        )
                        return []

            return []

        except Exception as e:
            self.logger.warning(f"Google Scholar search failed: {str(e)}")
            return []

    def _score_candidates(self, candidates: List[Dict], query_string: str) -> List[Dict]:
        """Score candidates using two-layer scoring: Query-Match Score + Tie-Break."""
        scored_candidates = []

        # Normalize query for title matching
        normalized_query = query_string.strip()
        # Try to derive a probable title part: cut at first 4-digit year
        title_part = re.split(r"\b(19|20)\d{2}\b", normalized_query)[0].strip() or normalized_query
        # Remove common "et al." noise
        title_part = re.sub(r"\bet\s*al\.?\b", "", title_part, flags=re.IGNORECASE).strip()

        # Venue synonyms for query normalization only (not scoring)
        synonyms = {
            "nips": "neural information processing systems",
            "neurips": "neural information processing systems",
            "cvpr": "computer vision and pattern recognition",
            "iclr": "international conference on learning representations",
            "icml": "international conference on machine learning",
        }

        normalized_query_lower = normalized_query.lower()
        normalized_query_evidence = re.sub(
            r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", normalized_query_lower)
        ).strip()
        # Expand query with venue synonyms for better matching
        for k, v in synonyms.items():
            if k in normalized_query_lower and v not in normalized_query_lower:
                normalized_query += f" {v}"
                normalized_query_lower = normalized_query.lower()

        # Normalize candidate venue names
        def normalize_venue(venue):
            if not venue:
                return ""
            venue_lower = venue.lower()
            for k, v in synonyms.items():
                if k in venue_lower:
                    return venue.replace(k, v).replace(k.upper(), v)
            return venue

        query_year = None
        has_query_year = False
        year_match = re.search(r"\b(19|20)\d{2}\b", normalized_query)
        if year_match:
            query_year = int(year_match.group(0))
            has_query_year = True

        # Check if query contains venue hints
        has_venue_in_query = any(syn in normalized_query_lower for syn in synonyms.keys()) or any(
            journal_word in normalized_query_lower
            for journal_word in ["journal", "proceedings", "conference", "transactions"]
        )

        # Dynamic weight calculation based on available query signals
        # If a signal is missing, redistribute its weight to other signals
        available_signals = ["title", "author"]  # Always available
        if has_query_year:
            available_signals.append("year")
        if has_venue_in_query:
            available_signals.append("venue")

        # Base weights (will be normalized)
        base_weights = {"title": 0.55, "author": 0.25, "year": 0.15, "venue": 0.10}

        # Normalize weights for available signals
        available_weight_sum = sum(base_weights[s] for s in available_signals)
        weights = {s: base_weights[s] / available_weight_sum for s in available_signals}

        for candidate in candidates:
            scores: Dict[str, Any] = {}

            # Title similarity (core signal)
            candidate_title = candidate.get("title", "").lower()
            base_title = title_part.lower()
            title_score = 0
            title_in_query = False
            if candidate_title and base_title:
                ratio = fuzz.ratio(base_title, candidate_title)
                partial = fuzz.partial_ratio(base_title, candidate_title)
                token_sort = fuzz.token_sort_ratio(base_title, candidate_title)
                token_set = fuzz.token_set_ratio(base_title, candidate_title)
                candidate_title_evidence = re.sub(
                    r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", candidate_title)
                ).strip()
                # Exact normalized containment is strong evidence while fuzzy
                # partial matching against the entire citation is not: the
                # latter can over-score an unrelated title that shares only a
                # phrase such as "all you need".
                title_in_query = bool(
                    len(candidate_title_evidence) >= 12
                    and candidate_title_evidence in normalized_query_evidence
                )
                title_score = max(ratio, partial, token_sort, token_set)
                if title_in_query:
                    title_score = 100
                # Bonus for exact phrase match
                if base_title in candidate_title or candidate_title in base_title:
                    title_score = min(title_score + 10, 100)
            scores["title"] = title_score
            scores["title_in_query"] = title_in_query

            # Author matching
            author_score = 0
            if candidate.get("authors"):
                authors_text = " ".join(candidate["authors"]).lower()
                query_lower = normalized_query.lower()
                exact_match = any(
                    author.lower().strip() in query_lower for author in candidate["authors"]
                )
                if exact_match:
                    author_score = 80
                else:
                    author_score = fuzz.partial_ratio(query_lower, authors_text)
            scores["author"] = author_score

            # Year matching (only if query has year)
            year_score = 0
            year_conflict = False
            if query_year is not None and candidate.get("year"):
                try:
                    candidate_year = int(candidate["year"])
                    year_diff = abs(candidate_year - query_year)
                    if year_diff == 0:
                        year_score = 100
                    elif year_diff <= 2:
                        year_score = 70
                    elif year_diff <= 5:
                        year_score = 30
                    else:
                        # The query explicitly cites a year this candidate
                        # contradicts by more than five years. That is not a
                        # weak signal but contradictory evidence — a same-title
                        # later work (commentary, book chapter, reprint) must
                        # not outrank on title similarity alone.
                        year_conflict = True
                except (ValueError, TypeError):
                    pass
            scores["year"] = year_score

            # Venue matching (only if query has venue hint)
            venue_score = 0
            venue_lower = ""
            if candidate.get("journal"):
                normalized_venue = normalize_venue(candidate["journal"])
                venue_lower = normalized_venue.lower()
                if has_venue_in_query:
                    if venue_lower and venue_lower in normalized_query_lower:
                        venue_score = 80  # Exact venue mention
                    else:
                        venue_score = fuzz.partial_ratio(normalized_query_lower, venue_lower)
            scores["venue"] = venue_score

            # Year and venue only corroborate a candidate that already looks
            # like the cited work — countless works share any given year or
            # venue, so without title similarity they are not evidence and
            # must not lift unrelated candidates up the ranking.
            title_gate = scores["title"] / 100.0
            scores["year"] = round(scores["year"] * title_gate, 1)
            scores["venue"] = round(scores["venue"] * title_gate, 1)

            # Compute Query-Match Score (0-100)
            match_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in available_signals)
            if year_conflict:
                match_score *= 0.65
            match_score = min(max(match_score, 0), 100)

            # Store for tie-break layer
            candidate_copy = candidate.copy()
            candidate_copy["match_score"] = round(match_score, 2)
            scores["year_conflict"] = year_conflict
            candidate_copy["score_breakdown"] = scores
            candidate_copy["_weights"] = weights  # Internal use for debugging
            scored_candidates.append(candidate_copy)

        # Sort by match score descending
        scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)

        # Tie-break layer: candidates within 5 points of the top score form a
        # near-tie cluster whose raw scores are not meaningfully different, so
        # order that cluster by the tie-break rank (exact title, venue hit, has
        # DOI, source tier) instead of by raw score. Candidates outside the
        # cluster keep their score order.
        if len(scored_candidates) >= 2:

            def tie_break_rank(c):
                sb = c.get("score_breakdown", {})
                # 1. Exact title match (highest priority) — unless the
                # candidate's year contradicts the year the query cites.
                exact_title = int(sb.get("title", 0) >= 90 and not sb.get("year_conflict"))
                # 2. Venue exact hit
                venue_hit = int(sb.get("venue", 0) >= 70)
                # 3. Has DOI
                has_doi = int(bool(c.get("doi")))
                # 4. Preserve a consulted source's own relevance order when
                # OneCite's lexical scores are effectively tied.
                source_rank = c.get("_source_rank")
                try:
                    source_position = -int(source_rank)
                except (TypeError, ValueError):
                    source_position = -10_000
                # 5. Source tier (lower number = better)
                source_tier = {
                    "crossref": 1,
                    "pubmed": 2,
                    "arxiv": 3,
                    "semantic_scholar": 4,
                    "google_books": 5,
                    "datacite": 6,
                    "zenodo": 7,
                    "google_scholar": 8,
                }.get(c.get("source"), 9)
                # A final raw-score term makes the ordering deterministic when
                # every higher-priority signal is equal.
                return (
                    exact_title,
                    venue_hit,
                    has_doi,
                    source_position,
                    -source_tier,
                    c.get("match_score", 0),
                )

            best_score = scored_candidates[0]["match_score"]
            has_direct_title_evidence = any(
                c.get("score_breakdown", {}).get("title_in_query") for c in scored_candidates
            )
            # Sparse citations sometimes contain only authors, venue, volume,
            # and page.  In that case OneCite's lexical score cannot identify
            # the title and should defer more strongly to a source's own
            # bibliographic relevance order rather than invent precision.
            tie_window = 5 if has_direct_title_evidence else 25
            cluster = [c for c in scored_candidates if best_score - c["match_score"] <= tie_window]
            rest = [c for c in scored_candidates if best_score - c["match_score"] > tie_window]
            cluster.sort(key=tie_break_rank, reverse=True)
            scored_candidates = cluster + rest

        return scored_candidates
