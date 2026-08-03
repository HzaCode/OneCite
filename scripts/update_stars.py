#!/usr/bin/env python3
"""Auto-update awesome-cli-apps GitHub stars badge in README files."""

import re
import sys
from pathlib import Path

import requests

# Target repo to track stars for (awesome-cli-apps)
REPO_OWNER = "agarrharr"
REPO_NAME = "awesome-cli-apps"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

# Badge pattern to update the "Featured-Awesome CLI Apps XXk" badge
BADGE_PATTERN = (
    r"(https://img\.shields\.io/badge/Featured-Awesome%20CLI%20Apps%20)([\d.]+k)(%E2%AD%90)"
)


def format_stars(count: int) -> str:
    """Format star count to human readable string."""
    if count >= 1000:
        return f"{count / 1000:.1f}k".replace(".0k", "k")
    return str(count)


def get_github_stars() -> int:
    """Fetch star count from GitHub API."""
    try:
        response = requests.get(GITHUB_API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("stargazers_count", 0)
    except Exception as e:
        print(f"Error fetching stars: {e}")
        sys.exit(1)


def update_readme_stars_badge(filepath: Path, stars: int) -> bool:
    """Update awesome-cli-apps stars badge in README."""
    content = filepath.read_text(encoding="utf-8")
    original_content = content

    formatted = format_stars(stars)

    # Pattern for the awesome-cli-apps featured badge
    # Matches: https://img.shields.io/badge/Featured-Awesome%20CLI%20Apps%20XXk%E2%AD%90-...
    badge_pattern = (
        r"(https://img\.shields\.io/badge/Featured-Awesome%20CLI%20Apps%20)([\d.]+k)(%E2%AD%90)"
    )

    def replace_stars(match):
        return match.group(1) + formatted + match.group(3)

    content = re.sub(badge_pattern, replace_stars, content)

    if content != original_content:
        filepath.write_text(content, encoding="utf-8")
        print(f"Updated awesome-cli-apps stars in {filepath}: {formatted}")
        return True
    else:
        print(f"No changes needed in {filepath}")
        return False


def main():
    """Main entry point."""
    stars = get_github_stars()
    print(f"Current GitHub stars: {stars} ({format_stars(stars)})")

    # Update main README
    readme_path = Path("README.md")
    if readme_path.exists():
        update_readme_stars_badge(readme_path, stars)
    else:
        print("README.md not found")

    # Update docs README if exists
    docs_readme = Path("docs/README.md")
    if docs_readme.exists():
        update_readme_stars_badge(docs_readme, stars)


if __name__ == "__main__":
    main()
