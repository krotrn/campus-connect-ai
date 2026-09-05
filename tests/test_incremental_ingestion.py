"""Tests for incremental ingestion, git sync, webhook, and BM25 thread safety."""

import hashlib
import hmac
import json
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, services
from src.api.webhook import verify_github_signature
from src.config import settings
from src.ingestion.git_sync import GitPullResult, pull_corpus
from src.ingestion.pipeline import IngestionPipeline, _point_id
from src.retrieval.retriever import Retriever


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


# ─────────────────────────────────────────────────────────────────────────────
# Git Pull Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_git_pull_returns_changed_files():
    """pull_corpus returns a GitPullResult with before/after SHAs and changed files."""
    before_sha = "aaa111"
    after_sha = "bbb222"
    diff_output = "src/auth.ts\nREADME.md\n"

    with patch("src.ingestion.git_sync._run_git") as mock_git:
        # Sequence: rev-parse HEAD (before), git pull, rev-parse HEAD (after), git diff
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout=f"{before_sha}\n"),  # HEAD before
            MagicMock(returncode=0, stdout="Updating...\n"),     # git pull
            MagicMock(returncode=0, stdout=f"{after_sha}\n"),   # HEAD after
            MagicMock(returncode=0, stdout=diff_output),         # git diff
        ]
        result = pull_corpus(settings.corpus_path, branch="main")

    assert result.before_sha == before_sha
    assert result.after_sha == after_sha
    assert result.changed_files == ["src/auth.ts", "README.md"]
    assert not result.up_to_date
    assert not result.error


def test_git_pull_up_to_date():
    """When HEAD doesn't change, pull_corpus returns up_to_date=True."""
    sha = "ccc333"

    with patch("src.ingestion.git_sync._run_git") as mock_git:
        mock_git.side_effect = [
            MagicMock(returncode=0, stdout=f"{sha}\n"),
            MagicMock(returncode=0, stdout="Already up to date.\n"),
            MagicMock(returncode=0, stdout=f"{sha}\n"),
        ]
        result = pull_corpus(settings.corpus_path, branch="main")

    assert result.up_to_date
    assert result.changed_files == []


def test_git_pull_not_a_repo(tmp_path):
    """pull_corpus returns an error for a directory without .git."""
    result = pull_corpus(tmp_path, branch="main")
    assert result.error
    assert "Not a git repository" in result.error


# ─────────────────────────────────────────────────────────────────────────────
# Incremental Ingestion Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_point_id_deterministic():
    """_point_id returns consistent IDs for the same (file, index) pair."""
    id1 = _point_id("src/auth.ts", 0)
    id2 = _point_id("src/auth.ts", 0)
    id3 = _point_id("src/auth.ts", 1)

    assert id1 == id2
    assert id1 != id3
    assert isinstance(id1, int)


def test_is_ingestable():
    """_is_ingestable filters correctly based on extension/ignore rules."""
    assert IngestionPipeline._is_ingestable("src/auth.ts") is True
    assert IngestionPipeline._is_ingestable("README.md") is True
    assert IngestionPipeline._is_ingestable("node_modules/pkg/index.js") is False
    assert IngestionPipeline._is_ingestable("pnpm-lock.yaml") is False
    assert IngestionPipeline._is_ingestable("photo.png") is False
    assert IngestionPipeline._is_ingestable(".env.example") is True


# ─────────────────────────────────────────────────────────────────────────────
# Webhook Tests
# ─────────────────────────────────────────────────────────────────────────────


WEBHOOK_SECRET = "test-secret-12345"


def _make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute X-Hub-Signature-256 header value for test payloads."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_verify_github_signature_valid():
    body = b'{"ref":"refs/heads/main"}'
    sig = _make_signature(body)
    assert verify_github_signature(body, sig, WEBHOOK_SECRET) is True


def test_verify_github_signature_invalid():
    body = b'{"ref":"refs/heads/main"}'
    assert verify_github_signature(body, "sha256=badhex", WEBHOOK_SECRET) is False
    assert verify_github_signature(body, "", WEBHOOK_SECRET) is False
    assert verify_github_signature(body, "not-sha256-prefix", WEBHOOK_SECRET) is False


def test_webhook_rejects_invalid_signature(client):
    """POST /webhook/github with bad HMAC returns 403."""
    with patch.object(settings, "github_webhook_secret", WEBHOOK_SECRET):
        response = client.post(
            "/webhook/github",
            json={"ref": "refs/heads/main"},
            headers={"X-Hub-Signature-256": "sha256=invalid"},
        )
    assert response.status_code == 403


def test_webhook_accepts_valid_push(client):
    """POST /webhook/github with valid HMAC + main branch returns 202."""
    payload = {"ref": "refs/heads/main"}
    body = json.dumps(payload).encode()
    sig = _make_signature(body)

    with patch.object(settings, "github_webhook_secret", WEBHOOK_SECRET), \
         patch("src.ingestion.git_sync.pull_corpus") as mock_pull, \
         patch("src.api.tasks.trigger_incremental_ingestion") as mock_ingest:

        mock_pull.return_value = GitPullResult(
            before_sha="aaa",
            after_sha="bbb",
            changed_files=["src/auth.ts"],
        )
        mock_ingest.return_value = True

        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "ingestion_started"
    assert data["changed_files"] == 1


def test_webhook_ignores_non_main_branch(client):
    """POST /webhook/github with push to a non-main branch returns 200 ignored."""
    payload = {"ref": "refs/heads/feature-xyz"}
    body = json.dumps(payload).encode()
    sig = _make_signature(body)

    with patch.object(settings, "github_webhook_secret", WEBHOOK_SECRET):
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-Hub-Signature-256": sig,
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


# ─────────────────────────────────────────────────────────────────────────────
# BM25 Thread Safety Tests
# ─────────────────────────────────────────────────────────────────────────────


def test_bm25_reload_thread_safety():
    """Concurrent reload_bm25 + retrieve calls do not raise exceptions."""
    retriever = services.get("retriever")
    if not retriever:
        retriever = Retriever()

    errors = []

    def do_retrieves(n=5):
        for _ in range(n):
            try:
                retriever.retrieve("authentication middleware", top_k=2)
            except Exception as e:
                errors.append(e)

    def do_reloads(n=2):
        for _ in range(n):
            try:
                retriever.reload_bm25()
            except Exception as e:
                errors.append(e)

    threads = [
        threading.Thread(target=do_retrieves),
        threading.Thread(target=do_reloads),
        threading.Thread(target=do_retrieves),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert errors == [], f"Thread safety errors: {errors}"
