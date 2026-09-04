import pytest
from src.agent.tools import (
    find_file_dependents,
    get_commit_details,
    get_git_commit_history,
)


def test_get_git_commit_history():
    history = get_git_commit_history(max_count=3)
    assert history is not None
    assert len(history) > 10
    assert " - " in history


def test_get_commit_details_valid():
    # Test with a known commit in campus-connect
    details = get_commit_details("6e19f61")
    assert "6e19f61" in details
    assert "Add integration tests" in details
    # Stat summary should be present
    assert "changed" in details or "insertion" in details or "test" in details.lower()


def test_get_commit_details_invalid():
    details = get_commit_details("invalid; rm -rf /")
    assert "Invalid commit hash" in details


def test_find_file_dependents():
    # redis is imported by several files in campus-connect (e.g. redis-connection, bullmq)
    dependents = find_file_dependents("redis")
    assert isinstance(dependents, list)
    assert len(dependents) > 0
    # Every dependent path should be a relative path
    for d in dependents:
        assert not d.startswith("/")

