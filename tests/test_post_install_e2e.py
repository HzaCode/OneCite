#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end sanity check that mirrors what a user would do right after
``pip install onecite``: import, run --help, process a small file,
and call the Python API.
"""

import subprocess
import sys
import os
from unittest.mock import patch

from .mock_responses import mock_requests_get


def test_post_install_e2e(tmp_path):
    import onecite

    # 1. package metadata
    assert hasattr(onecite, "__version__")
    assert hasattr(onecite, "__author__")

    # 2. CLI --help
    r = subprocess.run(
        [sys.executable, "-m", "onecite.cli", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, r.stderr
    assert "onecite" in r.stdout.lower()

    # 3. CLI process (hits the network – may be slow)
    refs = tmp_path / "refs.txt"
    refs.write_text(
        "10.1038/nature14539\n"
        "Attention is all you need\n"
        "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "-m", "onecite.cli", "process", str(refs), "--quiet"],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "ONECITE_OFFLINE_FIXTURES": "1"},
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip(), "expected non-empty output"

    # 4. Python API quick-check
    from onecite import process_references

    with patch("onecite.pipeline.requests.get", side_effect=mock_requests_get):
        result = process_references(
            input_content="10.1038/nature14539",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=lambda c: 0 if c else -1,
        )
    assert result and result.get("results")
