"""
Git synchronization utilities for the AEIA corpus directory.

Provides ``pull_corpus()`` to run ``git pull origin main`` inside the target
codebase repository and return the list of files that changed.
"""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitPullResult:
    """Outcome of a ``git pull`` on the corpus directory."""

    before_sha: str
    after_sha: str
    changed_files: list[str] = field(default_factory=list)
    up_to_date: bool = False
    error: str = ""


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command and return the CompletedProcess."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )


def pull_corpus(corpus_path: Path, branch: str = "main") -> GitPullResult:
    """Pull latest changes from the remote and return what changed.

    Steps:
      1. Record the current HEAD sha.
      2. ``git pull origin <branch>``
      3. Record the new HEAD sha.
      4. If they differ, run ``git diff --name-only <before>..<after>`` to
         get the list of changed files.

    Returns a ``GitPullResult`` with commit SHAs and changed file paths
    (relative to the repo root).
    """
    git_dir = corpus_path / ".git"
    if not git_dir.is_dir():
        return GitPullResult(
            before_sha="",
            after_sha="",
            error=f"Not a git repository: {corpus_path}",
        )

    # 1. Current HEAD
    before = _run_git(["rev-parse", "HEAD"], cwd=corpus_path)
    if before.returncode != 0:
        return GitPullResult(
            before_sha="",
            after_sha="",
            error=f"git rev-parse HEAD failed: {before.stderr.strip()}",
        )
    before_sha = before.stdout.strip()

    # 2. Pull
    pull = _run_git(["pull", "origin", branch], cwd=corpus_path)
    if pull.returncode != 0:
        return GitPullResult(
            before_sha=before_sha,
            after_sha=before_sha,
            error=f"git pull failed: {pull.stderr.strip()}",
        )

    # 3. New HEAD
    after = _run_git(["rev-parse", "HEAD"], cwd=corpus_path)
    after_sha = after.stdout.strip()

    # 4. Already up to date?
    if before_sha == after_sha:
        return GitPullResult(
            before_sha=before_sha,
            after_sha=after_sha,
            up_to_date=True,
        )

    # 5. Changed files
    diff = _run_git(
        ["diff", "--name-only", f"{before_sha}..{after_sha}"],
        cwd=corpus_path,
    )
    changed = [f for f in diff.stdout.strip().splitlines() if f]

    return GitPullResult(
        before_sha=before_sha,
        after_sha=after_sha,
        changed_files=changed,
    )
