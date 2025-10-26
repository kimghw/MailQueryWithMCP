#!/usr/bin/env python3
"""Pre-commit hook to check for naive datetime.now() usage

This hook prevents commits that use datetime.now() instead of utc_now()
from infra.utils.datetime_utils.

Exit codes:
    0: No issues found
    1: Found datetime.now() usage (blocks commit)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


# Patterns to detect
NAIVE_DATETIME_PATTERNS = [
    (r'\bdatetime\.now\(\)', 'datetime.now()', 'utc_now()'),
    (r'\bdt\.now\(\)', 'dt.now()', 'utc_now()'),
]

# Allowed patterns (legitimate uses)
ALLOWED_PATTERNS = [
    r'#.*datetime\.now\(\)',  # In comments
    r'""".*datetime\.now\(\).*"""',  # In docstrings
    r"'.*datetime\.now\(\).*'",  # In strings
    r'".*datetime\.now\(\).*"',  # In strings
    r'def.*datetime\.now\(\)',  # Function definitions (e.g., in datetime_utils.py)
    r'# ❌.*datetime\.now\(\)',  # In documentation examples (marked as wrong)
]


def is_allowed_context(line: str, pattern: str) -> bool:
    """Check if the pattern usage is in an allowed context

    Args:
        line: Source code line
        pattern: Pattern that was matched

    Returns:
        True if usage is allowed (e.g., in comments, strings)
    """
    for allowed in ALLOWED_PATTERNS:
        if re.search(allowed, line, re.IGNORECASE):
            return True
    return False


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """Check a Python file for naive datetime usage

    Args:
        filepath: Path to the Python file

    Returns:
        List of (line_number, line_content, pattern) tuples
    """
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            # Skip empty lines
            if not line.strip():
                continue

            # Check each pattern
            for pattern, bad_usage, good_usage in NAIVE_DATETIME_PATTERNS:
                if re.search(pattern, line):
                    # Check if it's in an allowed context
                    if not is_allowed_context(line, pattern):
                        issues.append((line_num, line.strip(), bad_usage))

    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)

    return issues


def print_issues(filepath: Path, issues: List[Tuple[int, str, str]]) -> None:
    """Print found issues in a formatted way

    Args:
        filepath: Path to the file
        issues: List of issues found
    """
    print(f"\n❌ {filepath}")
    print("=" * 80)

    for line_num, line_content, bad_usage in issues:
        print(f"  Line {line_num}: {bad_usage} found")
        print(f"    {line_content}")

    print()
    print("💡 Fix:")
    print("  Replace with:")
    print("    from infra.utils.datetime_utils import utc_now")
    print("    now = utc_now()  # timezone-aware UTC datetime")
    print()


def main(filenames: List[str]) -> int:
    """Main entry point

    Args:
        filenames: List of files to check

    Returns:
        Exit code (0 = success, 1 = issues found)
    """
    total_issues = 0
    files_with_issues = []

    for filename in filenames:
        filepath = Path(filename)

        # Skip non-Python files
        if filepath.suffix != '.py':
            continue

        # Skip excluded patterns
        if any(pattern in str(filepath) for pattern in ['venv/', '.venv/', '__pycache__']):
            continue

        # Check the file
        issues = check_file(filepath)

        if issues:
            total_issues += len(issues)
            files_with_issues.append((filepath, issues))

    # Print results
    if files_with_issues:
        print("\n" + "=" * 80)
        print("⚠️  DATETIME USAGE CHECK FAILED")
        print("=" * 80)

        for filepath, issues in files_with_issues:
            print_issues(filepath, issues)

        print("=" * 80)
        print(f"Found {total_issues} naive datetime.now() usage(s) in {len(files_with_issues)} file(s)")
        print("=" * 80)
        print()
        print("📖 See docs/DATETIME_USAGE_GUIDE.md for best practices")
        print()

        return 1

    return 0


if __name__ == '__main__':
    # Get files from command line arguments
    if len(sys.argv) < 2:
        print("Usage: check_datetime_usage.py <file1> <file2> ...", file=sys.stderr)
        sys.exit(0)

    filenames = sys.argv[1:]
    sys.exit(main(filenames))
