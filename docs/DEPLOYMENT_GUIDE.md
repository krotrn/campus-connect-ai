# AEIA — Free Deployment Guide

> Deploy AEIA at **$0/month** using free-tier services. This guide covers three deployment options ranked by ease of setup.

---

## Prerequisites

- A [Google AI Studio](https://aistudio.google.com/) account (free Gemini API key)
- A [GitHub](https://github.com/) account (for repo hosting and CI)
- [Docker](https://docs.docker.com/get-docker/) installed locally (for building images)

---

## Environment Variables Reference

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key from AI Studio | — |
| `QDRANT_URL` | ✅ | Qdrant vector database URL | `http://localhost:6333` |
| `COLLECTION_NAME` | ✅ | Qdrant collection name | `campus_connect` |
| `API_KEY` | ✅ | API authentication key for endpoints | `dev-key-change-me` |
| `RATE_LIMIT` | ❌ | Request rate limit | `20/minute` |
| `CORPUS_PATH` | ❌ | Path to cloned corpus repository | `./corpus/campus-connect` |
| `LANGFUSE_PUBLIC_KEY` | ❌ | Langfuse observability public key | — |
| `LANGFUSE_SECRET_KEY` | ❌ | Langfuse observability secret key | — |
| `LANGFUSE_HOST` | ❌ | Langfuse host URL | `https://cloud.langfuse.com` |
| `GITHUB_WEBHOOK_SECRET` | ❌ | HMAC-SHA256 secret for webhook verification | — |

---

## Option 1: Render (Recommended — Easiest)

### Why Render?
- **Free tier**: 750 hours/month for web services (enough for always-on)
- **Free managed PostgreSQL** (if needed in future)
- **Auto-deploy from GitHub** on every push
- **Free Qdrant Cloud** tier pairs perfectly

### Step 1: Set Up Free Qdrant Cloud

1. Go to [Qdrant Cloud](https://cloud.qdrant.io/) and create a free account
2. Create a new **free-tier cluster** (1GB storage, shared resources)
3. Note your cluster URL (e.g., `https://abc123.us-east4-0.gcp.cloud.qdrant.io:6333`)
4. Note your API key from the cluster dashboard

### Step 2: Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Web Service**
2. Connect your GitHub repository
3. Configure the service:

| Setting | Value |
|---------|-------|
| **Name** | `aeia` |
| **Region** | Oregon (US West) or nearest |
| **Branch** | `main` |
| **Runtime** | Docker |
| **Instance Type** | Free |

4. Add environment variables:

```bash
GEMINI_API_KEY=your-gemini-api-key
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-cloud-api-key
COLLECTION_NAME=campus_connect
API_KEY=your-secure-api-key
RATE_LIMIT=20/minute
```

5. Click **Create Web Service**

### Step 3: Initial Corpus Ingestion

After deployment, trigger ingestion via the API:

```bash
# Clone corpus into the running container (one-time setup)
# Option A: Use the /ingest endpoint
curl -X POST https://aeia.onrender.com/ingest \
  -H "X-API-Key: your-secure-api-key"

# Option B: Run ingestion locally and upload to Qdrant Cloud
# (Recommended for initial setup — faster and more reliable)
git clone https://github.com/coding-pundit-nitap/campus-connect corpus/campus-connect
PYTHONPATH=. QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333 uv run python -m src.ingestion.pipeline
```

### Step 4: Verify Deployment

```bash
# Health check
curl https://aeia.onrender.com/health

# Ask a question
curl -X POST https://aeia.onrender.com/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secure-api-key" \
  -d '{"question": "Where is user authentication implemented?"}'

# Open the Web UI
# Visit: https://aeia.onrender.com/ui
```

> **Note:** Render free tier services spin down after 15 minutes of inactivity. The first request after spin-down takes ~30-60s to cold-start. This is normal for a portfolio demo.

### Render Deployment Checklist

- [ ] Qdrant Cloud free cluster created
- [ ] Render web service created with Docker runtime
- [ ] Environment variables configured
- [ ] Initial ingestion completed
- [ ] Health check passing
- [ ] Web UI accessible at `/ui`

---

## Option 2: Railway

### Why Railway?
- **$5 free credit/month** (no credit card for trial)
- Supports **Docker Compose** natively (can run Qdrant + API together)
- Simple GitHub integration
- Better cold-start times than Render

### Step 1: Deploy with Railway

1. Go to [Railway](https://railway.app/) → **New Project** → **Deploy from GitHub Repo**
2. Select your AEIA repository
3. Railway will auto-detect the Dockerfile

### Step 2: Add Qdrant Service

1. In your Railway project, click **New** → **Database** → **Docker Image**
2. Use image: `qdrant/qdrant:latest`
3. Add a volume mount: `/qdrant/storage`
4. Expose port `6333`
5. Note the internal Railway URL (e.g., `http://qdrant.railway.internal:6333`)

### Step 3: Configure Variables

In the AEIA service settings, add:

```bash
GEMINI_API_KEY=your-gemini-api-key
QDRANT_URL=http://qdrant.railway.internal:6333
COLLECTION_NAME=campus_connect
API_KEY=your-secure-api-key
RATE_LIMIT=20/minute
PORT=8000
```

### Step 4: Ingest and Verify

Same as Render Step 3 and Step 4, using your Railway URL instead.

> **Note:** Railway's free tier gives $5/month credit. A lightweight app like AEIA typically uses ~$2-3/month, well within the free allowance.

---

## Option 3: Fly.io

### Why Fly.io?
- **3 shared VMs free** (256MB RAM each)
- Global edge deployment
- Persistent volumes available

### Step 1: Install Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

### Step 2: Create fly.toml

Create a `fly.toml` in the project root:

```toml
app = "aeia"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[env]
  COLLECTION_NAME = "campus_connect"
  RATE_LIMIT = "20/minute"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1
```

### Step 3: Set Secrets and Deploy

```bash
fly secrets set GEMINI_API_KEY=your-gemini-api-key
fly secrets set QDRANT_URL=https://your-qdrant-cloud-url:6333
fly secrets set API_KEY=your-secure-api-key

fly deploy
```

### Step 4: Verify

```bash
fly status
curl https://aeia.fly.dev/health
```

> **Note:** Fly.io free tier VMs have 256MB RAM. If the embedding model causes OOM, use Qdrant Cloud (external) instead of co-hosting Qdrant on Fly.io, and consider using the `--workers 1` flag for uvicorn.

---

## Option 4: Local Docker (Development & Demos)

For local development or in-person demos:

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/aeia.git
cd aeia

# 2. Create .env file
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# 3. Start everything with Docker Compose
docker compose up -d

# 4. Clone and ingest the corpus
git clone https://github.com/coding-pundit-nitap/campus-connect corpus/campus-connect
PYTHONPATH=. uv run python -m src.ingestion.pipeline

# 5. Verify
curl http://localhost:8000/health

# 6. Open Web UI
# Visit: http://localhost:8000/ui
```

---

## Free Qdrant Cloud Setup (Detailed)

All cloud deployment options (Render, Railway, Fly.io) benefit from using **Qdrant Cloud free tier** as the vector database:

1. Visit [cloud.qdrant.io](https://cloud.qdrant.io/)
2. Sign up (free, no credit card)
3. Click **Create Cluster**:
   - **Name**: `aeia-prod`
   - **Cloud Provider**: GCP or AWS
   - **Region**: Choose closest to your deployment
   - **Plan**: Free (1GB storage, 1M vectors)
4. After creation, go to **Data Access Management** → **API Keys**
5. Create a new API key and save it securely
6. Your `QDRANT_URL` will be: `https://YOUR_CLUSTER_ID.REGION.gcp.cloud.qdrant.io:6333`

> **Important:** The free tier includes 1GB storage and supports up to 1M vectors — more than enough for AEIA's ~94K LOC corpus.

---

## Updating the Deployment

### Automatic (Recommended)

All three cloud platforms support **auto-deploy on push to main**:
- **Render**: Enabled by default when connected to GitHub
- **Railway**: Enabled by default when connected to GitHub
- **Fly.io**: Set up via `fly deploy` in GitHub Actions

### GitHub Actions CI/CD (Fly.io)

Add to `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Fly.io
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

---

## Cost Summary

| Component | Service | Free Tier Limit | AEIA Usage |
|-----------|---------|-----------------|------------|
| **API Server** | Render / Railway / Fly.io | 750 hrs or $5/mo or 3 VMs | Well within limits |
| **Vector DB** | Qdrant Cloud | 1GB / 1M vectors | ~500 vectors |
| **LLM** | Google Gemini (AI Studio) | 1,500 req/day (Flash) | Well within limits |
| **Embeddings** | BGE-small (local FastEmbed) | Unlimited (runs locally) | Zero cost |
| **Observability** | Langfuse Cloud (optional) | 50K observations/mo | Optional |
| **CI/CD** | GitHub Actions | 2,000 min/mo | Minimal usage |
| | | **Total Monthly Cost** | **$0.00** |

---

## Troubleshooting

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `503 Service Unavailable` on first request | Service is cold-starting (Render free tier) | Wait 30-60s and retry |
| `ConnectionRefusedError: Qdrant` | Qdrant URL misconfigured | Verify `QDRANT_URL` env var matches your Qdrant Cloud cluster URL |
| `401 Unauthorized` | Missing or wrong API key | Check `X-API-Key` header matches `API_KEY` env var |
| `429 Too Many Requests` | Gemini rate limit hit | Wait and retry; free tier has 1,500 req/day limit |
| OOM on Fly.io | 256MB RAM insufficient for embeddings | Use Qdrant Cloud externally; reduce `--workers` to 1 |
| Ingestion fails | Corpus not cloned | Run `git clone` for corpus first, then trigger `/ingest` |

### Checking Logs

```bash
# Render
# View logs in Render Dashboard → Your Service → Logs

# Railway
railway logs

# Fly.io
fly logs

# Docker (local)
docker compose logs -f api
```

---

## Recommended Setup for Portfolio Demo

> **TL;DR**: Use **Render + Qdrant Cloud** — it's the fastest path to a working live demo URL.

1. **Qdrant Cloud** free tier for vector storage (persistent, no spin-down)
2. **Render** free tier for the API (auto-deploys from GitHub)
3. Run **initial ingestion locally** pointing at Qdrant Cloud (faster and more reliable)
4. Add the live URL to your README as a badge:
   ```markdown
   [![Live Demo](https://img.shields.io/badge/Live_Demo-aeia.onrender.com-blue?style=for-the-badge)](https://aeia.onrender.com/ui)
   ```
5. Add the live URL to your resume next to the project title
