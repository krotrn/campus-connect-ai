import logging
import os
import re
import subprocess
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)

# Directories never worth scanning for source dependencies.
SCAN_IGNORE_DIRS = {"node_modules", ".next", ".git", "dist", "build", "coverage"}
CODE_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs"}


def _get_corpus_dir() -> Path:
    corpus_path = settings.corpus_path
    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus directory not found at {corpus_path}")
    return corpus_path


def get_git_commit_history(max_count: int = 5, path: str | None = None) -> str:
    """
    Retrieve recent git commit logs from the target corpus repository.
    Safe, read-only git command.
    """
    corpus_dir = _get_corpus_dir()
    max_count = max(1, min(max_count, 30))

    cmd = [
        "git",
        "log",
        f"-n{max_count}",
        '--pretty=format:%h - %an, %ar : %s',
    ]

    if path:
        # Sanitize path to prevent flag injection
        clean_path = str(Path(path).as_posix()).lstrip("-")
        cmd.extend(["--", clean_path])

    try:
        res = subprocess.run(
            cmd,
            cwd=str(corpus_dir),
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        output = res.stdout.strip()
        return output if output else "No git commit history found."
    except subprocess.CalledProcessError as e:
        logger.warning("git log failed: %s", e.stderr.strip())
        return f"Error executing git log: {e.stderr.strip()}"
    except Exception as e:
        logger.warning("git log failed: %s", e)
        return f"Error retrieving git history: {str(e)}"


def get_commit_details(commit_hash: str) -> str:
    """
    Retrieve commit details and changed files for a specific commit hash.
    Safe, read-only git command with strict hex hash validation.
    """
    clean_hash = commit_hash.strip().strip("'\"")
    if not re.match(r"^[0-9a-fA-F]{4,40}$", clean_hash):
        return f"Invalid commit hash: '{commit_hash}'. Must be a 4-40 character hexadecimal string."

    corpus_dir = _get_corpus_dir()
    cmd = ["git", "show", "--stat", "--oneline", clean_hash]

    try:
        res = subprocess.run(
            cmd,
            cwd=str(corpus_dir),
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning("git show failed for %s: %s", clean_hash, e.stderr.strip())
        return f"Error showing commit {clean_hash}: {e.stderr.strip()}"
    except Exception as e:
        logger.warning("git show failed for %s: %s", clean_hash, e)
        return f"Error retrieving commit details: {str(e)}"


def find_file_dependents(module_name: str, max_results: int = 20) -> list[str]:
    """
    Scan the codebase to find source files that import or depend on the given module.
    Searches for import / require statements across TypeScript and JavaScript files.
    """
    corpus_dir = _get_corpus_dir()

    # Clean target name for matching
    clean_target = module_name.strip().strip("'\"")
    # Remove file extensions like .ts, .tsx, .js
    base_target = re.sub(r"\.(tsx?|jsx?|mjs)$", "", clean_target)
    # Extract filename without directory path for flexible matching
    target_basename = Path(base_target).name

    dependents: list[str] = []

    # Pattern matches import ... from '...target...' or require('...target...')
    regex_pattern = re.compile(
        rf"""(?:import\s+.*?from\s+['"][^'"]*?{re.escape(target_basename)}[^'"]*?['"]|require\s*\(\s*['"][^'"]*?{re.escape(target_basename)}[^'"]*?['"]\s*\))""",
        re.MULTILINE,
    )

    # os.walk lets us prune ignored directories in place; rglob would still
    # descend into node_modules before filtering each path out.
    for root, dirnames, filenames in os.walk(corpus_dir):
        dirnames[:] = [d for d in dirnames if d not in SCAN_IGNORE_DIRS]
        for filename in filenames:
            if Path(filename).suffix.lower() not in CODE_EXTENSIONS:
                continue
            p = Path(root) / filename
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if regex_pattern.search(content):
                dependents.append(str(p.relative_to(corpus_dir)))
                if len(dependents) >= max_results:
                    return dependents

    return dependents

