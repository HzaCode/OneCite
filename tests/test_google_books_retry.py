"""Google Books rate-limit resilience.

Unauthenticated Google Books requests are aggressively rate-limited; a
single 429 must not fail an ISBN entry that a short backoff would resolve.
"""

from unittest.mock import patch

from onecite.pipeline.identifier import IdentifierModule


class _Response:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            from requests.exceptions import HTTPError

            raise HTTPError(f"HTTP {self.status_code}", response=self)


_BOOK_PAYLOAD = {
    "items": [
        {
            "volumeInfo": {
                "title": "Deep Learning",
                "authors": ["Ian Goodfellow", "Yoshua Bengio", "Aaron Courville"],
                "publisher": "MIT Press",
                "publishedDate": "2016",
                "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780262035613"}],
            }
        }
    ]
}


def test_retries_past_429_and_succeeds():
    identifier = IdentifierModule()
    responses = iter([_Response(429), _Response(429), _Response(200, _BOOK_PAYLOAD)])
    sleeps = []

    with patch("onecite.pipeline.requests.get", side_effect=lambda *a, **k: next(responses)):
        with patch(
            "onecite.pipeline.identifier.time.sleep", side_effect=lambda s: sleeps.append(s)
        ):
            results = identifier._search_google_books("ISBN 978-0-262-03561-3")

    assert results, "expected the third attempt to succeed"
    assert results[0]["title"] == "Deep Learning"
    assert len(sleeps) == 2  # backed off twice before succeeding


def test_gives_up_after_initial_attempt_and_three_retries():
    identifier = IdentifierModule()
    calls = []

    def always_429(*args, **kwargs):
        calls.append(1)
        return _Response(429)

    with patch("onecite.pipeline.requests.get", side_effect=always_429):
        with patch("onecite.pipeline.identifier.time.sleep"):
            results = identifier._search_google_books("ISBN 978-0-262-03561-3")

    assert results == []  # fails closed, no fabricated book metadata
    assert len(calls) == 4


def test_non_retryable_error_is_not_retried():
    identifier = IdentifierModule()
    calls = []

    def not_found(*args, **kwargs):
        calls.append(1)
        return _Response(404)

    with patch("onecite.pipeline.requests.get", side_effect=not_found):
        with patch("onecite.pipeline.identifier.time.sleep") as sleep_mock:
            results = identifier._search_google_books("ISBN 978-0-262-03561-3")

    assert results == []
    assert len(calls) == 1
    sleep_mock.assert_not_called()
