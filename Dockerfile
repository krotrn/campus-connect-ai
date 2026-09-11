FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1

# git is required at runtime: the agent's git_history / git_commit tools and the
# webhook's corpus sync all shell out to it against the mounted corpus.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install locked dependencies
RUN uv sync --frozen --no-dev

# Copy application source code
COPY src/ ./src/

# The corpus is a runtime input, not a build artifact: mount it as a volume
# (see compose.yml). Create the mount point so a missing volume fails loudly
# at the corpus check rather than at an unexpected path error.
RUN mkdir -p /app/corpus /app/.cache

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# The base image has no curl/wget, so probe with the interpreter that is present.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["uv", "run", "python", "-c", \
         "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status==200 else 1)"]

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
