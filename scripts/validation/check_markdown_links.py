"""Portable Markdown Link and Path Validator for VeriTrace.

Validates that:
1. All Markdown links inside the repository use portable, repository-relative paths
   relative to the source file's directory.
2. No machine-specific or absolute paths (e.g. file:///, C:/Users/...) exist.
3. All relative link targets resolve to existing files or directories on disk.
4. Includes all tracked and untracked Markdown files across the repository.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


def find_markdown_files(root: Path) -> list[Path]:
    """Find all markdown files, ignoring virtual environments and VCS dirs."""
    md_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith(".md"):
                md_files.append(Path(dirpath) / f)
    return sorted(md_files)


def validate_markdown_links(root: Path) -> tuple[int, list[str]]:
    """Validate all markdown links across discovered markdown files."""
    md_files = find_markdown_files(root)
    total_links_checked = 0
    violations: list[str] = []

    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md_path in md_files:
        rel_src = md_path.relative_to(root)
        try:
            content = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as err:
            violations.append(f"{rel_src}: UTF-8 decode error: {err}")
            continue

        for line_num, line in enumerate(content.splitlines(), start=1):
            for match in link_pattern.finditer(line):
                text = match.group(1).strip()
                link = match.group(2).strip()

                # Ignore external URLs, mailto, and intra-page anchors
                if (
                    link.startswith(("http://", "https://", "mailto:", "#"))
                ):
                    continue

                total_links_checked += 1

                # Check for machine-specific path prefixes
                lower_link = link.lower()
                if (
                    lower_link.startswith("file:")
                    or "c:" in lower_link
                    or "users/" in lower_link
                    or "users\\" in lower_link
                ):
                    violations.append(f"{rel_src}:{line_num}: Non-portable link: [{text}]({link})")
                    continue

                # Separate path and fragment anchor
                path_part, _, _anchor = link.partition("#")
                clean_path = path_part.strip()
                if not clean_path:
                    # Pure anchor handled above
                    continue

                # Target must resolve relative to the Markdown file's directory
                target_path = (md_path.parent / clean_path).resolve()
                if not target_path.exists():
                    violations.append(
                        f"{rel_src}:{line_num}: Broken link: [{text}]({link}) -> "
                        f"Target '{target_path}' not found."
                    )

    return total_links_checked, violations


def main() -> int:
    print(f"Checking Markdown link portability across repository at: {ROOT}")
    total_checked, violations = validate_markdown_links(ROOT)
    print(f"Total Markdown links inspected: {total_checked}")

    if violations:
        print(f"\nFAILED: Found {len(violations)} link violations:\n")
        for v in violations:
            print(f"  - {v}")
        return 1

    print("SUCCESS: All Markdown links are portable and resolve to existing targets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
