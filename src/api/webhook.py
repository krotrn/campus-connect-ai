"""
GitHub webhook handler for automatic corpus pull + incremental ingestion.

Validates incoming GitHub push events using HMAC-SHA256 signatures,
runs ``git pull`` on the corpus, and triggers delta-only re-ingestion
for changed files.
"""

import hashlib
import hmac

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.config import settings


def verify_github_signature(
    payload_body: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """Validate the ``X-Hub-Signature-256`` header against the payload.

    GitHub sends ``sha256=<hex-digest>``; we recompute it and compare
    using a constant-time comparison to prevent timing attacks.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


async def handle_github_webhook(request: Request):
    """Process a GitHub push webhook.

    1. Validate HMAC-SHA256 signature.
    2. Check that the push targets ``refs/heads/main``.
    3. Run ``git pull`` on the corpus directory.
    4. Trigger incremental ingestion for the changed files.
    5. Return 202 Accepted with before/after commit SHAs.
    """
    # ── Signature validation ──────────────────────────────────────────────
    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GITHUB_WEBHOOK_SECRET is not configured on the server.",
        )

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_github_signature(body, signature, settings.github_webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature.",
        )

    # ── Parse payload ─────────────────────────────────────────────────────
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload.",
        )

    ref = payload.get("ref", "")
    if ref != "refs/heads/main":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ignored",
                "message": f"Push to '{ref}' ignored (only refs/heads/main triggers ingestion).",
            },
        )

    # ── Git pull (run in executor to avoid blocking the event loop) ────
    import asyncio
    from src.ingestion.git_sync import pull_corpus

    loop = asyncio.get_running_loop()
    pull_result = await loop.run_in_executor(
        None, pull_corpus, settings.corpus_path, "main"
    )

    if pull_result.error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Git pull failed: {pull_result.error}",
        )

    if pull_result.up_to_date:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "up_to_date",
                "message": "Corpus already up to date, no ingestion needed.",
                "sha": pull_result.after_sha,
            },
        )

    # ── Trigger incremental ingestion ─────────────────────────────────────
    from src.api.tasks import trigger_incremental_ingestion

    started = await trigger_incremental_ingestion(pull_result.changed_files)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "ingestion_started",
            "before_sha": pull_result.before_sha,
            "after_sha": pull_result.after_sha,
            "changed_files": len(pull_result.changed_files),
            "ingestion_queued": started,
        },
    )
