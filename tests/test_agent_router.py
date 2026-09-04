import pytest
from src.agent.router import classify_route_fast, route_query


def test_router_git_commit():
    route, reason, target = route_query("What changed in commit 6e19f61?")
    assert route == "git_commit"
    assert target == "6e19f61"


def test_router_git_history():
    route, reason, target = route_query("Show recent commits and git log")
    assert route == "git_history"


def test_router_file_dependents():
    route, reason, target = route_query("Which files depend on redis?")
    assert route == "file_dependents"
    assert "redis" in target.lower()


def test_router_direct_rag():
    route, reason, target = route_query("Where is user authentication implemented?")
    assert route == "direct_rag"

