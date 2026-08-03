"""The test mocks must stay derived from the bundled offline fixtures.

Two hand-maintained copies of the same DOI's metadata silently drifted
apart once already (missing ``URL``/``is-referenced-by-count`` on one side,
missing ``ISSN`` on the other). These checks pin the derivation: every
field of the bundled fixture must appear identically in the test mock.
"""

from onecite.benchmarks import offline
from tests import mock_responses


def _assert_superset(mock, fixture):
    for key, value in fixture["message"].items():
        assert mock["message"].get(key) == value, f"drifted field: {key}"


def test_crossref_mocks_are_supersets_of_offline_fixtures():
    _assert_superset(
        mock_responses.MOCK_CROSSREF_RESPONSE, offline.CROSSREF_WORK_NATURE_DEEP_LEARNING
    )
    _assert_superset(mock_responses.MOCK_CROSSREF_DQN_RESPONSE, offline.CROSSREF_WORK_NATURE_DQN)
    _assert_superset(
        mock_responses.MOCK_CROSSREF_PROCEEDINGS_RESPONSE, offline.CROSSREF_WORK_TRANSFORMER
    )


def test_arxiv_mock_is_the_bundled_atom_fixture():
    assert mock_responses.MOCK_ARXIV_RESPONSE == offline.ARXIV_TRANSFORMER


def test_derivation_does_not_mutate_the_bundled_fixture():
    # copy.deepcopy in mock_responses must protect the package-level data:
    # the ISSN extra belongs to the test layer only.
    assert "ISSN" not in offline.CROSSREF_WORK_NATURE_DEEP_LEARNING["message"]
    assert "ISSN" not in offline.CROSSREF_WORK_NATURE_DQN["message"]
