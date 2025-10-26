#!/usr/bin/env python3
"""Pre-commit hook to prevent direct commits to protected branches

This hook prevents direct commits to main/master branches.
Force push with --no-verify to bypass (not recommended).

Exit codes:
    0: Commit allowed
    1: Commit blocked (protected branch)
"""

import subprocess
import sys


PROTECTED_BRANCHES = ['main', 'master', 'production']


def get_current_branch() -> str:
    """Get the current Git branch name

    Returns:
        Branch name (e.g., 'main', 'feature/xyz')
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ''


def main() -> int:
    """Main entry point

    Returns:
        Exit code (0 = allow commit, 1 = block commit)
    """
    current_branch = get_current_branch()

    if not current_branch:
        # Can't determine branch, allow commit
        return 0

    if current_branch in PROTECTED_BRANCHES:
        print("\n" + "=" * 80)
        print("❌ COMMIT BLOCKED: Direct commits to protected branches are not allowed")
        print("=" * 80)
        print()
        print(f"  Current branch: {current_branch}")
        print(f"  Protected branches: {', '.join(PROTECTED_BRANCHES)}")
        print()
        print("💡 Instead:")
        print("  1. Create a feature branch:")
        print(f"     git checkout -b feature/your-feature-name")
        print()
        print("  2. Make your changes and commit:")
        print("     git add .")
        print("     git commit -m 'Your commit message'")
        print()
        print("  3. Push and create a pull request:")
        print("     git push -u origin feature/your-feature-name")
        print()
        print("⚠️  To bypass this check (NOT recommended):")
        print("     git commit --no-verify")
        print()
        print("=" * 80)
        print()

        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
