"""Year-conflict handling in suggestion scoring.

When the query explicitly cites a year, a candidate whose year contradicts
it by more than five years is very unlikely to be the referenced work —
famous titles attract later commentaries, book chapters, and reprints with
identical titles. Title similarity alone must not rank those above the
real match.
"""

from onecite.pipeline.identifier import IdentifierModule

QUERY = "Attention is all you need, Vaswani et al., NIPS 2017"

TRUE_PAPER = {
    "source": "semantic_scholar",
    "doi": "10.5555/3295222.3295349",
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
    "year": 2017,
    "journal": "Advances in Neural Information Processing Systems",
    "citations": 90000,
}

LOOKALIKE_2025 = {
    "source": "crossref",
    "doi": "10.1201/9781003561460-19",
    "title": "Attention Is All You Need",
    "authors": ["J. Mark Bishop", "Gabriel Seiberth"],
    "year": 2025,
    "journal": "Driving Intelligence: The Green Book",
    "citations": 4,
}


def test_true_paper_outranks_same_title_lookalike():
    identifier = IdentifierModule()
    scored = identifier._score_candidates([LOOKALIKE_2025, TRUE_PAPER], QUERY)
    assert scored[0]["doi"] == TRUE_PAPER["doi"]


def test_year_conflict_is_flagged_and_penalized():
    identifier = IdentifierModule()
    scored = identifier._score_candidates([LOOKALIKE_2025, TRUE_PAPER], QUERY)
    by_doi = {c["doi"]: c for c in scored}
    lookalike = by_doi[LOOKALIKE_2025["doi"]]
    true_paper = by_doi[TRUE_PAPER["doi"]]
    assert lookalike["score_breakdown"]["year_conflict"] is True
    assert true_paper["score_breakdown"]["year_conflict"] is False
    assert lookalike["match_score"] < true_paper["match_score"]


def test_small_year_gap_is_not_penalized():
    # arXiv year vs published year commonly differ by 1-2 years; that is a
    # weak signal, not a contradiction.
    published_next_year = dict(TRUE_PAPER, year=2018, doi="10.5555/published.2018")
    identifier = IdentifierModule()
    scored = identifier._score_candidates([published_next_year], QUERY)
    assert scored[0]["score_breakdown"]["year_conflict"] is False
    # Title matches exactly, so the year signal passes through ungated.
    assert scored[0]["score_breakdown"]["year"] == 70


def test_matching_year_does_not_rescue_unrelated_title():
    # A 2017 work whose title merely shares a phrase fragment must not ride
    # the year match up the ranking — countless works share any given year.
    unrelated_2017 = {
        "source": "crossref",
        "doi": "10.1234/unrelated.2017",
        "title": "Football preview 2017 - all you need to know",
        "authors": ["Sports Desk"],
        "year": 2017,
        "journal": "Weekly Sports",
        "citations": 0,
    }
    identifier = IdentifierModule()
    scored = identifier._score_candidates([unrelated_2017, TRUE_PAPER], QUERY)
    assert scored[0]["doi"] == TRUE_PAPER["doi"]
    by_doi = {c["doi"]: c for c in scored}
    assert by_doi["10.1234/unrelated.2017"]["match_score"] < 50
    # The gated year contribution is disclosed in the breakdown.
    assert by_doi["10.1234/unrelated.2017"]["score_breakdown"]["year"] < 100
