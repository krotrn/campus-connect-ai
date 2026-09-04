# Post-Mortem: Semantic Bias in Config File Retrieval

## Date
2026-09-03 → 2026-09-05

## Summary

During V2 evaluation, 4 out of 20 golden test queries consistently failed to retrieve the correct source files. Investigation revealed that embedding models (BGE-small-en-v1.5) treat raw YAML, SQL DDL, and dotenv KEY=VALUE content as semantically opaque — they cannot connect natural-language queries ("What services depend on Redis?") to infrastructure config syntax (`redis: image: redis:8.2.1-alpine`).

## Timeline

### Day 1 (2026-09-03): V1 → V2 Migration

**14:00** — V1 baseline established: Recall@5 70.0%, MRR 0.638

**15:00** — Implemented hybrid BM25 + dense retrieval with RRF
- **Result**: Recall@5 improved to 75.0%, but MRR dropped to 0.464
- **Root cause**: Equal-weight RRF punished docs ranked #1 by dense when BM25 disagreed

**15:30** — Tested cross-encoder reranking (FlashRank, ms-marco-MiniLM-L-12-v2)
- **Result**: All metrics degraded. Recall@10: 85% → 80%, MRR: 0.638 → 0.455, Latency: 43ms → 1453ms
- **Root cause**: Web-trained cross-encoder actively downranks code chunks

**16:00** — Switched to weighted RRF (dense 0.7, BM25 0.3)
- **Result**: Recall@10 recovered to 80.0%, MRR to 0.470

**16:30** — Deep investigation of 4 persistent misses

### Investigation Findings

#### q005: `.env.example` — Corpus Gap
```
Path('.env.example').suffix → ""  (empty string!)
```
The Python `pathlib` library treats `.env` as the file stem, not the extension. The `ALLOWED_EXTENSIONS` filter silently dropped the file.

**Fix**: Added `ALLOWED_FILENAMES` allowlist for dotfiles.

#### q007, q018: Redis / MinIO in compose files — Semantic Gap

The `compose.yml` chunk containing the Redis service definition:
```yaml
redis:
  image: redis:8.2.1-alpine
  container_name: campus_connect_redis
```

Was ranked **#11** for the query "What services depend on Redis?" — far below TypeScript files that *import* Redis:
```typescript
import Redis from "ioredis";  // ← BGE-small understands this as "Redis-related"
```

**Root cause**: YAML syntax has no semantic signal. BGE-small's training data contains very few YAML infrastructure files, so the embedding space places YAML blocks far from natural-language Redis queries.

**Embedding space visualization**:
```
Query: "What depends on Redis?"
  → near: TypeScript imports (redis.ts, redis-connection.ts)
  → far:  YAML service blocks (compose.yml redis:)
```

#### q008: SQL Migration — Semantic Gap

The migration SQL:
```sql
CREATE TABLE "BatchDeliveryStatus" (
    "current_milestone" "BatchMilestone" NOT NULL DEFAULT 'PACKING',
```

Was ranked **#3** (docs about milestones ranked higher) for "Which migration added batch delivery and tracking milestones?"

**Root cause**: SQL DDL syntax (`CREATE TABLE`, column definitions) doesn't semantically match the natural-language concept of "adding batch delivery milestones". The docs that *describe* the feature in prose rank higher.

### Day 2: Semantic Prefix Fix

**Solution**: Prepend human-readable context headers to config files during chunking:

```
# Docker Compose infrastructure definition: compose.yml
# This file defines the services, networks, and volumes
# for the application stack including databases, caches, object storage, and workers.
redis:
  image: redis:8.2.1-alpine
```

The prefix gives BGE-small a semantic anchor — it now understands the chunk is about "infrastructure services" and "databases, caches, object storage".

**After re-ingestion with prefixes**:

| Metric | V1 | V2 Final | Δ |
|--------|-----|---------|---|
| Recall@5 | 70.0% | **85.0%** | **+15%** |
| Recall@10 | 85.0% | **95.0%** | **+10%** |
| MRR | 0.638 | 0.588 | −8% |

Fixed queries:
- ✅ q005 (.env.example) — now Rank 1
- ✅ q008 (batch migration) — now Rank 2
- ⚠️ q007 (Redis) — improved to Rank 8 (was #11)
- ❌ q018 (object storage) — still missed

## Lessons Learned

1. **Embedding models have blind spots for config syntax**. YAML, SQL DDL, and KEY=VALUE formats are underrepresented in training data. Always test retrieval with config-file queries.

2. **Cross-encoder rerankers trained on web data hurt code RAG**. `ms-marco-MiniLM-L-12-v2` assumes passage-style text, not source code. Don't assume "reranking always helps."

3. **Equal-weight RRF is dangerous for code**. BM25 on code is noisy (camelCase, imports, package names). Give dense search the majority weight.

4. **`.suffix` in Python treats dotfiles as extensionless**. `Path('.env.example').suffix` returns `""`. Always test ingestion with edge-case filenames.

5. **Semantic prefixes are a cheap, powerful fix**. 2-3 lines of natural language before raw config content dramatically improves embedding quality for free.

## Open Questions

- q018 (MinIO/object storage) is still missed. The compose prefix mentions "object storage" generically, but `file-upload.service.ts` (which uses S3Client) still ranks higher. Possible fix: service-specific prefixes extracted from YAML labels.
- MRR regression (0.638 → 0.588) remains. BM25 occasionally demotes V1's top-1 hits. Consider removing BM25 entirely if MRR is prioritized over Recall.
